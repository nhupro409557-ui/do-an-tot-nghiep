from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_customer_report(
    session: AsyncSession,
    *,
    from_utc: datetime,
    to_utc: datetime,
    tier: str | None = None,
    segment: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    normalized_search = f"%{search.strip().lower()}%" if search and search.strip() else None
    params = {
        "from_utc": from_utc,
        "to_utc": to_utc,
        "tier": tier,
        "segment": segment,
        "search": normalized_search,
        "limit": limit,
        "offset": (page - 1) * limit,
    }
    base_cte = """
        WITH customer_users AS (
            SELECT u.*
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE r.code = 'CUSTOMER' AND u.deleted_at IS NULL
        ),
        customer_activity AS (
            SELECT
                u.id,
                u.full_name,
                u.email,
                COALESCE(u.loyalty_tier, 'MEMBER') AS tier,
                u.created_at AS registered_at,
                COUNT(DISTINCT o.id) FILTER (
                    WHERE o.completed_at >= :from_utc AND o.completed_at < :to_utc
                )::integer AS order_count,
                COALESCE(SUM(o.total_amount) FILTER (
                    WHERE o.completed_at >= :from_utc AND o.completed_at < :to_utc
                ), 0) - COALESCE(refunds.amount, 0) AS net_spent,
                EXISTS (
                    SELECT 1 FROM orders previous_order
                    WHERE previous_order.user_id = u.id
                      AND previous_order.completed_at < :from_utc
                ) AS bought_before,
                EXISTS (
                    SELECT 1 FROM orders period_order
                    WHERE period_order.user_id = u.id
                      AND period_order.completed_at >= :from_utc
                      AND period_order.completed_at < :to_utc
                ) AS bought_in_period
            FROM customer_users u
            LEFT JOIN orders o ON o.user_id = u.id
            LEFT JOIN LATERAL (
                SELECT SUM(rt.refund_amount) AS amount
                FROM refund_transactions rt
                WHERE rt.user_id = u.id
                  AND rt.status = 'COMPLETED'
                  AND rt.completed_at >= :from_utc
                  AND rt.completed_at < :to_utc
            ) refunds ON TRUE
            GROUP BY
                u.id,
                u.full_name,
                u.email,
                u.loyalty_tier,
                u.created_at,
                refunds.amount
        ),
        report_customers AS (
            SELECT *,
                CASE
                    WHEN bought_in_period AND bought_before THEN 'RETURNING'
                    WHEN bought_in_period THEN 'FIRST_TIME'
                    ELSE 'NEW_NO_ORDER'
                END AS segment
            FROM customer_activity
            WHERE (
                (registered_at >= :from_utc AND registered_at < :to_utc)
                OR bought_in_period
            )
        ),
        filtered_customers AS (
            SELECT *
            FROM report_customers
            WHERE (CAST(:tier AS text) IS NULL OR tier = CAST(:tier AS text))
              AND (CAST(:segment AS text) IS NULL OR segment = CAST(:segment AS text))
              AND (
                CAST(:search AS text) IS NULL
                OR LOWER(full_name) LIKE CAST(:search AS text)
                OR LOWER(email) LIKE CAST(:search AS text)
              )
        )
    """
    summary_result = await session.execute(
        text(
            base_cte
            + """
            SELECT
                COUNT(*) FILTER (
                    WHERE registered_at >= :from_utc AND registered_at < :to_utc
                ) AS new_customers,
                COUNT(*) FILTER (WHERE bought_in_period) AS active_customers,
                COUNT(*) FILTER (WHERE segment = 'FIRST_TIME') AS first_time_buyers,
                COUNT(*) FILTER (WHERE segment = 'RETURNING') AS returning_customers
            FROM report_customers
            """
        ),
        params,
    )
    summary = dict(summary_result.mappings().one())
    tiers_result = await session.execute(
        text(
            base_cte
            + """
            SELECT tier, COUNT(*) AS customers, COALESCE(SUM(net_spent), 0) AS net_revenue
            FROM report_customers
            WHERE bought_in_period
            GROUP BY tier
            ORDER BY customers DESC, tier
            """
        ),
        params,
    )
    total_result = await session.execute(
        text(
            base_cte
            + """
            SELECT COUNT(*)::integer
            FROM filtered_customers
            """
        ),
        params,
    )
    total = int(total_result.scalar_one() or 0)
    items_result = await session.execute(
        text(
            base_cte
            + """
            SELECT id::text, full_name, email, tier, registered_at,
                   order_count, net_spent, segment
            FROM filtered_customers
            ORDER BY net_spent DESC, registered_at DESC, id
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    items = [dict(row) for row in items_result.mappings().all()]
    return {
        "summary": summary,
        "tiers": [
            {
                "tier": row["tier"],
                "customers": int(row["customers"] or 0),
                "net_revenue": Decimal(row["net_revenue"] or 0),
            }
            for row in tiers_result.mappings().all()
        ],
        "items": items,
        "total": total,
    }


async def get_customer_retention(
    session: AsyncSession,
    *,
    cohort_limit: int = 12,
    timezone_name: str = "Asia/Bangkok",
) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH customer_users AS (
                SELECT u.id, date_trunc(
                    'month', u.created_at AT TIME ZONE :timezone_name
                )::date AS cohort_month
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE r.code = 'CUSTOMER' AND u.deleted_at IS NULL
            ),
            recent_cohorts AS (
                SELECT DISTINCT cohort_month
                FROM customer_users
                ORDER BY cohort_month DESC
                LIMIT :cohort_limit
            ),
            cohort_sizes AS (
                SELECT cu.cohort_month, COUNT(*)::integer AS cohort_size
                FROM customer_users cu
                JOIN recent_cohorts rc ON rc.cohort_month = cu.cohort_month
                GROUP BY cu.cohort_month
            ),
            retained AS (
                SELECT
                    cu.cohort_month,
                    (
                        EXTRACT(YEAR FROM age(activity.activity_month, cu.cohort_month)) * 12
                        + EXTRACT(MONTH FROM age(activity.activity_month, cu.cohort_month))
                    )::integer AS month_offset,
                    COUNT(DISTINCT cu.id)::integer AS customers
                FROM customer_users cu
                JOIN recent_cohorts rc ON rc.cohort_month = cu.cohort_month
                JOIN LATERAL (
                    SELECT DISTINCT date_trunc(
                        'month', o.completed_at AT TIME ZONE :timezone_name
                    )::date AS activity_month
                    FROM orders o
                    WHERE o.user_id = cu.id AND o.completed_at IS NOT NULL
                ) activity ON activity.activity_month >= cu.cohort_month
                GROUP BY cu.cohort_month, activity.activity_month
            )
            SELECT cs.cohort_month, cs.cohort_size,
                   retained.month_offset, retained.customers
            FROM cohort_sizes cs
            LEFT JOIN retained ON retained.cohort_month = cs.cohort_month
            ORDER BY cs.cohort_month DESC, retained.month_offset
            """
        ),
        {"cohort_limit": cohort_limit, "timezone_name": timezone_name},
    )
    return [dict(row) for row in result.mappings().all()]
