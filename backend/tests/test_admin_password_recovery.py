import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from starlette.requests import Request

from app.api.routers.auth_utils import ForgotPasswordRequest
from app.api.routers.auth_verification import forgot_password


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/forgot-password",
            "headers": [(b"user-agent", b"test-agent")],
            "client": ("127.0.0.1", 12345),
        }
    )


class AdminPasswordRecoveryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session = AsyncMock()
        self.user = SimpleNamespace(
            id=uuid4(),
            email="nhupro409557@gmail.com",
            full_name="Huỳnh Nhu",
        )

    async def test_admin_reset_email_and_response_preserve_admin_context(self) -> None:
        with (
            patch("app.api.routers.auth_verification.ensure_auth_verification_tables", new=AsyncMock()),
            patch("app.api.routers.auth_verification.enforce_rate_limit"),
            patch(
                "app.api.routers.auth_verification.auth_repo.get_active_user_by_email",
                new=AsyncMock(return_value=self.user),
            ),
            patch(
                "app.api.routers.auth_verification.auth_repo.list_permissions_for_user",
                new=AsyncMock(return_value=["admin.access"]),
            ),
            patch("app.api.routers.auth_verification.auth_repo.delete_password_reset_by_email", new=AsyncMock()),
            patch("app.api.routers.auth_verification.auth_repo.insert_password_reset_token", new=AsyncMock()),
            patch("app.api.routers.auth_verification.send_auth_email") as send_email,
        ):
            result = await forgot_password(
                payload=ForgotPasswordRequest(email=self.user.email),
                request=make_request(),
                session=self.session,
            )

        self.assertTrue(result.adminContext)
        self.assertIn("&context=admin", send_email.call_args.args[3])

    async def test_customer_reset_does_not_gain_admin_context(self) -> None:
        customer = SimpleNamespace(id=uuid4(), email="customer@example.com", full_name="Khách hàng")
        with (
            patch("app.api.routers.auth_verification.ensure_auth_verification_tables", new=AsyncMock()),
            patch("app.api.routers.auth_verification.enforce_rate_limit"),
            patch(
                "app.api.routers.auth_verification.auth_repo.get_active_user_by_email",
                new=AsyncMock(return_value=customer),
            ),
            patch(
                "app.api.routers.auth_verification.auth_repo.list_permissions_for_user",
                new=AsyncMock(return_value=[]),
            ),
            patch("app.api.routers.auth_verification.auth_repo.delete_password_reset_by_email", new=AsyncMock()),
            patch("app.api.routers.auth_verification.auth_repo.insert_password_reset_token", new=AsyncMock()),
            patch("app.api.routers.auth_verification.send_auth_email") as send_email,
        ):
            result = await forgot_password(
                payload=ForgotPasswordRequest(email=customer.email),
                request=make_request(),
                session=self.session,
            )

        self.assertFalse(result.adminContext)
        self.assertNotIn("context=admin", send_email.call_args.args[3])


if __name__ == "__main__":
    unittest.main()
