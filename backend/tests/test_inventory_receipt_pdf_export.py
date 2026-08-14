from io import BytesIO
from unittest import TestCase
from unittest.mock import patch

from pypdf import PdfReader

from app.application.services import document_export_service


class InventoryReceiptPdfExportTest(TestCase):
    def test_pdf_is_rendered_when_windows_fonts_are_unavailable(self) -> None:
        receipt = {
            "referenceCode": "NK-TEST-PDF",
            "status": "COMPLETED",
            "supplierName": "Nhà cung cấp kiểm thử",
            "receiptReasonCode": "NK_MUA",
            "locationName": "Kho chính",
            "note": "Kiểm tra xuất phiếu nhập kho.",
            "lines": [
                {
                    "productName": "Củ sạc nhanh",
                    "variantSku": "SAC-TEST",
                    "plannedQuantity": 1,
                    "receivedQuantity": 1,
                    "unitCost": 500000,
                }
            ],
        }

        with patch.object(document_export_service.Path, "exists", return_value=False):
            content, filename = document_export_service.render_inventory_receipt_pdf(receipt)

        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)
        self.assertEqual(filename, "NK-TEST-PDF.pdf")
        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        self.assertIn("Nhà cung cấp kiểm thử", text)
        self.assertIn("Củ sạc nhanh", text)
