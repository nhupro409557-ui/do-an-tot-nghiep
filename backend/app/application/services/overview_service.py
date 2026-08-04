from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import overview_repo
from app.infrastructure.database.repositories.reporting.revenue import (
    get_lifetime_revenue_summary,
)


async def get_admin_overview(session: AsyncSession) -> dict:
    row = await overview_repo.get_admin_overview_counts(session)
    revenue = await get_lifetime_revenue_summary(session)
    revenue_by_day = await overview_repo.list_revenue_by_day(session)
    revenue_by_month = await overview_repo.list_revenue_by_month(session)
    top_products = await overview_repo.list_top_products(session)

    return {
        "products": {"total": row["products_total"], "active": row["products_active"]},
        "categories": {"total": row["categories_total"]},
        "brands": {"total": row["brands_total"]},
        "orders": {
            "total": row["orders_total"],
            "pending": row["orders_pending"],
            "processing": row["orders_processing"],
            "cancelled": row["orders_cancelled"],
            "refunded": row["orders_refunded"],
        },
        "vouchers": {"total": row["vouchers_total"], "active": row["vouchers_active"]},
        "customers": {"total": row["customers_total"]},
        "reviews": {"total": row["reviews_total"], "pending": row["reviews_pending"]},
        "revenue": float(revenue["net_revenue"]),
        "costOfGoodsSold": float(revenue["cost_of_goods_sold"]),
        "grossProfit": float(
            revenue["net_revenue"] - revenue["cost_of_goods_sold"]
        ),
        "revenueByDay": revenue_by_day,
        "revenueByMonth": revenue_by_month,
        "topProducts": top_products,
        "lowStockCount": row["products_low_stock"],
        "negativeStockCount": row["products_negative_stock"],
        "riskyVoucherCount": row["vouchers_risky"],
    }
