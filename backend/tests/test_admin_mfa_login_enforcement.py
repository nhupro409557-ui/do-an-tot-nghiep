import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException, Response
from starlette.requests import Request

from app.api.routers.auth import login
from app.api.routers.auth_social import google_login
from app.api.routers.auth_utils import GoogleLoginRequest, LoginRequest


def make_request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"user-agent", b"test-agent")],
            "client": ("127.0.0.1", 12345),
        }
    )


class AdminMfaLoginEnforcementTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.user = SimpleNamespace(
            id=uuid4(),
            role_id=uuid4(),
            email="admin@example.com",
            password_hash="hashed-password",
            full_name="Quản trị viên",
            profile_json={},
        )
        self.session = AsyncMock()

    async def test_password_login_rejects_admin_account_before_issuing_token(self) -> None:
        with (
            patch(
                "app.api.routers.auth.auth_repo.get_active_user_by_email",
                new=AsyncMock(return_value=self.user),
            ),
            patch("app.api.routers.auth.pwd_context.verify", return_value=True),
            patch(
                "app.api.routers.auth_utils.auth_repo.list_permissions_for_user",
                new=AsyncMock(return_value=["admin:read"]),
            ),
            patch("app.api.routers.auth_utils.audit_log", new=AsyncMock()),
            patch("app.api.routers.auth.issue_auth_response", new=AsyncMock()) as issue_response,
        ):
            with self.assertRaises(HTTPException) as raised:
                await login(
                    payload=LoginRequest(email=self.user.email, password="correct-password"),
                    request=make_request("/api/auth/login"),
                    response=Response(),
                    session=self.session,
                )

        self.assertEqual(raised.exception.status_code, 403)
        issue_response.assert_not_awaited()

    async def test_google_login_rejects_existing_admin_account_before_issuing_token(self) -> None:
        with (
            patch(
                "app.api.routers.auth_social._verified_google_profile",
                new=AsyncMock(
                    return_value={
                        "email": self.user.email,
                        "name": self.user.full_name,
                        "picture": None,
                    }
                ),
            ),
            patch(
                "app.api.routers.auth_social.auth_repo.get_active_user_by_email",
                new=AsyncMock(return_value=self.user),
            ),
            patch(
                "app.api.routers.auth_social.auth_repo.list_permissions_for_user",
                new=AsyncMock(return_value=["admin:read"]),
            ),
            patch("app.api.routers.auth_utils.audit_log", new=AsyncMock()),
            patch("app.api.routers.auth_social.issue_auth_response", new=AsyncMock()) as issue_response,
        ):
            with self.assertRaises(HTTPException) as raised:
                await google_login(
                    payload=GoogleLoginRequest(credential="x" * 20),
                    request=make_request("/api/auth/google"),
                    response=Response(),
                    session=self.session,
                )

        self.assertEqual(raised.exception.status_code, 403)
        issue_response.assert_not_awaited()

    async def test_password_login_still_allows_customer_without_admin_permissions(self) -> None:
        expected = object()
        with (
            patch(
                "app.api.routers.auth.auth_repo.get_active_user_by_email",
                new=AsyncMock(return_value=self.user),
            ),
            patch("app.api.routers.auth.pwd_context.verify", return_value=True),
            patch(
                "app.api.routers.auth_utils.auth_repo.list_permissions_for_user",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.api.routers.auth.issue_auth_response",
                new=AsyncMock(return_value=expected),
            ) as issue_response,
        ):
            result = await login(
                payload=LoginRequest(email=self.user.email, password="correct-password"),
                request=make_request("/api/auth/login"),
                response=Response(),
                session=self.session,
            )

        self.assertIs(result, expected)
        issue_response.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
