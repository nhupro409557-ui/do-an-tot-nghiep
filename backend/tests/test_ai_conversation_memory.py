import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from redis.exceptions import RedisError

from app.application.ai.conversation_memory import (
    ConversationMemoryService,
    ConversationMemorySnapshot,
    active_entities_from_context,
    resolve_follow_up,
)
from app.application.ai.intent_router import route_intent
from app.application.ai.schemas import AIAssistantResponse


class AIConversationResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conversation_id = uuid4()
        self.memory = ConversationMemorySnapshot(
            conversation_id=self.conversation_id,
            user_id=None,
            active_intent="PRODUCT_SEARCH",
            active_entities={
                "products": [
                    {"id": "p1", "name": "OPPO Reno15 5G"},
                    {"id": "p2", "name": "Samsung Galaxy A57 5G"},
                ],
                "order": {"orderCode": "EMV4212922531", "status": "SHIPPING"},
            },
        )

    def test_resolves_ordinal_product_before_routing(self) -> None:
        resolved = resolve_follow_up("Con thứ hai pin bao nhiêu?", self.memory)
        self.assertIn("Samsung Galaxy A57 5G", resolved)
        self.assertNotEqual(route_intent(resolved).intent, "OUT_OF_SCOPE")

    def test_resolves_short_product_pronoun(self) -> None:
        resolved = resolve_follow_up("Nó còn màu đen không?", self.memory)
        self.assertIn("OPPO Reno15 5G", resolved)
        self.assertEqual(route_intent(resolved).intent, "STOCK_AVAILABILITY")

    def test_product_follow_up_with_word_thieu_is_not_misread_as_complaint(self) -> None:
        resolved = resolve_follow_up("Camera chụp thiếu sáng thế nào?", self.memory)
        self.assertIn("OPPO Reno15 5G", resolved)
        self.assertEqual(route_intent(resolved).intent, "PRODUCT_REVIEW")

    def test_resolves_order_follow_up(self) -> None:
        resolved = resolve_follow_up("Khi nào tới?", self.memory)
        self.assertIn("EMV4212922531", resolved)
        self.assertIn(route_intent(resolved).intent, {"ORDER_LOOKUP", "SHIPPING_LOOKUP"})

    def test_does_not_replace_explicit_product(self) -> None:
        message = "iPhone 17 Pro còn hàng không?"
        self.assertEqual(resolve_follow_up(message, self.memory), message)

    def test_affirmation_after_handover_becomes_staff_request(self) -> None:
        self.memory.handover_offered_at = datetime.now(timezone.utc)
        resolved = resolve_follow_up("Đồng ý", self.memory)
        self.assertIn("nhân viên chăm sóc khách hàng", resolved)
        self.assertEqual(route_intent(resolved).intent, "COMPLAINT")

    def test_extracts_verified_entities_without_copying_sensitive_fields(self) -> None:
        entities = active_entities_from_context(
            {
                "products": [{"id": "p1", "name": "Điện thoại mẫu", "price": 10_000_000}],
                "order": {"orderCode": "EMV4212922531", "recipientPhone": "0900000000"},
            },
            {},
        )
        self.assertEqual(entities["products"][0], {"id": "p1", "name": "Điện thoại mẫu", "slug": None})
        self.assertEqual(entities["order"], {"orderCode": "EMV4212922531", "status": None})


class AIConversationFailureTrackingTest(unittest.IsolatedAsyncioTestCase):
    async def test_offers_handover_after_two_repeated_unresolved_turns(self) -> None:
        conversation_id = uuid4()
        service = ConversationMemoryService(session=object(), redis=None)
        response = AIAssistantResponse(
            conversation_id=conversation_id,
            answer="Bạn muốn hỏi sản phẩm nào?",
            intent="PRODUCT_SEARCH",
            needs_clarification=True,
            clarification_question="Bạn muốn hỏi sản phẩm nào?",
            answer_mode="DETERMINISTIC",
            provider_used="SYSTEM",
            verification_passed=True,
        )
        memory = ConversationMemorySnapshot(
            conversation_id=conversation_id,
            user_id=None,
            active_intent="PRODUCT_SEARCH",
            pending_slots={"intent": "PRODUCT_SEARCH"},
        )
        with (
            patch("app.application.ai.conversation_memory.redis_is_available", return_value=False),
            patch(
                "app.application.ai.conversation_memory.ai_repo.update_ai_conversation_session",
                new=AsyncMock(return_value=True),
            ),
        ):
            first = await service.record_turn(
                memory=memory,
                user_message="Mẫu đó",
                response=response,
            )
            second = await service.record_turn(
                memory=first.snapshot,
                user_message="Mẫu đó",
                response=response,
            )

        self.assertEqual(first.snapshot.unresolved_streak, 1)
        self.assertFalse(first.should_offer_handover)
        self.assertEqual(second.snapshot.unresolved_streak, 2)
        self.assertTrue(second.should_offer_handover)


class AIConversationCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_loads_session_state_from_redis_cache(self) -> None:
        conversation_id = uuid4()
        redis = AsyncMock()
        redis.get.return_value = (
            '{"userId": null, "activeIntent": "PRODUCT_SEARCH", '
            '"activeEntities": {"products": [{"id": "p1", "name": "Điện thoại mẫu"}]}, '
            '"pendingSlots": {}, "summary": "Đang tư vấn sản phẩm.", '
            '"unresolvedStreak": 0, "lastFailureReason": null, "handoverOfferedAt": null}'
        )
        service = ConversationMemoryService(session=object(), redis=redis)

        with (
            patch("app.application.ai.conversation_memory.redis_is_available", return_value=True),
            patch(
                "app.application.ai.conversation_memory.ai_repo.get_or_create_ai_conversation_session",
                new=AsyncMock(),
            ) as database_load,
            patch(
                "app.application.ai.conversation_memory.ai_repo.get_recent_ai_conversation_turns",
                new=AsyncMock(return_value=[]),
            ),
        ):
            memory = await service.load(conversation_id=conversation_id, user_id=None)

        self.assertEqual(memory.active_intent, "PRODUCT_SEARCH")
        self.assertEqual(memory.active_entities["products"][0]["name"], "Điện thoại mẫu")
        database_load.assert_not_awaited()

    async def test_falls_back_to_database_when_redis_fails(self) -> None:
        conversation_id = uuid4()
        redis = AsyncMock()
        redis.get.side_effect = RedisError("Redis tạm thời không khả dụng")
        database_row = {
            "activeIntent": "ORDER_LOOKUP",
            "activeEntities": {"order": {"orderCode": "EMV001"}},
            "pendingSlots": {},
            "summary": "Đang tra cứu đơn hàng.",
            "unresolvedStreak": 0,
            "lastFailureReason": None,
            "handoverOfferedAt": None,
        }
        service = ConversationMemoryService(session=object(), redis=redis)

        with (
            patch("app.application.ai.conversation_memory.redis_is_available", return_value=True),
            patch("app.application.ai.conversation_memory.mark_redis_unavailable") as mark_unavailable,
            patch(
                "app.application.ai.conversation_memory.ai_repo.get_or_create_ai_conversation_session",
                new=AsyncMock(return_value=database_row),
            ) as database_load,
            patch(
                "app.application.ai.conversation_memory.ai_repo.get_recent_ai_conversation_turns",
                new=AsyncMock(return_value=[]),
            ),
        ):
            memory = await service.load(conversation_id=conversation_id, user_id=None)

        self.assertEqual(memory.active_intent, "ORDER_LOOKUP")
        database_load.assert_awaited_once()
        mark_unavailable.assert_called_once()


if __name__ == "__main__":
    unittest.main()
