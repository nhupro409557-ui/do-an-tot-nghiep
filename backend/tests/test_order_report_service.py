import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.application.reporting.order_report_service import get_order_report
from app.application.reporting.period import build_report_period


class OrderReportServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_maps_summary_breakdowns_and_pagination(self) -> None:
        period = build_report_period(
            from_date=date(2026, 7, 1),
            to_date=date(2026, 8, 1),
        )
        repository_result = {
            "summary": {
                "total_orders": 3,
                "completed_orders": 2,
                "cancelled_orders": 1,
                "total_amount": Decimal("900"),
                "average_order_value": Decimal("300"),
            },
            "breakdowns": {
                "statuses": [{"key": "COMPLETED", "count": 2, "amount": Decimal("700")}],
                "channels": [{"key": "ONLINE", "count": 3, "amount": Decimal("900")}],
                "payment_methods": [],
                "payment_statuses": [],
                "fulfillment_methods": [],
            },
            "items": [
                {
                    "id": "order-1",
                    "order_code": "ORD-001",
                    "customer_name": "Nguyễn Văn A",
                    "email": "a@example.com",
                    "status": "COMPLETED",
                    "channel": "ONLINE",
                    "payment_method": "COD",
                    "payment_status": "PAID",
                    "fulfillment_method": "DELIVERY",
                    "total_amount": Decimal("500"),
                    "created_at": "2026-07-02T08:00:00+00:00",
                    "completed_at": "2026-07-03T08:00:00+00:00",
                }
            ],
            "total": 3,
        }
        with patch(
            "app.application.reporting.order_report_service.order_report_repo.get_order_report",
            new=AsyncMock(return_value=repository_result),
        ):
            report = await get_order_report(
                AsyncMock(),
                period=period,
                date_basis="createdAt",
                page=2,
                limit=2,
            )

        self.assertEqual(report.summary.totalOrders, 3)
        self.assertEqual(report.breakdowns.statuses[0].key, "COMPLETED")
        self.assertEqual(report.items[0].orderCode, "ORD-001")
        self.assertEqual(report.pagination.totalPages, 2)
        self.assertEqual(report.pagination.page, 2)


if __name__ == "__main__":
    unittest.main()
