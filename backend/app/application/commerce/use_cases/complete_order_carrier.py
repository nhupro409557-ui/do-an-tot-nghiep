from .common import *


class CompleteOrderCarrierMixin:
    async def quote_carrier_shipment(self, *, order_id: UUID, provider: str | None = None) -> CarrierShipmentResponse:
        order = await commerce_repo.get_order_for_update(self._session, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
        item_count = await self._order_item_count(order.id)
        quote = await SandboxShippingPricingService().quote(
            self._session,
            shipping_address=order.shipping_address,
            subtotal_amount=Decimal(order.subtotal_amount or 0),
            item_count=item_count,
            provider=provider or order.shipping_provider,
        )
        return CarrierShipmentResponse(
            order_id=order.id,
            order_code=order.order_code,
            provider=quote.provider,
            tracking_code=order.tracking_code,
            carrier_status="QUOTED",
            shipping_fee=quote.fee,
            estimated_days=quote.estimated_days,
            message=quote.note,
        )

    async def create_carrier_shipment(self, *, order_id: UUID, provider: str | None = None) -> CarrierShipmentResponse:
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if order.status in {"CANCELLED", "REFUNDED", "RETURNED"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Không thể tạo vận đơn cho đơn đã đóng.")

            shipment = await self._shipping_gateway.register_shipment(
                provider=provider or order.shipping_provider,
                order_code=order.order_code,
                recipient_name=order.recipient_name,
                recipient_phone=order.recipient_phone,
                shipping_address=order.shipping_address,
            )
            order.shipping_provider = shipment.provider or normalize_mock_carrier(provider)
            order.tracking_code = order.tracking_code or shipment.tracking_code
            commerce_repo.save_model(self._session, order)
            await self._insert_shipment_event(
                order=order,
                event_code="CREATED",
                title="Đã tạo vận đơn thử nghiệm",
                description="Vận đơn được tạo bằng mock carrier, không phát sinh giao hàng thật.",
                source="MOCK_CARRIER",
            )
            await self._insert_order_history(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by="mock-carrier",
                note=f"Tạo vận đơn thử nghiệm {order.tracking_code}.",
            )

        return await self.quote_carrier_shipment(order_id=order_id, provider=provider)

    async def cancel_carrier_shipment(self, *, order_id: UUID, reason: str | None = None) -> CarrierShipmentResponse:
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if not order.tracking_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đơn hàng chưa có mã vận đơn để huỷ.")
            await self._insert_shipment_event(
                order=order,
                event_code="CANCELLED",
                title="Đã huỷ vận đơn thử nghiệm",
                description=(reason or "Admin huỷ vận đơn trên môi trường mô phỏng.").strip(),
                source="MOCK_CARRIER",
            )
            await self._insert_order_history(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by="mock-carrier",
                note=(reason or "Huỷ vận đơn thử nghiệm.").strip(),
            )
        response = await self.quote_carrier_shipment(order_id=order_id, provider=None)
        response.carrier_status = "CANCELLED"
        response.message = "Đã huỷ vận đơn thử nghiệm; trạng thái đơn hàng không bị đổi tự động."
        return response

    async def update_carrier_event(
        self,
        *,
        order_id: UUID,
        event_code: str,
        note: str | None = None,
    ) -> CarrierShipmentResponse:
        titles = {
            "CREATED": "Đã tạo vận đơn thử nghiệm",
            "HANDED_TO_CARRIER": "Đơn hàng đã bàn giao cho đơn vị vận chuyển",
            "IN_TRANSIT": "Đơn hàng đang được giao",
            "DELIVERED": "Đơn hàng đã được giao",
            "DELIVERY_FAILED": "Giao hàng không thành công",
            "CANCELLED": "Đã huỷ vận đơn thử nghiệm",
        }
        if event_code not in titles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái vận chuyển không hợp lệ.")
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if not order.tracking_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đơn hàng chưa có mã vận đơn.")
            await self._insert_shipment_event(
                order=order,
                event_code=event_code,
                title=titles[event_code],
                description=note,
                source="MOCK_CARRIER",
            )
            await self._insert_order_history(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by="mock-carrier",
                note=note or titles[event_code],
            )
        response = await self.quote_carrier_shipment(order_id=order_id, provider=None)
        response.carrier_status = event_code
        response.message = titles[event_code]
        return response

    async def _order_item_count(self, order_id: UUID) -> int:
        result = await self._session.execute(
            text("SELECT COALESCE(SUM(quantity), 0)::int FROM order_items WHERE order_id = :order_id"),
            {"order_id": order_id},
        )
        return max(1, int(result.scalar() or 1))

    async def _insert_shipment_event(
        self,
        *,
        order: Order,
        event_code: str,
        title: str,
        description: str | None = None,
        source: str = "MOCK_CARRIER",
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO shipment_events
                    (id, order_id, event_code, title, description, shipping_provider, tracking_code, source)
                SELECT :id, :order_id, CAST(:event_code AS VARCHAR), CAST(:title AS VARCHAR), CAST(:description AS VARCHAR), CAST(:provider AS VARCHAR), CAST(:tracking_code AS VARCHAR), CAST(:source AS VARCHAR)
                WHERE NOT EXISTS (
                    SELECT 1 FROM shipment_events
                    WHERE order_id = :order_id
                      AND event_code = CAST(:event_code AS VARCHAR)
                      AND COALESCE(tracking_code, '') = COALESCE(CAST(:tracking_code AS VARCHAR), '')
                      AND source = CAST(:source AS VARCHAR)
                )
                """
            ),
            {
                "id": uuid4(),
                "order_id": order.id,
                "event_code": event_code,
                "title": title,
                "description": description,
                "provider": order.shipping_provider,
                "tracking_code": order.tracking_code,
                "source": source,
            },
        )

    def _insert_order_history(
        self,
        *,
        order: Order,
        old_status: str,
        new_status: str,
        changed_by: str,
        note: str | None = None,
    ) -> None:
        commerce_repo.save_model(
            self._session,
            OrderHistoryLog(
                id=uuid4(),
                order_id=order.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                note=note,
                metadata_json={
                    "shipping_provider": order.shipping_provider,
                    "tracking_code": order.tracking_code,
                },
            ),
        )
