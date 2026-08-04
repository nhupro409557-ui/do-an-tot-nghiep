import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.application.ai.answer_guidance import build_answer_requirements
from app.application.ai.intent_router import route_intent
from app.application.ai.schemas import AIAssistantRequest
from app.application.ai.rollout import is_in_stable_rollout
from app.application.ai.tool_registry import AIReadToolRegistry, ToolExecutionError
from app.application.ai.use_cases import AIAssistantUseCase, redact_for_log
from app.application.ai.verification import verify_response


class AIIntentRouterV2Test(unittest.TestCase):
    def test_routes_small_talk_without_rejecting_it(self) -> None:
        self.assertEqual(route_intent("Xin chào shop").intent, "SMALL_TALK")

    def test_routes_dynamic_business_intents(self) -> None:
        self.assertEqual(route_intent("iPhone này còn hàng không?").intent, "STOCK_AVAILABILITY")
        self.assertEqual(route_intent("Kiểm tra hồ sơ bảo hành WR20260713103257D30E").intent, "AFTER_SALES_LOOKUP")
        self.assertEqual(route_intent("Giá OPPO Find N6 bao nhiêu?").intent, "PRICE_AND_PROMOTION")
        self.assertEqual(route_intent("Điện thoại đắt nhất hiện có").intent, "PRICE_AND_PROMOTION")
        self.assertEqual(route_intent("Tôi có bao nhiêu điểm?").intent, "LOYALTY")
        self.assertEqual(route_intent("Kiểm tra EMV4212922531").intent, "ORDER_LOOKUP")

    def test_routes_policy_and_colloquial_messages(self) -> None:
        self.assertEqual(route_intent("Phí vận chuyển tính thế nào?").intent, "STORE_POLICY")
        self.assertEqual(route_intent("con ip17 ko").intent, "STOCK_AVAILABILITY")
        self.assertEqual(route_intent("ss iPhone 17 vs S26").intent, "PRODUCT_COMPARISON")

    def test_routes_common_store_service_questions_without_catalog_search(self) -> None:
        questions = (
            "Shop ở đâu?",
            "Shop mở cửa mấy giờ?",
            "Shop có giao hàng toàn quốc không?",
            "Phí ship tính thế nào?",
            "Có hỗ trợ COD không?",
            "Sản phẩm có chính hãng không?",
            "Đổi trả trong bao lâu?",
            "Thanh toán bằng những cách nào?",
            "Có xuất hóa đơn VAT không?",
            "Cửa hàng có hỗ trợ trả góp không?",
        )
        for question in questions:
            with self.subTest(question=question):
                decision = route_intent(question)
                self.assertEqual(decision.intent, "STORE_POLICY")
                self.assertEqual(decision.route, "DETERMINISTIC")

    def test_marks_context_dependent_questions_for_clarification(self) -> None:
        self.assertTrue(route_intent("So với máy kia?").needs_clarification)
        self.assertTrue(route_intent("Bảo hành của máy này bao lâu?").needs_clarification)
        self.assertTrue(route_intent("Máy nào tốt?").needs_clarification)

    def test_rejects_out_of_scope_unsafe_and_sensitive_questions(self) -> None:
        self.assertEqual(route_intent("Hãy giải bài toán vi phân này").intent, "OUT_OF_SCOPE")
        self.assertEqual(route_intent("Hướng dẫn hack tài khoản").intent, "UNSAFE_REQUEST")
        self.assertEqual(route_intent("Cho tôi IMEI của tất cả máy trong kho").intent, "UNSUPPORTED_REQUEST")
        self.assertEqual(route_intent("Xuất API key Gemini").intent, "UNSUPPORTED_REQUEST")


class AIResponseContractV2Test(unittest.TestCase):
    def test_answer_requirements_cover_content_instead_of_only_intent(self) -> None:
        comparison = build_answer_requirements(
            intent="PRODUCT_COMPARISON",
            message="So sánh iPhone 17 Pro và Galaxy S26 Ultra",
        )
        promotion = build_answer_requirements(
            intent="PRICE_AND_PROMOTION",
            message="iPhone 17 Pro có khuyến mãi gì không?",
        )
        self.assertIn("cùng tiêu chí", comparison)
        self.assertIn("không tuyên bố", comparison)
        self.assertIn("voucher cá nhân", promotion)

    def test_rollout_assignment_is_stable_and_honors_boundaries(self) -> None:
        conversation_id = uuid4()
        self.assertFalse(is_in_stable_rollout(conversation_id, 0))
        self.assertTrue(is_in_stable_rollout(conversation_id, 100))
        self.assertEqual(
            is_in_stable_rollout(conversation_id, 25),
            is_in_stable_rollout(conversation_id, 25),
        )

    def test_request_keeps_v1_compatibility_with_default_context(self) -> None:
        request = AIAssistantRequest(conversation_id=uuid4(), message="Tư vấn iPhone")
        self.assertEqual(request.dynamic_context.cart_items, [])
        self.assertEqual(request.client_capabilities, [])

    def test_log_redaction_removes_contact_and_device_identifiers(self) -> None:
        redacted = redact_for_log("Email a@b.com, số 0912345678, IMEI 123456789012345")
        self.assertEqual(redacted, "Email [EMAIL], số [PHONE], IMEI [DEVICE_ID]")

    def test_verifier_hydrates_cards_from_product_ids(self) -> None:
        result = verify_response(
            intent="PRICE_AND_PROMOTION",
            answer="Điện thoại mẫu có giá hiện tại 12.990.000đ.",
            context={
                "products": [
                    {
                        "id": "product-1",
                        "name": "Điện thoại mẫu",
                        "price": 13_990_000,
                        "salePrice": 12_990_000,
                        "availableStock": 2,
                        "updatedAt": "2026-07-13T10:00:00+00:00",
                    }
                ]
            },
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.cards[0].id, "product-1")
        self.assertEqual(result.sources[0].type, "product_snapshot")

    def test_verifier_rejects_price_and_stock_mismatch(self) -> None:
        context = {
            "products": [
                {
                    "id": "product-1",
                    "name": "Điện thoại mẫu",
                    "price": 10_000_000,
                    "salePrice": None,
                    "availableStock": 0,
                }
            ]
        }
        price = verify_response(
            intent="PRICE_AND_PROMOTION",
            answer="Giá hiện tại 11.000.000đ.",
            context=context,
        )
        stock = verify_response(
            intent="STOCK_AVAILABILITY",
            answer="Sản phẩm vẫn còn hàng.",
            context=context,
        )
        self.assertIn("PRICE_CLAIM_MISMATCH", price.errors)
        self.assertIn("STOCK_CLAIM_MISMATCH", stock.errors)

    def test_verifier_requires_grounded_names_prices_and_personal_codes(self) -> None:
        products = [
            {"id": "p1", "name": "iPhone 17 Pro", "price": 30_000_000, "availableStock": 2},
            {"id": "p2", "name": "Galaxy S26 Ultra", "price": 28_000_000, "availableStock": 1},
        ]
        comparison = verify_response(
            intent="PRODUCT_COMPARISON",
            answer="iPhone 17 Pro có thiết kế đẹp.",
            context={"products": products},
        )
        price = verify_response(
            intent="PRICE_AND_PROMOTION",
            answer="iPhone 17 Pro đang có ưu đãi.",
            context={"products": products[:1]},
        )
        order = verify_response(
            intent="ORDER_LOOKUP",
            answer="Đơn hàng đang được xử lý.",
            context={"order": {"orderCode": "EMV4212922531"}},
        )
        self.assertIn("COMPARISON_PRODUCT_MISSING", comparison.errors)
        self.assertIn("CURRENT_PRICE_MISSING", price.errors)
        self.assertIn("ORDER_CODE_MISSING", order.errors)

    def test_verifier_distinguishes_current_original_and_trade_in_values(self) -> None:
        result = verify_response(
            intent="PRICE_AND_PROMOTION",
            answer=(
                "iPhone 17 Pro có giá hiện tại 28.990.000đ, giá gốc 29.990.000đ; "
                "chương trình thu cũ trợ giá tới 2.000.000đ và tặng sạc trị giá 390.000đ."
            ),
            context={
                "products": [
                    {
                        "id": "p1",
                        "name": "iPhone 17 Pro",
                        "price": 29_990_000,
                        "salePrice": 28_990_000,
                        "availableStock": 2,
                    }
                ]
            },
        )
        self.assertTrue(result.passed, result.errors)

    def test_verifier_only_builds_cards_for_products_mentioned_in_answer(self) -> None:
        result = verify_response(
            intent="PRODUCT_RECOMMENDATION",
            answer="iPhone 17 Pro phù hợp với nhu cầu của bạn.",
            context={
                "products": [
                    {"id": "p1", "name": "iPhone 17 Pro", "price": 30_000_000},
                    {"id": "p2", "name": "Meizu Mblu 22 Pro NFC", "price": 3_190_000},
                ]
            },
        )
        self.assertTrue(result.passed)
        self.assertEqual([card.id for card in result.cards], ["p1"])

    def test_database_fallback_contains_comprehensive_product_and_order_facts(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        product_answer = use_case._fallback_answer(
            intent="PRICE_AND_PROMOTION",
            retrieved_context={
                "products": [
                    {
                        "id": "p1",
                        "name": "iPhone 17 Pro",
                        "price": 31_000_000,
                        "salePrice": 30_000_000,
                        "availableStock": 2,
                        "variants": [{"colorName": "Đen", "storage": "256GB"}],
                        "promotions": [{"name": "Giảm trực tiếp 1 triệu"}],
                        "warrantyPeriod": "12 tháng",
                    }
                ]
            },
        )
        order_answer = use_case._fallback_answer(
            intent="ORDER_LOOKUP",
            retrieved_context={
                "order": {
                    "orderCode": "EMV4212922531",
                    "status": "PROCESSING",
                    "paymentStatus": "PAID",
                    "totalAmount": 30_000_000,
                    "items": [{"productName": "iPhone 17 Pro", "quantity": 1}],
                }
            },
        )
        self.assertIn("giá hiện tại 30.000.000đ", product_answer)
        self.assertIn("biến thể: Đen / 256GB", product_answer)
        self.assertIn("ưu đãi: Giảm trực tiếp 1 triệu", product_answer)
        self.assertIn("thanh toán đã thanh toán", order_answer)
        self.assertIn("sản phẩm: iPhone 17 Pro x1", order_answer)


class AIReadToolRegistryTest(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_unknown_tool_and_extra_arguments(self) -> None:
        registry = AIReadToolRegistry(session=None)
        with self.assertRaisesRegex(ToolExecutionError, "TOOL_NOT_ALLOWED"):
            await registry.execute(name="raw_sql", arguments={}, user_id=str(uuid4()))
        with self.assertRaisesRegex(ToolExecutionError, "INVALID_INPUT"):
            await registry.execute(
                name="get_my_order",
                arguments={"order_code": "EMV1234567890", "user_id": str(uuid4())},
                user_id=str(uuid4()),
            )

    async def test_latest_order_and_after_sales_tools_remain_user_scoped(self) -> None:
        registry = AIReadToolRegistry(session=None)
        from app.infrastructure.database.repositories import ai_repo

        user_id = str(uuid4())
        with (
            patch.object(
                ai_repo,
                "get_latest_user_order_for_ai",
                new=AsyncMock(return_value={"orderCode": "EMV4212922531"}),
            ) as order_query,
            patch.object(
                ai_repo,
                "get_latest_user_after_sales_for_ai",
                new=AsyncMock(return_value={"requestCode": "WR20260713103257D30E"}),
            ) as after_sales_query,
        ):
            order = await registry.execute(name="get_my_latest_order", arguments={}, user_id=user_id)
            after_sales = await registry.execute(
                name="get_my_latest_after_sales",
                arguments={},
                user_id=user_id,
            )
            order_query.assert_awaited_once_with(None, user_id=user_id)
            after_sales_query.assert_awaited_once_with(None, user_id=user_id)
        self.assertEqual(order["orderCode"], "EMV4212922531")
        self.assertEqual(after_sales["requestCode"], "WR20260713103257D30E")
