from .common import *
from .complete_order import CompleteOrderUseCase


MOMO_TERMINAL_FAILURE_CODES = {1001, 1002, 1003, 1004, 1005, 1006, 1007, 1017, 1026}


def is_momo_terminal_failure(result: dict | None) -> bool:
    if not result or result.get("resultCode") is None:
        return False
    try:
        result_code = int(result["resultCode"])
    except (TypeError, ValueError):
        return False
    return result_code in MOMO_TERMINAL_FAILURE_CODES


class PaymentUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._momo_gateway = MoMoSandboxGateway()
        self._sepay_gateway = SePayPaymentGateway()
        self._zalopay_gateway = ZaloPaySandboxGateway()

    async def _order_accepts_successful_payment(self, order_id: UUID) -> bool:
        order = await commerce_repo.get_order_for_update(self._session, order_id)
        return bool(order and order.status == "PENDING")

    async def _mark_order_payment_failed_if_pending(self, order_id: UUID, *, internal_note: str, changed_by: str) -> None:
        order = await commerce_repo.get_order_for_update(self._session, order_id)
        if order is None or order.status != "PENDING":
            return
        await CompleteOrderUseCase(session=self._session).execute(
            order_id=order_id,
            status_value="PAYMENT_FAILED",
            internal_note=internal_note,
            changed_by=changed_by,
        )


    async def get_status(self, payment_id: UUID) -> PaymentStatusResponse:
        payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
        order = await self._session.get(Order, payment.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")

        momo_result = None
        if payment.status == "PENDING" and payment.provider == "MOMO":
            try:
                momo_result = await self._momo_gateway.query_payment(
                    order_code=payment.transaction_ref,
                    request_id=str(payment.id),
                )
            except Exception as e:
                import logging
                logger = logging.getLogger("uvicorn.error")
                logger.error("Lỗi khi đối soát tự động MoMo: %s", e)

        now = datetime.now(timezone.utc)
        if momo_result and momo_result.get("resultCode") == 0 and order.status == "PENDING":
            await self._session.rollback()
            async with self._session.begin():
                payment = await commerce_repo.get_payment_transaction_by_id_for_update(self._session, payment_id)
                if payment is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
                if payment.status == "PENDING":
                    payment.status = "PAID"
                    payment.paid_at = now
                    payment.raw_response = {**(payment.raw_response or {}), "query_api": momo_result}
                    commerce_repo.save_model(self._session, payment)
                    await CompleteOrderUseCase(session=self._session).execute(
                        order_id=payment.order_id,
                        status_value="PAID",
                        internal_note="Xác nhận thanh toán qua đối soát API MoMo.",
                        changed_by="momo-query-api",
                    )
            payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
            order = await self._session.get(Order, payment.order_id)

        elif payment.status == "PENDING" and is_momo_terminal_failure(momo_result):
            await self._session.rollback()
            async with self._session.begin():
                payment = await commerce_repo.get_payment_transaction_by_id_for_update(
                    self._session,
                    payment_id,
                )
                if payment is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Không tìm thấy giao dịch thanh toán.",
                    )
                if payment.status == "PENDING":
                    result_code = int(momo_result["resultCode"])
                    failure_message = str(
                        momo_result.get("message") or f"MoMo resultCode={result_code}"
                    )
                    payment.status = "FAILED"
                    payment.failed_at = now
                    payment.raw_response = {
                        **(payment.raw_response or {}),
                        "query_api": momo_result,
                        "failure_message": failure_message,
                    }
                    commerce_repo.save_model(self._session, payment)
                    await self._mark_order_payment_failed_if_pending(
                        order_id=payment.order_id,
                        internal_note=f"Đối soát MoMo xác nhận thanh toán thất bại: resultCode={result_code}.",
                        changed_by="momo-query-api",
                    )
            payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
            order = await self._session.get(Order, payment.order_id)

        elif payment.status == "PENDING" and payment.expires_at and payment.expires_at <= now:
            await self._session.rollback()
            async with self._session.begin():
                payment = await commerce_repo.get_payment_transaction_by_id_for_update(self._session, payment_id)
                if payment is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
                if payment.status == "PENDING":
                    payment.status = "EXPIRED"
                    payment.failed_at = now
                    payment.raw_response = {
                        **(payment.raw_response or {}),
                        "failure_message": "Phiên thanh toán đã hết hạn.",
                    }
                    commerce_repo.save_model(self._session, payment)
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note="Phiên thanh toán đã hết hạn.",
                    changed_by="payment-expirer",
                )
            payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
            order = await self._session.get(Order, payment.order_id)
        raw_response = payment.raw_response or {}
        return PaymentStatusResponse(
            id=payment.id,
            order_id=payment.order_id,
            order_code=order.order_code,
            order_status=order.status,
            provider=payment.provider,
            amount=Decimal(payment.amount),
            status=payment.status,
            attempt_number=payment.attempt_number,
            checkout_url=payment.checkout_url,
            checkout_method=raw_response.get("checkout_method"),
            checkout_fields=raw_response.get("checkout_fields") if isinstance(raw_response.get("checkout_fields"), dict) else {},
            expires_at=payment.expires_at.isoformat() if payment.expires_at else None,
            paid_at=payment.paid_at.isoformat() if payment.paid_at else None,
            failure_message=raw_response.get("failure_message"),
        )

    async def cancel(self, payment_id: UUID) -> PaymentStatusResponse:
        now = datetime.now(timezone.utc)
        async with self._session.begin():
            payment = await commerce_repo.get_payment_transaction_by_id_for_update(self._session, payment_id)
            if payment is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
            order = await commerce_repo.get_order_for_update(self._session, payment.order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if payment.status in {"PAID", "REFUNDED"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giao dịch đã hoàn tất, không thể hủy.")
            if payment.status == "PENDING":
                payment.status = "FAILED"
                payment.failed_at = now
                payment.raw_response = {
                    **(payment.raw_response or {}),
                    "failure_message": "Khách hàng đã hủy phiên thanh toán.",
                }
                commerce_repo.save_model(self._session, payment)
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note="Khách hàng đã hủy phiên thanh toán.",
                    changed_by="payment-cancelled-by-customer",
                )
        return await self.get_status(payment_id)

    async def retry(self, payment_id: UUID) -> PaymentStatusResponse:
        # Giai đoạn 1: Đọc và kiểm tra điều kiện ban đầu trong một transaction ngắn
        async with self._session.begin():
            previous = await commerce_repo.get_payment_transaction(self._session, payment_id)
            if previous is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
            order = await commerce_repo.get_order_for_update(self._session, previous.order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if order.payment_status == "PAID":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng đã được thanh toán.")
            if order.status != "PENDING":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng không còn chờ thanh toán.")

            # 1. Kiểm tra chéo tồn kho (Reservation Check)
            has_shippable_items = await self._session.scalar(
                text(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM order_items
                        WHERE order_id = :order_id AND used_device_id IS NULL
                    )
                    """
                ),
                {"order_id": order.id},
            )
            if has_shippable_items:
                has_active_reservations = await self._session.scalar(
                    text(
                        """
                        SELECT EXISTS(
                            SELECT 1 FROM inventory_reservations
                            WHERE order_id = :order_id AND status = 'ACTIVE'
                        )
                        """
                    ),
                    {"order_id": order.id},
                )
                if not has_active_reservations:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Phiếu giữ chỗ tồn kho của đơn hàng đã hết hạn hoặc bị giải phóng. Vui lòng tạo đơn hàng mới."
                    )

            # 2. Kiểm tra chéo Voucher (Voucher Validation)
            if order.voucher_code:
                voucher = await commerce_repo.get_active_voucher(self._session, order.voucher_code)
                if not voucher:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Voucher áp dụng cho đơn hàng không còn tồn tại hoặc đã bị tắt."
                    )
                now_utc = datetime.now(timezone.utc)
                if voucher.starts_at and voucher.starts_at > now_utc:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Voucher áp dụng cho đơn hàng chưa đến thời gian hiệu lực."
                    )
                if voucher.ends_at and voucher.ends_at < now_utc:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Voucher áp dụng cho đơn hàng đã hết hạn sử dụng."
                    )

            provider = previous.provider
            order_code = order.order_code
            total_amount = order.total_amount
            user_id = order.user_id
            order_id = order.id

            latest = await commerce_repo.get_latest_payment_transaction(self._session, order.id)
            next_attempt = (latest.attempt_number if latest else 0) + 1

        # Giai đoạn 2: Gọi API gateway ở ngoài transaction để tránh giữ khóa DB lâu và tránh kẹt trạng thái đơn hàng khi API lỗi
        now = datetime.now(timezone.utc)
        payment_id_new = uuid4()
        if provider == "MOMO":
            provider_order_id = f"{order_code}-{next_attempt}"
            payment_init = await self._momo_gateway.create_payment(
                order_code=provider_order_id,
                amount=Decimal(total_amount),
                order_info=f"Thanh toán lại đơn hàng {order_code}",
                extra_data={"orderCode": order_code, "attempt": next_attempt},
                request_id=str(payment_id_new),
            )
            timeout_minutes = settings.momo_payment_timeout_minutes
        elif provider == "ZALOPAY":
            vietnam_date = datetime.now(timezone(timedelta(hours=7))).strftime("%y%m%d")
            provider_order_id = f"{vietnam_date}_{order_code[-10:]}{next_attempt:02d}"
            payment_init = await self._zalopay_gateway.create_payment(
                app_trans_id=provider_order_id,
                amount=Decimal(total_amount),
                app_user=str(user_id or "electromart-sandbox"),
                description=f"ElectroMart Sandbox - Thanh toán lại đơn hàng {order_code}",
                callback_url=settings.zalopay_callback_url,
                redirect_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}",
            )
            timeout_minutes = settings.zalopay_payment_timeout_minutes
        elif provider == "SEPAY":
            provider_order_id = f"{order_code}-{next_attempt}"
            payment_init = self._sepay_gateway.create_checkout(
                order_invoice_number=provider_order_id,
                order_amount=Decimal(total_amount),
                order_description=f"Thanh toán lại đơn hàng {order_code}",
                success_url=f"{settings.frontend_url.rstrip('/')}/orders/{order_id}?payment=success",
                error_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}?payment=error",
                cancel_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}?payment=cancel",
                customer_id=str(user_id) if user_id else None,
            )
            timeout_minutes = settings.sepay_payment_timeout_minutes
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cổng thanh toán không hỗ trợ thử lại.")
        
        expires_at = now + timedelta(minutes=timeout_minutes)

        # Giai đoạn 3: Thực hiện cập nhật DB trong transaction thứ hai (đã có kết quả gateway thành công)
        async with self._session.begin():
            # Lock order lần nữa để tránh race condition trong thời gian gọi API gateway
            order_lock = await commerce_repo.get_order_for_update(self._session, order_id)
            if order_lock is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if order_lock.payment_status == "PAID":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng đã được thanh toán.")
            if order_lock.status != "PENDING":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng không còn chờ thanh toán.")

            # Hủy/Đánh dấu THẤT BẠI các giao dịch thanh toán PENDING cũ của đơn hàng
            await self._session.execute(
                text(
                    """
                    UPDATE payment_transactions
                    SET status = 'FAILED', failed_at = NOW(),
                        raw_response = raw_response || '{"failure_message": "Bị hủy do khởi tạo phiên thanh toán mới."}'::jsonb
                    WHERE order_id = :order_id AND status = 'PENDING'
                    """
                ),
                {"order_id": order_id}
            )

            payment = PaymentTransaction(
                id=payment_id_new,
                order_id=order_id,
                provider=provider,
                amount=total_amount,
                status="PENDING",
                transaction_ref=provider_order_id,
                checkout_url=payment_init.checkout_url,
                attempt_number=next_attempt,
                expires_at=expires_at,
                raw_response=payment_init.raw_response or {},
            )
            commerce_repo.save_model(self._session, payment)
            
        return await self.get_status(payment_id_new)

    async def process_sepay_ipn(self, payload: dict, *, secret_key: str | None) -> dict:
        import re

        # 1. Trích xuất mã đơn hàng bằng Regex từ các trường payload (hỗ trợ cả EMV và EC)
        order_code = ""
        for field_name in ["code", "transactionContent", "transaction_content", "content", "description", "body", "order_invoice_number", "invoice_number", "order_id", "orderCode"]:
            field_val = payload.get(field_name)
            if field_val and isinstance(field_val, str):
                match = re.search(r"EMV[0-9]{6,12}|EC[0-9A-Z]{10}", field_val.upper())
                if match:
                    order_code = match.group(0)
                    break

        # 2. Lấy invoice_number (SePay Checkout Link) nếu có
        invoice_number = str(
            payload.get("order_invoice_number")
            or payload.get("invoice_number")
            or payload.get("order_id")
            or payload.get("orderCode")
            or ""
        )

        # Nếu không trích xuất được cả order_code lẫn invoice_number, ném lỗi
        if not order_code and not invoice_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu mã đơn SePay hoặc nội dung chuyển tiền không chứa mã đơn hàng.")

        signature_valid = self._sepay_gateway.verify_ipn_secret(secret_key)

        # Tạo event_key duy nhất dựa trên ID giao dịch để tránh xử lý trùng lặp
        transaction_id = str(
            payload.get("id")
            or payload.get("transaction_id")
            or payload.get("sepay_transaction_id")
            or payload.get("reference_id")
            or ""
        )
        event_key = ":".join(
            [
                invoice_number or order_code,
                transaction_id,
                str(payload.get("event_type") or payload.get("order_status") or payload.get("status") or ""),
            ]
        )

        # Thử tìm PaymentTransaction bằng invoice_number trước (SePay Checkout Link)
        payment = None
        if invoice_number:
            payment = await commerce_repo.get_payment_transaction_by_reference_for_update(
                self._session,
                provider="SEPAY",
                transaction_ref=invoice_number,
            )

        # Nếu không tìm thấy, thử tìm qua mã đơn hàng trích xuất bằng Regex (Chuyển khoản Ngân hàng Trực tiếp)
        if payment is None and order_code:
            from app.infrastructure.database.repositories import order_repo
            order_id = await order_repo.get_order_id_by_code(self._session, order_code)
            if order_id:
                # Lấy giao dịch thanh toán gần nhất của đơn hàng
                payment = await commerce_repo.get_latest_payment_transaction(self._session, order_id)

                # Nếu chưa tồn tại giao dịch thanh toán (khách chuyển khoản trực tiếp bằng ngân hàng)
                if payment is None:
                    order = await self._session.get(Order, order_id)
                    if order:
                        from datetime import timedelta
                        payment = PaymentTransaction(
                            id=uuid4(),
                            order_id=order.id,
                            provider="SEPAY",
                            amount=order.total_amount,
                            status="PENDING",
                            transaction_ref=order_code,
                            attempt_number=1,
                            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                            raw_response={"note": "Tự động tạo từ Webhook chuyển khoản trực tiếp SePay"},
                        )
                        commerce_repo.save_model(self._session, payment)
                        await self._session.flush()
                else:
                    payment = await commerce_repo.get_payment_transaction_by_id_for_update(
                        self._session,
                        payment.id,
                    )

        event_id = uuid4()
        inserted = await commerce_repo.create_webhook_event(
            self._session,
            event_id=event_id,
            provider="SEPAY",
            event_key=event_key,
            order_id=payment.order_id if payment else None,
            payment_transaction_id=payment.id if payment else None,
            signature_valid=signature_valid,
            payload=payload,
        )
        if not inserted:
            await self._session.rollback()
            return {"success": True, "duplicate": True}
        if not signature_valid:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Secret key IPN SePay không hợp lệ.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Secret key IPN không hợp lệ.")
        if payment is None:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Không tìm thấy giao dịch SePay.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch SePay.")

        # Lấy số tiền thực nhận (hỗ trợ các trường của chuyển khoản ngân hàng SePay như transferAmount, amountIn)
        paid_amount = Decimal(
            str(
                payload.get("transferAmount")
                or payload.get("amountIn")
                or payload.get("order_amount")
                or payload.get("amount")
                or payload.get("transaction_amount")
                or payload.get("total_amount")
                or 0
            )
        )
        if paid_amount < Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền IPN SePay không đủ so với giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền thanh toán không đủ.")
        else:
            payment.amount = paid_amount # Ghi nhận số tiền thực tế khách đã chuyển khoản

        if payment.status != "PENDING":
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
                error_message=f"Giao dịch không còn ở trạng thái PENDING (trạng thái hiện tại: {payment.status}).",
            )
            await self._session.commit()
            return {"success": True, "duplicate": True}

        event_type = str(payload.get("event_type") or payload.get("order_status") or payload.get("status") or "").upper()
        transfer_type = str(payload.get("transferType") or "").lower()
        amount_in = Decimal(str(payload.get("amountIn") or 0))
        if not event_type and (transfer_type == "in" or amount_in > 0):
            event_type = "PAID"

        now = datetime.now(timezone.utc)
        payment.raw_response = {**(payment.raw_response or {}), "ipn": payload}
        class AsyncNullContext:
            async def __aenter__(self): return None
            async def __aexit__(self, exc_type, exc_val, exc_tb): return False

        if event_type in {"ORDER_PAID", "PAID", "SUCCESS", "SUCCEEDED"}:
            if not await self._order_accepts_successful_payment(payment.order_id):
                payment.status = "PAID_LATE"
                payment.paid_at = now
                commerce_repo.save_model(self._session, payment)
                await commerce_repo.finish_webhook_event(
                    self._session,
                    event_id=event_id,
                    processing_status="WARNING",
                    error_message="Khách thanh toán trễ, đơn hàng đã bị hủy hoặc thất bại trước đó.",
                )
                await self._session.commit()
                return {"success": True, "duplicate": True}

            ctx = self._session.begin() if not self._session.in_transaction() else AsyncNullContext()
            async with ctx:
                payment.status = "PAID"
                payment.paid_at = now
                commerce_repo.save_model(self._session, payment)
                await commerce_repo.finish_webhook_event(
                    self._session,
                    event_id=event_id,
                    processing_status="PROCESSED",
                )
                await CompleteOrderUseCase(session=self._session).execute(
                    order_id=payment.order_id,
                    status_value="PAID",
                    internal_note="SePay IPN xác nhận thanh toán thành công.",
                    changed_by="sepay-ipn",
                )
        else:
            ctx = self._session.begin() if not self._session.in_transaction() else AsyncNullContext()
            async with ctx:
                payment.status = "FAILED"
                payment.failed_at = now
                payment.raw_response = {
                    **payment.raw_response,
                    "failure_message": str(payload.get("message") or f"SePay event={event_type}"),
                }
                commerce_repo.save_model(self._session, payment)
                await commerce_repo.finish_webhook_event(
                    self._session,
                    event_id=event_id,
                    processing_status="PROCESSED",
                )
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note=f"SePay IPN báo thanh toán thất bại: {event_type or 'UNKNOWN'}.",
                    changed_by="sepay-ipn",
                )
        if self._session.in_transaction():
            await self._session.commit()
        return {"success": True, "duplicate": False}


    async def process_momo_ipn(self, payload: dict) -> dict:
        provider_order_id = str(payload.get("orderId") or "")
        if not provider_order_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu orderId.")
        signature_valid = self._momo_gateway.verify_ipn_signature(payload)
        event_key = ":".join(
            [
                str(payload.get("partnerCode") or ""),
                provider_order_id,
                str(payload.get("requestId") or ""),
                str(payload.get("transId") or ""),
                str(payload.get("resultCode") or ""),
            ]
        )
        payment = await commerce_repo.get_payment_transaction_by_reference_for_update(
            self._session,
            provider="MOMO",
            transaction_ref=provider_order_id,
        )
        order_id = payment.order_id if payment else None
        event_id = uuid4()
        inserted = await commerce_repo.create_webhook_event(
            self._session,
            event_id=event_id,
            provider="MOMO",
            event_key=event_key,
            order_id=order_id,
            payment_transaction_id=payment.id if payment else None,
            signature_valid=signature_valid,
            payload=payload,
        )
        if not inserted:
            await self._session.rollback()
            return {"ok": True, "duplicate": True}
        if not signature_valid:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Chữ ký IPN MoMo không hợp lệ.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chữ ký IPN không hợp lệ.")
        if order_id is None or payment is None:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Không tìm thấy đơn hàng hoặc giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch.")
        if Decimal(str(payload.get("amount") or 0)) != Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền IPN không khớp giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền thanh toán không khớp.")
        if payment.status != "PENDING":
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
                error_message=f"Giao dịch không còn ở trạng thái PENDING (trạng thái hiện tại: {payment.status}).",
            )
            await self._session.commit()
            return {"ok": True, "duplicate": True}

        result_code = int(payload.get("resultCode")) if payload.get("resultCode") is not None else -1
        now = datetime.now(timezone.utc)
        payment.raw_response = {**(payment.raw_response or {}), "ipn": payload}
        class AsyncNullContext:
            async def __aenter__(self): return None
            async def __aexit__(self, exc_type, exc_val, exc_tb): return False

        if result_code == 0:
            if not await self._order_accepts_successful_payment(order_id):
                payment.status = "PAID_LATE"
                payment.paid_at = now
                commerce_repo.save_model(self._session, payment)
                await commerce_repo.finish_webhook_event(
                    self._session,
                    event_id=event_id,
                    processing_status="WARNING",
                    error_message="Khách thanh toán trễ, đơn hàng đã bị hủy hoặc thất bại trước đó.",
                )
                await self._session.commit()
                return {"ok": True, "duplicate": True}

            ctx = self._session.begin() if not self._session.in_transaction() else AsyncNullContext()
            async with ctx:
                payment.status = "PAID"
                payment.paid_at = now
                commerce_repo.save_model(self._session, payment)
                await commerce_repo.finish_webhook_event(
                    self._session,
                    event_id=event_id,
                    processing_status="PROCESSED",
                )
                await CompleteOrderUseCase(session=self._session).execute(
                    order_id=order_id,
                    status_value="PAID",
                    internal_note="MoMo Sandbox IPN xác nhận thanh toán thành công.",
                    changed_by="momo-sandbox-ipn",
                )
        else:
            ctx = self._session.begin() if not self._session.in_transaction() else AsyncNullContext()
            async with ctx:
                payment.status = "FAILED"
                payment.failed_at = now
                payment.raw_response = {
                    **payment.raw_response,
                    "failure_message": str(payload.get("message") or f"MoMo resultCode={result_code}"),
                }
                commerce_repo.save_model(self._session, payment)
                await commerce_repo.finish_webhook_event(
                    self._session,
                    event_id=event_id,
                    processing_status="PROCESSED",
                )
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note=f"MoMo IPN báo thanh toán thất bại: resultCode={result_code}.",
                    changed_by="momo-sandbox-ipn",
                )
        if self._session.in_transaction():
            await self._session.commit()
        return {"ok": True, "duplicate": False}


    async def process_zalopay_callback(self, payload: dict) -> dict:
        callback_data = str(payload.get("data") or "")
        callback_mac = str(payload.get("mac") or "")
        if not self._zalopay_gateway.verify_callback(callback_data, callback_mac):
            return {"return_code": -1, "return_message": "mac not equal"}
        try:
            data = json.loads(callback_data)
        except ValueError:
            return {"return_code": 0, "return_message": "callback data invalid"}
        app_trans_id = str(data.get("app_trans_id") or "")
        payment = await commerce_repo.get_payment_transaction_by_reference_for_update(
            self._session,
            provider="ZALOPAY",
            transaction_ref=app_trans_id,
        )
        event_id = uuid4()
        event_key = f"{app_trans_id}:{data.get('zp_trans_id', '')}"
        inserted = await commerce_repo.create_webhook_event(
            self._session,
            event_id=event_id,
            provider="ZALOPAY",
            event_key=event_key,
            order_id=payment.order_id if payment else None,
            payment_transaction_id=payment.id if payment else None,
            signature_valid=True,
            payload=payload,
        )
        if not inserted:
            await self._session.rollback()
            return {"return_code": 2, "return_message": "duplicate"}
        if payment is None:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Không tìm thấy giao dịch ZaloPay.",
            )
            await self._session.commit()
            return {"return_code": 0, "return_message": "payment not found"}
        if Decimal(str(data.get("amount") or 0)) != Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền callback không khớp giao dịch.",
            )
            await self._session.commit()
            return {"return_code": -1, "return_message": "amount not equal"}
        if payment.status != "PENDING":
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
                error_message=f"Giao dịch không còn ở trạng thái PENDING (trạng thái hiện tại: {payment.status}).",
            )
            await self._session.commit()
            return {"return_code": 2, "return_message": "duplicate"}

        if not await self._order_accepts_successful_payment(payment.order_id):
            payment.status = "PAID_LATE"
            payment.paid_at = datetime.now(timezone.utc)
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="WARNING",
                error_message="Khách thanh toán trễ, đơn hàng đã bị hủy hoặc thất bại trước đó.",
            )
            await self._session.commit()
            return {"return_code": 1, "return_message": "success"}

        class AsyncNullContext:
            async def __aenter__(self): return None
            async def __aexit__(self, exc_type, exc_val, exc_tb): return False

        ctx = self._session.begin() if not self._session.in_transaction() else AsyncNullContext()
        async with ctx:
            payment.status = "PAID"
            payment.paid_at = datetime.now(timezone.utc)
            payment.transaction_ref = app_trans_id
            payment.raw_response = {
                **(payment.raw_response or {}),
                "callback": data,
                "zp_trans_id": data.get("zp_trans_id"),
            }
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await CompleteOrderUseCase(session=self._session).execute(
                order_id=payment.order_id,
                status_value="PAID",
                internal_note="ZaloPay Sandbox callback xác nhận thanh toán thành công.",
                changed_by="zalopay-sandbox-callback",
            )

        if self._session.in_transaction():
            await self._session.commit()
        return {"return_code": 1, "return_message": "success"}
