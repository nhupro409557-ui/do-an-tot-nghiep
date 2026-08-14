from .common import *
from .voucher_service import VoucherService
from .complete_order_carrier import CompleteOrderCarrierMixin
from .complete_order_fulfillment import CompleteOrderFulfillmentMixin
from app.infrastructure.database.repositories import used_product_repo

class CompleteOrderUseCase(CompleteOrderCarrierMixin, CompleteOrderFulfillmentMixin):
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._shipping_gateway = ShippingGateway()

    # Keep order state changes centralized so stock, payment, and loyalty side effects stay consistent.
    async def execute(
        self,
        *,
        order_id: UUID,
        status_value: str | None = None,
        assigned_staff_name: str | None = None,
        internal_note: str | None = None,
        cancellation_reason: str | None = None,
        shipping_provider: str | None = None,
        tracking_code: str | None = None,
        return_source: str | None = None,
        return_reason: str | None = None,
        return_tracking_code: str | None = None,
        return_received_condition: str | None = None,
        refund_payment: bool = False,
        changed_by: str | None = None,
        issue_allocations: list | None = None,
        run_external_side_effects: bool = True,
        customer_receipt_confirmed: bool = False,
        actor_id: UUID | None = None,
    ) -> None:
        pending_shipping_registration = None
        refund_jobs = []

        class AsyncNullContext:
            async def __aenter__(self):
                return None
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        ctx = self._session.begin() if not self._session.in_transaction() else AsyncNullContext()
        async with ctx:
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")

            previous_status = order.status
            now = datetime.now(timezone.utc)

            if (
                status_value == "COMPLETED"
                and status_value != previous_status
                and order.order_purpose in {"WARRANTY_REPLACEMENT", "WARRANTY_RETURN", "RETURN_EXCHANGE"}
                and not customer_receipt_confirmed
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cần xác nhận khách đã nhận máy hậu mãi trước khi hoàn tất đơn.",
                )

            if assigned_staff_name is not None:
                order.assigned_staff_name = assigned_staff_name.strip() or None
            if internal_note is not None:
                order.internal_note = internal_note.strip() or None
            if shipping_provider is not None:
                order.shipping_provider = shipping_provider.strip() or None
            if tracking_code is not None:
                order.tracking_code = tracking_code.strip() or None
            if return_source is not None:
                order.return_source = return_source.strip().upper() or None
            if return_reason is not None:
                order.return_reason = return_reason.strip() or None
            if return_tracking_code is not None:
                order.return_tracking_code = return_tracking_code.strip() or None
            if return_received_condition is not None:
                order.return_received_condition = return_received_condition.strip().upper() or None

            if status_value is not None and status_value != previous_status:
                allowed_transitions = ORDER_STATUS_TRANSITIONS.get(previous_status, set())
                if status_value not in allowed_transitions:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Không thể chuyển đơn hàng từ {previous_status} sang {status_value}.",
                    )

                if status_value == "CANCELLED" and not (cancellation_reason or order.cancellation_reason):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cần nhập lý do khi hủy đơn hàng.",
                    )

                if status_value == "RETURNING":
                    if not order.return_source:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cần chọn hướng hoàn hàng trước khi bắt đầu hoàn.",
                        )
                    if not order.return_reason:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cần nhập lý do hoàn hàng.",
                        )
                    if order.return_source == "CUSTOMER_RETURN" and not await self._has_managed_return_request(order.id):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Khách đã nhận hàng phải tạo hồ sơ đổi trả trong mục Hậu mãi trước khi chuyển đơn sang đang hoàn.",
                        )

                if status_value == "RETURNED":
                    if not order.return_source or not order.return_received_condition:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cần xác nhận nguồn hoàn và tình trạng hàng khi cửa hàng tiếp nhận.",
                        )
                    if order.return_source == "CUSTOMER_RETURN" and not await self._has_managed_return_request(order.id):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Hàng khách chủ động trả phải được tiếp nhận qua hồ sơ đổi trả/hậu mãi.",
                        )

                if status_value in {"PAID", "PROCESSING", "SHIPPED", "COMPLETED"} and order.payment_method not in {"COD", "NO_PAYMENT"}:
                    paid_transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
                    if not any(tx.status == "PAID" and Decimal(tx.amount) >= Decimal(order.total_amount) for tx in paid_transactions):
                        raise HTTPException(status_code=409, detail="Đơn online chưa có giao dịch thanh toán thành công.")

                order.status = status_value
                if status_value in {"PAID", "COMPLETED"}:
                    order.payment_status = "PAID"
                if status_value == "SHIPPED":
                    if order.order_purpose != "WARRANTY_RETURN":
                        # Check if there is an outbound document linked to this order
                        outbound_res = await self._session.execute(
                            text("SELECT id, status, document_no FROM inventory_documents WHERE order_id = :order_id AND document_type = 'OUTBOUND'"),
                            {"order_id": order.id}
                        )
                        outbound_row = outbound_res.mappings().first()
                        if outbound_row:
                            if outbound_row["status"] == "COMPLETED":
                                # Physical inventory is already posted, skip shipping items logic.
                                # But we MUST close active reservations as CONSUMED!
                                await commerce_repo.close_active_order_reservations(
                                    self._session,
                                    order_id=order.id,
                                    status="CONSUMED",
                                )
                                await used_product_repo.mark_order_devices_sold(
                                    self._session,
                                    order_id=order.id,
                                    order_code=order.order_code,
                                )
                            else:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Đơn hàng đang có phiếu xuất kho chưa hoàn tất ({outbound_row['document_no']}). Vui lòng hoàn tất phiếu xuất kho để giao hàng."
                                )
                        else:
                            # Fallback to default FIFO shipping
                            await self._ship_order_items(order, issue_allocations=issue_allocations or [])

                    # Hoãn gọi API Shipping
                    if not order.tracking_code:
                        pending_shipping_registration = {
                            "provider": order.shipping_provider,
                            "order_code": order.order_code,
                            "recipient_name": order.recipient_name,
                            "recipient_phone": order.recipient_phone,
                            "shipping_address": order.shipping_address,
                        }
                    order.shipped_at = now
                if status_value == "COMPLETED":
                    order.completed_at = now
                    if order.payment_method == "COD" and Decimal(str(order.total_amount or 0)) > 0:
                        paid_transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
                        if not any(tx.status == "PAID" for tx in paid_transactions):
                            commerce_repo.save_model(
                                self._session,
                                PaymentTransaction(
                                    id=uuid4(),
                                    order_id=order.id,
                                    provider="COD",
                                    amount=order.total_amount,
                                    status="PAID",
                                    transaction_ref=f"{order.order_code}-COD",
                                    attempt_number=1,
                                    paid_at=now,
                                    raw_response={"message": "Khách hàng đã thanh toán tiền mặt khi nhận hàng (COD)."},
                                )
                            )
                    await VoucherService(session=self._session).confirm_voucher_usage(order=order)
                    if order.order_purpose in {"WARRANTY_REPLACEMENT", "WARRANTY_RETURN", "RETURN_EXCHANGE"}:
                        request_type = "WARRANTY" if order.order_purpose in {"WARRANTY_REPLACEMENT", "WARRANTY_RETURN"} else "RETURN"
                        request_table = "warranty_requests" if request_type == "WARRANTY" else "return_requests"
                        request_id = order.warranty_request_id if request_type == "WARRANTY" else order.return_request_id
                        previous_request_status = await self._session.scalar(
                            text(f"SELECT status FROM {request_table} WHERE id = :request_id FOR UPDATE"),
                            {"request_id": request_id},
                        )
                        if request_id and previous_request_status not in {"COMPLETED", "CANCELLED", "REJECTED", "CLOSED_EXPIRED"}:
                            await self._session.execute(
                                text(f"UPDATE {request_table} SET status = 'COMPLETED', closed_at = NOW(), updated_at = NOW() WHERE id = :request_id"),
                                {"request_id": request_id},
                            )
                            await self._session.execute(
                                text(
                                    """
                                    INSERT INTO after_sales_events (
                                        id, reference_type, reference_id, old_status, new_status,
                                        actor_id, note, metadata
                                    ) VALUES (
                                        :id, :reference_type, :reference_id, :old_status, 'COMPLETED',
                                        :actor_id, :note, jsonb_build_object(
                                            'orderId', CAST(CAST(:order_id AS UUID) AS TEXT),
                                            'source', CAST(:confirmation_source AS TEXT),
                                            'customerReceiptConfirmed', TRUE
                                        )
                                    )
                                    """
                                ),
                                {
                                    "id": uuid4(), "reference_type": request_type, "reference_id": request_id,
                                    "old_status": previous_request_status, "order_id": order.id,
                                    "actor_id": actor_id,
                                    "confirmation_source": (
                                        "ADMIN_RECEIPT_CONFIRMED" if actor_id else "DELIVERY_COMPLETED"
                                    ),
                                    "note": "Khách đã nhận máy hậu mãi; hồ sơ được hoàn tất tự động.",
                                },
                            )
                            if order.order_purpose == "RETURN_EXCHANGE":
                                from app.application.after_sales.return_disposition import (
                                    finalize_returned_identifier_disposition,
                                )

                                await finalize_returned_identifier_disposition(
                                    self._session,
                                    request_id=request_id,
                                    actor_id=actor_id,
                                )
                            if order.order_purpose == "WARRANTY_RETURN":
                                from app.application.after_sales.identifier_groups import (
                                    lock_identifier_group,
                                    update_locked_identifier_group_status,
                                )

                                repaired_items = (
                                    await self._session.execute(
                                        text(
                                            """
                                            SELECT wri.product_id, wri.product_variant_id,
                                                   wri.imei, wri.serial_number, oi.used_device_id
                                            FROM warranty_request_items wri
                                            JOIN order_items oi ON oi.id = wri.order_item_id
                                            WHERE wri.request_id = :request_id
                                            """
                                        ),
                                        {"request_id": request_id},
                                    )
                                ).mappings().all()
                                for repaired_item in repaired_items:
                                    if repaired_item["imei"] or repaired_item["serial_number"]:
                                        identifier_group = await lock_identifier_group(
                                            self._session,
                                            product_id=repaired_item["product_id"],
                                            variant_id=repaired_item["product_variant_id"],
                                            imei=repaired_item["imei"],
                                            serial_number=repaired_item["serial_number"],
                                        )
                                        await update_locked_identifier_group_status(
                                            self._session,
                                            group=identifier_group,
                                            target_status="SOLD",
                                            allowed_statuses={"WARRANTY"},
                                            clear_location=True,
                                        )
                                    if repaired_item["used_device_id"]:
                                        await used_product_repo.transition_after_sales_device(
                                            self._session,
                                            device_id=repaired_item["used_device_id"],
                                            target_status="SOLD",
                                            allowed_statuses={"REPAIRING", "SOLD"},
                                            event_type="DEVICE_WARRANTY_REPAIRED",
                                            note="Khách đã nhận lại thiết bị sau sửa chữa bảo hành.",
                                            metadata={"requestId": str(request_id), "orderId": str(order.id)},
                                        )
                if status_value == "PAID":
                    await VoucherService(session=self._session).confirm_voucher_usage(order=order)
                if status_value == "CANCELLED":
                    order.cancelled_at = now
                    order.cancellation_reason = (cancellation_reason or order.cancellation_reason or "").strip() or None
                    if order.order_purpose != "WARRANTY_RETURN":
                        await self._release_or_restock_unshipped_order(order, reservation_status="CANCELLED")

                    # Cancel linked outbound document if it exists and is not completed
                    await self._session.execute(
                        text(
                            """
                            UPDATE inventory_documents
                            SET status = 'CANCELLED', cancelled_at = NOW(), cancelled_by = :actor_id
                            WHERE order_id = :order_id AND document_type = 'OUTBOUND' AND status != 'COMPLETED'
                            """
                        ),
                        {"order_id": order.id, "actor_id": order.assigned_staff_name or order.user_id},
                    )
                    if order.order_purpose == "WARRANTY_RETURN":
                        from app.application.after_sales.fulfillment import handle_after_sales_order_cancelled

                        await handle_after_sales_order_cancelled(
                            self._session,
                            order_id=order.id,
                            order_purpose=order.order_purpose,
                            warranty_request_id=order.warranty_request_id,
                            changed_by=changed_by,
                            reason=order.cancellation_reason,
                        )

                    transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
                    for tx in transactions:
                        if tx.status == "PENDING":
                            tx.status = "FAILED"
                            tx.failed_at = now
                            tx.raw_response = {
                                **(tx.raw_response or {}),
                                "failure_message": "Đơn hàng đã bị hủy trước khi thanh toán hoàn tất.",
                            }
                            commerce_repo.save_model(self._session, tx)
                if status_value == "REFUNDED":
                    order.refunded_at = now
                    if previous_status != "RETURNED":
                        await self._release_or_restock_unshipped_order(order, reservation_status="RELEASED")
                    
                    # Cancel linked outbound document if it exists and is not completed
                    await self._session.execute(
                        text(
                            """
                            UPDATE inventory_documents
                            SET status = 'CANCELLED', cancelled_at = NOW(), cancelled_by = :actor_id
                            WHERE order_id = :order_id AND document_type = 'OUTBOUND' AND status != 'COMPLETED'
                            """
                        ),
                        {"order_id": order.id, "actor_id": order.assigned_staff_name or order.user_id},
                    )
                    refund_payment = True
                if status_value == "PAYMENT_FAILED":
                    order.cancelled_at = now
                    order.payment_status = "FAILED"
                    await self._release_or_restock_unshipped_order(order, reservation_status="EXPIRED")
                    transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
                    for tx in transactions:
                        if tx.status == "PENDING":
                            tx.status = "FAILED"
                            tx.failed_at = now
                            tx.raw_response = {
                                **(tx.raw_response or {}),
                                "failure_message": "Đơn hàng đã chuyển sang trạng thái thanh toán thất bại.",
                            }
                            commerce_repo.save_model(self._session, tx)
                if status_value == "RETURNED":
                    order.return_received_at = now
                    if (
                        order.return_source == "DELIVERY_REFUSED"
                        and order.return_received_condition == "SEALED"
                        and not await self._has_managed_return_request(order.id)
                    ):
                        await self._restock_order_items(order)

            # Tạo bù phiếu xuất cho đơn hợp lệ kể cả khi admin lưu lại cùng trạng thái.
            # Hàm tạo phiếu có kiểm tra idempotent nên không sinh chứng từ trùng.
            if status_value is not None and order.status in {"PAID", "PROCESSING"}:
                from app.application.services.inventory_service import create_outbound_document_from_order
                await create_outbound_document_from_order(self._session, order.id)

            if cancellation_reason is not None and order.status in {"CANCELLED", "PAYMENT_FAILED"}:
                order.cancellation_reason = cancellation_reason.strip() or None

            # Chỉ ghi nhận khi shop/admin đã tự chuyển tiền hoàn lại ở ngoài hệ thống.
            if refund_payment:
                transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
                for tx in transactions:
                    if tx.status == "PAID":
                        refund_jobs.append({
                            "id": tx.id,
                            "provider": tx.provider,
                            "amount": tx.amount,
                        })
                if order.payment_method == "COD":
                    order.payment_status = "REFUNDED"
                    order.refunded_at = order.refunded_at or now

            if (
                order.status in {"CANCELLED", "REFUNDED", "RETURNED", "PAYMENT_FAILED"}
                and previous_status not in {"CANCELLED", "REFUNDED", "RETURNED", "PAYMENT_FAILED"}
            ):
                await self._reverse_loyalty_for_closed_order(order)

            commerce_repo.save_model(self._session, order)

            if order.status == "COMPLETED" and previous_status != "COMPLETED" and order.user_id:
                user = await commerce_repo.get_user_for_update(self._session, order.user_id)
                if user and user.loyalty_wallet_status == "ACTIVE":
                    from app.application.services.loyalty_maintenance_service import upgrade_tier_after_order
                    balance_before = user.loyalty_points_balance
                    user.loyalty_points_balance += order.loyalty_points_earned
                    await upgrade_tier_after_order(
                        self._session,
                        user=user,
                        order_id=order.id,
                        order_amount=order.total_amount,
                    )
                    if order.loyalty_points_earned > 0:
                        commerce_repo.save_model(
                            self._session,
                            LoyaltyTransaction(
                                id=uuid4(),
                                user_id=user.id,
                                order_id=order.id,
                                type=LoyaltyTransactionType.EARN,
                                points=order.loyalty_points_earned,
                                balance_before=balance_before,
                                balance_after=user.loyalty_points_balance,
                                reason="Tích điểm khi đơn hàng hoàn tất.",
                                metadata_json={"order_code": order.order_code},
                            ),
                        )
                    commerce_repo.save_model(self._session, user)

            if (
                order.status in {"CANCELLED", "PAYMENT_FAILED"}
                and previous_status not in {"CANCELLED", "PAYMENT_FAILED"}
                and order.voucher_code
            ):
                await VoucherService(session=self._session).rollback_voucher_usage(order=order)
            elif (
                order.status == "REFUNDED"
                and previous_status != "REFUNDED"
                and order.voucher_code
            ):
                voucher = await commerce_repo.get_voucher_by_order_code_for_update(self._session, order.voucher_code)
                if voucher and voucher.refund_policy in {"ALWAYS", "SHOP_FAULT_ONLY"}:
                    await VoucherService(session=self._session).rollback_voucher_usage(order=order)

            if status_value is not None and status_value != previous_status:
                commerce_repo.save_model(
                    self._session,
                    OrderHistoryLog(
                        id=uuid4(),
                        order_id=order.id,
                        old_status=previous_status,
                        new_status=order.status,
                        changed_by=changed_by or "admin-console",
                        note=internal_note or cancellation_reason,
                        metadata_json={
                            "shipping_provider": order.shipping_provider,
                            "tracking_code": order.tracking_code,
                            "refund_payment": refund_payment,
                            "customer_receipt_confirmed": customer_receipt_confirmed,
                        },
                    ),
                )
                user = await commerce_repo.get_user(self._session, order.user_id) if order.user_id else None
                from types import SimpleNamespace
                order_snapshot = SimpleNamespace(
                    status=order.status,
                    order_code=order.order_code,
                    total_amount=order.total_amount,
                    payment_method=order.payment_method,
                    tracking_code=order.tracking_code,
                    shipping_provider=order.shipping_provider,
                    cancellation_reason=order.cancellation_reason,
                    recipient_name=order.recipient_name,
                )
                user_snapshot = SimpleNamespace(
                    email=user.email,
                    full_name=user.full_name,
                ) if user else None

                shipment_events = {
                    "CONFIRMED": [("CONFIRMED", "Đơn hàng đã được xác nhận")],
                    "PAID": [("CONFIRMED", "Đơn hàng đã được xác nhận")],
                    "PROCESSING": [("PACKED", "Đơn hàng đang được đóng gói")],
                    "SHIPPED": [
                        ("HANDED_TO_CARRIER", "Đơn hàng đã bàn giao cho đơn vị vận chuyển"),
                        ("IN_TRANSIT", "Đơn hàng đang được giao"),
                    ],
                    "COMPLETED": [("DELIVERED", "Đơn hàng đã được giao")],
                }
                for event_code, title in shipment_events.get(order.status, []):
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO shipment_events
                                (id, order_id, event_code, title, shipping_provider, tracking_code, source)
                            SELECT :id, :order_id, CAST(:event_code AS VARCHAR), CAST(:title AS VARCHAR), CAST(:provider AS VARCHAR), CAST(:tracking_code AS VARCHAR), 'INTERNAL'
                            WHERE NOT EXISTS (
                                SELECT 1 FROM shipment_events
                                WHERE order_id=:order_id AND event_code=CAST(:event_code AS VARCHAR)
                            )
                            """
                        ),
                        {
                            "id": uuid4(), "order_id": order.id, "event_code": event_code,
                            "title": title, "provider": order.shipping_provider,
                            "tracking_code": order.tracking_code,
                        },
                    )
                if order.user_id:
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO notifications
                                (id, user_id, type, title, message, entity_type, entity_id,
                                 action_url, idempotency_key, available_at)
                            VALUES
                                (:id, :user_id, 'order', 'Cập nhật đơn hàng', :message,
                                 'ORDER', :order_id, :action_url, :key, NOW() + INTERVAL '2 minutes')
                            ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
                            """
                        ),
                        {
                            "id": uuid4(), "user_id": order.user_id, "order_id": order.id,
                            "message": f"Đơn hàng {order.order_code} đã chuyển sang trạng thái {order.status}.",
                            "action_url": f"/orders/{order.id}",
                            "key": f"order:{order.id}:{order.status}",
                        },
                    )

        # NGOÀI RANH GIỚI TRANSACTION CHÍNH:

        # 1. Gọi API Shipping
        if run_external_side_effects and pending_shipping_registration:
            try:
                shipment = await self._shipping_gateway.register_shipment(
                    provider=pending_shipping_registration["provider"],
                    order_code=pending_shipping_registration["order_code"],
                    recipient_name=pending_shipping_registration["recipient_name"],
                    recipient_phone=pending_shipping_registration["recipient_phone"],
                    shipping_address=pending_shipping_registration["shipping_address"],
                )
                if shipment.success:
                    in_tx = self._session.in_transaction()
                    tx = self._session.begin() if not in_tx else AsyncNullContext()
                    async with tx:
                        order_to_update = await self._session.get(Order, order_id)
                        if order_to_update:
                            order_to_update.shipping_provider = shipment.provider or order_to_update.shipping_provider
                            order_to_update.tracking_code = order_to_update.tracking_code or shipment.tracking_code
                            commerce_repo.save_model(self._session, order_to_update)
                    if in_tx:
                        await self._session.flush()
            except Exception as e:
                import logging
                logger = logging.getLogger("uvicorn.error")
                logger.error("Lỗi khi kết nối đăng ký đơn vị vận chuyển: %s", e)

        # 3. Thực hiện hoàn tiền qua gateway ngoài transaction chính
        if refund_payment and refund_jobs:
            from app.application.commerce.integrations import RefundGateway
            refund_gateway = RefundGateway()
            refunded_any = False
            for job in refund_jobs:
                try:
                    refund_res = await refund_gateway.refund(
                        provider=job["provider"],
                        order_code=order_snapshot.order_code,
                        amount=job["amount"],
                    )
                    if refund_res.success:
                        in_tx = self._session.in_transaction()
                        tx_ctx = self._session.begin() if not in_tx else AsyncNullContext()
                        async with tx_ctx:
                            tx_model = await commerce_repo.get_payment_transaction_by_id_for_update(self._session, job["id"])
                            if tx_model:
                                tx_model.status = "REFUNDED"
                                tx_model.raw_response = {
                                    **(tx_model.raw_response or {}),
                                    "refund_marked_at": now.isoformat(),
                                    "refund_mode": "MANUAL",
                                    "refund_message": refund_res.message,
                                    "refund_ref": refund_res.provider_ref,
                                    "refund_marked_by": changed_by or "admin-console",
                                }
                                commerce_repo.save_model(self._session, tx_model)
                                refunded_any = True
                        if in_tx:
                            await self._session.flush()
                except Exception as e:
                    import logging
                    logger = logging.getLogger("uvicorn.error")
                    logger.error("Lỗi khi kết nối hoàn tiền qua gateway: %s", e)

            if refunded_any:
                in_tx = self._session.in_transaction()
                tx_ctx = self._session.begin() if not in_tx else AsyncNullContext()
                async with tx_ctx:
                    order_to_update = await self._session.get(Order, order_id)
                    if order_to_update:
                        order_to_update.payment_status = "REFUNDED"
                        order_to_update.refunded_at = order_to_update.refunded_at or now
                        commerce_repo.save_model(self._session, order_to_update)
                if in_tx:
                    await self._session.flush()

        # 2. Kích hoạt gửi email sau khi transaction chính đã commit
        if run_external_side_effects and status_value is not None and status_value != previous_status:
            import asyncio
            asyncio.create_task(asyncio.to_thread(self._send_order_status_email, order=order_snapshot, user=user_snapshot))

    async def run_committed_shipping_side_effects(self, *, order_id: UUID) -> None:
        """Đăng ký vận chuyển và gửi email sau khi transaction xuất kho đã commit."""
        order = await self._session.get(Order, order_id)
        if not order or order.status != "SHIPPED":
            return

        if not order.tracking_code:
            try:
                shipment = await self._shipping_gateway.register_shipment(
                    provider=order.shipping_provider,
                    order_code=order.order_code,
                    recipient_name=order.recipient_name,
                    recipient_phone=order.recipient_phone,
                    shipping_address=order.shipping_address,
                )
                if shipment.success:
                    order.shipping_provider = shipment.provider or order.shipping_provider
                    order.tracking_code = order.tracking_code or shipment.tracking_code
                    commerce_repo.save_model(self._session, order)
                    await self._session.commit()
            except Exception as exc:
                import logging
                logging.getLogger("uvicorn.error").error(
                    "Lỗi khi đăng ký vận chuyển sau khi xuất kho: %s",
                    exc,
                )
                await self._session.rollback()

        order = await self._session.get(Order, order_id, populate_existing=True)
        if not order or order.status != "SHIPPED":
            return
        user = await self._session.get(User, order.user_id) if order.user_id else None
        import asyncio
        asyncio.create_task(asyncio.to_thread(self._send_order_status_email, order=order, user=user))

    async def execute_admin_update(
        self,
        *,
        order_id: UUID,
        request: AdminUpdateOrderRequest,
        actor_id: UUID | None = None,
    ) -> None:
        await self.execute(
            order_id=order_id,
            status_value=request.status,
            assigned_staff_name=request.assigned_staff_name,
            internal_note=request.internal_note,
            cancellation_reason=request.cancellation_reason,
            shipping_provider=request.shipping_provider,
            tracking_code=request.tracking_code,
            return_source=request.return_source,
            return_reason=request.return_reason,
            return_tracking_code=request.return_tracking_code,
            return_received_condition=request.return_received_condition,
            refund_payment=request.refund_payment,
            changed_by=request.changed_by or (f"admin:{actor_id}" if actor_id else None),
            issue_allocations=request.issue_allocations,
            customer_receipt_confirmed=request.customer_receipt_confirmed,
            actor_id=actor_id,
        )

    async def _reverse_loyalty_for_closed_order(self, order: Order) -> None:
        if not order.user_id:
            return
        user = await commerce_repo.get_user_for_update(self._session, order.user_id)
        if not user:
            return

        redeemed = int(order.loyalty_points_used or 0)
        if redeemed > 0:
            already_refunded = await self._session.scalar(
                text(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM loyalty_transactions
                        WHERE order_id = :order_id AND type = 'REFUND'
                    )
                    """
                ),
                {"order_id": order.id},
            )
            if not already_refunded:
                balance_before = int(user.loyalty_points_balance or 0)
                user.loyalty_points_balance = balance_before + redeemed
                commerce_repo.save_model(
                    self._session,
                    LoyaltyTransaction(
                        id=uuid4(),
                        user_id=user.id,
                        order_id=order.id,
                        type=LoyaltyTransactionType.REFUND,
                        points=redeemed,
                        balance_before=balance_before,
                        balance_after=user.loyalty_points_balance,
                        reason="Hoàn lại điểm loyalty đã dùng khi đơn hàng bị hủy hoặc hoàn.",
                        metadata_json={"order_code": order.order_code, "status": order.status},
                    ),
                )

        earned = int(order.loyalty_points_earned or 0)
        if earned > 0:
            earned_recorded = await self._session.scalar(
                text(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM loyalty_transactions
                        WHERE order_id = :order_id AND type = 'EARN'
                    )
                    """
                ),
                {"order_id": order.id},
            )
            already_revoked = await self._session.scalar(
                text(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM loyalty_transactions
                        WHERE order_id = :order_id AND type = 'REVOKE'
                    )
                    """
                ),
                {"order_id": order.id},
            )
            if earned_recorded and not already_revoked:
                balance_before = int(user.loyalty_points_balance or 0)
                revoked_points = min(balance_before, earned)
                unrecovered_points = earned - revoked_points
                user.loyalty_points_balance = balance_before - revoked_points
                if revoked_points > 0:
                    commerce_repo.save_model(
                        self._session,
                        LoyaltyTransaction(
                            id=uuid4(),
                            user_id=user.id,
                            order_id=order.id,
                            type=LoyaltyTransactionType.REVOKE,
                            points=revoked_points,
                            balance_before=balance_before,
                            balance_after=user.loyalty_points_balance,
                            reason="Thu hồi điểm đã cộng khi đơn hàng bị hủy hoặc hoàn.",
                            metadata_json={
                                "order_code": order.order_code,
                                "status": order.status,
                                "requested_points": earned,
                                "unrecovered_points": unrecovered_points,
                            },
                        ),
                    )
        commerce_repo.save_model(self._session, user)
