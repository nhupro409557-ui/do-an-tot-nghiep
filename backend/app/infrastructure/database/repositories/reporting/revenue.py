from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _params(
    *,
    from_utc: datetime,
    to_utc: datetime,
    channel: str | None,
    payment_method: str | None,
) -> dict:
    return {
        "from_utc": from_utc,
        "to_utc": to_utc,
        "channel": channel,
        "payment_method": payment_method,
    }


def _cogs_period_filter_sql() -> str:
    return """
        ilm.created_at >= :from_utc
        AND ilm.created_at < :to_utc
    """


async def get_revenue_summary(
    session: AsyncSession,
    *,
    from_utc: datetime,
    to_utc: datetime,
    channel: str | None = None,
    payment_method: str | None = None,
) -> dict:
    result = await session.execute(
        text(
            f"""
            WITH filtered_orders AS (
                SELECT id, total_amount
                FROM orders
                WHERE completed_at >= :from_utc
                  AND completed_at < :to_utc
                  AND COALESCE(order_purpose, 'SALE') <> 'WARRANTY_RETURN'
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR payment_method = CAST(:payment_method AS text)
                  )
            ),
            filtered_refunds AS (
                SELECT rt.refund_amount
                FROM refund_transactions rt
                JOIN orders o ON o.id = rt.order_id
                WHERE rt.status = 'COMPLETED'
                  AND COALESCE(o.order_purpose, 'SALE') <> 'WARRANTY_RETURN'
                  AND rt.completed_at >= :from_utc
                  AND rt.completed_at < :to_utc
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR o.order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR o.payment_method = CAST(:payment_method AS text)
                  )
            ),
            filtered_cogs AS (
                SELECT CASE
                    WHEN ilm.movement_type = 'SALE' THEN ilm.quantity * COALESCE(il.unit_cost, 0)
                    WHEN ilm.movement_type = 'RETURN' THEN -ilm.quantity * COALESCE(il.unit_cost, 0)
                    ELSE 0
                END AS amount
                FROM inventory_lot_movements ilm
                JOIN inventory_lots il ON il.id = ilm.lot_id
                JOIN orders o ON o.id = ilm.order_id
                WHERE {_cogs_period_filter_sql()}
                  AND ilm.movement_type IN ('SALE', 'RETURN')
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR o.order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR o.payment_method = CAST(:payment_method AS text)
                  )
            )
            SELECT
                (SELECT COUNT(*) FROM filtered_orders) AS completed_orders,
                (SELECT COALESCE(SUM(total_amount), 0) FROM filtered_orders) AS gross_revenue,
                (SELECT COALESCE(SUM(refund_amount), 0) FROM filtered_refunds) AS refund_amount,
                (SELECT COALESCE(SUM(amount), 0) FROM filtered_cogs) AS cost_of_goods_sold
            """
        ),
        _params(
            from_utc=from_utc,
            to_utc=to_utc,
            channel=channel,
            payment_method=payment_method,
        ),
    )
    row = result.mappings().one()
    gross_revenue = Decimal(row["gross_revenue"] or 0)
    refund_amount = Decimal(row["refund_amount"] or 0)
    completed_orders = int(row["completed_orders"] or 0)
    net_revenue = gross_revenue - refund_amount
    return {
        "completed_orders": completed_orders,
        "gross_revenue": gross_revenue,
        "refund_amount": refund_amount,
        "net_revenue": net_revenue,
        "average_order_value": (
            net_revenue / completed_orders if completed_orders else Decimal("0")
        ),
        "cost_of_goods_sold": Decimal(row["cost_of_goods_sold"] or 0),
    }


async def get_lifetime_revenue_summary(session: AsyncSession) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM orders
                 WHERE completed_at IS NOT NULL
                   AND COALESCE(order_purpose, 'SALE') <> 'WARRANTY_RETURN') AS completed_orders,
                (SELECT COALESCE(SUM(total_amount), 0)
                 FROM orders
                 WHERE completed_at IS NOT NULL
                   AND COALESCE(order_purpose, 'SALE') <> 'WARRANTY_RETURN') AS gross_revenue,
                (SELECT COALESCE(SUM(refund_amount), 0)
                 FROM refund_transactions WHERE status = 'COMPLETED') AS refund_amount,
                (
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN ilm.movement_type = 'SALE'
                                THEN ilm.quantity * COALESCE(il.unit_cost, 0)
                            WHEN ilm.movement_type = 'RETURN'
                                THEN -ilm.quantity * COALESCE(il.unit_cost, 0)
                            ELSE 0
                        END
                    ), 0)
                    FROM inventory_lot_movements ilm
                    JOIN inventory_lots il ON il.id = ilm.lot_id
                    WHERE ilm.order_id IS NOT NULL
                      AND ilm.movement_type IN ('SALE', 'RETURN')
                ) AS cost_of_goods_sold
            """
        )
    )
    row = result.mappings().one()
    completed_orders = int(row["completed_orders"] or 0)
    gross_revenue = Decimal(row["gross_revenue"] or 0)
    refund_amount = Decimal(row["refund_amount"] or 0)
    net_revenue = gross_revenue - refund_amount
    return {
        "completed_orders": completed_orders,
        "gross_revenue": gross_revenue,
        "refund_amount": refund_amount,
        "net_revenue": net_revenue,
        "average_order_value": (
            net_revenue / completed_orders if completed_orders else Decimal("0")
        ),
        "cost_of_goods_sold": Decimal(row["cost_of_goods_sold"] or 0),
    }


async def get_revenue_series(
    session: AsyncSession,
    *,
    from_utc: datetime,
    to_utc: datetime,
    timezone_name: str,
    bucket: str,
    channel: str | None = None,
    payment_method: str | None = None,
) -> list[dict]:
    params = _params(
        from_utc=from_utc,
        to_utc=to_utc,
        channel=channel,
        payment_method=payment_method,
    )
    params.update({"timezone_name": timezone_name, "bucket": bucket})
    result = await session.execute(
        text(
            """
            WITH events AS (
                SELECT
                    completed_at AS occurred_at,
                    total_amount AS gross_amount,
                    0::numeric AS refund_amount
                FROM orders
                WHERE completed_at >= :from_utc
                  AND completed_at < :to_utc
                  AND COALESCE(order_purpose, 'SALE') <> 'WARRANTY_RETURN'
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR payment_method = CAST(:payment_method AS text)
                  )
                UNION ALL
                SELECT rt.completed_at, 0::numeric, rt.refund_amount
                FROM refund_transactions rt
                JOIN orders o ON o.id = rt.order_id
                WHERE rt.status = 'COMPLETED'
                  AND COALESCE(o.order_purpose, 'SALE') <> 'WARRANTY_RETURN'
                  AND rt.completed_at >= :from_utc
                  AND rt.completed_at < :to_utc
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR o.order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR o.payment_method = CAST(:payment_method AS text)
                  )
            )
            SELECT
                date_trunc(:bucket, occurred_at AT TIME ZONE :timezone_name)::date AS period_start,
                COALESCE(SUM(gross_amount), 0) AS gross_revenue,
                COALESCE(SUM(refund_amount), 0) AS refund_amount
            FROM events
            GROUP BY period_start
            ORDER BY period_start
            """
        ),
        params,
    )
    return [
        {
            "period_start": row["period_start"],
            "gross_revenue": Decimal(row["gross_revenue"] or 0),
            "refund_amount": Decimal(row["refund_amount"] or 0),
            "net_revenue": Decimal(row["gross_revenue"] or 0)
            - Decimal(row["refund_amount"] or 0),
        }
        for row in result.mappings().all()
    ]


async def get_revenue_breakdowns(
    session: AsyncSession,
    *,
    from_utc: datetime,
    to_utc: datetime,
    channel: str | None = None,
    payment_method: str | None = None,
) -> dict[str, list[dict]]:
    params = _params(
        from_utc=from_utc,
        to_utc=to_utc,
        channel=channel,
        payment_method=payment_method,
    )
    result = await session.execute(
        text(
            """
            WITH events AS (
                SELECT
                    order_type AS channel,
                    payment_method,
                    1 AS completed_orders,
                    total_amount AS gross_amount,
                    0::numeric AS refund_amount
                FROM orders
                WHERE completed_at >= :from_utc
                  AND completed_at < :to_utc
                  AND COALESCE(order_purpose, 'SALE') <> 'WARRANTY_RETURN'
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR payment_method = CAST(:payment_method AS text)
                  )
                UNION ALL
                SELECT
                    o.order_type,
                    o.payment_method,
                    0,
                    0::numeric,
                    rt.refund_amount
                FROM refund_transactions rt
                JOIN orders o ON o.id = rt.order_id
                WHERE rt.status = 'COMPLETED'
                  AND COALESCE(o.order_purpose, 'SALE') <> 'WARRANTY_RETURN'
                  AND rt.completed_at >= :from_utc
                  AND rt.completed_at < :to_utc
                  AND (
                    CAST(:channel AS text) IS NULL
                    OR o.order_type = CAST(:channel AS text)
                  )
                  AND (
                    CAST(:payment_method AS text) IS NULL
                    OR o.payment_method = CAST(:payment_method AS text)
                  )
            ),
            channel_rows AS (
                SELECT channel AS key,
                       SUM(completed_orders) AS completed_orders,
                       SUM(gross_amount) AS gross_revenue,
                       SUM(refund_amount) AS refund_amount
                FROM events
                GROUP BY channel
            ),
            payment_rows AS (
                SELECT payment_method AS key,
                       SUM(completed_orders) AS completed_orders,
                       SUM(gross_amount) AS gross_revenue,
                       SUM(refund_amount) AS refund_amount
                FROM events
                GROUP BY payment_method
            )
            SELECT 'channel' AS dimension, key, completed_orders, gross_revenue, refund_amount
            FROM channel_rows
            UNION ALL
            SELECT 'payment_method', key, completed_orders, gross_revenue, refund_amount
            FROM payment_rows
            ORDER BY dimension, gross_revenue DESC, key
            """
        ),
        params,
    )
    breakdowns: dict[str, list[dict]] = {"channels": [], "payment_methods": []}
    for row in result.mappings().all():
        gross_revenue = Decimal(row["gross_revenue"] or 0)
        refund_amount = Decimal(row["refund_amount"] or 0)
        item = {
            "key": str(row["key"] or "UNKNOWN"),
            "completed_orders": int(row["completed_orders"] or 0),
            "gross_revenue": gross_revenue,
            "refund_amount": refund_amount,
            "net_revenue": gross_revenue - refund_amount,
        }
        target = "channels" if row["dimension"] == "channel" else "payment_methods"
        breakdowns[target].append(item)
    return breakdowns
