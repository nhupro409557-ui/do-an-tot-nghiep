from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.reporting.schemas import (
    AdminCustomerReportResponse,
    AdminCustomerRetentionResponse,
)
from app.infrastructure.database.repositories.reporting import customers as customer_report_repo

from .period import ReportPeriod


def _percentage(part: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return (Decimal(part) * 100 / Decimal(total)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


async def get_customer_report(
    session: AsyncSession,
    *,
    period: ReportPeriod,
    tier: str | None = None,
    segment: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> AdminCustomerReportResponse:
    result = await customer_report_repo.get_customer_report(
        session,
        from_utc=period.from_utc,
        to_utc=period.to_utc,
        tier=tier.strip().upper() if tier else None,
        segment=segment.strip().upper() if segment else None,
        search=search,
        page=page,
        limit=limit,
    )
    summary = result["summary"]
    active_customers = int(summary["active_customers"] or 0)
    returning_customers = int(summary["returning_customers"] or 0)
    return AdminCustomerReportResponse(
        period={"fromDate": period.from_date, "toDate": period.to_date,
                "timezone": period.timezone_name, "bucket": period.bucket},
        summary={
            "newCustomers": int(summary["new_customers"] or 0),
            "activeCustomers": active_customers,
            "firstTimeBuyers": int(summary["first_time_buyers"] or 0),
            "returningCustomers": returning_customers,
            "repeatPurchaseRate": _percentage(returning_customers, active_customers),
        },
        tiers=[{"tier": row["tier"], "customers": row["customers"],
                "netRevenue": row["net_revenue"]} for row in result["tiers"]],
        items=[{
            "id": row["id"], "fullName": row["full_name"], "email": row["email"],
            "tier": row["tier"], "registeredAt": (
                row["registered_at"].isoformat()
                if hasattr(row["registered_at"], "isoformat") else str(row["registered_at"])
            ),
            "orderCount": row["order_count"], "netSpent": row["net_spent"],
            "segment": row["segment"],
        } for row in result["items"]],
        pagination={"page": page, "limit": limit, "total": result["total"],
                    "totalPages": ceil(result["total"] / limit) if result["total"] else 0},
    )


async def get_customer_retention_report(
    session: AsyncSession,
    *,
    cohort_limit: int = 12,
    timezone_name: str = "Asia/Bangkok",
) -> AdminCustomerRetentionResponse:
    rows = await customer_report_repo.get_customer_retention(
        session, cohort_limit=cohort_limit, timezone_name=timezone_name
    )
    cohorts: dict[date, dict] = {}
    for row in rows:
        cohort_month = row["cohort_month"]
        cohort_size = int(row["cohort_size"] or 0)
        cohort = cohorts.setdefault(cohort_month, {
            "cohortMonth": cohort_month, "cohortSize": cohort_size, "periods": []
        })
        if row["month_offset"] is not None:
            customers = int(row["customers"] or 0)
            cohort["periods"].append({
                "monthOffset": int(row["month_offset"]),
                "customers": customers,
                "retentionRate": _percentage(customers, cohort_size),
            })
    return AdminCustomerRetentionResponse(timezone=timezone_name, cohorts=list(cohorts.values()))
