from .common import *
from .voucher_service import VoucherService
from .complete_order_carrier import CompleteOrderCarrierMixin
from .complete_order_fulfillment import CompleteOrderFulfillmentMixin

class CompleteOrderUseCase(CompleteOrderCarrierMixin, CompleteOrderFulfillmentMixin):
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._refund_gateway = RefundGateway()
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
        refund_payment: bool = False,
        changed_by: str | None = None,
        issue_allocations: list | None = None,
    ) -> None:
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

            if assigned_staff_name is not None:
                order.assigned_staff_name = assigned_staff_name.strip() or None
            if internal_note is not None:
                order.internal_note = internal_note.strip() or None
            if shipping_provider is not None:
                order.shipping_provider = shipping_provider.strip() or None
            if tracking_code is not None:
                order.tracking_code = tracking_code.strip() or None

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

                order.status = status_value
                if status_value in {"PAID", "COMPLETED"}:
                    order.payment_status = "PAID"
                if status_value in {"PROCESSING", "PAID"}:
                    from app.application.services.inventory_service import create_outbound_document_from_order
                    await create_outbound_document_from_order(self._session, order.id)
                if status_value == "SHIPPED":
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
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Đơn hàng đang có phiếu xuất kho chưa hoàn tất ({outbound_row['document_no']}). Vui lòng hoàn tất phiếu xuất kho để giao hàng."
                            )
                    else:
                        # Fallback to default FIFO shipping
                        await self._ship_order_items(order, issue_allocations=issue_allocations or [])

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
                    order.shipped_at = now
                if status_value == "COMPLETED":
                    order.completed_at = now
                if status_value == "CANCELLED":
                    order.cancelled_at = now
                    order.cancellation_reason = (cancellation_reason or order.cancellation_reason or "").strip() or None
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

                    refund_payment = refund_payment or order.payment_method != "COD"
                if status_value == "REFUNDED":
                    order.refunded_at = now
                    if previous_status not in {"SHIPPED", "RETURNING", "RETURNED", "COMPLETED"}:
                        await self._release_or_restock_unshipped_order(order, reservation_status="RELEASED")
                    refund_payment = True
                if status_value == "PAYMENT_FAILED":
                    order.cancelled_at = now
                    order.payment_status = "FAILED"
                    await self._release_or_restock_unshipped_order(order, reservation_status="EXPIRED")
                if status_value == "RETURNED":
                    if not await self._has_managed_return_request(order.id):
                        await self._restock_order_items(order)

            if cancellation_reason is not None and order.status == "CANCELLED":
                order.cancellation_reason = cancellation_reason.strip() or None

            if refund_payment:
                await self._mark_payment_refunded(order, now=now)

            if (
                order.status in {"CANCELLED", "REFUNDED", "RETURNED"}
                and previous_status not in {"CANCELLED", "REFUNDED", "RETURNED"}
            ):
                await self._reverse_loyalty_for_closed_order(order)

            commerce_repo.save_model(self._session, order)

            if order.status == "COMPLETED" and previous_status != "COMPLETED" and order.user_id and order.loyalty_points_earned > 0:
                user = await commerce_repo.get_user_for_update(self._session, order.user_id)
                if user and user.loyalty_wallet_status == "ACTIVE":
                    balance_before = user.loyalty_points_balance
                    user.loyalty_points_balance += order.loyalty_points_earned
                    user.loyalty_tier = calculate_tier(user.loyalty_points_balance)
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
                            reason="Earn points when order is completed.",
                            metadata_json={"order_code": order.order_code},
                        ),
                    )
                    commerce_repo.save_model(self._session, user)

            if order.status in {"CANCELLED", "REFUNDED", "PAYMENT_FAILED"} and previous_status not in {"CANCELLED", "REFUNDED", "PAYMENT_FAILED"} and order.voucher_code:
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
                        },
                    ),
                )
                user = await commerce_repo.get_user(self._session, order.user_id) if order.user_id else None
                self._send_order_status_email(order=order, user=user)
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

    async def execute_admin_update(self, *, order_id: UUID, request: AdminUpdateOrderRequest) -> None:
        await self.execute(
            order_id=order_id,
            status_value=request.status,
            assigned_staff_name=request.assigned_staff_name,
            internal_note=request.internal_note,
            cancellation_reason=request.cancellation_reason,
            shipping_provider=request.shipping_provider,
            tracking_code=request.tracking_code,
            refund_payment=request.refund_payment,
            changed_by=request.changed_by,
            issue_allocations=request.issue_allocations,
        )

    async def _reverse_loyalty_for_closed_order(self, order: Order) -> None:
        if not order.user_id:
            return
        user = await commerce_repo.get_user_for_update(self._session, order.user_id)
        if not user or user.loyalty_wallet_status != "ACTIVE":
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
                user.loyalty_tier = calculate_tier(user.loyalty_points_balance)
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
                user.loyalty_points_balance = max(balance_before - earned, 0)
                user.loyalty_tier = calculate_tier(user.loyalty_points_balance)
                commerce_repo.save_model(
                    self._session,
                    LoyaltyTransaction(
                        id=uuid4(),
                        user_id=user.id,
                        order_id=order.id,
                        type=LoyaltyTransactionType.REVOKE,
                        points=earned,
                        balance_before=balance_before,
                        balance_after=user.loyalty_points_balance,
                        reason="Thu hồi điểm loyalty đã cộng khi đơn hàng bị hủy hoặc hoàn.",
                        metadata_json={"order_code": order.order_code, "status": order.status},
                    ),
                )
        commerce_repo.save_model(self._session, user)
