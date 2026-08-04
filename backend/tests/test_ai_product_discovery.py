import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases
from app.application.ai.intent_router import route_intent
from app.application.ai.use_cases import AIAssistantUseCase, price_intent_from_message


PRODUCT_SEARCH_FIXTURE = Path(__file__).parent / "fixtures" / "ai_product_search_cases.jsonl"
PRODUCT_ADVICE_FIXTURE = Path(__file__).parent / "fixtures" / "ai_product_advice_cases.jsonl"
PRODUCT_ADVICE_DIALOGUES = Path(__file__).parent / "fixtures" / "ai_product_advice_dialogues.json"


class AIProductSearchDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(PRODUCT_SEARCH_FIXTURE)

    def test_filtered_dataset_has_expected_size_and_support_labels(self) -> None:
        self.assertEqual(len(self.cases), 144)
        self.assertEqual(len({case.id for case in self.cases}), 144)
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"LIVE": 107, "CLARIFY": 27, "PLANNED": 10})

    def test_product_search_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])


class AIProductAdviceDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_evaluation_cases(PRODUCT_ADVICE_FIXTURE)

    def test_filtered_advice_dataset_has_expected_distribution(self) -> None:
        self.assertEqual(len(self.cases), 243)
        self.assertEqual(len({case.id for case in self.cases}), 243)
        self.assertEqual(
            Counter(case.category for case in self.cases),
            {
                "product_advice_basic": 15,
                "product_advice_need": 20,
                "product_advice_budget": 20,
                "product_advice_audience": 20,
                "product_advice_attribute": 20,
                "product_advice_brand": 19,
                "product_advice_comparison": 20,
                "product_advice_replacement": 15,
                "product_advice_gift": 19,
                "product_advice_review": 20,
                "product_advice_long_term": 15,
                "product_advice_ambiguous": 15,
                "product_advice_advanced": 25,
            },
        )
        support_counts = Counter(
            next(part.split("=", 1)[1] for part in case.notes.split("; ") if part.startswith("support_level="))
            for case in self.cases
        )
        self.assertEqual(support_counts, {"LIVE": 5, "CLARIFY": 147, "PLANNED": 91})

    def test_product_advice_router_release_gate_is_at_least_97_percent(self) -> None:
        result = evaluate_router(self.cases)
        self.assertGreaterEqual(result.intent_accuracy, 0.97, result.failures[:10])
        self.assertGreaterEqual(result.route_accuracy, 0.97, result.failures[:10])

    def test_ambiguous_advice_questions_require_clarification(self) -> None:
        ambiguous_cases = [case for case in self.cases if case.category == "product_advice_ambiguous"]
        self.assertEqual(len(ambiguous_cases), 15)
        for case in ambiguous_cases:
            with self.subTest(message=case.message):
                decision = route_intent(case.message)
                self.assertEqual(decision.intent, "PRODUCT_RECOMMENDATION")
                self.assertTrue(decision.needs_clarification)

    def test_in_scope_multiturn_dialogue_messages_are_routable(self) -> None:
        dialogues = json.loads(PRODUCT_ADVICE_DIALOGUES.read_text(encoding="utf-8"))
        self.assertEqual(len(dialogues), 2)
        for dialogue in dialogues:
            for turn in dialogue["turns"]:
                with self.subTest(dialogue=dialogue["id"], message=turn["message"]):
                    decision = route_intent(turn["message"])
                    self.assertIn(decision.intent, turn["expected_intents"])
                    self.assertNotEqual(decision.route, "POLICY")


class AIProductDiscoveryRoutingTest(unittest.TestCase):
    def test_routes_newest_product_phrasings_as_product_search(self) -> None:
        questions = (
            "Sản phẩm mới thêm gần nhất của cửa hàng là gì?",
            "Cho tôi xem sản phẩm mới nhất",
            "Cửa hàng vừa thêm những sản phẩm nào?",
            "Điện thoại mới cập nhật gần đây",
            "Hàng mới về có gì?",
        )
        for question in questions:
            with self.subTest(question=question):
                decision = route_intent(question)
                self.assertEqual(decision.intent, "PRODUCT_SEARCH")
                self.assertEqual(decision.route, "MODEL")

    def test_parses_approximately_ten_million_budget(self) -> None:
        decision = route_intent("Điện thoại 10tr của cửa hàng là những máy nào?")
        self.assertEqual(decision.intent, "PRICE_AND_PROMOTION")
        self.assertEqual(decision.route, "DETERMINISTIC")
        self.assertEqual(
            price_intent_from_message("Điện thoại 10tr của cửa hàng là những máy nào?"),
            (9_000_000, 11_000_000),
        )

    def test_parses_vnd_and_million_price_ranges(self) -> None:
        self.assertEqual(
            price_intent_from_message("Tìm sản phẩm dưới 500.000 đồng."),
            (None, 500_000),
        )
        self.assertEqual(
            price_intent_from_message("Cho tôi xem sản phẩm từ 500.000 đồng trở lên."),
            (500_000, None),
        )
        self.assertEqual(
            price_intent_from_message("Có laptop nào từ 20 đến 25 triệu không?"),
            (20_000_000, 25_000_000),
        )
        self.assertEqual(
            price_intent_from_message("Có sản phẩm nào đúng giá 999.000 đồng không?"),
            (999_000, 999_000),
        )


class AIProductDiscoveryRetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_newest_phone_query_sorts_by_created_time_and_filters_category(self) -> None:
        rows = [
            {
                "id": "phone-old",
                "name": "Điện thoại cũ hơn",
                "categorySlug": "smartphones",
                "categoryName": "Điện thoại",
                "createdAt": "2026-07-01T00:00:00+00:00",
            },
            {
                "id": "laptop-new",
                "name": "Laptop mới nhất",
                "categorySlug": "laptops",
                "categoryName": "Laptop",
                "createdAt": "2026-07-14T00:00:00+00:00",
            },
            {
                "id": "phone-new",
                "name": "Điện thoại mới nhất",
                "categorySlug": "smartphones",
                "categoryName": "Điện thoại",
                "createdAt": "2026-07-13T00:00:00+00:00",
            },
        ]
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            products = await use_case._find_products("Điện thoại mới thêm gần nhất của cửa hàng")

        self.assertEqual([product["id"] for product in products], ["phone-new", "phone-old"])

    async def test_sku_in_active_variant_participates_in_product_search(self) -> None:
        rows = [
            {
                "id": "matching-product",
                "name": "Điện thoại có biến thể cần tìm",
                "variants": [{"sku": "IP15-256-BLK", "color": "Đen", "storage": "256 GB"}],
            },
            {
                "id": "other-product",
                "name": "Điện thoại khác",
                "variants": [{"sku": "OTHER-128-WHT", "color": "Trắng", "storage": "128 GB"}],
            },
        ]
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            products = await use_case._find_products("Kiểm tra giúp tôi sản phẩm SKU IP15-256-BLK.")

        self.assertEqual([product["id"] for product in products], ["matching-product"])
