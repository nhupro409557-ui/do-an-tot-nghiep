from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


SORT_COLUMNS = {
    "unitsSold": "units_sold",
    "grossRevenue": "gross_revenue",
    "refundAmount": "refund_amount",
    "netRevenue": "net_revenue",
}


def _product_metrics_cte() -> str:
    return """
        WITH item_metrics AS (
            SELECT
                oi.id AS order_item_id,
                oi.order_id,
                COALESCE(oi.product_id, ud.product_id) AS product_id,
                COALESCE(oi.variant_id, ud.variant_id) AS variant_id,
                COALESCE(pv.sku, p.sku, ud.device_code, 'HANG-CU') AS sku,
                oi.product_name,
                p.category_id,
                p.subcategory_id,
                p.brand_id,
                (
                    o.completed_at >= :from_utc
                    AND o.completed_at < :to_utc
                ) AS sold_in_period,
                CASE
                    WHEN o.completed_at >= :from_utc AND o.completed_at < :to_utc
                    THEN oi.quantity ELSE 0
                END AS units_sold,
                CASE
                    WHEN o.completed_at >= :from_utc AND o.completed_at < :to_utc
                    THEN oi.total_price ELSE 0
                END AS gross_revenue,
                CASE
                    WHEN o.completed_at >= :from_utc
                     AND o.completed_at < :to_utc
                     AND o.subtotal_amount > 0
                    THEN oi.total_price * o.discount_amount / o.subtotal_amount
                    ELSE 0
                END AS allocated_discount,
                COALESCE(refunds.refund_amount, 0) AS refund_amount
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            LEFT JOIN used_devices ud ON ud.id = oi.used_device_id
            LEFT JOIN products p ON p.id = COALESCE(oi.product_id, ud.product_id)
            LEFT JOIN product_variants pv
                ON pv.id = COALESCE(oi.variant_id, ud.variant_id)
            LEFT JOIN LATERAL (
                SELECT SUM(rt.refund_amount) AS refund_amount
                FROM refund_transactions rt
                WHERE rt.order_item_id = oi.id
                  AND rt.status = 'COMPLETED'
                  AND rt.completed_at >= :from_utc
                  AND rt.completed_at < :to_utc
            ) refunds ON TRUE
            WHERE (
                (o.completed_at >= :from_utc AND o.completed_at < :to_utc)
                OR COALESCE(refunds.refund_amount, 0) > 0
            )
              AND (
                CAST(:category_id AS uuid) IS NULL
                OR p.category_id = CAST(:category_id AS uuid)
                OR p.subcategory_id = CAST(:category_id AS uuid)
              )
              AND (
                CAST(:brand_id AS uuid) IS NULL
                OR p.brand_id = CAST(:brand_id AS uuid)
              )
              AND (
                CAST(:search AS text) IS NULL
                OR LOWER(oi.product_name) LIKE CAST(:search AS text)
                OR LOWER(COALESCE(pv.sku, p.sku, ud.device_code, ''))
                    LIKE CAST(:search AS text)
              )
        ),
        grouped_products AS (
            SELECT
                product_id::text AS product_id,
                variant_id::text AS variant_id,
                MAX(sku) AS sku,
                MAX(product_name) AS product_name,
                SUM(units_sold)::integer AS units_sold,
                COUNT(DISTINCT order_id)
                    FILTER (WHERE sold_in_period)::integer AS order_count,
                SUM(gross_revenue) AS gross_revenue,
                SUM(allocated_discount) AS allocated_discount,
                SUM(refund_amount) AS refund_amount,
                SUM(gross_revenue - allocated_discount - refund_amount) AS net_revenue
            FROM item_metrics
            GROUP BY product_id, variant_id, sku
        )
    """


async def get_product_report(
    session: AsyncSession,
    *,
    from_utc: datetime,
    to_utc: datetime,
    category_id: UUID | None = None,
    brand_id: UUID | None = None,
    search: str | None = None,
    sort_by: str = "netRevenue",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 20,
) -> dict:
    normalized_search = f"%{search.strip().lower()}%" if search and search.strip() else None
    params = {
        "from_utc": from_utc,
        "to_utc": to_utc,
        "category_id": category_id,
        "brand_id": brand_id,
        "search": normalized_search,
        "limit": limit,
        "offset": (page - 1) * limit,
    }
    cte = _product_metrics_cte()
    summary_result = await session.execute(
        text(
            cte
            + """
            SELECT
                COUNT(*) AS total_products,
                COALESCE(SUM(units_sold), 0) AS units_sold,
                COALESCE(SUM(gross_revenue), 0) AS gross_revenue,
                COALESCE(SUM(allocated_discount), 0) AS allocated_discount,
                COALESCE(SUM(refund_amount), 0) AS refund_amount,
                COALESCE(SUM(net_revenue), 0) AS net_revenue,
                (
                    SELECT COALESCE(SUM(rt.refund_amount), 0)
                    FROM refund_transactions rt
                    WHERE rt.status = 'COMPLETED'
                      AND rt.order_item_id IS NULL
                      AND rt.completed_at >= :from_utc
                      AND rt.completed_at < :to_utc
                      AND CAST(:category_id AS uuid) IS NULL
                      AND CAST(:brand_id AS uuid) IS NULL
                      AND CAST(:search AS text) IS NULL
                ) AS unallocated_refund_amount
            FROM grouped_products
            """
        ),
        params,
    )
    summary_row = summary_result.mappings().one()
    order_column = SORT_COLUMNS[sort_by]
    order_direction = "ASC" if sort_order == "asc" else "DESC"
    items_result = await session.execute(
        text(
            cte
            + f"""
            SELECT *
            FROM grouped_products
            ORDER BY {order_column} {order_direction}, product_name, sku
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    total = int(summary_row["total_products"] or 0)
    return {
        "summary": {
            "total_products": total,
            "units_sold": int(summary_row["units_sold"] or 0),
            "gross_revenue": Decimal(summary_row["gross_revenue"] or 0),
            "allocated_discount": Decimal(summary_row["allocated_discount"] or 0),
            "refund_amount": Decimal(summary_row["refund_amount"] or 0),
            "net_revenue": Decimal(summary_row["net_revenue"] or 0),
            "unallocated_refund_amount": Decimal(
                summary_row["unallocated_refund_amount"] or 0
            ),
        },
        "items": [dict(row) for row in items_result.mappings().all()],
        "total": total,
    }
