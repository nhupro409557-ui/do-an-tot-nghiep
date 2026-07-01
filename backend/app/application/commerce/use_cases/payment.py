from .common import *
from .complete_order import CompleteOrderUseCase

class PaymentUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._momo_gateway = MoMoSandboxGateway()
        self._sepay_gateway = SePayPaymentGateway()
        self._zalopay_gateway = ZaloPaySandboxGateway()

    async def _mark_order_payment_failed_if_pending(self, order_id: UUID, *, internal_note: str, changed_by: str) -> None:
        order = await self._session.get(Order, order_id)
        if order is None or order.status != "PENDING":
            await self._session.rollback()
            return
        await self._session.rollback()
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

        # Truy vấn trực tiếp trạng thái từ MoMo nếu giao dịch đang chờ (PENDING)
        if payment.status == "PENDING" and payment.provider == "MOMO":
            try:
                momo_result = await self._momo_gateway.query_payment(
                    order_code=payment.transaction_ref,
                    request_id=str(payment.id),
                )
                # resultCode = 0 nghĩa là thanh toán thành công
                if momo_result.get("resultCode") == 0:
                    payment.status = "PAID"
                    payment.paid_at = datetime.now(timezone.utc)
                    payment.raw_response = {**(payment.raw_response or {}), "query_api": momo_result}
                    commerce_repo.save_model(self._session, payment)
                    await self._session.commit()
                    # Cập nhật đơn hàng thành PAID
                    await CompleteOrderUseCase(session=self._session).execute(
                        order_id=payment.order_id,
                        status_value="PAID",
                        internal_note="Xác nhận thanh toán tự động qua truy vấn API MoMo.",
                        changed_by="momo-query-api",
                    )
                    # Tải lại order và payment sau khi commit
                    payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
                    order = await self._session.get(Order, payment.order_id)
            except Exception as e:
                import logging
                logger = logging.getLogger("uvicorn.error")
                logger.error("Lỗi khi đối soát tự động MoMo: %s", e)

        now = datetime.now(timezone.utc)
        if payment.status == "PENDING" and payment.expires_at and payment.expires_at <= now:
            payment.status = "EXPIRED"
            payment.failed_at = now
            payment.raw_response = {
                **(payment.raw_response or {}),
                "failure_message": "Phiên thanh toán đã hết hạn.",
            }
            commerce_repo.save_model(self._session, payment)
            await self._session.commit()
            if order.status == "PENDING":
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note="Phiên thanh toán đã hết hạn.",
                    changed_by="payment-expirer",
                )
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
        payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
        order = await self._session.get(Order, payment.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
        if payment.status in {"PAID", "REFUNDED"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giao dịch đã hoàn tất, không thể hủy.")
        now = datetime.now(timezone.utc)
        if payment.status == "PENDING":
            payment.status = "FAILED"
            payment.failed_at = now
            payment.raw_response = {
                **(payment.raw_response or {}),
                "failure_message": "Khách hàng đã hủy phiên thanh toán.",
            }
            commerce_repo.save_model(self._session, payment)
            await self._session.commit()
            if order.status == "PENDING":
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note="Khách hàng đã hủy phiên thanh toán.",
                    changed_by="customer-payment-cancel",
                )
        return await self.get_status(payment.id)

    async def retry(self, payment_id: UUID) -> PaymentStatusResponse:
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
        latest = await commerce_repo.get_latest_payment_transaction(self._session, order.id)
        now = datetime.now(timezone.utc)
        if latest and latest.status == "PENDING" and (not latest.expires_at or latest.expires_at > now):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phiên thanh toán hiện tại vẫn còn hiệu lực.")
        next_attempt = (latest.attempt_number if latest else 0) + 1
        payment_id_new = uuid4()
        if previous.provider == "MOMO":
            provider_order_id = f"{order.order_code}-{next_attempt}"
            payment_init = await self._momo_gateway.create_payment(
                order_code=provider_order_id,
                amount=Decimal(order.total_amount),
                order_info=f"Thanh toán lại đơn hàng {order.order_code}",
                extra_data={"orderCode": order.order_code, "attempt": next_attempt},
                request_id=str(payment_id_new),
            )
            timeout_minutes = settings.momo_payment_timeout_minutes
        elif previous.provider == "ZALOPAY":
            vietnam_date = datetime.now(timezone(timedelta(hours=7))).strftime("%y%m%d")
            provider_order_id = f"{vietnam_date}_{order.order_code[-10:]}{next_attempt:02d}"
            payment_init = await self._zalopay_gateway.create_payment(
                app_trans_id=provider_order_id,
                amount=Decimal(order.total_amount),
                app_user=str(order.user_id or "electromart-sandbox"),
                description=f"ElectroMart Sandbox - Thanh toán lại đơn hàng {order.order_code}",
                callback_url=settings.zalopay_callback_url,
                redirect_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}",
            )
            timeout_minutes = settings.zalopay_payment_timeout_minutes
        elif previous.provider == "SEPAY":
            provider_order_id = f"{order.order_code}-{next_attempt}"
            payment_init = self._sepay_gateway.create_checkout(
                order_invoice_number=provider_order_id,
                order_amount=Decimal(order.total_amount),
                order_description=f"Thanh toán lại đơn hàng {order.order_code}",
                success_url=f"{settings.frontend_url.rstrip('/')}/orders/{order.id}?payment=success",
                error_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}?payment=error",
                cancel_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}?payment=cancel",
                customer_id=str(order.user_id) if order.user_id else None,
            )
            timeout_minutes = settings.sepay_payment_timeout_minutes
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cổng thanh toán không hỗ trợ thử lại.")
        expires_at = now + timedelta(minutes=timeout_minutes)
        payment = PaymentTransaction(
            id=payment_id_new,
            order_id=order.id,
            provider=previous.provider,
            amount=order.total_amount,
            status="PENDING",
            transaction_ref=provider_order_id,
            checkout_url=payment_init.checkout_url,
            attempt_number=next_attempt,
            expires_at=expires_at,
            raw_response=payment_init.raw_response or {},
        )
        commerce_repo.save_model(self._session, payment)
        await self._session.commit()
        return await self.get_status(payment.id)

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
        if paid_amount != Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền IPN SePay không khớp giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền thanh toán không khớp.")
        if payment.status in {"PAID", "REFUNDED"}:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
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
        if event_type in {"ORDER_PAID", "PAID", "SUCCESS", "SUCCEEDED"}:
            payment.status = "PAID"
            payment.paid_at = now
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await self._session.commit()
            await CompleteOrderUseCase(session=self._session).execute(
                order_id=payment.order_id,
                status_value="PAID",
                internal_note="SePay IPN xác nhận thanh toán thành công.",
                changed_by="sepay-ipn",
            )
        else:
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
            await self._session.commit()
            await self._mark_order_payment_failed_if_pending(
                order_id=payment.order_id,
                internal_note="SePay IPN báo thanh toán không thành công.",
                changed_by="sepay-ipn",
            )
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
        if payment.status in {"PAID", "REFUNDED"}:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
            )
            await self._session.commit()
            return {"ok": True, "duplicate": True}

        result_code = int(payload.get("resultCode") or -1)
        now = datetime.now(timezone.utc)
        payment.raw_response = {**(payment.raw_response or {}), "ipn": payload}
        if result_code == 0:
            payment.status = "PAID"
            payment.paid_at = now
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await self._session.commit()
            await CompleteOrderUseCase(session=self._session).execute(
                order_id=order_id,
                status_value="PAID",
                internal_note="MoMo Sandbox IPN xác nhận thanh toán thành công.",
                changed_by="momo-sandbox-ipn",
            )
        else:
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
            await self._session.commit()
            await self._mark_order_payment_failed_if_pending(
                order_id=order_id,
                internal_note="MoMo Sandbox IPN báo thanh toán không thành công.",
                changed_by="momo-sandbox-ipn",
            )
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
        if payment.status in {"PAID", "REFUNDED"}:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
            )
            await self._session.commit()
            return {"return_code": 2, "return_message": "duplicate"}

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
        await self._session.commit()
        await CompleteOrderUseCase(session=self._session).execute(
            order_id=payment.order_id,
            status_value="PAID",
            internal_note="ZaloPay Sandbox callback xác nhận thanh toán thành công.",
            changed_by="zalopay-sandbox-callback",
        )
        return {"return_code": 1, "return_message": "success"}
