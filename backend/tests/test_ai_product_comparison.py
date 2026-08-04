import json
import unittest
from collections import Counter
from pathlib import Path

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases
from app.application.ai.intent_router import route_intent


FIXTURE = Path(__file__).parent / "fixtures" / "ai_product_comparison_cases.jsonl"
DIALOGUES = Path(__file__).parent / "fixtures" / "ai_product_comparison_dialogues.json"


class AIProductComparisonDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(FIXTURE)

    def test_filtered_dataset_has_expected_distribution(self) -> None:
        self.assertEqual(len(self.cases), 243)
        self.assertEqual(len({case.id for case in self.cases}), 243)
        self.assertEqual(
            Counter(case.category for case in self.cases),
            {
                "product_comparison_basic": 13,
                "product_comparison_price": 13,
                "product_comparison_specification": 15,
                "product_comparison_design": 15,
                "product_comparison_durability": 14,
                "product_comparison_warranty": 15,
                "product_comparison_need": 15,
                "product_comparison_audience": 15,
                "product_comparison_experience": 15,
                "product_comparison_popularity": 15,
                "product_comparison_availability": 15,
                "product_comparison_brand": 13,
                "product_comparison_multiple": 20,
                "product_comparison_objective": 15,
                "product_comparison_ambiguous": 15,
                "product_comparison_advanced": 20,
            },
        )
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"CLARIFY": 147, "PLANNED": 96})

    def test_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_ambiguous_comparisons_require_clarification(self) -> None:
        cases = [case for case in self.cases if case.category == "product_comparison_ambiguous"]
        self.assertEqual(len(cases), 15)
        for case in cases:
            with self.subTest(message=case.message):
                decision = route_intent(case.message)
                self.assertIn(decision.intent, case.expected_intents)
                self.assertTrue(decision.needs_clarification)

    def test_in_scope_multiturn_dialogue_messages_are_routable(self) -> None:
        dialogues = json.loads(DIALOGUES.read_text(encoding="utf-8"))
        self.assertEqual(len(dialogues), 2)
        for dialogue in dialogues:
            for turn in dialogue["turns"]:
                with self.subTest(dialogue=dialogue["id"], message=turn["message"]):
                    decision = route_intent(turn["message"])
                    self.assertIn(decision.intent, turn["expected_intents"])
                    self.assertNotEqual(decision.route, "POLICY")


if __name__ == "__main__":
    unittest.main()
