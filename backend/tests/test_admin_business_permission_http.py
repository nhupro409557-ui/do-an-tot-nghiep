import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import httpx

from app.api.dependencies import get_user_permissions
from app.main import app


class AdminBusinessPermissionHttpTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.audit_patch = patch("app.main.audit_repo.insert_security_audit_log", new=AsyncMock())
        self.audit_patch.start()
        self.permissions: set[str] = set()

        async def current_permissions() -> set[str]:
            return self.permissions

        app.dependency_overrides[get_user_permissions] = current_permissions
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.audit_patch.stop()

    async def test_service_endpoints_return_403_without_service_permissions(self) -> None:
        service_id = uuid4()
        payload = {
            "code": "TEST-SERVICE",
            "name": "Dịch vụ kiểm thử",
            "serviceType": "SUPPORT_SERVICE",
        }
        requests = [
            ("GET", "/api/admin/attached-services", None),
            ("POST", "/api/admin/attached-services", payload),
            ("PATCH", f"/api/admin/attached-services/{service_id}", payload),
            ("DELETE", f"/api/admin/attached-services/{service_id}", None),
            ("PATCH", f"/api/admin/attached-services/{service_id}/deactivate", None),
            ("PATCH", f"/api/admin/attached-services/{service_id}/reactivate", None),
        ]
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                response = await self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 403, response.text)

    async def test_flash_sale_endpoints_return_403_without_flash_sale_permissions(self) -> None:
        sale_id = uuid4()
        payload = {
            "productId": str(uuid4()),
            "discountType": "PERCENT",
            "discountValue": 10,
        }
        requests = [
            ("GET", "/api/admin/flash-sales", None),
            ("POST", "/api/admin/flash-sales", payload),
            ("PATCH", f"/api/admin/flash-sales/{sale_id}", payload),
            ("DELETE", f"/api/admin/flash-sales/{sale_id}", None),
        ]
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                response = await self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 403, response.text)

    async def test_service_endpoints_allow_the_matching_permission(self) -> None:
        service_id = uuid4()
        payload = {
            "code": "TEST-SERVICE",
            "name": "Dịch vụ kiểm thử",
            "serviceType": "SUPPORT_SERVICE",
        }
        cases = [
            ("service:read", "GET", "/api/admin/attached-services", None, "list_attached_services", []),
            ("service:create", "POST", "/api/admin/attached-services", payload, "create_attached_service", {"id": str(service_id)}),
            ("service:update", "PATCH", f"/api/admin/attached-services/{service_id}", payload, "update_attached_service", {"ok": True}),
            ("service:delete", "DELETE", f"/api/admin/attached-services/{service_id}", None, "delete_attached_service", {"ok": True}),
            ("service:update", "PATCH", f"/api/admin/attached-services/{service_id}/deactivate", None, "deactivate_attached_service", {"ok": True}),
            ("service:update", "PATCH", f"/api/admin/attached-services/{service_id}/reactivate", None, "reactivate_attached_service", {"ok": True}),
        ]
        for permission, method, path, body, service_method, result in cases:
            with self.subTest(permission=permission, method=method, path=path):
                self.permissions = {permission}
                with patch(f"app.api.routers.admin_products.attached_service.{service_method}", new=AsyncMock(return_value=result)) as mocked:
                    response = await self.client.request(method, path, json=body)
                    self.assertLess(response.status_code, 400, response.text)
                    mocked.assert_awaited_once()

    async def test_flash_sale_endpoints_allow_the_matching_permission(self) -> None:
        sale_id = uuid4()
        payload = {
            "productId": str(uuid4()),
            "discountType": "PERCENT",
            "discountValue": 10,
        }
        cases = [
            ("flash_sale:read", "GET", "/api/admin/flash-sales", None, "list_flash_sales", []),
            ("flash_sale:create", "POST", "/api/admin/flash-sales", payload, "create_flash_sale", {"id": str(sale_id)}),
            ("flash_sale:update", "PATCH", f"/api/admin/flash-sales/{sale_id}", payload, "update_flash_sale", {"ok": True}),
            ("flash_sale:delete", "DELETE", f"/api/admin/flash-sales/{sale_id}", None, "delete_flash_sale", {"ok": True}),
        ]
        for permission, method, path, body, service_method, result in cases:
            with self.subTest(permission=permission, method=method, path=path):
                self.permissions = {permission}
                with patch(f"app.api.routers.admin_flash_sales.flash_sale_service.{service_method}", new=AsyncMock(return_value=result)) as mocked:
                    response = await self.client.request(method, path, json=body)
                    self.assertLess(response.status_code, 400, response.text)
                    mocked.assert_awaited_once()

    async def test_purchase_order_read_endpoints_return_403_without_inventory_read_permission(self) -> None:
        order_id = uuid4()
        for path in ("/api/admin/purchase-orders", f"/api/admin/purchase-orders/{order_id}"):
            with self.subTest(path=path):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 403, response.text)

    async def test_purchase_order_read_endpoints_allow_inventory_read_permission(self) -> None:
        order_id = uuid4()
        self.permissions = {"inventory:read"}
        cases = [
            ("/api/admin/purchase-orders", "list_purchase_orders", []),
            (f"/api/admin/purchase-orders/{order_id}", "get_purchase_order", {"id": str(order_id)}),
        ]
        for path, service_method, result in cases:
            with self.subTest(path=path):
                with patch(
                    f"app.api.routers.admin_purchase_orders.purchase_order_service.{service_method}",
                    new=AsyncMock(return_value=result),
                ) as mocked:
                    response = await self.client.get(path)
                    self.assertLess(response.status_code, 400, response.text)
                    mocked.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
