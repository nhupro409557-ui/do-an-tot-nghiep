import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from starlette.requests import Request

from app.api.routers.auth_mfa_recovery import (
    AdminMfaRecoveryVerifyRequest,
    hash_mfa_recovery_code,
    mask_email,
    start_admin_mfa_recovery,
    verify_admin_mfa_recovery,
)


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/admin/mfa-recovery",
            "headers": [(b"user-agent", b"test-agent")],
            "client": ("127.0.0.1", 12345),
        }
    )


class AdminMfaRecoveryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.user = SimpleNamespace(
            id=self.user_id,
            role_id=uuid4(),
            email="nhupro409557@gmail.com",
            full_name="Huỳnh Nhu",
        )
        self.session = AsyncMock()

    def test_hash_mfa_recovery_code_does_not_store_plaintext(self) -> None:
        digest = hash_mfa_recovery_code(self.user_id, "123456")

        self.assertNotEqual(digest, "123456")
        self.assertEqual(digest, hash_mfa_recovery_code(self.user_id, "123456"))
        self.assertNotEqual(digest, hash_mfa_recovery_code(self.user_id, "654321"))

    def test_mask_email_hides_most_of_the_mailbox(self) -> None:
        self.assertEqual(mask_email("nhupro409557@gmail.com"), "nh***57@gmail.com")

    async def test_start_requires_a_password_verified_mfa_challenge(self) -> None:
        with patch(
            "app.api.routers.auth_mfa_recovery.decode_admin_mfa_token",
                return_value=(self.user_id, "mfa_setup", "challenge-jti"),
        ):
            with self.assertRaises(HTTPException) as raised:
                await start_admin_mfa_recovery(
                    request=make_request(),
                    authorization="Bearer token",
                    session=self.session,
                )

        self.assertEqual(raised.exception.status_code, 401)

    async def test_start_sends_email_and_stores_only_the_code_hash(self) -> None:
        replace_recovery = AsyncMock()
        with (
            patch(
                "app.api.routers.auth_mfa_recovery.decode_admin_mfa_token",
                return_value=(self.user_id, "mfa_verify", "challenge-jti"),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery._get_recovery_user",
                new=AsyncMock(return_value=self.user),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery.auth_repo.replace_admin_mfa_recovery",
                new=replace_recovery,
            ),
            patch("app.api.routers.auth_mfa_recovery.audit_log", new=AsyncMock()),
            patch("app.api.routers.auth_mfa_recovery.send_auth_email") as send_email,
        ):
            result = await start_admin_mfa_recovery(
                request=make_request(),
                authorization="Bearer token",
                session=self.session,
            )

        sent_code = send_email.call_args.args[2]
        stored_hash = replace_recovery.await_args.kwargs["code_hash"]
        self.assertEqual(result.email, "nh***57@gmail.com")
        self.assertTrue(result.recoveryToken)
        self.assertRegex(sent_code, r"^\d{6}$")
        self.assertNotEqual(stored_hash, sent_code)
        self.assertEqual(stored_hash, hash_mfa_recovery_code(self.user_id, sent_code))

    async def test_verify_valid_email_code_returns_a_fresh_mfa_setup(self) -> None:
        code = "123456"
        recovery = {
            "code_hash": hash_mfa_recovery_code(self.user_id, code),
            "challenge_jti": "challenge-jti",
            "attempt_count": 0,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            "consumed_at": None,
        }
        patches = [
            patch(
                "app.api.routers.auth_mfa_recovery.decode_admin_mfa_token",
                return_value=(self.user_id, "mfa_recovery", "challenge-jti"),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery._get_recovery_user",
                new=AsyncMock(return_value=self.user),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery.auth_repo.get_admin_mfa_recovery_for_update",
                new=AsyncMock(return_value=recovery),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery.auth_repo.consume_admin_mfa_recovery",
                new=AsyncMock(),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery.auth_repo.upsert_admin_mfa_secret",
                new=AsyncMock(),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery.auth_repo.revoke_all_user_refresh_sessions",
                new=AsyncMock(),
            ),
            patch(
                "app.api.routers.auth_mfa_recovery.auth_repo.upsert_auth_session_revocation",
                new=AsyncMock(),
            ),
            patch("app.api.routers.auth_mfa_recovery.audit_log", new=AsyncMock()),
        ]
        started = [item.start() for item in patches]
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])

        result = await verify_admin_mfa_recovery(
            payload=AdminMfaRecoveryVerifyRequest(code=code),
            request=make_request(),
            authorization="Bearer token",
            session=self.session,
        )

        self.assertTrue(result.requiresMfaSetup)
        self.assertFalse(result.requiresMfa)
        self.assertIsNotNone(result.mfaSecret)
        self.assertIn("otpauth://", result.otpauthUrl or "")
        started[3].assert_awaited_once_with(self.session, self.user_id)
        started[5].assert_awaited_once_with(self.session, self.user_id)


if __name__ == "__main__":
    unittest.main()
