from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.reporting.schemas import AdminRevenueReportResponse
from app.infrastructure.database.repositories.reporting import revenue as revenue_repo

from .period import ReportPeriod, calculate_percentage_change


async def get_revenue_report(
    session: AsyncSession,
    *,
    period: ReportPeriod,
    channel: str | None = None,
    payment_method: str | None = None,
    include_profit: bool = False,
) -> AdminRevenueReportResponse:
    normalized_channel = channel.strip().upper() if channel else None
    normalized_payment_method = payment_method.strip().upper() if payment_method else None

    current = await revenue_repo.get_revenue_summary(
        session,
        from_utc=period.from_utc,
        to_utc=period.to_utc,
        channel=normalized_channel,
        payment_method=normalized_payment_method,
    )
    previous = await revenue_repo.get_revenue_summary(
        session,
        from_utc=period.previous_from_utc,
        to_utc=period.previous_to_utc,
        channel=normalized_channel,
        payment_method=normalized_payment_method,
    )
    series = await revenue_repo.get_revenue_series(
        session,
        from_utc=period.from_utc,
        to_utc=period.to_utc,
        timezone_name=period.timezone_name,
        bucket=period.bucket,
        channel=normalized_channel,
        payment_method=normalized_payment_method,
    )
    breakdowns = await revenue_repo.get_revenue_breakdowns(
        session,
        from_utc=period.from_utc,
        to_utc=period.to_utc,
        channel=normalized_channel,
        payment_method=normalized_payment_method,
    )

    cost_of_goods_sold = current["cost_of_goods_sold"] if include_profit else None
    gross_profit = (
        current["net_revenue"] - current["cost_of_goods_sold"]
        if include_profit
        else None
    )
    return AdminRevenueReportResponse(
        period={
            "fromDate": period.from_date,
            "toDate": period.to_date,
            "timezone": period.timezone_name,
            "bucket": period.bucket,
        },
        summary={
            "completedOrders": current["completed_orders"],
            "grossRevenue": current["gross_revenue"],
            "refundAmount": current["refund_amount"],
            "netRevenue": current["net_revenue"],
            "averageOrderValue": current["average_order_value"],
            "costOfGoodsSold": cost_of_goods_sold,
            "grossProfit": gross_profit,
        },
        comparison={
            "previousNetRevenue": previous["net_revenue"],
            "previousCompletedOrders": previous["completed_orders"],
            "revenueChangePercent": calculate_percentage_change(
                current["net_revenue"],
                previous["net_revenue"],
            ),
            "completedOrdersChangePercent": calculate_percentage_change(
                Decimal(current["completed_orders"]),
                Decimal(previous["completed_orders"]),
            ),
        },
        series=[
            {
                "periodStart": item["period_start"],
                "grossRevenue": item["gross_revenue"],
                "refundAmount": item["refund_amount"],
                "netRevenue": item["net_revenue"],
            }
            for item in series
        ],
        breakdowns={
            "channels": [
                {
                    "key": item["key"],
                    "completedOrders": item["completed_orders"],
                    "grossRevenue": item["gross_revenue"],
                    "refundAmount": item["refund_amount"],
                    "netRevenue": item["net_revenue"],
                }
                for item in breakdowns["channels"]
            ],
            "paymentMethods": [
                {
                    "key": item["key"],
                    "completedOrders": item["completed_orders"],
                    "grossRevenue": item["gross_revenue"],
                    "refundAmount": item["refund_amount"],
                    "netRevenue": item["net_revenue"],
                }
                for item in breakdowns["payment_methods"]
            ],
        },
    )
