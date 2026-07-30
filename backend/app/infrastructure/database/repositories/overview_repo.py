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
                (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE completed_at IS NOT NULL)
                  - (SELECT COALESCE(SUM(refund_amount), 0) FROM refund_transactions WHERE status = 'COMPLETED') AS total_revenue,
                (SELECT COALESCE(SUM(CASE WHEN ilm.movement_type = 'SALE' THEN ilm.quantity * COALESCE(il.unit_cost, 0) WHEN ilm.movement_type = 'RETURN' THEN -ilm.quantity * COALESCE(il.unit_cost, 0) ELSE 0 END), 0)
                 FROM inventory_lot_movements ilm JOIN inventory_lots il ON il.id = ilm.lot_id
                 WHERE ilm.order_id IS NOT NULL AND ilm.movement_type IN ('SALE', 'RETURN')) AS total_cogs,
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
            WITH events AS (
                SELECT completed_at AS occurred_at, total_amount AS amount
                FROM orders WHERE completed_at >= NOW() - INTERVAL '14 days'
                UNION ALL
                SELECT completed_at, -refund_amount
                FROM refund_transactions
                WHERE status = 'COMPLETED' AND completed_at >= NOW() - INTERVAL '14 days'
            )
            SELECT to_char(occurred_at, 'DD/MM') AS date, SUM(amount) AS total
            FROM events
            GROUP BY to_char(occurred_at, 'DD/MM'), date_trunc('day', occurred_at)
            ORDER BY date_trunc('day', occurred_at) ASC
            """
        )
    )
    return [{"date": row.date, "total": float(row.total)} for row in result]


async def list_revenue_by_month(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH events AS (
                SELECT completed_at AS occurred_at, total_amount AS amount
                FROM orders WHERE completed_at >= NOW() - INTERVAL '6 months'
                UNION ALL
                SELECT completed_at, -refund_amount
                FROM refund_transactions
                WHERE status = 'COMPLETED' AND completed_at >= NOW() - INTERVAL '6 months'
            )
            SELECT to_char(occurred_at, 'MM/YYYY') AS month, SUM(amount) AS total
            FROM events
            GROUP BY to_char(occurred_at, 'MM/YYYY'), date_trunc('month', occurred_at)
            ORDER BY date_trunc('month', occurred_at) ASC
            """
        )
    )
    return [{"month": row.month, "total": float(row.total)} for row in result]


async def list_top_products(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT order_items.product_id AS id, MAX(product_name) AS name, SUM(quantity) AS soldCount,
                   SUM(
                       CASE WHEN orders.subtotal_amount > 0
                           THEN total_price * GREATEST(orders.subtotal_amount - orders.discount_amount, 0) / orders.subtotal_amount
                           ELSE 0
                       END
                   ) - COALESCE(SUM(refunds.refund_amount), 0) AS periodRevenue
            FROM order_items
            JOIN orders ON orders.id = order_items.order_id
            LEFT JOIN LATERAL (
                SELECT SUM(refund_amount) AS refund_amount
                FROM refund_transactions
                WHERE order_item_id = order_items.id AND status = 'COMPLETED'
            ) refunds ON TRUE
            WHERE orders.completed_at IS NOT NULL
            GROUP BY order_items.product_id
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
