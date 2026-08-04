from math import ceil
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.reporting.schemas import AdminProductReportResponse
from app.infrastructure.database.repositories.reporting import products as product_report_repo

from .period import ReportPeriod


async def get_product_report(
    session: AsyncSession,
    *,
    period: ReportPeriod,
    category_id: UUID | None = None,
    brand_id: UUID | None = None,
    search: str | None = None,
    sort_by: str = "netRevenue",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 20,
) -> AdminProductReportResponse:
    result = await product_report_repo.get_product_report(
        session,
        from_utc=period.from_utc,
        to_utc=period.to_utc,
        category_id=category_id,
        brand_id=brand_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )
    summary = result["summary"]
    return AdminProductReportResponse(
        period={
            "fromDate": period.from_date,
            "toDate": period.to_date,
            "timezone": period.timezone_name,
            "bucket": period.bucket,
        },
        summary={
            "totalProducts": summary["total_products"],
            "unitsSold": summary["units_sold"],
            "grossRevenue": summary["gross_revenue"],
            "allocatedDiscount": summary["allocated_discount"],
            "refundAmount": summary["refund_amount"],
            "netRevenue": summary["net_revenue"],
            "unallocatedRefundAmount": summary["unallocated_refund_amount"],
        },
        items=[
            {
                "productId": item["product_id"],
                "variantId": item["variant_id"],
                "sku": item["sku"],
                "productName": item["product_name"],
                "unitsSold": item["units_sold"],
                "orderCount": item["order_count"],
                "grossRevenue": item["gross_revenue"],
                "allocatedDiscount": item["allocated_discount"],
                "refundAmount": item["refund_amount"],
                "netRevenue": item["net_revenue"],
            }
            for item in result["items"]
        ],
        pagination={
            "page": page,
            "limit": limit,
            "total": result["total"],
            "totalPages": ceil(result["total"] / limit) if result["total"] else 0,
        },
    )
