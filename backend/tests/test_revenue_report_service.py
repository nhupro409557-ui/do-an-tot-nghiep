import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.application.reporting.period import build_report_period
from app.application.reporting.revenue_service import get_revenue_report


class RevenueReportServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_maps_summary_comparison_series_and_breakdowns(self) -> None:
        period = build_report_period(
            from_date=date(2026, 7, 1),
            to_date=date(2026, 8, 1),
            timezone_name="Asia/Bangkok",
            bucket="day",
        )
        current = {
            "completed_orders": 3,
            "gross_revenue": Decimal("1200"),
            "refund_amount": Decimal("200"),
            "net_revenue": Decimal("1000"),
            "average_order_value": Decimal("333.3333"),
            "cost_of_goods_sold": Decimal("600"),
        }
        previous = {
            "completed_orders": 2,
            "gross_revenue": Decimal("900"),
            "refund_amount": Decimal("100"),
            "net_revenue": Decimal("800"),
            "average_order_value": Decimal("400"),
            "cost_of_goods_sold": Decimal("500"),
        }
        with (
            patch(
                "app.application.reporting.revenue_service.revenue_repo.get_revenue_summary",
                new=AsyncMock(side_effect=[current, previous]),
            ),
            patch(
                "app.application.reporting.revenue_service.revenue_repo.get_revenue_series",
                new=AsyncMock(
                    return_value=[
                        {
                            "period_start": date(2026, 7, 1),
                            "gross_revenue": Decimal("1200"),
                            "refund_amount": Decimal("200"),
                            "net_revenue": Decimal("1000"),
                        }
                    ]
                ),
            ),
            patch(
                "app.application.reporting.revenue_service.revenue_repo.get_revenue_breakdowns",
                new=AsyncMock(
                    return_value={
                        "channels": [
                            {
                                "key": "ONLINE",
                                "completed_orders": 3,
                                "gross_revenue": Decimal("1200"),
                                "refund_amount": Decimal("200"),
                                "net_revenue": Decimal("1000"),
                            }
                        ],
                        "payment_methods": [],
                    }
                ),
            ),
        ):
            report = await get_revenue_report(
                AsyncMock(),
                period=period,
                include_profit=True,
            )

        self.assertEqual(report.summary.netRevenue, Decimal("1000"))
        self.assertEqual(report.summary.grossProfit, Decimal("400"))
        self.assertEqual(report.comparison.revenueChangePercent, Decimal("25.00"))
        self.assertEqual(report.breakdowns.channels[0].key, "ONLINE")

    async def test_hides_profit_fields_without_permission(self) -> None:
        summary = {
            "completed_orders": 0,
            "gross_revenue": Decimal("0"),
            "refund_amount": Decimal("0"),
            "net_revenue": Decimal("0"),
            "average_order_value": Decimal("0"),
            "cost_of_goods_sold": Decimal("900"),
        }
        with (
            patch(
                "app.application.reporting.revenue_service.revenue_repo.get_revenue_summary",
                new=AsyncMock(side_effect=[summary, summary]),
            ),
            patch(
                "app.application.reporting.revenue_service.revenue_repo.get_revenue_series",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.application.reporting.revenue_service.revenue_repo.get_revenue_breakdowns",
                new=AsyncMock(return_value={"channels": [], "payment_methods": []}),
            ),
        ):
            report = await get_revenue_report(
                AsyncMock(),
                period=build_report_period(
                    from_date=date(2026, 7, 1),
                    to_date=date(2026, 8, 1),
                ),
                include_profit=False,
            )

        self.assertIsNone(report.summary.costOfGoodsSold)
        self.assertIsNone(report.summary.grossProfit)


if __name__ == "__main__":
    unittest.main()
