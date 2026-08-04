import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.api.dependencies import get_current_user_id, get_user_permissions
from app.application.reporting.export_job_service import (
    download_report_export,
    list_report_export_jobs,
)
from app.application.reporting.schemas import (
    AdminCustomerReportResponse,
    AdminOrderReportResponse,
    AdminProductReportResponse,
    AdminRevenueReportResponse,
)
from app.main import app


def _period(bucket: str = "day") -> dict:
    return {
        "fromDate": date(2026, 7, 1),
        "toDate": date(2026, 8, 1),
        "timezone": "Asia/Bangkok",
        "bucket": bucket,
    }


def _revenue_report() -> AdminRevenueReportResponse:
    return AdminRevenueReportResponse.model_validate(
        {
            "period": _period(),
            "summary": {
                "completedOrders": 0,
                "grossRevenue": Decimal("0"),
                "refundAmount": Decimal("0"),
                "netRevenue": Decimal("0"),
                "averageOrderValue": Decimal("0"),
            },
            "comparison": {
                "previousNetRevenue": Decimal("0"),
                "previousCompletedOrders": 0,
            },
            "series": [],
            "breakdowns": {"channels": [], "paymentMethods": []},
        }
    )


def _order_report() -> AdminOrderReportResponse:
    return AdminOrderReportResponse.model_validate(
        {
            "period": _period(),
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
            "pagination": {"page": 1, "limit": 20, "total": 0, "totalPages": 0},
        }
    )


def _product_report() -> AdminProductReportResponse:
    return AdminProductReportResponse.model_validate(
        {
            "period": _period(),
            "summary": {
                "totalProducts": 0,
                "unitsSold": 0,
                "grossRevenue": Decimal("0"),
                "allocatedDiscount": Decimal("0"),
                "refundAmount": Decimal("0"),
                "netRevenue": Decimal("0"),
                "unallocatedRefundAmount": Decimal("0"),
            },
            "items": [],
            "pagination": {"page": 1, "limit": 20, "total": 0, "totalPages": 0},
        }
    )


def _customer_report() -> AdminCustomerReportResponse:
    return AdminCustomerReportResponse.model_validate(
        {
            "period": _period("month"),
            "summary": {
                "newCustomers": 0,
                "activeCustomers": 0,
                "firstTimeBuyers": 0,
                "returningCustomers": 0,
                "repeatPurchaseRate": Decimal("0"),
            },
            "tiers": [],
            "items": [],
            "pagination": {"page": 1, "limit": 20, "total": 0, "totalPages": 0},
        }
    )


class AdminReportPermissionHttpTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.audit_patch = patch(
            "app.main.audit_repo.insert_security_audit_log",
            new=AsyncMock(),
        )
        self.audit_patch.start()
        self.permissions: set[str] = set()
        self.user_id = uuid4()

        async def current_permissions() -> set[str]:
            return self.permissions

        async def current_user_id():
            return self.user_id

        app.dependency_overrides[get_user_permissions] = current_permissions
        app.dependency_overrides[get_current_user_id] = current_user_id
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.audit_patch.stop()

    async def test_revenue_permission_cannot_read_other_report_domains(self) -> None:
        self.permissions = {"report:revenue_read"}
        cases = [
            (
                "/api/admin/reports/orders",
                "app.api.routers.admin_reports.get_order_report",
                _order_report(),
            ),
            (
                "/api/admin/reports/products",
                "app.api.routers.admin_reports.get_product_report",
                _product_report(),
            ),
            (
                "/api/admin/reports/customers",
                "app.api.routers.admin_reports.get_customer_report",
                _customer_report(),
            ),
        ]
        for path, target, report in cases:
            with self.subTest(path=path), patch(
                target,
                new=AsyncMock(return_value=report),
            ):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 403, response.text)

    async def test_each_report_domain_accepts_its_matching_read_permission(self) -> None:
        cases = [
            (
                "report:revenue_read",
                "/api/admin/reports/revenue",
                "app.api.routers.admin_reports.get_revenue_report",
                _revenue_report(),
            ),
            (
                "order:read",
                "/api/admin/reports/orders",
                "app.api.routers.admin_reports.get_order_report",
                _order_report(),
            ),
            (
                "product:read",
                "/api/admin/reports/products",
                "app.api.routers.admin_reports.get_product_report",
                _product_report(),
            ),
            (
                "customer:read",
                "/api/admin/reports/customers",
                "app.api.routers.admin_reports.get_customer_report",
                _customer_report(),
            ),
        ]
        for permission, path, target, report in cases:
            with self.subTest(permission=permission), patch(
                target,
                new=AsyncMock(return_value=report),
            ):
                self.permissions = {permission}
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)

    async def test_export_job_rejects_report_type_without_matching_permission(self) -> None:
        self.permissions = {"report:revenue_read"}
        payload = {
            "reportType": "orders",
            "from": "2026-07-01",
            "to": "2026-08-01",
        }
        with patch(
            "app.api.routers.admin_reports.create_report_export_job",
            new=AsyncMock(return_value={"jobId": str(uuid4()), "status": "PENDING"}),
        ) as mocked:
            response = await self.client.post("/api/admin/reports/exports", json=payload)

        self.assertEqual(response.status_code, 403, response.text)
        mocked.assert_not_awaited()


class ReportExportPermissionServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_only_queries_report_types_allowed_for_current_user(self) -> None:
        session = AsyncMock()
        with patch(
            "app.application.reporting.export_job_service.export_job_repo.list_export_jobs",
            new=AsyncMock(return_value=[]),
        ) as mocked:
            result = await list_report_export_jobs(
                session,
                requested_by=uuid4(),
                permissions={"order:read"},
            )

        self.assertEqual(result, [])
        self.assertEqual(mocked.await_args.kwargs["report_types"], ["orders"])

    async def test_download_rechecks_permission_for_job_report_type(self) -> None:
        session = AsyncMock()
        job = {
            "id": str(uuid4()),
            "reportType": "customers",
            "status": "COMPLETED",
            "filePath": "unused.csv",
            "filename": "unused.csv",
            "expiresAt": None,
        }
        with patch(
            "app.application.reporting.export_job_service.export_job_repo.get_export_job",
            new=AsyncMock(return_value=job),
        ):
            with self.assertRaises(HTTPException) as context:
                await download_report_export(
                    session,
                    job_id=uuid4(),
                    requested_by=uuid4(),
                    permissions={"report:revenue_read"},
                )

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
