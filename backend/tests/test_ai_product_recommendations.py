import unittest
from unittest.mock import AsyncMock, patch

from app.application.ai.use_cases import AIAssistantUseCase


PRODUCTS = [
    {
        "id": "phone-expensive",
        "name": "Điện thoại Cao Cấp",
        "price": 45_000_000,
        "salePrice": 40_000_000,
        "categoryName": "Điện thoại",
        "categorySlug": "smartphones",
        "rating": 4.5,
        "favoriteCount": 3,
    },
    {
        "id": "phone-cheap",
        "name": "Điện thoại Tiết Kiệm",
        "price": 5_000_000,
        "salePrice": 4_000_000,
        "categoryName": "Điện thoại",
        "categorySlug": "smartphones",
        "rating": 4,
        "favoriteCount": 1,
    },
    {
        "id": "laptop-more-expensive",
        "name": "Laptop Đắt Hơn",
        "price": 60_000_000,
        "salePrice": 55_000_000,
        "categoryName": "Laptop",
        "categorySlug": "laptops",
        "rating": 5,
        "favoriteCount": 10,
    },
    {
        "id": "iphone-17",
        "name": "iPhone 17",
        "price": 24_990_000,
        "salePrice": 23_990_000,
        "brand": "Apple",
        "categoryName": "Điện thoại",
        "categorySlug": "smartphones",
        "rating": 4.8,
        "favoriteCount": 5,
    },
    {
        "id": "iphone-17-pro",
        "name": "iPhone 17 Pro",
        "price": 40_990_000,
        "salePrice": 38_990_000,
        "brand": "Apple",
        "categoryName": "Điện thoại",
        "categorySlug": "smartphones",
        "rating": 4.9,
        "favoriteCount": 6,
    },
    {
        "id": "galaxy-s26-ultra",
        "name": "Samsung Galaxy S26 Ultra",
        "price": 36_990_000,
        "salePrice": 34_990_000,
        "brand": "Samsung",
        "categoryName": "Điện thoại",
        "categorySlug": "smartphones",
        "rating": 4.9,
        "favoriteCount": 8,
    },
    {
        "id": "unrelated-popular",
        "name": "Anker Prime 250W",
        "price": 5_990_000,
        "salePrice": 4_990_000,
        "brand": "Anker",
        "categoryName": "Phụ kiện",
        "categorySlug": "accessories",
        "rating": 5,
        "favoriteCount": 1000,
    },
]


class AIProductRecommendationsTest(unittest.IsolatedAsyncioTestCase):
    async def test_most_expensive_phone_returns_one_phone_using_effective_price(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("Điện thoại đắt nhất hiện có")

        self.assertEqual([product["id"] for product in products], ["phone-expensive"])

    async def test_least_expensive_phone_returns_one_phone(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("Điện thoại giá thấp nhất")

        self.assertEqual([product["id"] for product in products], ["phone-cheap"])

    async def test_phone_budget_query_excludes_other_categories(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("Tư vấn điện thoại cho tôi")

        self.assertTrue(products)
        self.assertTrue(all(product["categorySlug"] == "smartphones" for product in products))

    async def test_exact_model_query_does_not_return_unrelated_popular_products(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("Giá iPhone 17 Pro bao nhiêu?")

        self.assertEqual([product["id"] for product in products], ["iphone-17-pro"])

    async def test_slang_model_query_keeps_numeric_model_token(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("con ip17 ko")

        self.assertEqual([product["id"] for product in products], ["iphone-17"])

    async def test_comparison_returns_one_match_for_each_named_model(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("ss iPhone 17 vs S26 Ultra")

        self.assertEqual(
            [product["id"] for product in products],
            ["iphone-17", "galaxy-s26-ultra"],
        )

    async def test_brand_promotion_query_only_returns_matching_brand(self) -> None:
        use_case = AIAssistantUseCase(session=None, redis=None)
        with patch(
            "app.application.ai.use_cases.ai_repo.list_active_products_for_ai",
            new=AsyncMock(return_value=PRODUCTS),
        ):
            products = await use_case._find_products("iPhone đang có ưu đãi gì?")

        self.assertTrue(products)
        self.assertTrue(all("iphone" in product["name"].lower() for product in products))


if __name__ == "__main__":
    unittest.main()
