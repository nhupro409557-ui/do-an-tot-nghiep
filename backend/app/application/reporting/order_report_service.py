from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.reporting.schemas import AdminOrderReportResponse
from app.infrastructure.database.repositories.reporting import orders as order_report_repo

from .period import ReportPeriod


async def get_order_report(
    session: AsyncSession,
    *,
    period: ReportPeriod,
    date_basis: str,
    status: str | None = None,
    channel: str | None = None,
    payment_method: str | None = None,
    payment_status: str | None = None,
    fulfillment_method: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> AdminOrderReportResponse:
    result = await order_report_repo.get_order_report(
        session,
        from_utc=period.from_utc,
        to_utc=period.to_utc,
        date_basis=date_basis,
        status=status.strip().upper() if status else None,
        channel=channel.strip().upper() if channel else None,
        payment_method=payment_method.strip().upper() if payment_method else None,
        payment_status=payment_status.strip().upper() if payment_status else None,
        fulfillment_method=(
            fulfillment_method.strip().upper() if fulfillment_method else None
        ),
        search=search,
        page=page,
        limit=limit,
    )
    summary = result["summary"]
    breakdowns = result["breakdowns"]
    return AdminOrderReportResponse(
        period={
            "fromDate": period.from_date,
            "toDate": period.to_date,
            "timezone": period.timezone_name,
            "bucket": period.bucket,
        },
        dateBasis=date_basis,
        summary={
            "totalOrders": summary["total_orders"],
            "completedOrders": summary["completed_orders"],
            "cancelledOrders": summary["cancelled_orders"],
            "totalAmount": summary["total_amount"],
            "averageOrderValue": summary["average_order_value"],
        },
        breakdowns={
            "statuses": _map_breakdown(breakdowns["statuses"]),
            "channels": _map_breakdown(breakdowns["channels"]),
            "paymentMethods": _map_breakdown(breakdowns["payment_methods"]),
            "paymentStatuses": _map_breakdown(breakdowns["payment_statuses"]),
            "fulfillmentMethods": _map_breakdown(
                breakdowns["fulfillment_methods"]
            ),
        },
        items=[
            {
                "id": item["id"],
                "orderCode": item["order_code"],
                "customerName": item["customer_name"],
                "email": item["email"],
                "status": item["status"],
                "channel": item["channel"],
                "paymentMethod": item["payment_method"],
                "paymentStatus": item["payment_status"],
                "fulfillmentMethod": item["fulfillment_method"],
                "totalAmount": item["total_amount"],
                "createdAt": item["created_at"].isoformat()
                if hasattr(item["created_at"], "isoformat")
                else str(item["created_at"]),
                "completedAt": (
                    item["completed_at"].isoformat()
                    if hasattr(item["completed_at"], "isoformat")
                    else item["completed_at"]
                ),
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


def _map_breakdown(items: list[dict]) -> list[dict]:
    return [
        {"key": item["key"], "count": item["count"], "amount": item["amount"]}
        for item in items
    ]
