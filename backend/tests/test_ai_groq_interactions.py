import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.application.ai.groq_interactions import (
    GroqInteractionError,
    create_groq_chat_completion,
)


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload: object | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "Groq API error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses: list[object], **_: object) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object):
        self.requests.append({"url": url, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class GroqInteractionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_answer_and_sends_api_key_only_in_authorization_header(self) -> None:
        fake_client = _FakeAsyncClient(
            [
                _FakeResponse(
                    payload={
                        "id": "chatcmpl-1",
                        "choices": [{"message": {"content": "  Xin chào từ Groq  "}}],
                    }
                )
            ]
        )

        with patch(
            "app.application.ai.groq_interactions.httpx.AsyncClient",
            return_value=fake_client,
        ):
            result = await create_groq_chat_completion(
                api_key="test-secret",
                model="openai/gpt-oss-120b",
                system_instruction="Trả lời bằng tiếng Việt.",
                input_text="Tư vấn điện thoại",
                timeout_seconds=1,
                max_retries=0,
                max_completion_tokens=700,
                reasoning_effort="medium",
            )

        self.assertEqual(result.answer, "Xin chào từ Groq")
        self.assertEqual(result.response_id, "chatcmpl-1")
        request = fake_client.requests[0]
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-secret")
        self.assertNotIn("test-secret", str(request["json"]))
        self.assertFalse(request["json"]["stream"])

    async def test_rate_limit_is_reported_without_retrying(self) -> None:
        fake_client = _FakeAsyncClient([_FakeResponse(status_code=429)])

        with patch(
            "app.application.ai.groq_interactions.httpx.AsyncClient",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(GroqInteractionError, "MODEL_RATE_LIMITED"):
                await create_groq_chat_completion(
                    api_key="test-secret",
                    model="openai/gpt-oss-120b",
                    system_instruction="Trả lời bằng tiếng Việt.",
                    input_text="Tư vấn điện thoại",
                    timeout_seconds=1,
                    max_retries=2,
                    max_completion_tokens=700,
                    reasoning_effort="medium",
                )

        self.assertEqual(len(fake_client.requests), 1)

    async def test_retries_busy_provider_then_returns_answer(self) -> None:
        fake_client = _FakeAsyncClient(
            [
                _FakeResponse(status_code=503),
                _FakeResponse(
                    payload={
                        "id": "chatcmpl-2",
                        "choices": [{"message": {"content": "Đã hoạt động lại."}}],
                    }
                ),
            ]
        )

        with (
            patch(
                "app.application.ai.groq_interactions.httpx.AsyncClient",
                return_value=fake_client,
            ),
            patch("app.application.ai.groq_interactions.asyncio.sleep", new=AsyncMock()),
        ):
            result = await create_groq_chat_completion(
                api_key="test-secret",
                model="openai/gpt-oss-120b",
                system_instruction="Trả lời bằng tiếng Việt.",
                input_text="Tư vấn điện thoại",
                timeout_seconds=1,
                max_retries=1,
                max_completion_tokens=700,
                reasoning_effort="medium",
            )

        self.assertEqual(result.answer, "Đã hoạt động lại.")
        self.assertEqual(len(fake_client.requests), 2)

    async def test_rejects_malformed_provider_response(self) -> None:
        fake_client = _FakeAsyncClient([_FakeResponse(payload=["invalid"])])

        with patch(
            "app.application.ai.groq_interactions.httpx.AsyncClient",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(GroqInteractionError, "EMPTY_MODEL_RESPONSE"):
                await create_groq_chat_completion(
                    api_key="test-secret",
                    model="openai/gpt-oss-120b",
                    system_instruction="Trả lời bằng tiếng Việt.",
                    input_text="Tư vấn điện thoại",
                    timeout_seconds=1,
                    max_retries=0,
                    max_completion_tokens=700,
                    reasoning_effort="medium",
                )

    async def test_rejects_invalid_json_response(self) -> None:
        fake_client = _FakeAsyncClient([_FakeResponse(payload=ValueError("invalid json"))])

        with patch(
            "app.application.ai.groq_interactions.httpx.AsyncClient",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(GroqInteractionError, "EMPTY_MODEL_RESPONSE"):
                await create_groq_chat_completion(
                    api_key="test-secret",
                    model="openai/gpt-oss-120b",
                    system_instruction="Trả lời bằng tiếng Việt.",
                    input_text="Tư vấn điện thoại",
                    timeout_seconds=1,
                    max_retries=0,
                    max_completion_tokens=700,
                    reasoning_effort="medium",
                )


if __name__ == "__main__":
    unittest.main()
