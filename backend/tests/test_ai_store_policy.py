import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.application.ai.store_policy_context import (
    get_store_policy_context,
    render_store_policy_answer,
)


def policy_context(topic: str, *, cod_available: bool = True) -> dict:
    return {
        "topic": topic,
        "store": {"address": "123 Đường Mẫu", "hotline": "19000000"},
        "payment_methods": [
            {
                "code": "COD",
                "name": "Thanh toán khi nhận hàng",
                "is_active": True,
                "is_available": cod_available,
            },
            {
                "code": "BANK_TRANSFER",
                "name": "Chuyển khoản ngân hàng",
                "is_active": True,
                "is_available": True,
            },
        ],
        "delivery": {
            "free_shipping_threshold": 3_000_000,
            "inner_fee": 25_000,
            "near_fee": 35_000,
            "far_fee": 50_000,
        },
        "policies": {
            "delivery": "Cửa hàng hỗ trợ giao hàng toàn quốc.",
            "installment": "Trả góp theo điều kiện tại bước thanh toán.",
            "vat_invoice": "Có hỗ trợ hóa đơn VAT.",
            "authenticity": "Sản phẩm có thông tin nguồn gốc và hóa đơn.",
            "return_exchange": "Đổi trả theo điều kiện của sản phẩm; một đổi một khi đủ điều kiện.",
            "warranty": "Bảo hành theo sản phẩm và số serial/IMEI.",
            "privacy": "Chỉ sử dụng dữ liệu cần thiết.",
            "inspection": "Khách nên kiểm tra hàng khi nhận.",
        },
    }


class AIStorePolicyAnswerTest(unittest.TestCase):
    def test_cod_answer_uses_live_method_availability(self) -> None:
        self.assertIn("có hỗ trợ", render_store_policy_answer(policy_context("COD")))
        self.assertIn(
            "chưa khả dụng",
            render_store_policy_answer(policy_context("COD", cod_available=False)),
        )

    def test_delivery_answer_contains_configured_fees_and_threshold(self) -> None:
        answer = render_store_policy_answer(policy_context("DELIVERY"))
        self.assertIn("toàn quốc", answer)
        self.assertIn("25.000đ–50.000đ", answer)
        self.assertIn("3.000.000đ", answer)
        self.assertEqual(answer.count("Phí chính xác"), 1)

    def test_return_answer_does_not_claim_that_one_for_one_never_exists(self) -> None:
        answer = render_store_policy_answer(policy_context("RETURN_EXCHANGE"))
        self.assertIn("một đổi một", answer)
        self.assertIn("đủ điều kiện", answer)


class AIStorePolicyContextTest(unittest.IsolatedAsyncioTestCase):
    async def test_context_uses_latest_active_database_policy(self) -> None:
        updated_at = datetime(2026, 7, 14, 10, 0, tzinfo=timezone.utc)
        store = SimpleNamespace(
            name="Echophone",
            hotline="19000000",
            email="support@example.test",
            address="123 Đường Mẫu",
            description="Cửa hàng mẫu",
            updated_at=updated_at,
        )
        policies = [
            SimpleNamespace(
                code="OPENING_HOURS",
                content="Mở cửa từ 08:00 đến 21:00 hằng ngày.",
                is_active=True,
                updated_at=updated_at,
            ),
            SimpleNamespace(
                code="PRIVACY",
                content="Nội dung đã tạm ẩn.",
                is_active=False,
                updated_at=updated_at,
            ),
        ]
        with (
            patch("app.application.ai.store_policy_context.get_store_info", new=AsyncMock(return_value=store)),
            patch("app.application.ai.store_policy_context.list_public_payment_methods", new=AsyncMock(return_value=[])),
            patch("app.application.ai.store_policy_context.list_store_policies", new=AsyncMock(return_value=policies)),
        ):
            context = await get_store_policy_context(None, "Shop mở cửa mấy giờ?")

        self.assertEqual(context["policies"]["opening_hours"], "Mở cửa từ 08:00 đến 21:00 hằng ngày.")
        self.assertNotIn("privacy", context["policies"])
        self.assertEqual(context["source_version"], updated_at.isoformat())


if __name__ == "__main__":
    unittest.main()
