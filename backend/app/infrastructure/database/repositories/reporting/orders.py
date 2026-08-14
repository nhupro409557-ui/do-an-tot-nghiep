from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


DATE_COLUMNS = {
    "createdAt": "o.created_at",
    "completedAt": "o.completed_at",
}


def _build_filters(
    *,
    date_basis: str,
    status: str | None,
    channel: str | None,
    payment_method: str | None,
    payment_status: str | None,
    fulfillment_method: str | None,
    search: str | None,
) -> str:
    date_column = DATE_COLUMNS[date_basis]
    clauses = [
        f"{date_column} >= :from_utc",
        f"{date_column} < :to_utc",
        "COALESCE(o.order_purpose, 'SALE') <> 'WARRANTY_RETURN'",
        "(CAST(:status AS text) IS NULL OR o.status = CAST(:status AS text))",
        "(CAST(:channel AS text) IS NULL OR o.order_type = CAST(:channel AS text))",
        """(
            CAST(:payment_method AS text) IS NULL
            OR o.payment_method = CAST(:payment_method AS text)
        )""",
        """(
            CAST(:payment_status AS text) IS NULL
            OR o.payment_status = CAST(:payment_status AS text)
        )""",
        """(
            CAST(:fulfillment_method AS text) IS NULL
            OR o.fulfillment_method = CAST(:fulfillment_method AS text)
        )""",
        """(
            CAST(:search AS text) IS NULL
            OR LOWER(o.order_code) LIKE CAST(:search AS text)
            OR LOWER(COALESCE(u.full_name, o.recipient_name, '')) LIKE CAST(:search AS text)
            OR LOWER(COALESCE(u.email, o.recipient_email, '')) LIKE CAST(:search AS text)
        )""",
    ]
    return " AND ".join(clauses)


async def get_order_report(
    session: AsyncSession,
    *,
    from_utc: datetime,
    to_utc: datetime,
    date_basis: str,
    status: str | None = None,
    channel: str | None = None,
    payment_method: str | None = None,
    payment_status: str | None = None,
    fulfillment_method: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    normalized_search = f"%{search.strip().lower()}%" if search and search.strip() else None
    params = {
        "from_utc": from_utc,
        "to_utc": to_utc,
        "status": status,
        "channel": channel,
        "payment_method": payment_method,
        "payment_status": payment_status,
        "fulfillment_method": fulfillment_method,
        "search": normalized_search,
        "limit": limit,
        "offset": (page - 1) * limit,
    }
    where_sql = _build_filters(
        date_basis=date_basis,
        status=status,
        channel=channel,
        payment_method=payment_method,
        payment_status=payment_status,
        fulfillment_method=fulfillment_method,
        search=search,
    )
    summary_result = await session.execute(
        text(
            f"""
            SELECT
                COUNT(*) AS total_orders,
                COUNT(*) FILTER (WHERE o.completed_at IS NOT NULL) AS completed_orders,
                COUNT(*) FILTER (
                    WHERE o.status IN ('CANCELLED', 'CANCELED')
                ) AS cancelled_orders,
                COALESCE(SUM(o.total_amount), 0) AS total_amount
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            WHERE {where_sql}
            """
        ),
        params,
    )
    summary_row = summary_result.mappings().one()
    total_orders = int(summary_row["total_orders"] or 0)
    total_amount = Decimal(summary_row["total_amount"] or 0)

    breakdown_result = await session.execute(
        text(
            f"""
            WITH filtered_orders AS (
                SELECT
                    o.status,
                    o.order_type,
                    o.payment_method,
                    o.payment_status,
                    o.fulfillment_method,
                    o.total_amount
                FROM orders o
                LEFT JOIN users u ON u.id = o.user_id
                WHERE {where_sql}
            ),
            breakdowns AS (
                SELECT 'status' AS dimension, status AS key,
                       COUNT(*) AS count, SUM(total_amount) AS amount
                FROM filtered_orders GROUP BY status
                UNION ALL
                SELECT 'channel', order_type, COUNT(*), SUM(total_amount)
                FROM filtered_orders GROUP BY order_type
                UNION ALL
                SELECT 'payment_method', payment_method, COUNT(*), SUM(total_amount)
                FROM filtered_orders GROUP BY payment_method
                UNION ALL
                SELECT 'payment_status', payment_status, COUNT(*), SUM(total_amount)
                FROM filtered_orders GROUP BY payment_status
                UNION ALL
                SELECT 'fulfillment_method', fulfillment_method, COUNT(*), SUM(total_amount)
                FROM filtered_orders GROUP BY fulfillment_method
            )
            SELECT dimension, key, count, amount
            FROM breakdowns
            ORDER BY dimension, count DESC, key
            """
        ),
        params,
    )
    dimension_targets = {
        "status": "statuses",
        "channel": "channels",
        "payment_method": "payment_methods",
        "payment_status": "payment_statuses",
        "fulfillment_method": "fulfillment_methods",
    }
    breakdowns: dict[str, list[dict]] = {
        "statuses": [],
        "channels": [],
        "payment_methods": [],
        "payment_statuses": [],
        "fulfillment_methods": [],
    }
    for row in breakdown_result.mappings().all():
        breakdowns[dimension_targets[row["dimension"]]].append(
            {
                "key": str(row["key"] or "UNKNOWN"),
                "count": int(row["count"] or 0),
                "amount": Decimal(row["amount"] or 0),
            }
        )

    items_result = await session.execute(
        text(
            f"""
            SELECT
                o.id::text AS id,
                o.order_code AS order_code,
                COALESCE(u.full_name, o.recipient_name) AS customer_name,
                COALESCE(u.email, o.recipient_email) AS email,
                o.status,
                o.order_type AS channel,
                o.payment_method,
                o.payment_status,
                o.fulfillment_method,
                o.total_amount,
                o.created_at,
                o.completed_at
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            WHERE {where_sql}
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return {
        "summary": {
            "total_orders": total_orders,
            "completed_orders": int(summary_row["completed_orders"] or 0),
            "cancelled_orders": int(summary_row["cancelled_orders"] or 0),
            "total_amount": total_amount,
            "average_order_value": (
                total_amount / total_orders if total_orders else Decimal("0")
            ),
        },
        "breakdowns": breakdowns,
        "items": [dict(row) for row in items_result.mappings().all()],
        "total": total_orders,
    }
