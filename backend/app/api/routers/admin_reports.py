from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user_id,
    get_user_permissions,
    require_permission,
)
from app.application.reporting.customer_report_service import (
    get_customer_report,
    get_customer_retention_report,
)
from app.application.reporting.authorization import ensure_report_type_access
from app.application.reporting.export_service import (
    SYNC_EXPORT_LIMIT,
    export_customers_csv,
    export_orders_csv,
    export_revenue_csv,
)
from app.application.reporting.export_job_service import (
    create_report_export_job,
    download_report_export,
    list_report_export_jobs,
)
from app.application.reporting.period import build_report_period
from app.application.reporting.order_report_service import get_order_report
from app.application.reporting.product_report_service import get_product_report
from app.application.reporting.revenue_service import get_revenue_report
from app.application.reporting.schemas import (
    AdminCustomerReportResponse,
    AdminCustomerRetentionResponse,
    AdminOrderReportResponse,
    AdminProductReportResponse,
    AdminRevenueReportResponse,
    ReportExportRequest,
)
from app.infrastructure.database.session import get_session


router = APIRouter()


def _default_report_dates(timezone_name: str) -> tuple[date, date]:
    try:
        report_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Múi giờ báo cáo không hợp lệ.",
        ) from exc
    today = datetime.now(report_timezone).date()
    return today - timedelta(days=29), today + timedelta(days=1)


@router.get(
    "/reports/revenue",
    response_model=AdminRevenueReportResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(require_permission("report:revenue_read"))],
)
async def get_admin_revenue_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    bucket: str = Query(default="day", pattern="^(day|week|month)$"),
    channel: str | None = Query(default=None, min_length=1, max_length=30),
    payment_method: str | None = Query(
        default=None,
        alias="paymentMethod",
        min_length=1,
        max_length=30,
    ),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> AdminRevenueReportResponse:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket=bucket,
    )
    return await get_revenue_report(
        session,
        period=period,
        channel=channel,
        payment_method=payment_method,
        include_profit="report:profit_read" in permissions,
    )


@router.get(
    "/reports/orders",
    response_model=AdminOrderReportResponse,
    dependencies=[Depends(require_permission("order:read"))],
)
async def get_admin_order_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    date_basis: str = Query(
        default="createdAt",
        alias="dateBasis",
        pattern="^(createdAt|completedAt)$",
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        min_length=1,
        max_length=40,
    ),
    channel: str | None = Query(default=None, min_length=1, max_length=30),
    payment_method: str | None = Query(
        default=None,
        alias="paymentMethod",
        min_length=1,
        max_length=30,
    ),
    payment_status: str | None = Query(
        default=None,
        alias="paymentStatus",
        min_length=1,
        max_length=30,
    ),
    fulfillment_method: str | None = Query(
        default=None,
        alias="fulfillmentMethod",
        min_length=1,
        max_length=30,
    ),
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AdminOrderReportResponse:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket="day",
    )
    return await get_order_report(
        session,
        period=period,
        date_basis=date_basis,
        status=status_filter,
        channel=channel,
        payment_method=payment_method,
        payment_status=payment_status,
        fulfillment_method=fulfillment_method,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/reports/products",
    response_model=AdminProductReportResponse,
    dependencies=[Depends(require_permission("product:read"))],
)
async def get_admin_product_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    category_id: UUID | None = Query(default=None, alias="categoryId"),
    brand_id: UUID | None = Query(default=None, alias="brandId"),
    search: str | None = Query(default=None, max_length=120),
    sort_by: str = Query(
        default="netRevenue",
        alias="sortBy",
        pattern="^(unitsSold|grossRevenue|refundAmount|netRevenue)$",
    ),
    sort_order: str = Query(
        default="desc",
        alias="sortOrder",
        pattern="^(asc|desc)$",
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AdminProductReportResponse:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket="day",
    )
    return await get_product_report(
        session,
        period=period,
        category_id=category_id,
        brand_id=brand_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
    )


@router.get(
    "/reports/customers",
    response_model=AdminCustomerReportResponse,
    dependencies=[Depends(require_permission("customer:read"))],
)
async def get_admin_customer_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    tier: str | None = Query(default=None, max_length=30),
    segment: str | None = Query(
        default=None,
        pattern="^(FIRST_TIME|RETURNING|NEW_NO_ORDER)$",
    ),
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> AdminCustomerReportResponse:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket="month",
    )
    return await get_customer_report(
        session,
        period=period,
        tier=tier,
        segment=segment,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/reports/customers/retention",
    response_model=AdminCustomerRetentionResponse,
    dependencies=[Depends(require_permission("customer:read"))],
)
async def get_admin_customer_retention_report(
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    cohort_limit: int = Query(default=12, alias="cohortLimit", ge=1, le=24),
    session: AsyncSession = Depends(get_session),
) -> AdminCustomerRetentionResponse:
    _default_report_dates(timezone_name)
    return await get_customer_retention_report(
        session,
        cohort_limit=cohort_limit,
        timezone_name=timezone_name,
    )


@router.get(
    "/reports/revenue/export",
    response_class=Response,
    dependencies=[Depends(require_permission("report:revenue_read"))],
)
async def export_admin_revenue_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    bucket: str = Query(default="day", pattern="^(day|week|month)$"),
    channel: str | None = Query(default=None, min_length=1, max_length=30),
    payment_method: str | None = Query(
        default=None,
        alias="paymentMethod",
        min_length=1,
        max_length=30,
    ),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> Response:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket=bucket,
    )
    report = await get_revenue_report(
        session,
        period=period,
        channel=channel,
        payment_method=payment_method,
        include_profit="report:profit_read" in permissions,
    )
    return export_revenue_csv(report)


@router.get(
    "/reports/orders/export",
    response_class=Response,
    dependencies=[Depends(require_permission("order:read"))],
)
async def export_admin_order_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    date_basis: str = Query(
        default="createdAt",
        alias="dateBasis",
        pattern="^(createdAt|completedAt)$",
    ),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    channel: str | None = Query(default=None, max_length=30),
    payment_method: str | None = Query(default=None, alias="paymentMethod", max_length=30),
    payment_status: str | None = Query(
        default=None,
        alias="paymentStatus",
        max_length=30,
    ),
    fulfillment_method: str | None = Query(
        default=None,
        alias="fulfillmentMethod",
        max_length=30,
    ),
    search: str | None = Query(default=None, max_length=120),
    session: AsyncSession = Depends(get_session),
) -> Response:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket="day",
    )
    report = await get_order_report(
        session,
        period=period,
        date_basis=date_basis,
        status=status_filter,
        channel=channel,
        payment_method=payment_method,
        payment_status=payment_status,
        fulfillment_method=fulfillment_method,
        search=search,
        page=1,
        limit=SYNC_EXPORT_LIMIT + 1,
    )
    if report.pagination.total > SYNC_EXPORT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Báo cáo vượt 5.000 dòng. "
                "Vui lòng sử dụng tác vụ xuất nền."
            ),
        )
    return export_orders_csv(report)


@router.get(
    "/reports/customers/export",
    response_class=Response,
    dependencies=[Depends(require_permission("customer:read"))],
)
async def export_admin_customer_report(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str = Query(default="Asia/Bangkok", alias="timezone", max_length=80),
    tier: str | None = Query(default=None, max_length=30),
    segment: str | None = Query(
        default=None,
        pattern="^(FIRST_TIME|RETURNING|NEW_NO_ORDER)$",
    ),
    search: str | None = Query(default=None, max_length=120),
    session: AsyncSession = Depends(get_session),
) -> Response:
    default_from, default_to = _default_report_dates(timezone_name)
    period = build_report_period(
        from_date=from_date or default_from,
        to_date=to_date or default_to,
        timezone_name=timezone_name,
        bucket="month",
    )
    report = await get_customer_report(
        session,
        period=period,
        tier=tier,
        segment=segment,
        search=search,
        page=1,
        limit=SYNC_EXPORT_LIMIT + 1,
    )
    if report.pagination.total > SYNC_EXPORT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Báo cáo vượt 5.000 dòng. "
                "Vui lòng sử dụng tác vụ xuất nền."
            ),
        )
    return export_customers_csv(report)


@router.post(
    "/reports/exports",
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_admin_report_export(
    payload: ReportExportRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    ensure_report_type_access(payload.reportType, permissions)
    build_report_period(
        from_date=payload.fromDate,
        to_date=payload.toDate,
        timezone_name=payload.timezone,
        bucket="day",
    )
    filters = payload.model_dump(
        by_alias=True,
        exclude={"reportType"},
        exclude_none=True,
        mode="json",
    )
    return await create_report_export_job(
        session,
        requested_by=current_user_id,
        report_type=payload.reportType,
        filters=filters,
    )


@router.get(
    "/reports/exports",
)
async def list_admin_report_exports(
    current_user_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_report_export_jobs(
        session,
        requested_by=current_user_id,
        permissions=permissions,
    )


@router.get(
    "/reports/exports/{job_id}/download",
    response_class=FileResponse,
)
async def download_admin_report_export(
    job_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    return await download_report_export(
        session,
        job_id=job_id,
        requested_by=current_user_id,
        permissions=permissions,
    )
