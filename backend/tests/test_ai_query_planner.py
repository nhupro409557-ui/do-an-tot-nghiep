import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.application.ai.conversation_memory import ConversationMemorySnapshot, resolve_follow_up
from app.application.ai.intent_router import route_intent
from app.application.ai.query_planner import build_product_query_plan
from app.application.ai.use_cases import AIAssistantUseCase, render_product_fallback
from app.application.ai.verification import verify_response


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ai_multi_intent_planner_cases.jsonl"


class AIQueryPlannerFixtureTest(unittest.TestCase):
    def test_all_fifty_multi_intent_cases(self) -> None:
        cases = [
            json.loads(line)
            for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(cases), 50)

        for case in cases:
            with self.subTest(case=case["id"]):
                plan = build_product_query_plan(
                    case["message"],
                    base_intent=case["base_intent"],
                    base_needs_clarification=True,
                )
                self.assertIsNotNone(plan)
                assert plan is not None
                self.assertEqual(plan.primary_intent, case["expected_primary"])
                self.assertEqual(plan.can_auto_resolve, case["auto_resolve"])
                self.assertFalse(plan.needs_clarification)
                for intent in case["expected_intents"]:
                    self.assertIn(intent, plan.intents)
                for step in case["expected_steps"]:
                    self.assertIn(step, plan.steps)

    def test_hybrid_router_auto_resolves_constrained_comparison(self) -> None:
        message = "So sánh hai điện thoại khoảng 10 triệu, mẫu nào pin tốt hơn và còn màu đen?"
        decision = route_intent(message)
        self.assertEqual(decision.intent, "PRODUCT_COMPARISON")
        self.assertTrue(decision.needs_clarification)

        plan = build_product_query_plan(
            message,
            base_intent=decision.intent,
            base_needs_clarification=decision.needs_clarification,
        )

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertTrue(plan.can_auto_resolve)
        self.assertFalse(plan.needs_clarification)
        self.assertEqual(plan.constraints.category, "PHONE")
        self.assertEqual(plan.constraints.colors, ["Đen"])
        self.assertIn("battery", plan.constraints.priorities)

    def test_vague_comparison_still_requires_clarification(self) -> None:
        plan = build_product_query_plan(
            "So sánh giúp tôi hai sản phẩm.",
            base_intent="PRODUCT_COMPARISON",
            base_needs_clarification=True,
        )

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertFalse(plan.can_auto_resolve)
        self.assertTrue(plan.needs_clarification)

    def test_non_product_policy_is_not_replanned(self) -> None:
        plan = build_product_query_plan(
            "Hãy hủy đơn hàng giúp tôi.",
            base_intent="UNSUPPORTED_REQUEST",
            base_needs_clarification=False,
        )
        self.assertIsNone(plan)

    def test_vietnamese_word_do_is_not_misread_as_red_color(self) -> None:
        plan = build_product_query_plan(
            "Độ ồn thực tế thế nào?",
            base_intent="PRODUCT_REVIEW",
            base_needs_clarification=False,
        )
        self.assertIsNone(plan)


class AIQueryPlannerConversationTest(unittest.TestCase):
    def test_comparison_follow_up_keeps_both_products(self) -> None:
        memory = ConversationMemorySnapshot(
            conversation_id=uuid4(),
            user_id=None,
            active_intent="PRODUCT_COMPARISON",
            active_entities={
                "products": [
                    {"id": "p1", "name": "OPPO Reno15 5G"},
                    {"id": "p2", "name": "HONOR 400 5G"},
                ]
            },
        )

        resolved = resolve_follow_up("Cái nào pin tốt hơn?", memory)

        self.assertIn("OPPO Reno15 5G", resolved)
        self.assertIn("HONOR 400 5G", resolved)
        self.assertIn("So sánh", resolved)

    def test_product_reference_mau_do_is_not_treated_as_red_color(self) -> None:
        memory = ConversationMemorySnapshot(
            conversation_id=uuid4(),
            user_id=None,
            active_intent="PRICE_AND_PROMOTION",
            active_entities={
                "products": [
                    {"id": "p1", "name": "Cáp sạc Ugreen USB-C to USB-C 100W 2m"},
                ]
            },
        )

        resolved = resolve_follow_up("Mẫu đó hiện còn hàng không?", memory)
        decision = route_intent(resolved)
        plan = build_product_query_plan(
            resolved,
            base_intent=decision.intent,
            base_needs_clarification=decision.needs_clarification,
        )

        self.assertIsNotNone(plan)
        self.assertEqual(plan.constraints.category, "ACCESSORY")
        self.assertEqual(plan.constraints.colors, [])


class AIQueryPlannerVerificationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.context = {
            "query_plan": {
                "constraints": {
                    "colors": ["Đen"],
                    "priorities": ["battery"],
                    "require_in_stock": True,
                }
            },
            "products": [
                {
                    "id": "p1",
                    "name": "Điện thoại A",
                    "specifications": {"battery": "6000 mAh"},
                    "matchedVariants": [{"colorName": "Đen", "availableStock": 3}],
                },
                {
                    "id": "p2",
                    "name": "Điện thoại B",
                    "specifications": {"battery": "5000 mAh"},
                    "matchedVariants": [{"colorName": "Đen", "availableStock": 2}],
                },
            ],
        }

    def test_accepts_grounded_battery_and_color_comparison(self) -> None:
        result = verify_response(
            intent="PRODUCT_COMPARISON",
            answer=(
                "Điện thoại A có pin 6000 mAh và còn màu đen. "
                "Điện thoại B có pin 5000 mAh và còn màu đen."
            ),
            context=self.context,
        )
        self.assertTrue(result.passed, result.errors)

    def test_rejects_invented_battery_capacity(self) -> None:
        result = verify_response(
            intent="PRODUCT_COMPARISON",
            answer=(
                "Điện thoại A có pin 7000 mAh và còn màu đen. "
                "Điện thoại B có pin 5000 mAh và còn màu đen."
            ),
            context=self.context,
        )
        self.assertFalse(result.passed)
        self.assertIn("BATTERY_CLAIM_MISMATCH", result.errors)


class AIQueryPlannerProductSelectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_brand_comparison_keeps_both_requested_brands(self) -> None:
        def product(identifier: str, name: str, brand: str, description: str = "") -> dict:
            return {
                "id": identifier,
                "name": name,
                "slug": identifier,
                "brand": brand,
                "description": description,
                "price": 10_000_000,
                "salePrice": 10_000_000,
                "categoryName": "Điện thoại",
                "categorySlug": "dien-thoai",
                "specifications": {},
                "variants": [],
                "availableStock": 5,
                "rating": 0,
                "favoriteCount": 0,
            }

        message = "So sánh iPhone và Samsung, máy nào phù hợp để chụp ảnh và dùng lâu dài?"
        plan = build_product_query_plan(
            message,
            base_intent="PRODUCT_COMPARISON",
            base_needs_clarification=True,
        )
        use_case = AIAssistantUseCase(session=object(), redis=AsyncMock())
        rows = [
            product("iphone-17", "iPhone 17", "Apple"),
            product("galaxy-s26", "Samsung Galaxy S26", "Samsung"),
            product(
                "tecno-spark",
                "TECNO Spark",
                "TECNO",
                "Máy phù hợp để chụp ảnh và dùng lâu dài.",
            ),
        ]

        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            selected = await use_case._find_products(message, query_plan=plan)

        self.assertEqual([item["brand"] for item in selected[:2]], ["Apple", "Samsung"])

    async def test_generic_comparison_respects_budget_color_stock_and_battery_priority(self) -> None:
        def product(name: str, price: int, battery: int, color: str = "Đen") -> dict:
            return {
                "id": name,
                "name": name,
                "slug": name.lower(),
                "price": price,
                "salePrice": price,
                "categoryName": "Điện thoại",
                "categorySlug": "dien-thoai",
                "specifications": {"battery": f"{battery} mAh"},
                "variants": [
                    {
                        "id": f"{name}-variant",
                        "colorName": color,
                        "availableStock": 5,
                    }
                ],
                "availableStock": 5,
                "rating": 0,
                "favoriteCount": 0,
            }

        message = "So sánh hai điện thoại khoảng 10 triệu, mẫu nào pin tốt hơn và còn màu đen?"
        plan = build_product_query_plan(
            message,
            base_intent="PRODUCT_COMPARISON",
            base_needs_clarification=True,
        )
        use_case = AIAssistantUseCase(session=object(), redis=AsyncMock())
        rows = [
            product("Máy ngoài ngân sách", 40_000_000, 7000),
            product("Máy pin 6000", 10_500_000, 6000),
            product("Máy pin 5000", 9_500_000, 5000),
            product("Máy sai màu", 10_000_000, 6500, color="Trắng"),
        ]

        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=rows),
        ):
            selected = await use_case._find_products(message, query_plan=plan)

        self.assertEqual([item["name"] for item in selected[:2]], ["Máy pin 6000", "Máy pin 5000"])
        self.assertNotIn("Máy ngoài ngân sách", [item["name"] for item in selected])

    def test_comparison_fallback_concludes_equal_price_and_battery_winner(self) -> None:
        products = [
            {
                "name": "Máy A",
                "price": 10_000_000,
                "salePrice": 10_000_000,
                "availableStock": 2,
                "specifications": {"battery": "6000 mAh"},
            },
            {
                "name": "Máy B",
                "price": 10_000_000,
                "salePrice": 10_000_000,
                "availableStock": 2,
                "specifications": {"battery": "5000 mAh"},
            },
        ]

        answer = render_product_fallback(
            "PRODUCT_COMPARISON",
            products,
            query_plan={"constraints": {"priorities": ["battery"]}},
        )

        self.assertIn("cùng giá hiện tại 10.000.000đ", answer)
        self.assertIn("Máy A tốt hơn về dung lượng", answer)


if __name__ == "__main__":
    unittest.main()
