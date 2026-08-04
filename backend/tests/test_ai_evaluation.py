import unittest
from collections import Counter
from pathlib import Path

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases


FIXTURE = Path(__file__).parent / "fixtures" / "ai_eval_cases.jsonl"


class AIEvaluationDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(FIXTURE)

    def test_dataset_has_310_unique_cases_in_expected_groups(self) -> None:
        self.assertEqual(len(self.cases), 310)
        self.assertEqual(len({case.id for case in self.cases}), 310)
        self.assertEqual(
            Counter(case.category for case in self.cases),
            {
                "product_price_variant": 45,
                "stock": 25,
                "comparison": 25,
                "order_shipping": 25,
                "warranty_after_sales": 25,
                "promotion": 20,
                "used_product": 15,
                "ambiguous_multiturn": 20,
                "policy_rag": 15,
                "scope_smalltalk": 30,
                "security": 25,
                "resilience": 20,
                "qa_holdout": 10,
                "store_service": 10,
            },
        )

    def test_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_security_cases_never_request_raw_sql(self) -> None:
        security_cases = [case for case in self.cases if case.category == "security"]
        self.assertTrue(security_cases)
        self.assertTrue(all("raw_sql" in case.forbidden_tools for case in security_cases))
