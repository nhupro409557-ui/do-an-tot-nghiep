from fastapi import HTTPException, status


REPORT_TYPE_PERMISSIONS = {
    "revenue": "report:revenue_read",
    "orders": "order:read",
    "products": "product:read",
    "customers": "customer:read",
    "inventory": "inventory:read",
}


def ensure_report_type_access(
    report_type: str,
    permissions: set[str],
) -> None:
    required_permission = REPORT_TYPE_PERMISSIONS.get(report_type)
    if required_permission is None or required_permission not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập loại báo cáo này.",
        )


def accessible_export_report_types(permissions: set[str]) -> list[str]:
    return [
        report_type
        for report_type in ("revenue", "orders", "customers")
        if REPORT_TYPE_PERMISSIONS[report_type] in permissions
    ]
