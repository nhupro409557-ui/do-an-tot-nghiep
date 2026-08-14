import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.api.routers.ai_assistant import _traffic_origin
from app.application.ai.historical_synthetic_classifier import candidate_log_ids
from app.application.ai.schemas import AIAssistantRequest
from app.application.ai.service_query_planner import build_service_query_plan
from app.application.ai.use_cases import AIAssistantUseCase


class AIServiceQueryPlannerTest(unittest.TestCase):
    def test_plans_shipping_and_loyalty(self) -> None:
        plan = build_service_query_plan(
            "Đơn hàng của tôi giao tới đâu và tôi còn bao nhiêu điểm tích lũy?",
            base_intent="SHIPPING_LOOKUP",
        )

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.primary_intent, "SHIPPING_LOOKUP")
        self.assertEqual(plan.intents, ["SHIPPING_LOOKUP", "LOYALTY"])
        self.assertIn("get_order", plan.steps)
        self.assertIn("get_shipping_timeline", plan.steps)
        self.assertIn("get_loyalty", plan.steps)
        self.assertTrue(plan.requires_auth)

    def test_plans_after_sales_and_warranty_policy(self) -> None:
        plan = build_service_query_plan(
            "Hồ sơ bảo hành của tôi đang xử lý tới đâu và chính sách bảo hành thế nào?",
            base_intent="AFTER_SALES_LOOKUP",
        )

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.intents, ["AFTER_SALES_LOOKUP", "WARRANTY_POLICY"])
        self.assertEqual(plan.steps, ["get_after_sales", "get_store_policy"])

    def test_plans_loyalty_and_personal_vouchers(self) -> None:
        plan = build_service_query_plan(
            "Tôi có bao nhiêu điểm và có voucher nào dùng được?",
            base_intent="LOYALTY",
        )

        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertIn("VOUCHER_SUPPORT", plan.intents)
        self.assertIn("list_public_vouchers", plan.steps)
        self.assertIn("get_my_vouchers", plan.steps)

    def test_single_intent_does_not_create_compound_plan(self) -> None:
        self.assertIsNone(
            build_service_query_plan(
                "Tôi có bao nhiêu điểm tích lũy?",
                base_intent="LOYALTY",
            )
        )

    def test_out_of_scope_message_is_not_replanned(self) -> None:
        self.assertIsNone(
            build_service_query_plan(
                "Giải giúp tôi phương trình vi phân.",
                base_intent="OUT_OF_SCOPE",
            )
        )


class AIServiceQueryRetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_retrieves_shipping_and_loyalty_sequentially(self) -> None:
        use_case = AIAssistantUseCase(session=object(), redis=AsyncMock())

        async def execute_tool(*, name: str, arguments: dict, user_id: str | None):
            responses = {
                "get_my_latest_order": {
                    "orderCode": "EMV100",
                    "status": "SHIPPING",
                    "paymentStatus": "PAID",
                },
                "get_shipping_timeline": [
                    {"title": "Đã đến kho phân loại", "trackingCode": "TRACK100"}
                ],
                "get_my_loyalty": {
                    "pointsBalance": 1200,
                    "tier": "MEMBER",
                    "walletStatus": "ACTIVE",
                    "periodSpendAmount": 1_000_000,
                },
            }
            return responses[name]

        use_case._tools.execute = AsyncMock(side_effect=execute_tool)
        plan = build_service_query_plan(
            "Đơn hàng của tôi giao tới đâu và tôi còn bao nhiêu điểm tích lũy?",
            base_intent="SHIPPING_LOOKUP",
        )
        assert plan is not None
        request = AIAssistantRequest(conversation_id=uuid4(), message="Kiểm tra giúp tôi")

        context = await use_case._retrieve_service_plan_context(
            plan=plan,
            message="Đơn hàng của tôi giao tới đâu và tôi còn bao nhiêu điểm tích lũy?",
            user_id=str(uuid4()),
            request=request,
        )

        self.assertEqual(context["order"]["orderCode"], "EMV100")
        self.assertEqual(context["shipping_events"][0]["trackingCode"], "TRACK100")
        self.assertEqual(context["loyalty"]["pointsBalance"], 1200)
        self.assertEqual(
            [call.kwargs["name"] for call in use_case._tools.execute.await_args_list],
            ["get_my_latest_order", "get_shipping_timeline", "get_my_loyalty"],
        )

    def test_compound_fallback_contains_each_requested_section(self) -> None:
        use_case = AIAssistantUseCase(session=object(), redis=AsyncMock())
        answer = use_case._fallback_answer(
            intent="SHIPPING_LOOKUP",
            retrieved_context={
                "service_query_plan": {
                    "intents": ["SHIPPING_LOOKUP", "LOYALTY"],
                },
                "order": {
                    "orderCode": "EMV100",
                    "status": "SHIPPING",
                    "paymentStatus": "PAID",
                    "totalAmount": 10_000_000,
                    "trackingCode": "TRACK100",
                },
                "shipping_events": [],
                "loyalty": {
                    "pointsBalance": 1200,
                    "tier": "MEMBER",
                    "walletStatus": "ACTIVE",
                    "periodSpendAmount": 1_000_000,
                    "nextTierLabel": "Bạc",
                    "amountToNextTier": 4_000_000,
                },
            },
        )

        self.assertIn("Vận chuyển:", answer)
        self.assertIn("TRACK100", answer)
        self.assertIn("Điểm thành viên:", answer)
        self.assertIn("1.200 điểm", answer)


class AITrafficOriginTest(unittest.TestCase):
    def test_local_runner_with_explicit_capability_is_synthetic(self) -> None:
        self.assertEqual(
            _traffic_origin("127.0.0.1", ["response_v2", "synthetic_evaluation_v1"]),
            "SYNTHETIC",
        )

    def test_remote_client_cannot_mark_itself_synthetic(self) -> None:
        self.assertEqual(
            _traffic_origin("203.0.113.10", ["synthetic_evaluation_v1"]),
            "CUSTOMER",
        )

    def test_normal_local_browser_remains_customer(self) -> None:
        self.assertEqual(_traffic_origin("127.0.0.1", ["response_v2"]), "CUSTOMER")


class AISyntheticRateLimitTest(unittest.IsolatedAsyncioTestCase):
    async def test_synthetic_request_does_not_consume_customer_rate_limit(self) -> None:
        use_case = AIAssistantUseCase(session=AsyncMock(), redis=AsyncMock())
        use_case._enforce_rate_limit = AsyncMock()
        use_case._conversation_memory.load = AsyncMock(side_effect=RuntimeError("stop after rate-limit check"))
        request = AIAssistantRequest(conversation_id=uuid4(), message="Xin chào")

        with self.assertRaisesRegex(RuntimeError, "stop after rate-limit check"):
            await use_case.execute(user_id=None, request=request, traffic_origin="SYNTHETIC")

        use_case._enforce_rate_limit.assert_not_awaited()

    async def test_customer_request_still_consumes_rate_limit(self) -> None:
        use_case = AIAssistantUseCase(session=AsyncMock(), redis=AsyncMock())
        use_case._enforce_rate_limit = AsyncMock()
        use_case._conversation_memory.load = AsyncMock(side_effect=RuntimeError("stop after rate-limit check"))
        request = AIAssistantRequest(conversation_id=uuid4(), message="Xin chào")

        with self.assertRaisesRegex(RuntimeError, "stop after rate-limit check"):
            await use_case.execute(user_id=None, request=request, traffic_origin="CUSTOMER")

        use_case._enforce_rate_limit.assert_awaited_once_with(user_id=None)


class AIHistoricalSyntheticClassifierTest(unittest.TestCase):
    def test_selects_only_dense_fixture_session_without_feedback(self) -> None:
        candidate_conversation = uuid4()
        customer_conversation = uuid4()
        fixture_messages = {f"fixture-{index}" for index in range(25)}
        rows = [
            {"id": uuid4(), "conversation_id": candidate_conversation, "user_message": message}
            for message in fixture_messages
        ]
        rows.extend(
            {"id": uuid4(), "conversation_id": customer_conversation, "user_message": message}
            for message in list(fixture_messages)[:19]
        )

        selected, summaries = candidate_log_ids(
            rows,
            fixture_messages=fixture_messages,
            conversations_with_feedback=set(),
            min_matches=20,
            min_ratio=0.9,
        )

        self.assertEqual(len(selected), 25)
        self.assertEqual([item["conversation_id"] for item in summaries], [str(candidate_conversation)])

    def test_feedback_excludes_otherwise_matching_session(self) -> None:
        conversation_id = uuid4()
        fixture_messages = {f"fixture-{index}" for index in range(20)}
        rows = [
            {"id": uuid4(), "conversation_id": conversation_id, "user_message": message}
            for message in fixture_messages
        ]

        selected, summaries = candidate_log_ids(
            rows,
            fixture_messages=fixture_messages,
            conversations_with_feedback={conversation_id},
            min_matches=20,
            min_ratio=0.9,
        )

        self.assertEqual(selected, [])
        self.assertEqual(summaries, [])


if __name__ == "__main__":
    unittest.main()
