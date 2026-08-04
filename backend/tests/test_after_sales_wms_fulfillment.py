import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.application.after_sales.return_inventory import (
    RETURN_TO_STOCK_REASON,
    ensure_return_to_stock_inbound,
)
from fastapi import HTTPException

from app.application.after_sales.fulfillment import ensure_after_sales_outbound
from app.application.after_sales.schemas import UpdateAfterSalesStatusRequest
from app.application.after_sales.service import admin_update_status


class ReturnToStockInboundTest(unittest.IsolatedAsyncioTestCase):
    async def test_existing_document_is_reused(self) -> None:
        session = AsyncMock()
        document_id = uuid4()
        session.scalar.return_value = document_id
        with patch(
            "app.application.after_sales.return_inventory.inventory_repo.insert_inventory_receipt_document",
            new=AsyncMock(),
        ) as insert_document:
            result = await ensure_return_to_stock_inbound(
                session,
                request={"id": uuid4(), "order_id": uuid4(), "request_code": "RT-001"},
                items=[],
                actor_id=uuid4(),
                note="Đã đạt QC.",
            )
        self.assertEqual(result, document_id)
        insert_document.assert_not_awaited()

    async def test_new_stock_creates_draft_receipt_without_mutating_stock(self) -> None:
        session = AsyncMock()
        session.scalar.return_value = None
        location_result = MagicMock()
        location_result.mappings.return_value.first.return_value = {
            "id": uuid4(), "code": "MAIN", "name": "Kho chính"
        }
        session.execute.side_effect = [location_result, MagicMock()]
        item = {
            "product_id": uuid4(), "product_variant_id": uuid4(), "quantity": 1,
            "imei": "123456789012345", "serial_number": "SERIAL-001",
            "unit_price_snapshot": 1000,
        }
        with patch(
            "app.application.after_sales.return_inventory.inventory_repo.insert_inventory_receipt_document",
            new=AsyncMock(),
        ) as insert_document, patch(
            "app.application.after_sales.return_inventory.inventory_repo.insert_inventory_receipt_line",
            new=AsyncMock(),
        ) as insert_line:
            await ensure_return_to_stock_inbound(
                session,
                request={"id": uuid4(), "order_id": uuid4(), "request_code": "RT-002"},
                items=[item], actor_id=uuid4(), note="Thiết bị nguyên vẹn và đạt QC.",
            )
        self.assertEqual(insert_document.await_args.kwargs["status"], "DRAFT")
        self.assertEqual(insert_document.await_args.kwargs["reason"], RETURN_TO_STOCK_REASON)
        self.assertEqual(insert_line.await_args.kwargs["imeis"], ["123456789012345"])


class AfterSalesOutboundTest(unittest.IsolatedAsyncioTestCase):
    async def test_outbound_is_draft_document_from_service_order(self) -> None:
        session = AsyncMock()
        order_id = uuid4()
        document_id = uuid4()
        with patch(
            "app.application.after_sales.fulfillment.ensure_after_sales_order",
            new=AsyncMock(return_value=order_id),
        ), patch(
            "app.application.services.inventory.outbounds.create_outbound_document_from_order",
            new=AsyncMock(return_value=document_id),
        ) as create_outbound:
            result = await ensure_after_sales_outbound(
                session,
                kind="WARRANTY",
                request={"id": uuid4(), "request_code": "WR-001"},
                items=[],
            )
        self.assertEqual(result, document_id)
        create_outbound.assert_awaited_once_with(session, order_id)
        session.execute.assert_awaited_once()


class WarrantyQcTransitionTest(unittest.IsolatedAsyncioTestCase):
    async def test_received_warranty_can_start_qc_without_reinspection_branch(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        actor_id = uuid4()
        user_id = uuid4()
        request = {
            "id": request_id,
            "user_id": user_id,
            "request_code": "WR-START-QC",
            "status": "RECEIVED",
            "resolution_type": None,
        }
        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.update_request_status",
            new=AsyncMock(),
        ) as update_status, patch(
            "app.application.after_sales.service.after_sales_repo.insert_event",
            new=AsyncMock(),
        ) as insert_event, patch(
            "app.application.after_sales.service.after_sales_repo.notify",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.sync_warranty_imei_status",
            new=AsyncMock(),
        ):
            result = await admin_update_status(
                session,
                kind="WARRANTY",
                request_id=request_id,
                actor_id=actor_id,
                payload=UpdateAfterSalesStatusRequest(
                    status="QC_IN_PROGRESS",
                    note="Bắt đầu kiểm tra chất lượng thiết bị.",
                ),
            )

        self.assertEqual(result["status"], "QC_IN_PROGRESS")
        self.assertEqual(update_status.await_args.kwargs["status_value"], "QC_IN_PROGRESS")
        event_metadata = insert_event.await_args.kwargs.get("metadata") or {}
        self.assertNotEqual(event_metadata.get("action"), "REOPEN_QC")
        session.commit.assert_awaited_once()

    async def test_delivery_replacement_cannot_complete_before_delivery(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        request = {
            "id": request_id,
            "user_id": uuid4(),
            "request_code": "WR-WAIT-DELIVERY",
            "status": "REPLACEMENT_PROCESSING",
            "resolution_type": "REPLACEMENT",
        }
        fulfillment_result = MagicMock()
        fulfillment_result.mappings.return_value.first.return_value = {
            "status": "SHIPPED",
            "fulfillment_method": "DELIVERY",
        }
        session.execute.return_value = fulfillment_result
        session.scalar.return_value = True

        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=[]),
        ):
            with self.assertRaises(HTTPException) as raised:
                await admin_update_status(
                    session,
                    kind="WARRANTY",
                    request_id=request_id,
                    actor_id=uuid4(),
                    payload=UpdateAfterSalesStatusRequest(
                        status="COMPLETED",
                        note="Thử hoàn tất hồ sơ trước khi đơn giao máy hoàn thành.",
                    ),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("chưa được giao thành công", raised.exception.detail)
        session.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
