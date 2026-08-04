import csv
import io
from collections.abc import Iterable, Sequence
from typing import Any

from fastapi import Response

from app.application.reporting.schemas import (
    AdminCustomerReportResponse,
    AdminOrderReportResponse,
    AdminRevenueReportResponse,
)


SYNC_EXPORT_LIMIT = 5_000

REPORT_CSV_HEADERS = {
    "revenue": (
        "Kỳ",
        "Doanh thu gộp",
        "Tiền hoàn",
        "Doanh thu ròng",
    ),
    "orders": (
        "Mã đơn",
        "Khách hàng",
        "Email",
        "Trạng thái",
        "Kênh bán",
        "Phương thức thanh toán",
        "Trạng thái thanh toán",
        "Hình thức nhận hàng",
        "Tổng giá trị",
        "Ngày tạo",
        "Ngày hoàn tất",
    ),
    "customers": (
        "Khách hàng",
        "Email",
        "Hạng thành viên",
        "Ngày đăng ký",
        "Số đơn trong kỳ",
        "Chi tiêu ròng",
        "Phân nhóm",
    ),
}


def _safe_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _csv_response(
    *,
    filename: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
) -> Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_cell(value) for value in row])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def report_csv_rows(report_type: str, report) -> Iterable[Sequence[Any]]:
    if report_type == "revenue":
        return (
            (
                item.periodStart.isoformat(),
                item.grossRevenue,
                item.refundAmount,
                item.netRevenue,
            )
            for item in report.series
        )
    if report_type == "orders":
        return (
            (
                item.orderCode,
                item.customerName or "",
                item.email or "",
                item.status,
                item.channel,
                item.paymentMethod,
                item.paymentStatus,
                item.fulfillmentMethod,
                item.totalAmount,
                item.createdAt,
                item.completedAt or "",
            )
            for item in report.items
        )
    return (
        (
            item.fullName,
            item.email,
            item.tier,
            item.registeredAt,
            item.orderCount,
            item.netSpent,
            item.segment,
        )
        for item in report.items
    )


def export_revenue_csv(report: AdminRevenueReportResponse) -> Response:
    return _csv_response(
        filename=(
            f"bao-cao-doanh-thu-{report.period.fromDate}-"
            f"{report.period.toDate}.csv"
        ),
        headers=REPORT_CSV_HEADERS["revenue"],
        rows=report_csv_rows("revenue", report),
    )


def export_orders_csv(report: AdminOrderReportResponse) -> Response:
    return _csv_response(
        filename=(
            f"bao-cao-don-hang-{report.period.fromDate}-"
            f"{report.period.toDate}.csv"
        ),
        headers=REPORT_CSV_HEADERS["orders"],
        rows=report_csv_rows("orders", report),
    )


def export_customers_csv(report: AdminCustomerReportResponse) -> Response:
    return _csv_response(
        filename=(
            f"bao-cao-khach-hang-{report.period.fromDate}-"
            f"{report.period.toDate}.csv"
        ),
        headers=REPORT_CSV_HEADERS["customers"],
        rows=report_csv_rows("customers", report),
    )
