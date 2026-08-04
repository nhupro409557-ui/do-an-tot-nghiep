import unittest
from unittest.mock import AsyncMock, patch

from app.application.services.inventory.overview import (
    get_inventory_aging_report,
    get_inventory_reconciliation_report,
)


class InventoryReportPaginationTest(unittest.IsolatedAsyncioTestCase):
    async def test_aging_paginates_items_but_keeps_full_summary(self) -> None:
        rows = [
            {
                "bucket": "0_30",
                "productId": f"product-{index}",
                "productName": f"Sản phẩm {index}",
                "quantity": 1,
                "totalCost": 2,
                "averageAgeDays": 10,
                "maxAgeDays": 10,
            }
            for index in range(120)
        ]
        with patch(
            "app.application.services.inventory.overview."
            "inventory_repo.list_inventory_aging_rows",
            new=AsyncMock(return_value=rows),
        ):
            report = await get_inventory_aging_report(
                AsyncMock(),
                page=2,
                page_size=50,
            )

        self.assertEqual(len(report["items"]), 50)
        self.assertEqual(report["pagination"]["total"], 120)
        self.assertEqual(report["pagination"]["totalPages"], 3)
        self.assertEqual(report["buckets"][0]["skuCount"], 120)
        self.assertEqual(report["totalQuantity"], 120)

    async def test_reconciliation_paginates_items_but_keeps_full_summary(self) -> None:
        rows = [
            {
                "issueType": "LOT_QUANTITY_MISMATCH",
                "productId": f"product-{index}",
            }
            for index in range(120)
        ]
        with patch(
            "app.application.services.inventory.overview."
            "inventory_repo.list_inventory_reconciliation_rows",
            new=AsyncMock(return_value=rows),
        ):
            report = await get_inventory_reconciliation_report(
                AsyncMock(),
                page=3,
                page_size=50,
            )

        self.assertEqual(len(report["items"]), 20)
        self.assertEqual(report["pagination"]["total"], 120)
        self.assertEqual(report["pagination"]["totalPages"], 3)
        summary = {
            item["issueType"]: item["count"]
            for item in report["summary"]
        }
        self.assertEqual(summary["LOT_QUANTITY_MISMATCH"], 120)
        self.assertEqual(report["totalIssues"], 120)


if __name__ == "__main__":
    unittest.main()
