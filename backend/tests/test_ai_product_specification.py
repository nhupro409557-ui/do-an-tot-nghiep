import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases
from app.application.ai.intent_router import route_intent
from app.application.ai.use_cases import AIAssistantUseCase


FIXTURE = Path(__file__).parent / "fixtures" / "ai_product_specification_cases.jsonl"
DIALOGUES = Path(__file__).parent / "fixtures" / "ai_product_specification_dialogues.json"


class AIProductSpecificationDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(FIXTURE)

    def test_filtered_dataset_has_expected_distribution(self) -> None:
        self.assertEqual(len(self.cases), 296)
        self.assertEqual(len({case.id for case in self.cases}), 296)
        self.assertEqual(
            Counter(case.category for case in self.cases),
            {
                "product_specification_basic": 15,
                "product_specification_size_weight": 15,
                "product_specification_material": 14,
                "product_specification_power": 14,
                "product_specification_battery": 20,
                "product_specification_performance": 15,
                "product_specification_memory": 20,
                "product_specification_display": 20,
                "product_specification_camera": 20,
                "product_specification_audio": 15,
                "product_specification_connectivity": 20,
                "product_specification_durability": 15,
                "product_specification_software": 15,
                "product_specification_compatibility": 15,
                "product_specification_explanation": 14,
                "product_specification_reconciliation": 15,
                "product_specification_ambiguous": 14,
                "product_specification_advanced": 20,
            },
        )
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"PLANNED": 173, "CLARIFY": 123})

    def test_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_ambiguous_specification_questions_require_clarification(self) -> None:
        cases = [case for case in self.cases if case.category == "product_specification_ambiguous"]
        self.assertEqual(len(cases), 14)
        for case in cases:
            with self.subTest(message=case.message):
                decision = route_intent(case.message)
                self.assertIn(decision.intent, case.expected_intents)
                self.assertTrue(decision.needs_clarification)

    def test_in_scope_multiturn_dialogue_messages_are_routable(self) -> None:
        dialogues = json.loads(DIALOGUES.read_text(encoding="utf-8"))
        self.assertEqual(len(dialogues), 2)
        self.assertEqual(sum(len(dialogue["turns"]) for dialogue in dialogues), 14)
        for dialogue in dialogues:
            for turn in dialogue["turns"]:
                with self.subTest(dialogue=dialogue["id"], message=turn["message"]):
                    decision = route_intent(turn["message"])
                    self.assertIn(decision.intent, turn["expected_intents"])
                    self.assertNotEqual(decision.route, "POLICY")


class AIProductSpecificationRetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_page_product_is_used_for_generic_specification_question(self) -> None:
        rows = [
            {"id": "target-id", "slug": "dien-thoai-muc-tieu", "name": "Điện thoại mục tiêu"},
            {"id": "other-id", "slug": "dien-thoai-khac", "name": "Điện thoại khác"},
        ]
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            products = await use_case._find_products(
                "Sản phẩm này có bao nhiêu RAM?",
                page_product_id="dien-thoai-muc-tieu",
            )

        self.assertEqual([product["id"] for product in products], ["target-id"])


if __name__ == "__main__":
    unittest.main()
