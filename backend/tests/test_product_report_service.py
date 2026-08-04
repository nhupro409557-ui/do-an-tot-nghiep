import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.application.reporting.period import build_report_period
from app.application.reporting.product_report_service import get_product_report


class ProductReportServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_maps_product_metrics_and_pagination(self) -> None:
        repository_result = {
            "summary": {
                "total_products": 1,
                "units_sold": 4,
                "gross_revenue": Decimal("1000"),
                "allocated_discount": Decimal("100"),
                "refund_amount": Decimal("200"),
                "net_revenue": Decimal("700"),
                "unallocated_refund_amount": Decimal("50"),
            },
            "items": [
                {
                    "product_id": "product-1",
                    "variant_id": "variant-1",
                    "sku": "SKU-01",
                    "product_name": "Điện thoại A",
                    "units_sold": 4,
                    "order_count": 2,
                    "gross_revenue": Decimal("1000"),
                    "allocated_discount": Decimal("100"),
                    "refund_amount": Decimal("200"),
                    "net_revenue": Decimal("700"),
                }
            ],
            "total": 1,
        }
        with patch(
            "app.application.reporting.product_report_service.product_report_repo.get_product_report",
            new=AsyncMock(return_value=repository_result),
        ):
            report = await get_product_report(
                AsyncMock(),
                period=build_report_period(
                    from_date=date(2026, 7, 1),
                    to_date=date(2026, 8, 1),
                ),
                sort_by="netRevenue",
                page=1,
                limit=20,
            )

        self.assertEqual(report.summary.netRevenue, Decimal("700"))
        self.assertEqual(report.summary.unallocatedRefundAmount, Decimal("50"))
        self.assertEqual(report.items[0].sku, "SKU-01")
        self.assertEqual(report.pagination.totalPages, 1)


if __name__ == "__main__":
    unittest.main()
