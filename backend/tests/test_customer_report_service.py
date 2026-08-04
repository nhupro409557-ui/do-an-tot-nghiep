import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.application.reporting.customer_report_service import (
    get_customer_report,
    get_customer_retention_report,
)
from app.application.reporting.period import build_report_period


class CustomerReportServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_maps_customer_summary_and_segments(self) -> None:
        repository_result = {
            "summary": {
                "new_customers": 5,
                "active_customers": 4,
                "first_time_buyers": 2,
                "returning_customers": 2,
            },
            "tiers": [{"tier": "GOLD", "customers": 2, "net_revenue": Decimal("900")}],
            "items": [{
                "id": "user-1",
                "full_name": "Nguyễn Văn A",
                "email": "a@example.com",
                "tier": "GOLD",
                "registered_at": "2026-07-01T00:00:00+00:00",
                "order_count": 2,
                "net_spent": Decimal("900"),
                "segment": "RETURNING",
            }],
            "total": 1,
        }
        with patch(
            "app.application.reporting.customer_report_service.customer_report_repo.get_customer_report",
            new=AsyncMock(return_value=repository_result),
        ):
            report = await get_customer_report(
                AsyncMock(),
                period=build_report_period(
                    from_date=date(2026, 7, 1),
                    to_date=date(2026, 8, 1),
                ),
            )

        self.assertEqual(report.summary.repeatPurchaseRate, Decimal("50.00"))
        self.assertEqual(report.items[0].segment, "RETURNING")

    async def test_groups_flat_retention_rows_by_cohort(self) -> None:
        rows = [
            {
                "cohort_month": date(2026, 1, 1),
                "cohort_size": 10,
                "month_offset": 0,
                "customers": 4,
            },
            {
                "cohort_month": date(2026, 1, 1),
                "cohort_size": 10,
                "month_offset": 1,
                "customers": 2,
            },
        ]
        with patch(
            "app.application.reporting.customer_report_service.customer_report_repo.get_customer_retention",
            new=AsyncMock(return_value=rows),
        ):
            report = await get_customer_retention_report(AsyncMock())

        self.assertEqual(len(report.cohorts), 1)
        self.assertEqual(report.cohorts[0].periods[1].retentionRate, Decimal("20.00"))


if __name__ == "__main__":
    unittest.main()
