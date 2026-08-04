import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt

from app.application.ai.conversation_token import (
    TOKEN_TYPE,
    issue_conversation_token,
    validate_conversation_token,
)
from app.config import settings


class AIConversationTokenTest(unittest.TestCase):
    def test_accepts_signed_guest_conversation(self) -> None:
        conversation_id = uuid4()
        token, expires_at = issue_conversation_token(
            conversation_id=conversation_id,
            user_id=None,
            ttl_minutes=30,
        )

        validate_conversation_token(token, conversation_id=conversation_id, user_id=None)
        self.assertGreater(expires_at, datetime.now(timezone.utc))

    def test_rejects_different_conversation(self) -> None:
        token, _ = issue_conversation_token(
            conversation_id=uuid4(),
            user_id=None,
            ttl_minutes=30,
        )

        with self.assertRaisesRegex(ValueError, "không thuộc"):
            validate_conversation_token(token, conversation_id=uuid4(), user_id=None)

    def test_rejects_conversation_of_different_user(self) -> None:
        conversation_id = uuid4()
        token, _ = issue_conversation_token(
            conversation_id=conversation_id,
            user_id=uuid4(),
            ttl_minutes=30,
        )

        with self.assertRaisesRegex(ValueError, "không thuộc"):
            validate_conversation_token(token, conversation_id=conversation_id, user_id=uuid4())

    def test_rejects_expired_token(self) -> None:
        conversation_id = uuid4()
        expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        token = jwt.encode(
            {
                "typ": TOKEN_TYPE,
                "cid": str(conversation_id),
                "uid": None,
                "exp": int(expired_at.timestamp()),
            },
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with self.assertRaisesRegex(ValueError, "hết hạn"):
            validate_conversation_token(token, conversation_id=conversation_id, user_id=None)


if __name__ == "__main__":
    unittest.main()
