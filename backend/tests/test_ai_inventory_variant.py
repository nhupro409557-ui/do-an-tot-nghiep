import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases
from app.application.ai.intent_router import route_intent
from app.application.ai.use_cases import (
    AIAssistantUseCase,
    matching_product_variants,
    render_product_fallback,
)


FIXTURE = Path(__file__).parent / "fixtures" / "ai_inventory_variant_cases.jsonl"
DIALOGUES = Path(__file__).parent / "fixtures" / "ai_inventory_variant_dialogues.json"


class AIInventoryVariantDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(FIXTURE)

    def test_filtered_dataset_has_expected_distribution(self) -> None:
        self.assertEqual(len(self.cases), 302)
        self.assertEqual(len({case.id for case in self.cases}), 302)
        self.assertEqual(
            Counter(case.category for case in self.cases),
            {
                "inventory_variant_basic_stock": 14,
                "inventory_variant_quantity": 15,
                "inventory_variant_versions": 19,
                "inventory_variant_colors": 18,
                "inventory_variant_configuration": 20,
                "inventory_variant_branches": 19,
                "inventory_variant_restock": 19,
                "inventory_variant_preorder": 20,
                "inventory_variant_hold": 15,
                "inventory_variant_display_open_box": 15,
                "inventory_variant_discontinued": 15,
                "inventory_variant_codes": 14,
                "inventory_variant_combined": 17,
                "inventory_variant_replacement": 18,
                "inventory_variant_sync": 15,
                "inventory_variant_mismatch": 15,
                "inventory_variant_ambiguous": 14,
                "inventory_variant_advanced": 20,
            },
        )
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"CLARIFY": 211, "PLANNED": 85, "LIVE": 6})

    def test_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_ambiguous_stock_questions_require_clarification(self) -> None:
        cases = [case for case in self.cases if case.category == "inventory_variant_ambiguous"]
        self.assertEqual(len(cases), 14)
        for case in cases:
            with self.subTest(message=case.message):
                decision = route_intent(case.message)
                self.assertTrue(decision.needs_clarification)

    def test_branch_stock_question_requires_location_clarification(self) -> None:
        decision = route_intent("Chi nhánh gần tôi còn không?")

        self.assertEqual(decision.intent, "STOCK_AVAILABILITY")
        self.assertTrue(decision.needs_clarification)

    def test_in_scope_multiturn_dialogue_messages_are_routable(self) -> None:
        dialogues = json.loads(DIALOGUES.read_text(encoding="utf-8"))
        self.assertEqual(len(dialogues), 3)
        self.assertEqual(sum(len(dialogue["turns"]) for dialogue in dialogues), 20)
        for dialogue in dialogues:
            for turn in dialogue["turns"]:
                with self.subTest(dialogue=dialogue["id"], message=turn["message"]):
                    decision = route_intent(turn["message"])
                    self.assertIn(decision.intent, turn["expected_intents"])
                    self.assertNotEqual(decision.route, "POLICY")


class AIInventoryVariantAnswerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.product = {
            "id": "iphone-17-pro",
            "name": "iPhone 17 Pro",
            "availableStock": 10,
            "variants": [
                {
                    "sku": "IP17-BLK-256",
                    "colorName": "Đen",
                    "storage": "256 GB",
                    "ram": "12 GB",
                    "availableStock": 3,
                },
                {
                    "sku": "IP17-SLV-512",
                    "colorName": "Bạc",
                    "storage": "512 GB",
                    "ram": "12 GB",
                    "availableStock": 7,
                },
            ],
        }

    def test_variant_match_uses_color_and_storage_together(self) -> None:
        requested, variants = matching_product_variants(self.product, "Bản 256 GB màu đen còn hàng không?")

        self.assertTrue(requested)
        self.assertEqual([variant["sku"] for variant in variants], ["IP17-BLK-256"])

    def test_product_reference_mau_do_is_not_a_red_variant_request(self) -> None:
        requested, variants = matching_product_variants(
            self.product,
            "iPhone 17 Pro còn hàng không? Mẫu đó hiện còn hàng không?",
        )

        self.assertFalse(requested)
        self.assertEqual(variants, [])

    def test_stock_answer_uses_variant_stock_instead_of_product_total(self) -> None:
        product = dict(self.product)
        product["variantSelectionRequested"] = True
        product["matchedVariants"] = [self.product["variants"][0]]

        answer = render_product_fallback("STOCK_AVAILABILITY", [product])

        self.assertIn("IP17-BLK-256", answer)
        self.assertIn("còn 3 sản phẩm khả dụng", answer)
        self.assertNotIn("còn 10 sản phẩm", answer)


class AIInventoryVariantRetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_page_product_query_keeps_exact_variant_match(self) -> None:
        rows = [
            {
                "id": "iphone-17-pro",
                "slug": "iphone-17-pro",
                "name": "iPhone 17 Pro",
                "variants": [
                    {"sku": "IP17-BLK-256", "colorName": "Đen", "storage": "256 GB", "availableStock": 3},
                    {"sku": "IP17-SLV-512", "colorName": "Bạc", "storage": "512 GB", "availableStock": 7},
                ],
            }
        ]
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            products = await use_case._find_products(
                "Bản 256 GB màu đen còn hàng không?",
                page_product_id="iphone-17-pro",
            )

        self.assertTrue(products[0]["variantSelectionRequested"])
        self.assertEqual([variant["sku"] for variant in products[0]["matchedVariants"]], ["IP17-BLK-256"])


if __name__ == "__main__":
    unittest.main()
