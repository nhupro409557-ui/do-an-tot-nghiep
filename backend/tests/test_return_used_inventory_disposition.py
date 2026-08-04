import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from pydantic import ValidationError

from app.application.after_sales.inspection import _create_return_disposition_document
from app.application.after_sales.schemas import InspectAfterSalesRequest


class ReturnInventoryDispositionTest(unittest.TestCase):
    def test_supported_inventory_dispositions(self) -> None:
        for disposition in ("NEW_STOCK", "USED_INTAKE", "REPAIR", "SCRAP"):
            payload = InspectAfterSalesRequest(
                result="APPROVE_REFUND",
                qc_note="Thiết bị đã được kiểm tra đầy đủ.",
                inventory_disposition=disposition,
            )
            self.assertEqual(payload.inventory_disposition, disposition)

    def test_unknown_inventory_disposition_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            InspectAfterSalesRequest(
                result="APPROVE_REFUND",
                qc_note="Thiết bị đã được kiểm tra đầy đủ.",
                inventory_disposition="SELL_AS_NEW_ANYWAY",
            )


class ReturnDispositionDocumentTest(unittest.IsolatedAsyncioTestCase):
    async def _create(self, disposition: str):
        session = AsyncMock()
        session.scalar.return_value = uuid4()
        request = {"id": uuid4(), "order_id": uuid4(), "request_code": "RT-TEST-001"}
        items = [{
            "product_id": uuid4(), "product_variant_id": None, "quantity": 1,
            "imei": "123456789012345", "serial_number": "SERIAL-001",
        }]
        with patch("app.application.after_sales.inspection.inventory_repo.insert_inventory_internal_hold_document", new=AsyncMock()) as hold_doc, \
             patch("app.application.after_sales.inspection.inventory_repo.insert_inventory_internal_hold_line", new=AsyncMock()) as hold_line, \
             patch("app.application.after_sales.inspection.inventory_repo.insert_inventory_disposal_document", new=AsyncMock()) as disposal_doc, \
             patch("app.application.after_sales.inspection.inventory_repo.insert_inventory_disposal_line", new=AsyncMock()) as disposal_line:
            await _create_return_disposition_document(
                session, request=request, items=items, disposition=disposition,
                actor_id=uuid4(), note="Kết quả QC yêu cầu xử lý riêng.",
            )
            return hold_doc, hold_line, disposal_doc, disposal_line

    async def test_repair_creates_internal_hold_with_identifiers(self) -> None:
        hold_doc, hold_line, disposal_doc, disposal_line = await self._create("REPAIR")
        hold_doc.assert_awaited_once()
        hold_line.assert_awaited_once()
        self.assertEqual(hold_line.await_args.kwargs["imeis"], ["123456789012345"])
        disposal_doc.assert_not_awaited()
        disposal_line.assert_not_awaited()

    async def test_scrap_creates_disposal_with_identifiers(self) -> None:
        hold_doc, hold_line, disposal_doc, disposal_line = await self._create("SCRAP")
        disposal_doc.assert_awaited_once()
        disposal_line.assert_awaited_once()
        self.assertEqual(disposal_line.await_args.kwargs["serial_numbers"], ["SERIAL-001"])
        hold_doc.assert_not_awaited()
        hold_line.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
