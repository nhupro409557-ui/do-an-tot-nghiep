import json
import unittest
from collections import Counter
from pathlib import Path

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases
from app.application.ai.intent_router import route_intent
from app.application.ai.store_policy_context import _policy_topic, render_store_policy_answer
from app.application.ai.use_cases import AIAssistantUseCase


FIXTURES_DIR = Path(__file__).parent / "fixtures"
GROUP_COUNTS = {
    7: 65,
    8: 55,
    9: 45,
    10: 57,
    11: 50,
    12: 47,
    13: 54,
    14: 43,
    15: 43,
    16: 40,
    17: 40,
    18: 53,
    19: 54,
    20: 75,
}
DIALOGUES = FIXTURES_DIR / "ai_business_07_20_dialogues.json"


class AIBusinessGroupsDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases_by_group = {
            group: load_evaluation_cases(FIXTURES_DIR / f"ai_business_{group:02d}_cases.jsonl")
            for group in GROUP_COUNTS
        }
        cls.cases = [case for cases in cls.cases_by_group.values() for case in cases]

    def test_groups_are_separate_and_have_expected_counts(self) -> None:
        self.assertEqual({group: len(cases) for group, cases in self.cases_by_group.items()}, GROUP_COUNTS)
        self.assertEqual(len(self.cases), 721)
        self.assertEqual(len({case.id for case in self.cases}), 721)

    def test_support_levels_are_explicit(self) -> None:
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"LIVE": 547, "CLARIFY": 174})

    def test_each_group_passes_router_release_gate(self) -> None:
        for group, cases in self.cases_by_group.items():
            with self.subTest(group=group):
                result = evaluate_router(cases)
                self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
                self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_multiturn_dialogues_are_routable(self) -> None:
        dialogues = json.loads(DIALOGUES.read_text(encoding="utf-8"))
        self.assertEqual(len(dialogues), 13)
        self.assertEqual(sum(len(dialogue["turns"]) for dialogue in dialogues), 70)
        for dialogue in dialogues:
            for turn in dialogue["turns"]:
                with self.subTest(group=dialogue["group"], message=turn["message"]):
                    decision = route_intent(turn["message"])
                    self.assertIn(decision.intent, turn["expected_intents"])
                    self.assertNotEqual(decision.route, "POLICY")

    def test_out_of_catalog_examples_are_excluded(self) -> None:
        messages = {case.message for case in self.cases}
        self.assertNotIn("Quần áo có co sau khi giặt không?", messages)
        self.assertNotIn("Giày có đúng size không?", messages)
        self.assertNotIn("Mỹ phẩm có gây kích ứng không?", messages)
        self.assertNotIn("Đồ gia dụng có tốn điện không?", messages)


class AIBusinessGroupsRoutingTest(unittest.TestCase):
    def test_cart_and_account_policy_answers_state_safe_boundaries(self) -> None:
        cart_answer = render_store_policy_answer({"topic": "CART_ORDER"})
        account_answer = render_store_policy_answer({"topic": "ACCOUNT"})

        self.assertEqual(_policy_topic("Sản phẩm trong giỏ có được giữ không?"), "CART_ORDER")
        self.assertIn("chưa được xem là đã giữ chắc chắn", cart_answer)
        self.assertIn("Không cung cấp mật khẩu, OTP, PIN hoặc CVV", account_answer)

    def test_rating_points_are_not_loyalty_points(self) -> None:
        self.assertEqual(route_intent("Điểm đánh giá trung bình là bao nhiêu?").intent, "PRODUCT_REVIEW")
        self.assertEqual(
            route_intent("iPhone 17 Pro khác Galaxy S26 Ultra ở điểm nào?").intent,
            "PRODUCT_COMPARISON",
        )

    def test_old_phone_number_is_not_a_used_phone(self) -> None:
        self.assertEqual(route_intent("Tôi mất số điện thoại cũ.").intent, "ACCOUNT_SUPPORT")

    def test_physical_hazard_gets_immediate_safety_guidance(self) -> None:
        decision = route_intent("Pin sản phẩm bị phồng.")
        self.assertEqual(decision.intent, "COMPLAINT")
        use_case = AIAssistantUseCase(session=None, redis=None)
        answer = use_case._fallback_answer(
            intent="COMPLAINT",
            retrieved_context={"urgent_support_topic": "FIRE_BATTERY"},
        )
        self.assertIn("ngừng sử dụng", answer)
        self.assertIn("114", answer)

    def test_account_fraud_never_requests_sensitive_codes(self) -> None:
        decision = route_intent("Có người yêu cầu tôi cung cấp OTP.")
        self.assertEqual(decision.intent, "COMPLAINT")
        use_case = AIAssistantUseCase(session=None, redis=None)
        answer = use_case._fallback_answer(
            intent="COMPLAINT",
            retrieved_context={"urgent_support_topic": "ACCOUNT_FRAUD"},
        )
        self.assertIn("không cung cấp OTP, PIN hoặc CVV", answer)
        self.assertIn("không thể tự khóa tài khoản", answer)


if __name__ == "__main__":
    unittest.main()
