import unittest
from datetime import date
from decimal import Decimal

from app.application.reporting.export_service import (
    export_customers_csv,
    export_revenue_csv,
)
from app.application.reporting.schemas import (
    AdminCustomerReportResponse,
    AdminRevenueReportResponse,
)


class ReportExportServiceTest(unittest.TestCase):
    def test_revenue_csv_has_utf8_bom_and_vietnamese_headers(self) -> None:
        report = AdminRevenueReportResponse.model_validate(
            {
                "period": {
                    "fromDate": date(2026, 7, 1),
                    "toDate": date(2026, 7, 2),
                    "timezone": "Asia/Bangkok",
                    "bucket": "day",
                },
                "summary": {
                    "completedOrders": 1,
                    "grossRevenue": Decimal("100"),
                    "refundAmount": Decimal("10"),
                    "netRevenue": Decimal("90"),
                    "averageOrderValue": Decimal("90"),
                },
                "comparison": {
                    "previousNetRevenue": Decimal("0"),
                    "previousCompletedOrders": 0,
                },
                "series": [
                    {
                        "periodStart": date(2026, 7, 1),
                        "grossRevenue": Decimal("100"),
                        "refundAmount": Decimal("10"),
                        "netRevenue": Decimal("90"),
                    }
                ],
                "breakdowns": {"channels": [], "paymentMethods": []},
            }
        )

        response = export_revenue_csv(report)

        self.assertTrue(response.body.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Doanh thu gộp", response.body.decode("utf-8-sig"))

    def test_customer_csv_neutralizes_spreadsheet_formula_prefix(self) -> None:
        report = AdminCustomerReportResponse.model_validate(
            {
                "period": {
                    "fromDate": date(2026, 7, 1),
                    "toDate": date(2026, 8, 1),
                    "timezone": "Asia/Bangkok",
                    "bucket": "month",
                },
                "summary": {
                    "newCustomers": 1,
                    "activeCustomers": 0,
                    "firstTimeBuyers": 0,
                    "returningCustomers": 0,
                    "repeatPurchaseRate": Decimal("0"),
                },
                "tiers": [],
                "items": [
                    {
                        "id": "customer-1",
                        "fullName": "=HYPERLINK(\"https://example.com\")",
                        "email": "customer@example.com",
                        "tier": "MEMBER",
                        "registeredAt": "2026-07-01T00:00:00+00:00",
                        "orderCount": 0,
                        "netSpent": Decimal("0"),
                        "segment": "NEW_NO_ORDER",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 1,
                    "total": 1,
                    "totalPages": 1,
                },
            }
        )

        response = export_customers_csv(report)

        self.assertIn(
            "'=HYPERLINK",
            response.body.decode("utf-8-sig"),
        )


if __name__ == "__main__":
    unittest.main()
