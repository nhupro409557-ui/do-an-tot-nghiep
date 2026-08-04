import unittest

from app.application.ai.intent_router import route_intent
from app.application.ai.use_cases import AIAssistantUseCase
from app.application.ai.verification import verify_response
from app.application.services.loyalty_maintenance_service import loyalty_tier_progress


class AILoyaltyRoutingTest(unittest.TestCase):
    def test_routes_tier_progress_phrasings_to_loyalty(self) -> None:
        questions = (
            "Tôi cần bao nhiêu tiền nữa để lên hạng?",
            "Còn bao nhiêu doanh số để lên hạng Vàng?",
            "Bao giờ tôi được nâng hạng thành viên?",
            "Tiến độ thăng hạng của tôi thế nào?",
            "Doanh số xét hạng hiện tại là bao nhiêu?",
            "Tôi đang ở hạng thành viên nào?",
        )
        for question in questions:
            with self.subTest(question=question):
                decision = route_intent(question)
                self.assertEqual(decision.intent, "LOYALTY")
                self.assertEqual(decision.route, "DETERMINISTIC")


class AILoyaltyProgressTest(unittest.TestCase):
    def test_next_tier_uses_current_tier_and_period_spend(self) -> None:
        self.assertEqual(
            loyalty_tier_progress(current_tier="MEMBER", period_spend_amount=10_000_000),
            {
                "nextTier": "SILVER",
                "nextTierLabel": "Bạc",
                "nextTierTarget": 30_000_000,
                "amountToNextTier": 20_000_000,
            },
        )
        self.assertEqual(
            loyalty_tier_progress(current_tier="SILVER", period_spend_amount=40_000_000)["amountToNextTier"],
            40_000_000,
        )
        self.assertEqual(
            loyalty_tier_progress(current_tier="GOLD", period_spend_amount=100_000_000)["amountToNextTier"],
            50_000_000,
        )
        self.assertIsNone(
            loyalty_tier_progress(current_tier="DIAMOND", period_spend_amount=0)["nextTier"],
        )

    def test_loyalty_fallback_answers_points_spend_and_amount_to_next_tier(self) -> None:
        loyalty = {
            "pointsBalance": 1_250,
            "tier": "SILVER",
            "walletStatus": "ACTIVE",
            "periodSpendAmount": 40_000_000,
            "periodEndsAt": "2026-12-31T00:00:00+00:00",
            "nextTier": "GOLD",
            "nextTierLabel": "Vàng",
            "nextTierTarget": 80_000_000,
            "amountToNextTier": 40_000_000,
        }
        use_case = AIAssistantUseCase(session=None, redis=None)
        answer = use_case._fallback_answer(intent="LOYALTY", retrieved_context={"loyalty": loyalty})
        verification = verify_response(intent="LOYALTY", answer=answer, context={"loyalty": loyalty})

        self.assertIn("1.250 điểm", answer)
        self.assertIn("hạng Bạc", answer)
        self.assertIn("Doanh số xét hạng trong kỳ hiện tại là 40.000.000đ", answer)
        self.assertIn("cần mua thêm 40.000.000đ", answer.lower())
        self.assertIn("hạng Vàng", answer)
        self.assertIn("31/12/2026", answer)
        self.assertNotIn("T00:00:00", answer)
        self.assertTrue(verification.passed, verification.errors)
