import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.application.ai.contracts import VerificationResult
from app.application.ai.gemini_interactions import GeminiInteractionError
from app.application.ai.local_circuit_breaker import (
    clear_local_model_state,
    get_local_circuit_status,
)
from app.application.ai.schemas import AIAssistantRequest
from app.application.ai.use_cases import AIAssistantUseCase, GeneratedAnswer
from app.config import settings


class _StatefulFakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, **kwargs):
        self.values[key] = str(value)
        if kwargs.get("ex") is not None:
            self.expirations[key] = int(kwargs["ex"])

    async def delete(self, key: str):
        self.values.pop(key, None)
        self.expirations.pop(key, None)

    async def incr(self, key: str):
        value = int(self.values.get(key, "0")) + 1
        self.values[key] = str(value)
        return value

    async def expire(self, key: str, seconds: int):
        self.expirations[key] = seconds


class AIResilienceTest(unittest.IsolatedAsyncioTestCase):
    def test_comparison_prefers_lite_model_for_latency(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with (
            patch.object(settings, "ai_model_routing_enabled", True),
            patch.object(settings, "gemini_model", "gemini-primary"),
            patch.object(settings, "gemini_fallback_model", "gemini-lite"),
        ):
            models = use_case._models_for_intent("PRODUCT_COMPARISON")

        self.assertEqual(models, ["gemini-lite", "gemini-primary"])

    async def test_redis_outage_uses_process_local_circuit_breaker(self) -> None:
        model = "gemini-local-fallback"
        clear_local_model_state(model)
        use_case = AIAssistantUseCase(session=None, redis=None)

        with patch("app.application.ai.use_cases.redis_is_available", return_value=False):
            for _ in range(3):
                await use_case._record_model_failure(model)
            self.assertTrue(await use_case._is_model_circuit_open(model))

        status = get_local_circuit_status(model)
        self.assertTrue(status["open"])
        self.assertEqual(status["status"], "LOCAL_FALLBACK")
        clear_local_model_state(model)

    async def test_three_provider_failures_open_circuit_for_120_seconds(self) -> None:
        redis = _StatefulFakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)

        for _ in range(3):
            await use_case._record_model_failure("gemini-test")

        self.assertEqual(redis.values["ai:circuit-open:gemini-test"], "1")
        self.assertEqual(redis.expirations["ai:circuit-open:gemini-test"], 120)
        self.assertNotIn("ai:model-failures:gemini-test", redis.values)

    async def test_rate_limit_opens_circuit_immediately(self) -> None:
        redis = _StatefulFakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)

        with patch.object(settings, "ai_model_rate_limit_circuit_seconds", 300):
            await use_case._record_model_failure("gemini-rate-limited", reason="MODEL_RATE_LIMITED")

        self.assertEqual(redis.values["ai:circuit-open:gemini-rate-limited"], "1")
        self.assertEqual(redis.expirations["ai:circuit-open:gemini-rate-limited"], 300)
        self.assertNotIn("ai:model-failures:gemini-rate-limited", redis.values)

    async def test_timeout_opens_short_circuit_immediately(self) -> None:
        redis = _StatefulFakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)

        with patch.object(settings, "ai_model_timeout_circuit_seconds", 60):
            await use_case._record_model_failure("gemini-timeout", reason="MODEL_TIMEOUT")

        self.assertEqual(redis.values["ai:circuit-open:gemini-timeout"], "1")
        self.assertEqual(redis.expirations["ai:circuit-open:gemini-timeout"], 60)

    async def test_both_models_timeout_returns_database_fallback_with_reasons(self) -> None:
        redis = _StatefulFakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)
        request = AIAssistantRequest(conversation_id=uuid4(), message="Tư vấn iPhone")

        with (
            patch.object(settings, "gemini_api_key", "test-key"),
            patch.object(settings, "gemini_model", "gemini-primary"),
            patch.object(settings, "gemini_fallback_model", "gemini-fallback"),
            patch.object(use_case, "_generate_with_model", new=AsyncMock(side_effect=GeminiInteractionError("MODEL_TIMEOUT"))),
        ):
            result = await use_case._generate_answer(
                request,
                intent="PRODUCT_RECOMMENDATION",
                retrieved_context={"products": []},
            )

        self.assertEqual(result.answer_mode, "DATABASE_FALLBACK")
        self.assertEqual(result.provider_used, "SYSTEM")
        self.assertIn("gemini-primary:MODEL_TIMEOUT", result.fallback_reason or "")
        self.assertIn("gemini-fallback:MODEL_TIMEOUT", result.fallback_reason or "")

    async def test_open_primary_circuit_skips_to_fallback_model(self) -> None:
        redis = _StatefulFakeRedis()
        redis.values["ai:circuit-open:gemini-primary"] = "1"
        use_case = AIAssistantUseCase(session=None, redis=redis)
        request = AIAssistantRequest(conversation_id=uuid4(), message="Tư vấn iPhone")
        generate = AsyncMock(
            return_value=type("Result", (), {"answer": "Kết quả dự phòng", "tool_results": ()})()
        )

        with (
            patch.object(settings, "gemini_api_key", "test-key"),
            patch.object(settings, "gemini_model", "gemini-primary"),
            patch.object(settings, "gemini_fallback_model", "gemini-fallback"),
            patch.object(use_case, "_generate_with_model", new=generate),
        ):
            result = await use_case._generate_answer(
                request,
                intent="PRODUCT_RECOMMENDATION",
                retrieved_context={},
            )

        self.assertEqual(result.model_name, "gemini-fallback")
        self.assertIn("gemini-primary:CIRCUIT_OPEN", result.fallback_reason or "")
        generate.assert_awaited_once()
        self.assertEqual(generate.await_args.kwargs["model"], "gemini-fallback")

    async def test_verifier_failure_replaces_model_answer_with_database_fallback(self) -> None:
        redis = _StatefulFakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)
        request = AIAssistantRequest(conversation_id=uuid4(), message="Tư vấn iPhone")
        generated = GeneratedAnswer(
            answer="Câu trả lời sai dữ kiện.",
            answer_mode="GEMINI",
            provider_used="GEMINI",
            model_name="gemini-test",
        )

        with (
            patch.object(settings, "ai_response_v2_enabled", True),
            patch.object(settings, "ai_chat_v2_percent", 100),
            patch.object(settings, "ai_verifier_enabled", True),
            patch.object(use_case, "_enforce_rate_limit", new=AsyncMock()),
            patch.object(use_case, "_cache_dynamic_context", new=AsyncMock()),
            patch.object(use_case, "_retrieve_context", new=AsyncMock(return_value={"products": []})),
            patch.object(use_case, "_generate_answer", new=AsyncMock(return_value=generated)),
            patch.object(use_case, "_log", new=AsyncMock()),
            patch(
                "app.application.ai.use_cases.verify_response",
                side_effect=[
                    VerificationResult(passed=False, errors=["PRICE_CLAIM_MISMATCH"]),
                    VerificationResult(passed=True),
                ],
            ),
        ):
            response = await use_case.execute(user_id=None, request=request)

        self.assertEqual(response.answer_mode, "DATABASE_FALLBACK")
        self.assertEqual(response.provider_used, "SYSTEM")
        self.assertEqual(response.fallback_reason, "VERIFIER_FAILED:PRICE_CLAIM_MISMATCH")
        self.assertTrue(response.verification_passed)

    async def test_shadow_mode_logs_v2_decision_without_changing_v1_response(self) -> None:
        redis = _StatefulFakeRedis()
        use_case = AIAssistantUseCase(session=None, redis=redis)
        request = AIAssistantRequest(conversation_id=uuid4(), message="Phí vận chuyển tính thế nào?")
        log = AsyncMock()

        with (
            patch.object(settings, "ai_response_v2_enabled", True),
            patch.object(settings, "ai_chat_v2_percent", 0),
            patch.object(settings, "ai_shadow_mode_enabled", True),
            patch.object(settings, "ai_router_v2_enabled", True),
            patch.object(use_case, "_enforce_rate_limit", new=AsyncMock()),
            patch.object(use_case, "_cache_dynamic_context", new=AsyncMock()),
            patch.object(use_case, "_retrieve_context", new=AsyncMock(return_value={})),
            patch.object(
                use_case,
                "_generate_answer",
                new=AsyncMock(
                    return_value=GeneratedAnswer(
                        answer="Thông tin chính sách.",
                        answer_mode="GEMINI",
                        provider_used="GEMINI",
                        model_name="gemini-test",
                    )
                ),
            ),
            patch.object(use_case, "_log", new=log),
        ):
            response = await use_case.execute(user_id=None, request=request)

        self.assertEqual(response.version, "1")
        self.assertEqual(response.intent, "PRODUCT_ADVICE")
        shadow = log.await_args.kwargs["shadow_decision"]
        self.assertEqual(shadow.intent, "STORE_POLICY")
        self.assertEqual(shadow.route, "DETERMINISTIC")
