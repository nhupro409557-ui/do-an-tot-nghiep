from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_admin_overview_counts(session: AsyncSession) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM products) AS products_total,
                (SELECT COUNT(*) FROM products WHERE status = 'ACTIVE') AS products_active,
                (SELECT COUNT(*) FROM products WHERE COALESCE(stock_quantity, 0) < 0) AS products_negative_stock,
                (SELECT COUNT(*) FROM products WHERE COALESCE(stock_quantity, 0) <= 5) AS products_low_stock,
                (SELECT COUNT(*) FROM categories WHERE COALESCE(is_deleted, FALSE) = FALSE) AS categories_total,
                (SELECT COUNT(*) FROM brands WHERE is_active = TRUE) AS brands_total,
                (SELECT COUNT(*) FROM orders) AS orders_total,
                (SELECT COUNT(*) FROM orders WHERE status = 'PENDING') AS orders_pending,
                (SELECT COUNT(*) FROM orders WHERE status = 'PROCESSING') AS orders_processing,
                (SELECT COUNT(*) FROM orders WHERE status IN ('CANCELLED', 'CANCELED')) AS orders_cancelled,
                (SELECT COUNT(*) FROM orders WHERE status IN ('REFUNDED', 'RETURNED', 'RETURNING')) AS orders_refunded,
                (SELECT COALESCE(SUM(total_amount), 0) FROM orders) AS total_revenue,
                (SELECT COUNT(*) FROM vouchers) AS vouchers_total,
                (SELECT COUNT(*) FROM vouchers WHERE status = 'ACTIVE') AS vouchers_active,
                (SELECT COUNT(*) FROM vouchers WHERE status = 'ACTIVE' AND COALESCE(total_budget_cap, 0) > 0 AND (COALESCE(total_discount_used, 0) / total_budget_cap) >= 0.8) AS vouchers_risky,
                (SELECT COUNT(*) FROM users) AS customers_total,
                (SELECT COUNT(*) FROM product_reviews) AS reviews_total,
                (SELECT COUNT(*) FROM product_reviews WHERE status = 'PENDING') AS reviews_pending
            """
        )
    )
    return dict(result.one()._mapping)


async def list_revenue_by_day(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT to_char(created_at, 'DD/MM') AS date, SUM(total_amount) AS total
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '14 days'
            GROUP BY to_char(created_at, 'DD/MM'), date_trunc('day', created_at)
            ORDER BY date_trunc('day', created_at) ASC
            """
        )
    )
    return [{"date": row.date, "total": float(row.total)} for row in result]


async def list_revenue_by_month(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT to_char(created_at, 'MM/YYYY') AS month, SUM(total_amount) AS total
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '6 months'
            GROUP BY to_char(created_at, 'MM/YYYY'), date_trunc('month', created_at)
            ORDER BY date_trunc('month', created_at) ASC
            """
        )
    )
    return [{"month": row.month, "total": float(row.total)} for row in result]


async def list_top_products(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT product_id AS id, MAX(product_name) AS name, SUM(quantity) AS soldCount, SUM(total_price) AS periodRevenue
            FROM order_items
            JOIN orders ON orders.id = order_items.order_id
            WHERE orders.status NOT IN ('CANCELLED', 'CANCELED', 'REFUNDED', 'RETURNED')
            GROUP BY product_id
            ORDER BY SUM(quantity) DESC NULLS LAST
            LIMIT 5
            """
        )
    )
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "soldCount": int(row.soldcount),
            "periodRevenue": float(row.periodrevenue),
        }
        for row in result
        if row.id
    ]
