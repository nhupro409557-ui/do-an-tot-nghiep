import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from google.genai import errors
from google.genai._gaos.lib.compat_errors import APITimeoutError

from app.application.ai.gemini_interactions import (
    GeminiInteractionError,
    GeminiInteractionResult,
    create_gemini_interaction,
)
from app.application.ai.schemas import AIAssistantRequest, DynamicAIContext
from app.application.ai.use_cases import AIAssistantUseCase
from app.config import settings


class _FakeInteractions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[dict] = []

    async def create(self, **body):
        self.requests.append(body)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.interactions = _FakeInteractions(responses)
        self.aio = SimpleNamespace(
            interactions=self.interactions,
            aclose=self._close,
        )
        self.closed = False

    async def _close(self) -> None:
        self.closed = True


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, **kwargs):
        self.values[key] = value
        if kwargs.get("ex") is not None:
            self.expirations[key] = int(kwargs["ex"])

    async def delete(self, key: str):
        self.values.pop(key, None)


class GeminiInteractionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_executes_interactions_function_call_and_returns_tool_context(self) -> None:
        fake_client = _FakeClient(
            [
                SimpleNamespace(
                    output_text="",
                    id="interaction-tool-call",
                    steps=[
                        SimpleNamespace(
                            type="function_call",
                            name="search_products",
                            id="call-1",
                            arguments={"query": "iPhone"},
                        )
                    ],
                ),
                SimpleNamespace(
                    output_text="Mình tìm thấy sản phẩm phù hợp.",
                    id="interaction-final",
                    steps=[],
                ),
            ]
        )
        handler = AsyncMock(return_value={"products": [{"id": "product-1"}]})

        with patch(
            "app.application.ai.gemini_interactions.genai.Client",
            return_value=fake_client,
        ):
            result = await create_gemini_interaction(
                api_key="test-key",
                model="gemini-3.5-flash",
                system_instruction="Chỉ dùng dữ liệu tool.",
                input_text="Tư vấn iPhone",
                previous_interaction_id=None,
                thinking_level="low",
                timeout_seconds=1,
                max_retries=0,
                tools=[{"type": "function", "name": "search_products"}],
                tool_handler=handler,
                max_tool_calls=4,
            )

        self.assertEqual(result.answer, "Mình tìm thấy sản phẩm phù hợp.")
        self.assertEqual(result.interaction_id, "interaction-final")
        self.assertEqual(result.tool_results[0]["name"], "search_products")
        self.assertEqual(fake_client.interactions.requests[1]["previous_interaction_id"], "interaction-tool-call")
        self.assertEqual(fake_client.interactions.requests[1]["input"][0]["type"], "function_result")
        handler.assert_awaited_once_with("search_products", {"query": "iPhone"})

    async def test_retries_busy_model_and_preserves_conversation_state(self) -> None:
        busy = errors.ServerError(
            503,
            {"error": {"code": 503, "status": "UNAVAILABLE", "message": "busy"}},
        )
        fake_client = _FakeClient(
            [busy, SimpleNamespace(output_text="  Xin chào  ", id="interaction-2")]
        )

        with patch(
            "app.application.ai.gemini_interactions.genai.Client",
            return_value=fake_client,
        ):
            result = await create_gemini_interaction(
                api_key="test-key",
                model="gemini-3.5-flash",
                system_instruction="Trả lời bằng tiếng Việt.",
                input_text="Tư vấn điện thoại",
                previous_interaction_id="interaction-1",
                thinking_level="low",
                timeout_seconds=1,
                max_retries=1,
            )

        self.assertEqual(result.answer, "Xin chào")
        self.assertEqual(result.interaction_id, "interaction-2")
        self.assertEqual(len(fake_client.interactions.requests), 2)
        self.assertEqual(
            fake_client.interactions.requests[1]["previous_interaction_id"],
            "interaction-1",
        )
        self.assertEqual(
            fake_client.interactions.requests[1]["generation_config"]["thinking_level"],
            "low",
        )
        self.assertTrue(fake_client.closed)

    async def test_falls_back_to_31_flash_lite_when_35_flash_is_rate_limited(self) -> None:
        redis = _FakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)
        request = AIAssistantRequest(
            conversation_id=uuid4(),
            message="Tư vấn điện thoại",
            dynamic_context=DynamicAIContext(),
        )
        call_gemini = AsyncMock(
            side_effect=[
                GeminiInteractionError("MODEL_RATE_LIMITED"),
                GeminiInteractionResult(
                    answer="Đây là câu trả lời từ model dự phòng.",
                    interaction_id="fallback-interaction",
                ),
            ]
        )

        with (
            patch.object(settings, "gemini_api_key", "test-key"),
            patch.object(settings, "gemini_model", "gemini-3.5-flash"),
            patch.object(settings, "gemini_fallback_model", "gemini-3.1-flash-lite"),
            patch.object(use_case, "_call_gemini", call_gemini),
        ):
            generated = await use_case._generate_answer(
                request,
                intent="PRODUCT_ADVICE",
                retrieved_context={},
            )

        self.assertEqual(generated.answer_mode, "GEMINI")
        self.assertEqual(generated.model_name, "gemini-3.1-flash-lite")
        self.assertEqual(call_gemini.await_count, 2)
        self.assertEqual(call_gemini.await_args_list[0].kwargs["model"], "gemini-3.5-flash")
        self.assertEqual(
            call_gemini.await_args_list[1].kwargs["model"],
            "gemini-3.1-flash-lite",
        )
        stored_state = redis.values[f"ai:interaction:{request.conversation_id}"]
        self.assertIn('"model": "gemini-3.1-flash-lite"', stored_state)
        self.assertEqual(redis.values["ai:circuit-open:gemini-3.5-flash"], "1")

    async def test_rate_limit_does_not_retry_same_model(self) -> None:
        rate_limited = errors.ClientError(
            429,
            {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}},
        )
        fake_client = _FakeClient([rate_limited])

        with patch("app.application.ai.gemini_interactions.genai.Client", return_value=fake_client):
            with self.assertRaisesRegex(GeminiInteractionError, "MODEL_RATE_LIMITED"):
                await create_gemini_interaction(
                    api_key="test-key",
                    model="gemini-3.5-flash",
                    system_instruction="Trả lời bằng tiếng Việt.",
                    input_text="So sánh hai sản phẩm",
                    previous_interaction_id=None,
                    thinking_level="low",
                    timeout_seconds=1,
                    max_retries=3,
                )

        self.assertEqual(len(fake_client.interactions.requests), 1)

    async def test_reports_invalid_previous_interaction_without_retry(self) -> None:
        bad_request = errors.ClientError(
            400,
            {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "invalid"}},
        )
        fake_client = _FakeClient([bad_request])

        with patch(
            "app.application.ai.gemini_interactions.genai.Client",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(
                GeminiInteractionError,
                "INVALID_INTERACTION_STATE",
            ):
                await create_gemini_interaction(
                    api_key="test-key",
                    model="gemini-3.5-flash",
                    system_instruction="Trả lời bằng tiếng Việt.",
                    input_text="Tiếp tục",
                    previous_interaction_id="expired-interaction",
                    thinking_level="low",
                    timeout_seconds=1,
                    max_retries=2,
                )

        self.assertEqual(len(fake_client.interactions.requests), 1)
        self.assertTrue(fake_client.closed)

    async def test_converts_interactions_sdk_timeout_to_fallback_reason(self) -> None:
        timeout = APITimeoutError(httpx.Request("POST", "https://example.test/interactions"))
        fake_client = _FakeClient([timeout])

        with patch(
            "app.application.ai.gemini_interactions.genai.Client",
            return_value=fake_client,
        ):
            with self.assertRaisesRegex(GeminiInteractionError, "MODEL_TIMEOUT"):
                await create_gemini_interaction(
                    api_key="test-key",
                    model="gemini-3.5-flash",
                    system_instruction="Trả lời bằng tiếng Việt.",
                    input_text="Tư vấn điện thoại",
                    previous_interaction_id=None,
                    thinking_level="low",
                    timeout_seconds=1,
                    max_retries=0,
                )

        self.assertTrue(fake_client.closed)


if __name__ == "__main__":
    unittest.main()
