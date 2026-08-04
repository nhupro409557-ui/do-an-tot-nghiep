import unittest
from decimal import Decimal

from app.application.ai.intent_router import route_intent
from app.application.ai.planned_business_support import (
    render_account_support_answer,
    render_cart_support_answer,
    render_product_review_answer,
    render_voucher_support_answer,
)
from app.application.ai.use_cases import AIAssistantUseCase


class AIPlannedBusinessRoutingTest(unittest.TestCase):
    def test_routes_each_implemented_business_capability(self) -> None:
        cases = {
            "Làm sao thêm sản phẩm vào giỏ hàng?": "CART_SUPPORT",
            "Có voucher nào dùng được không?": "VOUCHER_SUPPORT",
            "Điểm đánh giá trung bình là bao nhiêu?": "PRODUCT_REVIEW",
            "Tôi quên mật khẩu.": "ACCOUNT_SUPPORT",
            "Tôi muốn gặp nhân viên tư vấn.": "COMPLAINT",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                decision = route_intent(message)
                self.assertEqual(decision.intent, expected)
                self.assertEqual(decision.route, "DETERMINISTIC")

    def test_review_requires_product_except_management_policy(self) -> None:
        self.assertTrue(route_intent("Pin thực tế dùng được bao lâu?").needs_clarification)
        self.assertFalse(route_intent("Làm sao đánh giá sản phẩm?").needs_clarification)


class AIPlannedBusinessAnswerTest(unittest.TestCase):
    def test_cart_answer_uses_live_cart_and_order_state(self) -> None:
        answer = render_cart_support_answer(
            {
                "message": "Làm sao hủy đơn hàng?",
                "cart_items": [{"name": "iPhone", "quantity": 2, "price": 10_000_000}],
                "order": {"orderCode": "EMV4212922531", "status": "PENDING"},
            }
        )
        self.assertIn("EMV4212922531", answer)
        self.assertIn("có thể", answer)
        self.assertIn("không tự hủy", answer)

    def test_voucher_answer_calculates_best_discount_from_cart(self) -> None:
        answer = render_voucher_support_answer(
            {
                "message": "Mã nào giúp tôi giảm nhiều nhất?",
                "cart_items": [{"quantity": 1, "price": 3_000_000}],
                "user_vouchers": [
                    {
                        "code": "GIAM10",
                        "discountType": "PERCENTAGE",
                        "discountAmount": Decimal("10"),
                        "minOrderValue": 0,
                        "maxDiscount": 250_000,
                    },
                    {
                        "code": "GIAM300K",
                        "discountType": "FIXED",
                        "discountAmount": 300_000,
                        "minOrderValue": 0,
                    },
                ],
            }
        )
        self.assertIn("GIAM300K", answer)
        self.assertIn("300.000đ", answer)

    def test_account_answer_matches_real_auth_capabilities(self) -> None:
        self.assertIn("15 phút", render_account_support_answer({"message": "Mã OTP có hiệu lực bao lâu?"}))
        self.assertIn("chưa hỗ trợ đăng nhập Apple", render_account_support_answer({"message": "Đăng nhập Apple được không?"}))
        self.assertIn("thu hồi toàn bộ phiên", render_account_support_answer({"message": "Đăng xuất khỏi tất cả thiết bị"}))

    def test_review_answer_only_uses_published_review_snapshot(self) -> None:
        answer = render_product_review_answer(
            {
                "message": "Điểm đánh giá trung bình là bao nhiêu?",
                "product": {"id": "p1", "name": "Điện thoại mẫu"},
                "review_insights": {"averageRating": 4.25, "reviewCount": 8},
            }
        )
        self.assertIn("Điện thoại mẫu", answer)
        self.assertIn("4.2/5", answer)
        self.assertIn("8 đánh giá", answer)

    def test_complaint_answer_includes_trackable_support_code(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        answer = use_case._fallback_answer(
            intent="COMPLAINT",
            retrieved_context={
                "support_request": {"requestCode": "CSABC123456789", "status": "OPEN"},
                "urgent_support_topic": None,
            },
        )
        self.assertIn("CSABC123456789", answer)
        self.assertIn("đã tiếp nhận", answer)


if __name__ == "__main__":
    unittest.main()
