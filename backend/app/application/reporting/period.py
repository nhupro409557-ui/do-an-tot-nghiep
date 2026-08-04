from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status


ALLOWED_BUCKETS = {"day", "week", "month"}
MAX_REPORT_DAYS = 366


@dataclass(frozen=True)
class ReportPeriod:
    from_date: date
    to_date: date
    from_utc: datetime
    to_utc: datetime
    previous_from_utc: datetime
    previous_to_utc: datetime
    timezone_name: str
    bucket: str


def build_report_period(
    *,
    from_date: date,
    to_date: date,
    timezone_name: str = "Asia/Bangkok",
    bucket: str = "day",
) -> ReportPeriod:
    if from_date >= to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ngày bắt đầu phải trước ngày kết thúc.",
        )

    duration = to_date - from_date
    if duration.days > MAX_REPORT_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Khoảng thời gian báo cáo không được vượt quá {MAX_REPORT_DAYS} ngày.",
        )

    normalized_bucket = bucket.strip().lower()
    if normalized_bucket not in ALLOWED_BUCKETS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nhóm thời gian chỉ hỗ trợ ngày, tuần hoặc tháng.",
        )

    try:
        local_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Múi giờ báo cáo không hợp lệ.",
        ) from exc

    local_from = datetime.combine(from_date, datetime.min.time(), tzinfo=local_timezone)
    local_to = datetime.combine(to_date, datetime.min.time(), tzinfo=local_timezone)
    from_utc = local_from.astimezone(timezone.utc)
    to_utc = local_to.astimezone(timezone.utc)
    previous_local_from = datetime.combine(
        from_date - duration,
        datetime.min.time(),
        tzinfo=local_timezone,
    )

    return ReportPeriod(
        from_date=from_date,
        to_date=to_date,
        from_utc=from_utc,
        to_utc=to_utc,
        previous_from_utc=previous_local_from.astimezone(timezone.utc),
        previous_to_utc=from_utc,
        timezone_name=timezone_name,
        bucket=normalized_bucket,
    )


def calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return Decimal("0") if current == 0 else None
    return (((current - previous) / abs(previous)) * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
