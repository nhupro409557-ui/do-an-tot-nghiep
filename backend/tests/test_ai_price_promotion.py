import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases
from app.application.ai.intent_router import route_intent
from app.application.ai.use_cases import (
    AIAssistantUseCase,
    price_intent_from_message,
    render_product_fallback,
)


FIXTURE = Path(__file__).parent / "fixtures" / "ai_price_promotion_cases.jsonl"
DIALOGUES = Path(__file__).parent / "fixtures" / "ai_price_promotion_dialogues.json"


class AIPricePromotionDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(FIXTURE)

    def test_filtered_dataset_has_expected_distribution(self) -> None:
        self.assertEqual(len(self.cases), 289)
        self.assertEqual(len({case.id for case in self.cases}), 289)
        self.assertEqual(
            Counter(case.category for case in self.cases),
            {
                "price_promotion_basic": 19,
                "price_promotion_budget_search": 18,
                "price_promotion_discount": 17,
                "price_promotion_timing": 20,
                "price_promotion_voucher": 20,
                "price_promotion_conditions": 20,
                "price_promotion_stacking": 15,
                "price_promotion_bundle_gift": 20,
                "price_promotion_member": 20,
                "price_promotion_payment": 20,
                "price_promotion_shipping": 15,
                "price_promotion_price_change": 15,
                "price_promotion_invoice_tax": 15,
                "price_promotion_refund_return": 15,
                "price_promotion_ambiguous": 15,
                "price_promotion_advanced": 25,
            },
        )
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"CLARIFY": 232, "PLANNED": 35, "LIVE": 22})

    def test_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_ambiguous_price_questions_require_clarification(self) -> None:
        cases = [case for case in self.cases if case.category == "price_promotion_ambiguous"]
        self.assertEqual(len(cases), 15)
        for case in cases:
            with self.subTest(message=case.message):
                decision = route_intent(case.message)
                self.assertEqual(decision.intent, "PRICE_AND_PROMOTION")
                self.assertTrue(decision.needs_clarification)

    def test_in_scope_multiturn_dialogue_messages_are_routable(self) -> None:
        dialogues = json.loads(DIALOGUES.read_text(encoding="utf-8"))
        self.assertEqual(len(dialogues), 4)
        self.assertEqual(sum(len(dialogue["turns"]) for dialogue in dialogues), 25)
        for dialogue in dialogues:
            for turn in dialogue["turns"]:
                with self.subTest(dialogue=dialogue["id"], message=turn["message"]):
                    decision = route_intent(turn["message"])
                    self.assertIn(decision.intent, turn["expected_intents"])
                    self.assertNotEqual(decision.route, "POLICY")


class AIPricePromotionAnswerTest(unittest.TestCase):
    def test_product_fallback_states_discount_amount_and_percentage(self) -> None:
        answer = render_product_fallback(
            "PRICE_AND_PROMOTION",
            [
                {
                    "name": "Điện thoại A",
                    "price": 10_000_000,
                    "salePrice": 8_000_000,
                    "availableStock": 5,
                }
            ],
        )

        self.assertIn("giá hiện tại 8.000.000đ", answer)
        self.assertIn("giá gốc 10.000.000đ", answer)
        self.assertIn("giảm 2.000.000đ (20%)", answer)

    def test_relative_budget_increase_is_not_parsed_as_absolute_product_price(self) -> None:
        self.assertEqual(
            price_intent_from_message("Nếu tăng ngân sách thêm 1 triệu, tôi có lựa chọn nào tốt hơn?"),
            (None, None),
        )


class AIPricePromotionRetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_discount_queries_filter_and_rank_real_sale_prices(self) -> None:
        rows = [
            {"id": "discount-25", "name": "Máy giảm 25%", "price": 10_000_000, "salePrice": 7_500_000},
            {"id": "discount-10", "name": "Máy giảm 10%", "price": 10_000_000, "salePrice": 9_000_000},
            {"id": "no-discount", "name": "Máy không giảm", "price": 10_000_000, "salePrice": 10_000_000},
        ]
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            discounted = await use_case._find_products("Cho tôi xem tất cả sản phẩm đang giảm giá.")
            above_twenty = await use_case._find_products("Có sản phẩm nào giảm trên 20% không?")

        self.assertEqual([product["id"] for product in discounted], ["discount-25", "discount-10"])
        self.assertEqual([product["id"] for product in above_twenty], ["discount-25"])

    async def test_three_cheapest_query_returns_three_products_in_price_order(self) -> None:
        rows = [
            {"id": "p4", "name": "Máy 4", "price": 4_000_000},
            {"id": "p1", "name": "Máy 1", "price": 1_000_000},
            {"id": "p3", "name": "Máy 3", "price": 3_000_000},
            {"id": "p2", "name": "Máy 2", "price": 2_000_000},
        ]
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            products = await use_case._find_products("Cho tôi xem ba sản phẩm rẻ nhất.")

        self.assertEqual([product["id"] for product in products], ["p1", "p2", "p3"])


if __name__ == "__main__":
    unittest.main()
