from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_admin_product_to_database_to_storefront_catalog(
    api_client,
    db_session,
    admin_headers,
):
    suffix = uuid4().hex[:8]
    product_name = f"Sản phẩm kiểm thử {suffix}"
    category_id = await db_session.scalar(
        text(
            """
            SELECT id
            FROM categories
            WHERE is_active = TRUE
            ORDER BY created_at
            LIMIT 1
            """
        )
    )
    assert category_id is not None
    created = await api_client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={
            "name": product_name,
            "price": 1_250_000,
            "stock": 0,
            "brand": "Hãng kiểm thử",
            "category": "ACCESSORY",
            "categoryId": str(category_id),
            "imageUrl": "https://example.com/product-test.jpg",
            "description": "Dữ liệu chỉ tồn tại trong database kiểm thử.",
            "status": "ACTIVE",
        },
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    submitted = await api_client.post(
        f"/api/admin/products/{product_id}/submit",
        headers=admin_headers,
    )
    assert submitted.status_code == 200, submitted.text
    approved = await api_client.post(
        f"/api/admin/products/{product_id}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text

    stored = (
        await db_session.execute(
            text(
                """
                SELECT name, price, status
                FROM products
                WHERE id = :product_id
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().one()
    assert stored["name"] == product_name
    assert float(stored["price"]) == 1_250_000
    assert stored["status"] == "ACTIVE"

    detail = await api_client.get(f"/api/catalog/products/{product_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["name"] == product_name

    listing = await api_client.get("/api/catalog/products", params={"search": product_name})
    assert listing.status_code == 200, listing.text
    assert product_name in listing.text
