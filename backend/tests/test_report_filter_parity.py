import unittest
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.api.dependencies import get_user_permissions
from app.application.reporting.export_job_service import write_report_export_file
from app.application.reporting.schemas import (
    AdminCustomerReportResponse,
    AdminOrderReportResponse,
    ReportExportRequest,
)
from app.infrastructure.database.session import get_session
from app.main import app


def _order_report() -> AdminOrderReportResponse:
    return AdminOrderReportResponse.model_validate(
        {
            "period": {
                "fromDate": date(2026, 7, 1),
                "toDate": date(2026, 8, 1),
                "timezone": "Asia/Bangkok",
                "bucket": "day",
            },
            "dateBasis": "createdAt",
            "summary": {
                "totalOrders": 0,
                "completedOrders": 0,
                "cancelledOrders": 0,
                "totalAmount": Decimal("0"),
                "averageOrderValue": Decimal("0"),
            },
            "breakdowns": {
                "statuses": [],
                "channels": [],
                "paymentMethods": [],
                "paymentStatuses": [],
                "fulfillmentMethods": [],
            },
            "items": [],
            "pagination": {"page": 1, "limit": 1, "total": 0, "totalPages": 0},
        }
    )


def _customer_report() -> AdminCustomerReportResponse:
    return AdminCustomerReportResponse.model_validate(
        {
            "period": {
                "fromDate": date(2026, 7, 1),
                "toDate": date(2026, 8, 1),
                "timezone": "Asia/Bangkok",
                "bucket": "month",
            },
            "summary": {
                "newCustomers": 0,
                "activeCustomers": 0,
                "firstTimeBuyers": 0,
                "returningCustomers": 0,
                "repeatPurchaseRate": Decimal("0"),
            },
            "tiers": [],
            "items": [],
            "pagination": {"page": 1, "limit": 1, "total": 0, "totalPages": 0},
        }
    )


class ReportExportRequestFilterTest(unittest.TestCase):
    def test_background_export_contract_keeps_domain_filters(self) -> None:
        request = ReportExportRequest.model_validate(
            {
                "reportType": "orders",
                "from": "2026-07-01",
                "to": "2026-08-01",
                "paymentStatus": "PAID",
                "fulfillmentMethod": "DELIVERY",
                "tier": "GOLD",
                "segment": "RETURNING",
            }
        )

        filters = request.model_dump(
            by_alias=True,
            exclude={"reportType"},
            exclude_none=True,
            mode="json",
        )

        self.assertEqual(filters["paymentStatus"], "PAID")
        self.assertEqual(filters["fulfillmentMethod"], "DELIVERY")
        self.assertEqual(filters["tier"], "GOLD")
        self.assertEqual(filters["segment"], "RETURNING")


class SynchronousExportFilterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def session_override():
            yield AsyncMock()

        self.permissions: set[str] = set()

        async def permissions_override() -> set[str]:
            return self.permissions

        app.dependency_overrides[get_session] = session_override
        app.dependency_overrides[get_user_permissions] = permissions_override
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()

    async def test_order_csv_forwards_all_order_filters(self) -> None:
        self.permissions = {"order:read"}
        with patch(
            "app.api.routers.admin_reports.get_order_report",
            new=AsyncMock(return_value=_order_report()),
        ) as mocked:
            response = await self.client.get(
                "/api/admin/reports/orders/export",
                params={
                    "from": "2026-07-01",
                    "to": "2026-08-01",
                    "paymentStatus": "PAID",
                    "fulfillmentMethod": "DELIVERY",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(mocked.await_args.kwargs["payment_status"], "PAID")
        self.assertEqual(
            mocked.await_args.kwargs["fulfillment_method"],
            "DELIVERY",
        )

    async def test_customer_csv_forwards_all_customer_filters(self) -> None:
        self.permissions = {"customer:read"}
        with patch(
            "app.api.routers.admin_reports.get_customer_report",
            new=AsyncMock(return_value=_customer_report()),
        ) as mocked:
            response = await self.client.get(
                "/api/admin/reports/customers/export",
                params={
                    "from": "2026-07-01",
                    "to": "2026-08-01",
                    "tier": "GOLD",
                    "segment": "RETURNING",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(mocked.await_args.kwargs["tier"], "GOLD")
        self.assertEqual(mocked.await_args.kwargs["segment"], "RETURNING")


class BackgroundExportFilterTest(unittest.IsolatedAsyncioTestCase):
    async def test_order_job_forwards_all_order_filters(self) -> None:
        with patch(
            "app.application.reporting.export_job_service.get_order_report",
            new=AsyncMock(return_value=_order_report()),
        ) as mocked:
            with tempfile.TemporaryDirectory() as directory:
                await write_report_export_file(
                    AsyncMock(),
                    "orders",
                    {
                        "from": "2026-07-01",
                        "to": "2026-08-01",
                        "paymentStatus": "PAID",
                        "fulfillmentMethod": "DELIVERY",
                    },
                    Path(directory) / "orders.csv",
                )

        self.assertEqual(mocked.await_args.kwargs["payment_status"], "PAID")
        self.assertEqual(
            mocked.await_args.kwargs["fulfillment_method"],
            "DELIVERY",
        )

    async def test_customer_job_forwards_all_customer_filters(self) -> None:
        with patch(
            "app.application.reporting.export_job_service.get_customer_report",
            new=AsyncMock(return_value=_customer_report()),
        ) as mocked:
            with tempfile.TemporaryDirectory() as directory:
                await write_report_export_file(
                    AsyncMock(),
                    "customers",
                    {
                        "from": "2026-07-01",
                        "to": "2026-08-01",
                        "tier": "GOLD",
                        "segment": "RETURNING",
                    },
                    Path(directory) / "customers.csv",
                )

        self.assertEqual(mocked.await_args.kwargs["tier"], "GOLD")
        self.assertEqual(mocked.await_args.kwargs["segment"], "RETURNING")


if __name__ == "__main__":
    unittest.main()
