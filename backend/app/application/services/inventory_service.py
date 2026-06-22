import csv
import io
import re
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import document_export_service
from app.application.services.product_helper_service import persisted_sales_config, sync_parent_price_from_variants
from app.api.schemas.admin import InventoryAdjustmentPayload, InventoryAdjustmentRequestPayload, InventoryAdjustmentRequestStatusPayload, InventoryIdentifierEditDecisionPayload, InventoryIdentifierEditRequestPayload, InventoryLocationPayload, InventoryLocationStatusPayload, InventoryReceiptImeiPayload, InventoryReceiptPayload, InventoryReceiptQualityPayload, InventoryReceiptReversePayload, InventorySettingsPayload, InventoryStockCountPayload, InventoryStockCountStatusPayload, VariantInventoryPayload
from app.infrastructure.database.repositories import inventory_repo

IMEI_PATTERN = re.compile(r"^[0-9]{15}$")
SERIAL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{2,119}$")
RECEIPT_STATUSES = {"DRAFT", "PROCESSING_IMEI", "PENDING_APPROVAL", "PENDING_SHORTAGE_APPROVAL", "APPROVED", "COMPLETED", "CANCELLED", "REVERSED"}
RECEIPT_TRANSITIONS = {
    "DRAFT": {"PROCESSING_IMEI", "APPROVED", "CANCELLED"},
    "PROCESSING_IMEI": {"PENDING_APPROVAL", "PENDING_SHORTAGE_APPROVAL", "CANCELLED"},
    "PENDING_APPROVAL": {"APPROVED", "CANCELLED"},
    "PENDING_SHORTAGE_APPROVAL": {"APPROVED", "CANCELLED"},
    "APPROVED": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "REVERSED": set(),
}
RECEIPT_EDITABLE_STATUSES = {"DRAFT", "PROCESSING_IMEI", "PENDING_APPROVAL", "PENDING_SHORTAGE_APPROVAL", "APPROVED"}

INVENTORY_RECEIPT_REASONS = {
    "NK_MUA": "Nhập mua từ nhà cung cấp",
    "NK_TRA_NCC": "Nhà cung cấp trả lại hàng",
    "NK_KH_TRA": "Khách hàng trả hàng",
    "NK_BH": "Nhập bảo hành",
    "NK_DIEUCHINH": "Điều chỉnh tăng tồn kho",
    "NK_CHUYEN": "Nhập từ kho khác",
    "NK_SANXUAT": "Nhập thành phẩm",
    "NK_KHOI_TAO": "Nhập kho khởi tạo",
    "NK_KHAC": "Nhập khác",
}

STOCK_COUNT_STATUSES = {"DRAFT", "APPROVED", "CANCELLED"}
QUALITY_STATUS_LABELS = {
    "PENDING": "Chờ kiểm tra",
    "PASSED": "Đạt",
    "FAILED": "Không đạt",
}


def _receipt_metadata_from_payload(payload: InventoryReceiptPayload) -> dict:
    quality_status = str(payload.qualityStatus or "PENDING").strip().upper()
    if quality_status not in QUALITY_STATUS_LABELS:
        raise HTTPException(status_code=400, detail="Trạng thái kiểm tra chất lượng không hợp lệ.")
    attachments = []
    for item in payload.attachments:
        name = item.name.strip()
        url = item.url.strip()
        if not name or not url:
            raise HTTPException(status_code=400, detail="Chứng từ đính kèm phải có tên và đường dẫn.")
        attachments.append(
            {
                "type": item.type,
                "name": name,
                "url": url,
                "note": (item.note or "").strip() or None,
            }
        )
    discrepancies = []
    for item in payload.discrepancies:
        description = item.description.strip()
        if not description:
            raise HTTPException(status_code=400, detail="Biên bản sai lệch phải có mô tả.")
        discrepancies.append(
            {
                "type": item.type,
                "description": description,
                "quantity": item.quantity,
                "action": (item.action or "").strip() or None,
            }
        )
    return {
        "qualityStatus": quality_status,
        "qualityLabel": QUALITY_STATUS_LABELS[quality_status],
        "qualityNote": (payload.qualityNote or "").strip() or None,
        "quarantine": bool(payload.quarantine),
        "quarantineLocation": (payload.quarantineLocation or "").strip() or None,
        "attachments": attachments,
        "discrepancies": discrepancies,
    }


def _normalize_location_code(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip().upper())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def _location_sort_order_from_code(code: str, fallback: int = 99999) -> int:
    match = re.match(r"^([A-Z])-([0-9]{2})-([0-9]{2})$", code)
    if match:
        aisle = ord(match.group(1)) - ord("A") + 1
        return aisle * 10000 + int(match.group(2)) * 100 + int(match.group(3))
    if code.startswith("QC-"):
        return 90000
    if code.startswith("BH-"):
        return 91000
    if code.startswith("ERR-"):
        return 92000
    if code.startswith("RT-"):
        return 93000
    return fallback


async def _get_active_inventory_location(session: AsyncSession, location_id: UUID, line_label: str = "Kệ hàng") -> dict:
    location = await inventory_repo.get_inventory_location_by_id(session, location_id)
    if not location:
        raise HTTPException(status_code=404, detail=f"{line_label} không tồn tại.")
    if str(location.get("status") or "").upper() != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"{line_label} đã bị khóa, không thể nhập thêm hàng.")
    return location


async def _resolve_receipt_line_location(session: AsyncSession, line, fallback_location_id: UUID, index: int) -> dict:
    selected_location_id = getattr(line, "warehouseLocationId", None)
    if selected_location_id:
        return await _get_active_inventory_location(session, selected_location_id, f"Dòng {index}: kệ hàng")

    storage_location_code = (line.storageLocationCode or "").strip()
    storage_location_name = (line.storageLocationName or "").strip()
    if storage_location_code:
        location = await inventory_repo.get_inventory_location_by_code(session, storage_location_code)
        if not location:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: mã kệ {storage_location_code} không tồn tại trong danh mục kệ hàng.")
        if str(location.get("status") or "").upper() != "ACTIVE":
            raise HTTPException(status_code=400, detail=f"Dòng {index}: kệ {storage_location_code} đã bị khóa, không thể nhập thêm hàng.")
        return location

    fallback = await _get_active_inventory_location(session, fallback_location_id, f"Dòng {index}: kệ mặc định")
    if storage_location_name and storage_location_name != fallback.get("name"):
        return {**fallback, "name": storage_location_name}
    return fallback


def _same_actor(left: UUID | str | None, right: UUID | str | None) -> bool:
    return bool(left and right and str(left) == str(right))


def _ensure_receipt_approval_allowed(receipt: dict, current_user_id: UUID | None) -> None:
    if _same_actor(receipt.get("created_by"), current_user_id):
        raise HTTPException(status_code=403, detail="Người lập phiếu không được tự duyệt phiếu nhập kho.")


def _ensure_super_admin_inventory_action(role_code: str | None, action_label: str) -> None:
    if role_code != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail=f"Chỉ Super Admin được {action_label}.")


def _policy_tracks_imei(policy_row: dict | None) -> bool:
    if not policy_row:
        return False
    sales_config = policy_row.get("sales_config") if isinstance(policy_row.get("sales_config"), dict) else {}
    imei_policy = sales_config.get("imeiPolicy") if isinstance(sales_config.get("imeiPolicy"), dict) else {}
    if str(imei_policy.get("mode") or "CATEGORY").upper() == "MANUAL":
        return bool(imei_policy.get("trackImei"))
    child_policy = policy_row.get("child_policy") if isinstance(policy_row.get("child_policy"), dict) else {}
    parent_policy = policy_row.get("parent_policy") if isinstance(policy_row.get("parent_policy"), dict) else {}
    if child_policy and not child_policy.get("inheritImeiPolicy", True):
        return bool(child_policy.get("trackImei"))
    return bool(parent_policy.get("trackImei"))


def _policy_tracks_serial_number(policy_row: dict | None) -> bool:
    if not policy_row:
        return False
    sales_config = policy_row.get("sales_config") if isinstance(policy_row.get("sales_config"), dict) else {}
    serial_policy = sales_config.get("serialPolicy") if isinstance(sales_config.get("serialPolicy"), dict) else {}
    if str(serial_policy.get("mode") or "CATEGORY").upper() == "MANUAL":
        return bool(serial_policy.get("trackSerialNumber"))
    child_policy = policy_row.get("child_policy") if isinstance(policy_row.get("child_policy"), dict) else {}
    parent_policy = policy_row.get("parent_policy") if isinstance(policy_row.get("parent_policy"), dict) else {}
    if child_policy and not child_policy.get("inheritSerialPolicy", True):
        return bool(child_policy.get("trackSerialNumber"))
    return bool(parent_policy.get("trackSerialNumber"))


def _effective_package_volume_cm3(policy_row: dict | None) -> float:
    if not policy_row:
        return 16 * 9 * 6 / 0.70
    child_policy = policy_row.get("child_policy") if isinstance(policy_row.get("child_policy"), dict) else {}
    parent_policy = policy_row.get("parent_policy") if isinstance(policy_row.get("parent_policy"), dict) else {}
    policy = parent_policy
    if child_policy and not child_policy.get("inheritStorageDimensions", True):
        policy = child_policy

    def positive_number(key: str, fallback: float) -> float:
        try:
            value = float(policy.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        return value if value > 0 else fallback

    length_cm = positive_number("packageLengthCm", 16)
    width_cm = positive_number("packageWidthCm", 9)
    height_cm = positive_number("packageHeightCm", 6)
    packing_ratio = min(1, max(0.01, positive_number("packingRatio", 0.70)))
    return (length_cm * width_cm * height_cm) / packing_ratio


async def _ensure_location_has_receipt_capacity(
    session: AsyncSession,
    *,
    location_id: UUID,
    line_index: int,
    quantity: int,
    policy_row: dict | None,
    requested_volume_by_location: dict[str, float],
) -> None:
    if quantity <= 0:
        return

    usage = await inventory_repo.get_inventory_location_capacity_usage(session, location_id)
    if not usage or usage.get("usableVolumeCm3") is None or usage.get("availableVolumeCm3") is None:
        return

    location_key = str(location_id)
    required_volume = quantity * _effective_package_volume_cm3(policy_row)
    previous_requested = requested_volume_by_location.get(location_key, 0)
    available_volume = float(usage.get("availableVolumeCm3") or 0) - previous_requested
    if required_volume > available_volume + 0.0001:
        location_code = usage.get("code") or "kệ đã chọn"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Dòng {line_index}: kệ {location_code} không đủ dung lượng. "
                f"Cần thêm {required_volume:,.0f} cm³, còn {max(available_volume, 0):,.0f} cm³."
            ),
        )
    requested_volume_by_location[location_key] = previous_requested + required_volume


def _clean_imeis(raw_imeis: list[str]) -> list[str]:
    return [str(item).strip() for item in raw_imeis if str(item).strip()]


def _clean_serial_numbers(raw_serial_numbers: list[str]) -> list[str]:
    return [str(item).strip().upper() for item in raw_serial_numbers if str(item).strip()]


def _validate_imei_format(imeis: list[str]) -> None:
    invalid = [imei for imei in imeis if not IMEI_PATTERN.match(imei)]
    if invalid:
        raise HTTPException(status_code=400, detail=f"IMEI không hợp lệ, cần đúng 15 chữ số: {', '.join(invalid[:5])}")


def _validate_serial_number_format(serial_numbers: list[str]) -> None:
    invalid = [serial_number for serial_number in serial_numbers if not SERIAL_PATTERN.match(serial_number)]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Serial number không hợp lệ: {', '.join(invalid[:5])}")


def _inventory_row_tracks_imei(row: dict) -> bool:
    sales_config = row.get("salesConfig") if isinstance(row.get("salesConfig"), dict) else {}
    imei_policy = sales_config.get("imeiPolicy") if isinstance(sales_config.get("imeiPolicy"), dict) else {}
    if str(imei_policy.get("mode") or "CATEGORY").upper() == "MANUAL":
        return bool(imei_policy.get("trackImei"))
    child_policy = row.get("childInventoryPolicy") if isinstance(row.get("childInventoryPolicy"), dict) else {}
    parent_policy = row.get("parentInventoryPolicy") if isinstance(row.get("parentInventoryPolicy"), dict) else {}
    if child_policy and not child_policy.get("inheritImeiPolicy", True):
        return bool(child_policy.get("trackImei"))
    return bool(parent_policy.get("trackImei"))


def _inventory_row_tracks_serial_number(row: dict) -> bool:
    sales_config = row.get("salesConfig") if isinstance(row.get("salesConfig"), dict) else {}
    serial_policy = sales_config.get("serialPolicy") if isinstance(sales_config.get("serialPolicy"), dict) else {}
    if str(serial_policy.get("mode") or "CATEGORY").upper() == "MANUAL":
        return bool(serial_policy.get("trackSerialNumber"))
    child_policy = row.get("childInventoryPolicy") if isinstance(row.get("childInventoryPolicy"), dict) else {}
    parent_policy = row.get("parentInventoryPolicy") if isinstance(row.get("parentInventoryPolicy"), dict) else {}
    if child_policy and not child_policy.get("inheritSerialPolicy", True):
        return bool(child_policy.get("trackSerialNumber"))
    return bool(parent_policy.get("trackSerialNumber"))


def _shape_inventory_level_row(row: dict) -> dict:
    stock_quantity = int(row.get("variantStock") if row.get("variantId") else row.get("productStock") or 0)
    reservation_reserved = int(row.get("reservationReservedQuantity") or 0)
    imei_reserved = int(row.get("imeiReservedQuantity") or 0)
    serial_reserved = int(row.get("serialReservedQuantity") or 0)
    reserved_quantity = max(reservation_reserved, imei_reserved, serial_reserved)
    available_quantity = max(stock_quantity - reserved_quantity, 0)
    sales_config = row.get("salesConfig") if isinstance(row.get("salesConfig"), dict) else {}
    minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
    tracks_imei = _inventory_row_tracks_imei(row)
    tracks_serial_number = _inventory_row_tracks_serial_number(row)
    stock_state = "OUT_OF_STOCK"
    if available_quantity > 0:
        stock_state = "AVAILABLE"
    elif reserved_quantity > 0:
        stock_state = "RESERVED"
    elif stock_quantity > 0:
        stock_state = "UNAVAILABLE"
    return {
        "productId": row.get("productId"),
        "productName": row.get("productName"),
        "productSku": row.get("productSku"),
        "productStatus": row.get("productStatus"),
        "variantId": row.get("variantId"),
        "variantSku": row.get("variantSku"),
        "variantConfiguration": row.get("configuration"),
        "variantColor": row.get("colorName"),
        "physicalStock": stock_quantity,
        "reservedStock": reserved_quantity,
        "availableStock": available_quantity,
        "averageUnitCost": float(row.get("averageUnitCost") or 0),
        "locations": row.get("locations") if isinstance(row.get("locations"), list) else [],
        "minimumStock": minimum_stock,
        "stockAlert": "LOW" if available_quantity <= minimum_stock else "OK",
        "stockState": stock_state,
        "tracksImei": tracks_imei,
        "tracksSerialNumber": tracks_serial_number,
        "primaryImei": row.get("primaryImei"),
        "supplementalImei": int(row.get("supplementalImeiQuantity") or 0),
        "imeiSummary": {
            "inStock": int(row.get("inStockImeiQuantity") or 0),
            "reserved": int(row.get("reservedImeiQuantity") or 0),
            "sold": int(row.get("soldImeiQuantity") or 0),
            "warranty": int(row.get("warrantyImeiQuantity") or 0),
            "scrap": int(row.get("scrapImeiQuantity") or 0),
        },
        "serialNumberSummary": {
            "inStock": int(row.get("inStockSerialQuantity") or 0),
            "reserved": int(row.get("reservedSerialQuantity") or 0),
            "sold": int(row.get("soldSerialQuantity") or 0),
            "warranty": int(row.get("warrantySerialQuantity") or 0),
            "scrap": int(row.get("scrapSerialQuantity") or 0),
        },
        "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
    }


async def get_product_inventory(session: AsyncSession, product_id: UUID) -> dict:
    product_data = await inventory_repo.get_product_inventory_summary(session, product_id)
    if not product_data:
        raise HTTPException(status_code=404, detail="Product not found.")
    variants = await inventory_repo.list_product_inventory_variants(session, product_id)
    logs = await inventory_repo.list_inventory_adjustment_logs(session, product_id)
    sales_config = product_data.get("salesConfig") if isinstance(product_data.get("salesConfig"), dict) else {}
    minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
    product_data.update(
        {
            "minimumStock": minimum_stock,
            "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
            "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
            "stockAlert": "LOW" if int(product_data.get("stockQuantity") or 0) <= minimum_stock else "OK",
        }
    )
    return {**product_data, "variants": variants, "logs": logs}

async def update_product_inventory_settings(
    session: AsyncSession,
    product_id: UUID,
    payload: InventorySettingsPayload,
) -> dict:
    row = await inventory_repo.get_product_sales_config_for_update(session, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found.")
    sales_config = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
    merged = persisted_sales_config(
        {
            **sales_config,
            "minimumStock": payload.minimumStock,
            "blockSaleWhenOutOfStock": payload.blockSaleWhenOutOfStock,
            "cycleCountDays": payload.cycleCountDays or sales_config.get("cycleCountDays") or 30,
        }
    )
    await inventory_repo.update_product_sales_config(session, product_id=product_id, sales_config=merged)
    await session.commit()
    return {"ok": True, **merged}

async def export_inventory_snapshot(session: AsyncSession, search: str = "") -> Response:
    rows = await inventory_repo.list_inventory_snapshot_rows(session, search)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "productId",
            "productName",
            "productSku",
            "variantId",
            "variantSku",
            "variantConfiguration",
            "variantColor",
            "physicalStock",
            "reservedStock",
            "availableStock",
            "averageUnitCost",
            "minimumStock",
            "stockAlert",
            "stockState",
            "tracksImei",
            "tracksSerialNumber",
            "primaryImei",
            "supplementalImei",
            "inStockImei",
            "reservedImei",
            "soldImei",
            "warrantyImei",
            "scrapImei",
            "inStockSerialNumber",
            "reservedSerialNumber",
            "soldSerialNumber",
            "warrantySerialNumber",
            "scrapSerialNumber",
            "productStatus",
            "blockSaleWhenOutOfStock",
        ],
    )
    writer.writeheader()
    for row in rows:
        shaped = _shape_inventory_level_row(row)
        writer.writerow(
            {
                "productId": shaped["productId"],
                "productName": shaped["productName"],
                "productSku": shaped["productSku"],
                "variantId": shaped["variantId"] or "",
                "variantSku": shaped["variantSku"] or "",
                "variantConfiguration": shaped["variantConfiguration"] or "",
                "variantColor": shaped["variantColor"] or "",
                "physicalStock": shaped["physicalStock"],
                "reservedStock": shaped["reservedStock"],
                "availableStock": shaped["availableStock"],
                "averageUnitCost": shaped["averageUnitCost"],
                "minimumStock": shaped["minimumStock"],
                "stockAlert": "Cần nhập thêm" if shaped["stockAlert"] == "LOW" else "Ổn định",
                "stockState": shaped["stockState"],
                "tracksImei": "Có" if shaped["tracksImei"] else "Không",
                "tracksSerialNumber": "Có" if shaped["tracksSerialNumber"] else "Không",
                "primaryImei": shaped["primaryImei"] or "",
                "supplementalImei": shaped["supplementalImei"],
                "inStockImei": shaped["imeiSummary"]["inStock"],
                "reservedImei": shaped["imeiSummary"]["reserved"],
                "soldImei": shaped["imeiSummary"]["sold"],
                "warrantyImei": shaped["imeiSummary"]["warranty"],
                "scrapImei": shaped["imeiSummary"]["scrap"],
                "inStockSerialNumber": shaped["serialNumberSummary"]["inStock"],
                "reservedSerialNumber": shaped["serialNumberSummary"]["reserved"],
                "soldSerialNumber": shaped["serialNumberSummary"]["sold"],
                "warrantySerialNumber": shaped["serialNumberSummary"]["warranty"],
                "scrapSerialNumber": shaped["serialNumberSummary"]["scrap"],
                "productStatus": shaped["productStatus"],
                "blockSaleWhenOutOfStock": "Có" if shaped["blockSaleWhenOutOfStock"] else "Không",
            }
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inventory-export.csv"'},
    )


async def list_inventory_levels(
    session: AsyncSession,
    search: str = "",
    stock_filter: str = "",
    location: str = "",
    category_id: str = "",
    brand_id: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    rows = await inventory_repo.list_inventory_level_rows(session, search.strip())
    category_id = category_id.strip()
    brand_id = brand_id.strip()
    if category_id:
        rows = [
            row for row in rows
            if str(row.get("categoryId") or "") == category_id
            or str(row.get("subcategoryId") or "") == category_id
        ]
    if brand_id:
        rows = [row for row in rows if str(row.get("brandId") or "") == brand_id]
    shaped_rows = [_shape_inventory_level_row(row) for row in rows]
    stock_filter = stock_filter.strip().upper()
    location = location.strip().lower()
    if stock_filter == "LOW":
        shaped_rows = [row for row in shaped_rows if row["stockAlert"] == "LOW"]
    elif stock_filter == "IN_STOCK":
        shaped_rows = [row for row in shaped_rows if row["physicalStock"] > 0]
    elif stock_filter == "RESERVED":
        shaped_rows = [row for row in shaped_rows if row["reservedStock"] > 0]
    if location:
        shaped_rows = [
            row for row in shaped_rows
            if any(
                location in str(item.get("code") or "").lower()
                or location in str(item.get("name") or "").lower()
                for item in row.get("locations") or []
            )
        ]
    total = len(shaped_rows)
    start = (page - 1) * page_size
    return {
        "items": shaped_rows[start:start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


async def list_inventory_locations(
    session: AsyncSession,
    search: str = "",
    include_inactive: bool = True,
    zone: str = "",
    purpose: str = "",
    status: str = "",
    aisle: str = "",
    shelf: str = "",
    bin: str = "",
) -> list[dict]:
    normalized_purpose = str(purpose or "").strip().upper()
    normalized_status = str(status or "").strip().upper()
    normalized_aisle = str(aisle or "").strip().upper()
    normalized_shelf = str(shelf or "").strip()
    normalized_bin = str(bin or "").strip()
    if normalized_purpose and normalized_purpose not in {"STORAGE", "WARRANTY", "QC", "DAMAGED", "RETURN", "VIRTUAL"}:
        raise HTTPException(status_code=400, detail="Loại kệ hàng không hợp lệ.")
    if normalized_status and normalized_status not in {"ACTIVE", "INACTIVE"}:
        raise HTTPException(status_code=400, detail="Trạng thái kệ hàng không hợp lệ.")
    if normalized_aisle and not re.fullmatch(r"[A-Z]", normalized_aisle):
        raise HTTPException(status_code=400, detail="Dãy kệ không hợp lệ.")
    if normalized_shelf and not re.fullmatch(r"\d{1,2}", normalized_shelf):
        raise HTTPException(status_code=400, detail="Số kệ không hợp lệ.")
    if normalized_bin and not re.fullmatch(r"\d{1,2}", normalized_bin):
        raise HTTPException(status_code=400, detail="Số ô không hợp lệ.")
    return await inventory_repo.list_inventory_locations(
        session,
        search,
        include_inactive,
        zone.strip(),
        normalized_purpose,
        normalized_status,
        normalized_aisle,
        normalized_shelf.zfill(2) if normalized_shelf else "",
        normalized_bin.zfill(2) if normalized_bin else "",
    )


async def create_inventory_location(session: AsyncSession, payload: InventoryLocationPayload) -> dict:
    code = _normalize_location_code(payload.code)
    name = payload.name.strip()
    purpose = str(payload.purpose or "STORAGE").strip().upper()
    sort_order = int(payload.sortOrder or 0) or _location_sort_order_from_code(code)
    if not code:
        raise HTTPException(status_code=400, detail="Mã kệ hàng không hợp lệ.")
    existing = await inventory_repo.get_inventory_location_by_code(session, code)
    if existing:
        raise HTTPException(status_code=409, detail="Mã kệ hàng đã tồn tại.")
    location = await inventory_repo.create_inventory_location(
        session,
        location_id=uuid4(),
        code=code,
        name=name,
        zone=(payload.zone or "").strip() or None,
        purpose=purpose,
        sort_order=sort_order,
        allow_mixed_sku=bool(payload.allowMixedSku),
        length_cm=payload.lengthCm,
        width_cm=payload.widthCm,
        height_cm=payload.heightCm,
        usable_ratio=payload.usableRatio,
        description=(payload.description or "").strip() or None,
    )
    await session.commit()
    return location


async def update_inventory_location(session: AsyncSession, location_id: UUID, payload: InventoryLocationPayload) -> dict:
    current = await inventory_repo.get_inventory_location_by_id(session, location_id)
    if not current:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    code = _normalize_location_code(payload.code)
    purpose = str(payload.purpose or "STORAGE").strip().upper()
    sort_order = int(payload.sortOrder or 0) or _location_sort_order_from_code(code)
    if not code:
        raise HTTPException(status_code=400, detail="Mã kệ hàng không hợp lệ.")
    existing = await inventory_repo.get_inventory_location_by_code(session, code)
    if existing and str(existing["id"]) != str(location_id):
        raise HTTPException(status_code=409, detail="Mã kệ hàng đã tồn tại.")
    location = await inventory_repo.update_inventory_location(
        session,
        location_id=location_id,
        code=code,
        name=payload.name.strip(),
        zone=(payload.zone or "").strip() or None,
        purpose=purpose,
        sort_order=sort_order,
        allow_mixed_sku=bool(payload.allowMixedSku),
        length_cm=payload.lengthCm,
        width_cm=payload.widthCm,
        height_cm=payload.heightCm,
        usable_ratio=payload.usableRatio,
        description=(payload.description or "").strip() or None,
    )
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    await session.commit()
    return location


async def update_inventory_location_status(session: AsyncSession, location_id: UUID, payload: InventoryLocationStatusPayload) -> dict:
    current = await inventory_repo.get_inventory_location_by_id(session, location_id)
    if not current:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    if current.get("isDefault") and not payload.isActive:
        raise HTTPException(status_code=400, detail="Không thể khóa kệ mặc định của kho chính.")
    if not payload.isActive and await inventory_repo.inventory_location_has_stock(session, location_id):
        raise HTTPException(status_code=400, detail="Kệ còn tồn kho, cần xử lý hết tồn trước khi khóa.")
    location = await inventory_repo.set_inventory_location_status(
        session,
        location_id=location_id,
        status="ACTIVE" if payload.isActive else "INACTIVE",
    )
    if not location:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ hàng.")
    await session.commit()
    return location


async def get_inventory_dashboard(session: AsyncSession, search: str = "") -> dict:
    raw_rows = await inventory_repo.list_inventory_level_rows(session, search.strip())
    rows = [_shape_inventory_level_row(row) for row in raw_rows]
    total_sku = len(rows)
    low_stock_rows = [row for row in rows if row["stockAlert"] == "LOW"]
    inventory_value = sum(float(row["physicalStock"] or 0) * float(row["averageUnitCost"] or 0) for row in rows)
    top_stock = sorted(rows, key=lambda row: int(row["physicalStock"] or 0), reverse=True)[:8]
    top_need_restock = sorted(
        low_stock_rows,
        key=lambda row: int(row["minimumStock"] or 0) - int(row["availableStock"] or 0),
        reverse=True,
    )[:8]
    return {
        "totalSku": total_sku,
        "lowStockCount": len(low_stock_rows),
        "inventoryValue": inventory_value,
        "reservedSkuCount": len([row for row in rows if row["reservedStock"] > 0]),
        "topStock": top_stock,
        "topNeedRestock": top_need_restock,
    }


async def list_inventory_ledger(
    session: AsyncSession,
    search: str = "",
    product_id: str = "",
    date_from: str = "",
    date_to: str = "",
    transaction_type: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    for label, value in {"Từ ngày": date_from, "Đến ngày": date_to}.items():
        if value:
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"{label} không hợp lệ.") from exc
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="Từ ngày không được lớn hơn đến ngày.")
    transaction_type = transaction_type.strip().upper()
    if transaction_type and transaction_type not in {"RECEIPT", "ADJUSTMENT", "SALE", "RETURN", "REVERSAL"}:
        raise HTTPException(status_code=400, detail="Loại giao dịch sổ kho không hợp lệ.")
    rows = await inventory_repo.list_inventory_ledger_rows(
        session,
        search=search.strip(),
        product_id=product_id.strip(),
        date_from=date_from.strip(),
        date_to=date_to.strip(),
        transaction_type=transaction_type,
    )
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "page": page, "pageSize": page_size, "total": total, "totalPages": max(1, (total + page_size - 1) // page_size)}


async def list_inventory_identifiers(session: AsyncSession, product_id: UUID, variant_id: UUID | None = None) -> dict:
    imeis = await inventory_repo.list_product_imeis_for_inventory(session, product_id, variant_id)
    serial_numbers = await inventory_repo.list_product_serial_numbers_for_inventory(session, product_id, variant_id)
    edit_requests = await inventory_repo.list_identifier_edit_requests(
        session,
        product_id=product_id,
        variant_id=variant_id,
        limit=100,
    )
    return {
        "productId": str(product_id),
        "variantId": str(variant_id) if variant_id else None,
        "imeis": imeis,
        "serialNumbers": serial_numbers,
        "editRequests": edit_requests,
    }


async def list_inventory_issue_suggestions(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
    quantity: int = 1,
) -> list[dict]:
    requested_quantity = max(1, min(int(quantity or 1), 500))
    identifier_rows = await inventory_repo.list_identifier_issue_candidates(
        session,
        product_id=product_id,
        variant_id=variant_id,
        limit=requested_quantity,
    )
    if identifier_rows:
        grouped: dict[str, dict] = {}
        for item in identifier_rows:
            location_id = str(item.get("locationId") or "")
            if not location_id:
                continue
            group = grouped.setdefault(
                location_id,
                {
                    "warehouseLocationId": location_id,
                    "locationCode": item.get("locationCode"),
                    "locationName": item.get("locationName"),
                    "availableQuantity": 0,
                    "suggestedQuantity": 0,
                    "oldestReceivedAt": item.get("receivedAt"),
                    "identifiers": [],
                    "mode": "IDENTIFIER",
                },
            )
            group["availableQuantity"] += 1
            group["suggestedQuantity"] += 1
            if not group.get("oldestReceivedAt") or (item.get("receivedAt") and item.get("receivedAt") < group["oldestReceivedAt"]):
                group["oldestReceivedAt"] = item.get("receivedAt")
            group["identifiers"].append(
                {
                    "type": item.get("identifierType"),
                    "value": item.get("value"),
                    "receivedAt": item.get("receivedAt"),
                }
            )
        return list(grouped.values())

    level_rows = await inventory_repo.list_level_issue_candidates(session, product_id=product_id, variant_id=variant_id)
    remaining = requested_quantity
    suggestions: list[dict] = []
    for row in level_rows:
        available = int(row.get("availableQuantity") or 0)
        if available <= 0 or remaining <= 0:
            continue
        suggested = min(available, remaining)
        suggestions.append(
            {
                "warehouseLocationId": row.get("locationId"),
                "locationCode": row.get("locationCode"),
                "locationName": row.get("locationName"),
                "availableQuantity": available,
                "suggestedQuantity": suggested,
                "oldestReceivedAt": row.get("updatedAt"),
                "identifiers": [],
                "mode": "QUANTITY",
            }
        )
        remaining -= suggested
    return suggestions


async def list_inventory_identifier_edit_requests(session: AsyncSession, status_filter: str = "PENDING") -> list[dict]:
    status_filter = status_filter.strip().upper()
    status = status_filter if status_filter in {"PENDING", "APPROVED", "CANCELLED"} else None
    return await inventory_repo.list_identifier_edit_requests(session, status=status, limit=200)


async def create_inventory_identifier_edit_request(
    session: AsyncSession,
    payload: InventoryIdentifierEditRequestPayload,
    current_user_id: UUID | None = None,
) -> dict:
    identifier_type = payload.identifierType.upper()
    new_value = payload.newValue.strip()
    reason = payload.reason.strip()
    if len(reason) < 5:
        raise HTTPException(status_code=400, detail="Lý do chỉnh sửa mã định danh phải có ít nhất 5 ký tự.")
    if identifier_type == "IMEI":
        _validate_imei_format([new_value])
    else:
        cleaned_serial_numbers = _clean_serial_numbers([new_value])
        if not cleaned_serial_numbers:
            raise HTTPException(status_code=400, detail="Serial number mới không được để trống.")
        new_value = cleaned_serial_numbers[0]
        _validate_serial_number_format([new_value])

    identifier = await inventory_repo.get_identifier_for_edit(session, identifier_type, payload.identifierId)
    if not identifier:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã định danh cần chỉnh sửa.")
    current_value = str(identifier["current_value"])
    if current_value == new_value:
        raise HTTPException(status_code=400, detail="Mã mới phải khác mã hiện tại.")
    if await inventory_repo.has_pending_identifier_edit_request(session, identifier_type, payload.identifierId):
        raise HTTPException(status_code=409, detail="Mã này đang có yêu cầu chỉnh sửa chờ duyệt.")

    if identifier_type == "IMEI":
        existing = await inventory_repo.list_existing_imeis(session, [new_value])
        if existing:
            raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {new_value}")
    else:
        existing = await inventory_repo.list_existing_serial_numbers(session, [new_value], product_id=identifier["product_id"])
        if existing:
            raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {new_value}")

    request_id = uuid4()
    await inventory_repo.insert_identifier_edit_request(
        session,
        request_id=request_id,
        identifier_type=identifier_type,
        identifier_id=payload.identifierId,
        product_id=identifier["product_id"],
        variant_id=identifier.get("variant_id"),
        current_value=current_value,
        new_value=new_value,
        reason=reason,
        requested_by=current_user_id,
    )
    await session.commit()
    return {
        "ok": True,
        "requestId": str(request_id),
        "status": "PENDING",
        "identifierType": identifier_type,
        "currentValue": current_value,
        "newValue": new_value,
    }


async def decide_inventory_identifier_edit_request(
    session: AsyncSession,
    request_id: UUID,
    payload: InventoryIdentifierEditDecisionPayload,
    current_user_id: UUID | None = None,
) -> dict:
    request = await inventory_repo.get_identifier_edit_request_for_update(session, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu chỉnh sửa mã định danh.")
    if request["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Yêu cầu chỉnh sửa này đã được xử lý.")

    decision = payload.decision.upper()
    if decision == "APPROVED":
        identifier_type = str(request["identifier_type"])
        new_value = str(request["new_value"])
        identifier = await inventory_repo.get_identifier_for_edit(session, identifier_type, request["identifier_id"])
        if not identifier:
            raise HTTPException(status_code=404, detail="Mã định danh gốc không còn tồn tại.")
        if str(identifier["current_value"]) != str(request["current_value"]):
            raise HTTPException(status_code=409, detail="Mã định danh đã thay đổi sau khi tạo yêu cầu, không thể duyệt tự động.")
        if identifier_type == "IMEI":
            existing = await inventory_repo.list_existing_imeis(session, [new_value])
            if existing:
                raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {new_value}")
        else:
            existing = await inventory_repo.list_existing_serial_numbers(session, [new_value], product_id=identifier["product_id"])
            if existing:
                raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {new_value}")
        await inventory_repo.update_identifier_value(session, identifier_type, request["identifier_id"], new_value)

    await inventory_repo.update_identifier_edit_request_status(
        session,
        request_id=request_id,
        status=decision,
        decided_by=current_user_id,
        decision_note=payload.note,
    )
    await session.commit()
    return {"ok": True, "requestId": str(request_id), "status": decision}


async def list_inventory_receipts(
    session: AsyncSession,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    if date_from:
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Từ ngày không hợp lệ.") from exc
    if date_to:
        try:
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Đến ngày không hợp lệ.") from exc
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="Từ ngày không được lớn hơn đến ngày.")
    rows = await inventory_repo.list_inventory_receipts(
        session,
        search.strip(),
        date_from.strip(),
        date_to.strip(),
    )
    normalized_status = status.strip().upper()
    if normalized_status:
        rows = [row for row in rows if str(row.get("status") or "COMPLETED").upper() == normalized_status]
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": rows[start:start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


async def get_inventory_receipt_report(session: AsyncSession) -> dict:
    return await inventory_repo.get_inventory_receipt_report(session)


async def export_inventory_receipt_document(session: AsyncSession, reference_code: str, export_format: str) -> Response:
    reference_code = reference_code.strip()
    export_format = export_format.strip().lower()
    if export_format not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Định dạng xuất phiếu không hợp lệ.")
    receipts = await inventory_repo.list_inventory_receipts(session, reference_code)
    receipt = next((item for item in receipts if str(item.get("referenceCode") or "") == reference_code), None)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if export_format == "pdf":
        content, filename = document_export_service.render_inventory_receipt_pdf(receipt)
        media_type = "application/pdf"
    else:
        content, filename = document_export_service.render_inventory_receipt_docx(receipt)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def list_inventory_stock_counts(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_stock_counts(session, search.strip())


async def list_inventory_adjustments(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_adjustments(session, search.strip())


async def create_inventory_stock_count(
    session: AsyncSession,
    payload: InventoryStockCountPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    if existing_receipt or existing_count:
        raise HTTPException(status_code=409, detail="Mã phiếu kiểm kê đã tồn tại.")
    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or "MAIN").strip() or "MAIN",
        name=(payload.locationName or "Kho chính").strip() or "Kho chính",
    )
    document_id = uuid4()
    await inventory_repo.insert_inventory_stock_count_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        reason=(payload.reason or "KIEM_KE_DINH_KY").strip() or "KIEM_KE_DINH_KY",
        note=payload.note,
        location_id=location["id"],
        created_by=current_user_id,
    )
    seen_keys: set[tuple[str, str]] = set()
    total_abs_variance = 0
    for index, line in enumerate(payload.lines, start=1):
        key = (str(line.productId), str(line.variantId or ""))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng trong phiếu kiểm kê.")
        seen_keys.add(key)
        product_id = line.productId
        variant_id = line.variantId
        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để kiểm kê.")
        expected_quantity = int(line.expectedQuantity)
        counted_quantity = int(line.countedQuantity)
        total_abs_variance += abs(counted_quantity - expected_quantity)
        await inventory_repo.insert_inventory_stock_count_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            expected_quantity=expected_quantity,
            counted_quantity=counted_quantity,
            note=line.note,
        )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(payload.lines),
        "absoluteVarianceQuantity": total_abs_variance,
    }


async def update_inventory_stock_count_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryStockCountStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu kiểm kê không hợp lệ.")
    document = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu kiểm kê.")
    if document["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ phiếu kiểm kê nháp mới được duyệt hoặc hủy.")

    lines = await inventory_repo.list_inventory_stock_count_lines(session, document["id"])
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    if target_status == "APPROVED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            counted_quantity = int(line["countedQuantity"] or 0)
            expected_quantity = int(line["expectedQuantity"] or 0)
            variance = counted_quantity - expected_quantity
            if variant_id:
                current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
            else:
                current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
            if not current_row:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: sản phẩm/biến thể không còn tồn tại.")
            old_quantity = int(current_row["stock_quantity"] or 0)
            if counted_quantity < 0:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số đếm không được âm.")
            if variant_id:
                await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=counted_quantity)
            else:
                await inventory_repo.update_product_stock(session, product_id=product_id, quantity=counted_quantity)
            await inventory_repo.set_inventory_level_counted_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                counted_quantity=counted_quantity,
            )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=old_quantity,
                new_quantity=counted_quantity,
                delta=counted_quantity - old_quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason=document.get("reason") or "KIEM_KE",
                note=line.get("note") or payload.note or f"Kiểm kê kho: lệch {variance}",
                supplier_name=None,
                unit_cost=None,
                location_code=document.get("locationCode") or "MAIN",
                location_name=document.get("locationName") or "Kho chính",
            )
            if variant_id:
                touched_products.add(product_id)
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "expectedQuantity": expected_quantity,
                    "countedQuantity": counted_quantity,
                    "oldQuantity": old_quantity,
                    "varianceQuantity": variance,
                }
            )
        for product_id in touched_products:
            await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=document["id"],
        status=target_status,
        note=payload.note,
        actor_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": target_status, "postedLineCount": len(posted_lines), "lines": posted_lines}


async def create_inventory_adjustment_request(
    session: AsyncSession,
    payload: InventoryAdjustmentRequestPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    existing_adjustment = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    if existing_receipt or existing_count or existing_adjustment:
        raise HTTPException(status_code=409, detail="Mã phiếu điều chỉnh tồn đã tồn tại.")
    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or "MAIN").strip() or "MAIN",
        name=(payload.locationName or "Kho chính").strip() or "Kho chính",
    )
    document_id = uuid4()
    await inventory_repo.insert_inventory_adjustment_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        reason=(payload.reason or "DIEU_CHINH_THU_CONG").strip() or "DIEU_CHINH_THU_CONG",
        note=payload.note,
        location_id=location["id"],
        created_by=current_user_id,
    )
    seen_keys: set[tuple[str, str]] = set()
    total_abs_variance = 0
    for index, line in enumerate(payload.lines, start=1):
        key = (str(line.productId), str(line.variantId or ""))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng trong phiếu điều chỉnh.")
        seen_keys.add(key)
        reason = line.reason.strip()
        if not reason:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: phải nhập lý do điều chỉnh.")
        product_id = line.productId
        variant_id = line.variantId
        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để điều chỉnh.")
        actual_current = int(current_row["stock_quantity"] or 0)
        current_quantity = int(line.currentQuantity)
        new_quantity = int(line.newQuantity)
        if current_quantity != actual_current:
            raise HTTPException(status_code=409, detail=f"Dòng {index}: tồn hệ thống đã thay đổi từ {current_quantity} sang {actual_current}, vui lòng tải lại trước khi tạo phiếu.")
        total_abs_variance += abs(new_quantity - current_quantity)
        await inventory_repo.insert_inventory_adjustment_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            current_quantity=current_quantity,
            new_quantity=new_quantity,
            reason=reason,
            note=line.note,
        )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(payload.lines),
        "absoluteVarianceQuantity": total_abs_variance,
    }


async def update_inventory_adjustment_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryAdjustmentRequestStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu điều chỉnh tồn không hợp lệ.")
    document = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu điều chỉnh tồn.")
    if document["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ phiếu điều chỉnh nháp mới được duyệt hoặc hủy.")

    lines = await inventory_repo.list_inventory_adjustment_lines(session, document["id"])
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    if target_status == "APPROVED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            requested_current = int(line["currentQuantity"] or 0)
            new_quantity = int(line["newQuantity"] or 0)
            if variant_id:
                current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
            else:
                current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
            if not current_row:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: sản phẩm/biến thể không còn tồn tại.")
            old_quantity = int(current_row["stock_quantity"] or 0)
            if old_quantity != requested_current:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: tồn hệ thống đã thay đổi từ {requested_current} sang {old_quantity}, không thể duyệt tự động.")
            if variant_id:
                await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_quantity)
            else:
                await inventory_repo.update_product_stock(session, product_id=product_id, quantity=new_quantity)
            await inventory_repo.set_inventory_level_counted_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                counted_quantity=new_quantity,
            )
            reason = str(line.get("reason") or document.get("reason") or "DIEU_CHINH_THU_CONG")
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                delta=new_quantity - old_quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason=reason,
                note=line.get("note") or payload.note,
                supplier_name=None,
                unit_cost=None,
                location_code=document.get("locationCode") or "MAIN",
                location_name=document.get("locationName") or "Kho chính",
            )
            if variant_id:
                touched_products.add(product_id)
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "oldQuantity": old_quantity,
                    "newQuantity": new_quantity,
                    "varianceQuantity": new_quantity - old_quantity,
                }
            )
        for product_id in touched_products:
            await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=document["id"],
        status=target_status,
        note=payload.note,
        actor_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": target_status, "postedLineCount": len(posted_lines), "lines": posted_lines}


async def adjust_product_inventory(
    session: AsyncSession,
    product_id: UUID,
    payload: InventoryAdjustmentPayload,
    idempotency_key: str | None = None,
) -> dict:
    idem_key = (idempotency_key or payload.referenceCode or "").strip()
    if idem_key:
        await inventory_repo.delete_old_inventory_idempotency(session)
        existing = await inventory_repo.get_inventory_idempotency_response(session, idem_key)
        if existing:
            return existing
    if payload.delta is None and payload.quantity is None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity.")
    if payload.delta is not None and payload.quantity is not None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity, not both.")
    
    actual_variant_id = payload.variantId
    if not actual_variant_id:
        active_variants = await inventory_repo.list_product_variant_ids(session, product_id)
        if len(active_variants) == 1:
            actual_variant_id = active_variants[0]["id"]
        elif len(active_variants) > 1:
            raise HTTPException(
                status_code=400,
                detail="Sản phẩm có nhiều biến thể. Vui lòng chọn biến thể cụ thể để điều chỉnh tồn kho."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Sản phẩm không có biến thể hoạt động nào."
            )

    row = await inventory_repo.get_variant_inventory_for_update(
        session,
        product_id=product_id,
        variant_id=actual_variant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Variant not found.")
    
    old_quantity = int(row["stock_quantity"] or 0)
    new_quantity = payload.quantity if payload.quantity is not None else old_quantity + int(payload.delta or 0)
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Inventory quantity cannot be negative.")
    await inventory_repo.update_variant_stock(session, variant_id=actual_variant_id, quantity=new_quantity)
    item_sku = row["sku"]

    delta = int(payload.delta or 0) if payload.delta is not None else (new_quantity - old_quantity)

    imeis = _clean_imeis(payload.imeis)
    serial_numbers = _clean_serial_numbers(payload.serialNumbers)
    if payload.transactionType == "RECEIPT" and delta > 0:
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        if _policy_tracks_imei(policy_row):
            if len(imeis) != delta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm cần quản lý IMEI. Vui lòng nhập đúng {delta} IMEI.",
                )
            if len(set(imeis)) != len(imeis):
                raise HTTPException(status_code=400, detail="Danh sách IMEI có mã bị trùng.")
            existing_imeis = await inventory_repo.list_existing_imeis(session, imeis)
            if existing_imeis:
                raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {', '.join(existing_imeis[:5])}")
            for imei in imeis:
                await inventory_repo.insert_product_imei(
                    session,
                    product_id=product_id,
                    variant_id=actual_variant_id,
                    imei=imei,
                    source_reference=payload.referenceCode,
                )
        elif imeis:
            raise HTTPException(status_code=400, detail="Sản phẩm không bật quản lý IMEI nên không được nhập IMEI.")
        if _policy_tracks_serial_number(policy_row):
            if len(serial_numbers) != delta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm cần quản lý serial number. Vui lòng nhập đúng {delta} serial number.",
                )
            _validate_serial_number_format(serial_numbers)
            if len(set(serial_numbers)) != len(serial_numbers):
                raise HTTPException(status_code=400, detail="Danh sách serial number có mã bị trùng.")
            existing_serial_numbers = await inventory_repo.list_existing_serial_numbers(session, serial_numbers, product_id=product_id)
            if existing_serial_numbers:
                raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {', '.join(existing_serial_numbers[:5])}")
            for serial_number in serial_numbers:
                await inventory_repo.insert_product_serial_number(
                    session,
                    product_id=product_id,
                    variant_id=actual_variant_id,
                    serial_number=serial_number,
                    source_reference=payload.referenceCode,
                )
        elif serial_numbers:
            raise HTTPException(status_code=400, detail="Sản phẩm không bật quản lý serial number nên không được nhập serial number.")
    await inventory_repo.insert_inventory_adjustment_log(
        session,
        log_id=uuid4(),
        product_id=product_id,
        variant_id=actual_variant_id,
        old_quantity=old_quantity,
        new_quantity=new_quantity,
        delta=delta,
        transaction_type=payload.transactionType,
        reference_code=payload.referenceCode,
        reason=payload.reason,
        note=payload.note,
        supplier_name=payload.supplierName,
        unit_cost=payload.unitCost,
        location_code=payload.locationCode,
        location_name=payload.locationName,
    )
    response_payload = {"ok": True, "oldQuantity": old_quantity, "newQuantity": new_quantity}
    if idem_key:
        await inventory_repo.insert_inventory_idempotency_response(
            session,
            key=idem_key,
            product_id=product_id,
            response_payload=response_payload,
        )
    await sync_parent_price_from_variants(session, product_id)
    await session.commit()
    return response_payload


async def create_inventory_receipt(
    session: AsyncSession,
    payload: InventoryReceiptPayload,
    idempotency_key: str | None = None,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    idem_key = (idempotency_key or reference_code).strip()
    if idem_key:
        await inventory_repo.delete_old_inventory_idempotency(session)
        existing = await inventory_repo.get_inventory_idempotency_response(session, idem_key)
        if existing:
            return existing

    requested_status = payload.status if payload.status in RECEIPT_STATUSES else "DRAFT"
    if requested_status != "DRAFT":
        raise HTTPException(status_code=400, detail="Phiếu nhập mới phải bắt đầu ở trạng thái Nháp.")
    receipt_reason_code = str(payload.receiptReasonCode or "NK_MUA").strip().upper()
    if receipt_reason_code not in INVENTORY_RECEIPT_REASONS:
        raise HTTPException(status_code=400, detail="Lý do nhập kho không hợp lệ.")
    if receipt_reason_code == "NK_KHAC" and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="Nhập khác phải ghi rõ lý do trong ghi chú chung.")
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if existing_receipt:
        raise HTTPException(status_code=409, detail="Mã phiếu nhập đã tồn tại.")

    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or "MAIN").strip() or "MAIN",
        name=(payload.locationName or "Kho chính").strip() or "Kho chính",
    )
    receipt_metadata = _receipt_metadata_from_payload(payload)
    document_id = uuid4()
    await inventory_repo.insert_inventory_receipt_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        status=requested_status,
        reason=receipt_reason_code,
        supplier_name=payload.supplierName,
        note=payload.note,
        location_id=location["id"],
        created_by=current_user_id,
        metadata=receipt_metadata,
    )

    prepared_lines: list[dict] = []
    await _validate_and_store_receipt_lines(session, document_id, location["id"], payload.lines, prepared_lines)

    response_payload = {
        "ok": True,
        "referenceCode": reference_code,
        "status": requested_status,
        "lineCount": len(prepared_lines),
        "postedLineCount": 0,
        "lines": prepared_lines,
    }
    if idem_key:
        await inventory_repo.insert_inventory_idempotency_response(
            session,
            key=idem_key,
            product_id=payload.lines[0].productId,
            response_payload=response_payload,
        )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="created",
        reference_code=reference_code,
        metadata={
            "status": requested_status,
            "reason": receipt_reason_code,
            "metadata": receipt_metadata,
            "lineCount": len(prepared_lines),
            "lines": prepared_lines,
        },
    )
    await session.commit()
    return response_payload


async def update_inventory_receipt(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptPayload,
    current_user_id: UUID | None = None,
    current_role_code: str | None = None,
) -> dict:
    reference_code = reference_code.strip()
    payload_reference_code = payload.referenceCode.strip()
    if payload_reference_code and payload_reference_code != reference_code:
        raise HTTPException(status_code=400, detail="Không được đổi mã phiếu nhập khi chỉnh sửa.")

    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt.get("posted_at") or receipt["status"] not in RECEIPT_EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Chỉ có thể chỉnh sửa phiếu nhập chưa hoàn tất quy trình.")
    if receipt["status"] in {"PENDING_APPROVAL", "PENDING_SHORTAGE_APPROVAL", "APPROVED"}:
        _ensure_super_admin_inventory_action(current_role_code, "trả phiếu nhập đã gửi duyệt về nháp để chỉnh sửa")
    previous_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    await inventory_repo.release_pending_inbound_identifiers(session, reference_code)

    receipt_reason_code = str(payload.receiptReasonCode or receipt.get("reason") or "NK_MUA").strip().upper()
    if receipt_reason_code not in INVENTORY_RECEIPT_REASONS:
        raise HTTPException(status_code=400, detail="Lý do nhập kho không hợp lệ.")
    if receipt_reason_code == "NK_KHAC" and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="Nhập khác phải ghi rõ lý do trong ghi chú chung.")

    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or receipt.get("locationCode") or "MAIN").strip() or "MAIN",
        name=(payload.locationName or receipt.get("locationName") or "Kho chính").strip() or "Kho chính",
    )
    receipt_metadata = _receipt_metadata_from_payload(payload)
    await inventory_repo.update_inventory_receipt_document(
        session,
        document_id=receipt["id"],
        reason=receipt_reason_code,
        supplier_name=payload.supplierName,
        note=payload.note,
        location_id=location["id"],
        metadata=receipt_metadata,
    )
    await inventory_repo.delete_inventory_receipt_lines(session, receipt["id"])

    prepared_lines: list[dict] = []
    await _validate_and_store_receipt_lines(session, receipt["id"], location["id"], payload.lines, prepared_lines)
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="updated",
        reference_code=reference_code,
        metadata={
            "fromStatus": receipt["status"],
            "toStatus": "DRAFT",
            "reason": receipt_reason_code,
            "metadata": receipt_metadata,
            "previousLines": [
                {
                    "lineId": str(line["id"]),
                    "productId": str(line["productId"]),
                    "variantId": str(line["variantId"]) if line.get("variantId") else None,
                    "quantity": int(line.get("quantity") or 0),
                    "receivedQuantity": int(line.get("receivedQuantity") or 0),
                    "tracksImei": bool(line.get("tracksImei")),
                    "tracksSerialNumber": bool(line.get("tracksSerialNumber")),
                }
                for line in previous_lines
            ],
            "newLines": prepared_lines,
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(prepared_lines),
        "postedLineCount": 0,
        "lines": prepared_lines,
    }


async def update_inventory_receipt_quality(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptQualityPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt.get("posted_at") or receipt["status"] in {"COMPLETED", "REVERSED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Không thể cập nhật QC cho phiếu nhập đã kết thúc.")
    quality_status = str(payload.qualityStatus or "PENDING").strip().upper()
    if quality_status not in QUALITY_STATUS_LABELS:
        raise HTTPException(status_code=400, detail="Trạng thái kiểm tra chất lượng không hợp lệ.")
    await inventory_repo.update_inventory_receipt_quality(
        session,
        document_id=receipt["id"],
        quality_status=quality_status,
        quality_note=(payload.qualityNote or "").strip() or None,
        quarantine=bool(payload.quarantine),
        quarantine_location=(payload.quarantineLocation or "").strip() or None,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="quality_updated",
        reference_code=reference_code,
        metadata={
            "fromQualityStatus": receipt.get("qualityStatus"),
            "toQualityStatus": quality_status,
            "qualityNote": (payload.qualityNote or "").strip() or None,
            "quarantine": bool(payload.quarantine),
            "quarantineLocation": (payload.quarantineLocation or "").strip() or None,
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "qualityStatus": quality_status,
        "quarantine": bool(payload.quarantine),
    }


async def delete_inventory_receipt(
    session: AsyncSession,
    reference_code: str,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt.get("posted_at") or receipt["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ có thể xóa phiếu nhập còn ở trạng thái nháp.")

    previous_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    await inventory_repo.delete_inventory_receipt_lines(session, receipt["id"])
    await inventory_repo.delete_inventory_receipt_document(session, receipt["id"])
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="deleted",
        reference_code=reference_code,
        metadata={
            "status": receipt["status"],
            "lineCount": len(previous_lines),
            "lines": [
                {
                    "lineId": str(line["id"]),
                    "productId": str(line["productId"]),
                    "variantId": str(line["variantId"]) if line.get("variantId") else None,
                    "quantity": int(line.get("quantity") or 0),
                }
                for line in previous_lines
            ],
        },
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "deleted": True}


async def _validate_and_store_receipt_lines(
    session: AsyncSession,
    document_id: UUID,
    location_id: UUID,
    lines: list,
    prepared_lines: list[dict],
) -> None:
    seen_keys: set[tuple[str, str]] = set()
    requested_volume_by_location: dict[str, float] = {}
    for index, line in enumerate(lines, start=1):
        product_id = line.productId
        actual_variant_id = line.variantId
        product_gate = await inventory_repo.get_product_receipt_eligibility_for_update(session, product_id)
        if not product_gate:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm để nhập kho.")
        product_label = f"{product_gate.get('name') or 'Sản phẩm'} ({product_gate.get('sku') or product_id})"
        product_status = str(product_gate.get("status") or "").upper()
        if product_gate.get("deleted_at") is not None:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: {product_label} đã bị xóa, không được nhập kho.")
        if product_status != "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: {product_label} đang ở trạng thái {product_status or 'không xác định'}, không được nhập kho.",
            )
        if product_gate.get("hidden_by_category") or product_gate.get("hidden_by_brand"):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: {product_label} đang bị ẩn theo danh mục hoặc thương hiệu, không được nhập kho.",
            )
        if product_gate.get("has_pending_revision"):
            raise HTTPException(
                status_code=409,
                detail=f"Dòng {index}: {product_label} đang có bản chỉnh sửa chờ duyệt. Vui lòng duyệt hoặc hủy bản chỉnh sửa trước khi nhập kho.",
            )
        if not actual_variant_id:
            active_variants = await inventory_repo.list_product_variant_ids(session, product_id)
            if len(active_variants) == 1:
                actual_variant_id = active_variants[0]["id"]
            elif len(active_variants) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {index}: sản phẩm có nhiều biến thể. Vui lòng chọn biến thể cần nhập kho.",
                )
            else:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không có biến thể hoạt động.")

        row = await inventory_repo.get_variant_inventory_for_update(
            session,
            product_id=product_id,
            variant_id=actual_variant_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy biến thể hợp lệ.")
        key = (str(product_id), str(actual_variant_id))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng trong phiếu nhập.")
        seen_keys.add(key)

        quantity = int(line.quantity)
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        tracks_imei = _policy_tracks_imei(policy_row)
        tracks_serial_number = _policy_tracks_serial_number(policy_row)
        line_location = await _resolve_receipt_line_location(session, line, location_id, index)
        line_location_id = line_location["id"]
        storage_location_code = str(line_location.get("code") or line.storageLocationCode or "").strip()
        storage_location_name = str(line_location.get("name") or line.storageLocationName or "").strip()
        await _ensure_location_has_receipt_capacity(
            session,
            location_id=line_location_id,
            line_index=index,
            quantity=quantity,
            policy_row=policy_row,
            requested_volume_by_location=requested_volume_by_location,
        )

        await inventory_repo.insert_inventory_receipt_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=actual_variant_id,
            location_id=line_location_id,
            quantity=quantity,
            unit_cost=line.unitCost,
            note=line.note,
            imeis=[],
            tracks_imei=tracks_imei,
            serial_numbers=[],
            tracks_serial_number=tracks_serial_number,
            storage_location_code=storage_location_code or None,
            storage_location_name=storage_location_name or None,
        )
        prepared_lines.append(
            {
                "productId": str(product_id),
                "variantId": str(actual_variant_id),
                "quantity": quantity,
                "imeiCount": 0,
                "tracksImei": tracks_imei,
                "serialNumberCount": 0,
                "tracksSerialNumber": tracks_serial_number,
                "warehouseLocationId": str(line_location_id),
                "storageLocationCode": storage_location_code or None,
                "storageLocationName": storage_location_name or None,
            }
        )


async def _post_inventory_receipt(
    session: AsyncSession,
    document_id: UUID,
    reference_code: str,
    receipt_reason_code: str | None,
    supplier_name: str | None,
    note: str | None,
    location_id: UUID | None,
    location_code: str | None,
    location_name: str | None,
) -> list[dict]:
    document_lines = await inventory_repo.list_inventory_receipt_lines(session, document_id)
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    requested_volume_by_location: dict[str, float] = {}

    for index, line in enumerate(document_lines, start=1):
        product_id = line["productId"]
        actual_variant_id = line["variantId"]
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line.get("receivedQuantity") or 0) if (tracks_imei or tracks_serial_number) else int(line["quantity"])
        if quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số lượng thực nhận phải lớn hơn 0 trước khi hoàn tất.")
        row = await inventory_repo.get_variant_inventory_for_update(
            session,
            product_id=product_id,
            variant_id=actual_variant_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy biến thể hợp lệ.")

        old_quantity = int(row["stock_quantity"] or 0)
        new_quantity = old_quantity + quantity
        imeis = [str(item).strip() for item in (line.get("imeis") or []) if str(item).strip()]
        serial_numbers = _clean_serial_numbers(line.get("serialNumbers") or [])
        if tracks_imei and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI phải khớp số lượng thực nhận trước khi hoàn tất.")
        if tracks_serial_number and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số serial number phải khớp số lượng thực nhận trước khi hoàn tất.")

        imei_statuses = await inventory_repo.list_imei_statuses(session, imeis)
        if tracks_imei and (
            len(imei_statuses) != len(imeis)
            or any(
                str(item.get("status")) != "PENDING_INBOUND"
                or str(item.get("source_reference")) != reference_code
                for item in imei_statuses
            )
        ):
            raise HTTPException(status_code=409, detail=f"Dòng {index}: IMEI chưa được giữ chỗ hợp lệ cho phiếu nhập này.")
        serial_statuses = await inventory_repo.list_product_serial_number_statuses(
            session,
            product_id=product_id,
            serial_numbers=serial_numbers,
        )
        if tracks_serial_number and (
            len(serial_statuses) != len(serial_numbers)
            or any(
                str(item.get("status")) != "PENDING_INBOUND"
                or str(item.get("source_reference")) != reference_code
                for item in serial_statuses
            )
        ):
            raise HTTPException(status_code=409, detail=f"Dòng {index}: serial number chưa được giữ chỗ hợp lệ cho phiếu nhập này.")

        await inventory_repo.update_variant_stock(session, variant_id=actual_variant_id, quantity=new_quantity)
        line_location_id = line.get("locationId") or location_id
        if line_location_id:
            await _get_active_inventory_location(session, line_location_id, f"Dòng {index}: kệ hàng")
            policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
            await _ensure_location_has_receipt_capacity(
                session,
                location_id=line_location_id,
                line_index=index,
                quantity=quantity,
                policy_row=policy_row,
                requested_volume_by_location=requested_volume_by_location,
            )
            await inventory_repo.post_inventory_level_receipt(
                session,
                product_id=product_id,
                variant_id=actual_variant_id,
                location_id=line_location_id,
                quantity=quantity,
                unit_cost=line.get("unitCost"),
            )
            await inventory_repo.create_inventory_lot_for_receipt(
                session,
                document_id=document_id,
                reference_code=reference_code,
                product_id=product_id,
                variant_id=actual_variant_id,
                location_id=line_location_id,
                quantity=quantity,
                unit_cost=line.get("unitCost"),
            )
            await inventory_repo.assign_identifier_locations_for_receipt_line(
                session,
                product_id=product_id,
                location_id=line_location_id,
                imeis=imeis,
                serial_numbers=serial_numbers,
            )
        await inventory_repo.insert_inventory_adjustment_log(
            session,
            log_id=uuid4(),
            product_id=product_id,
            variant_id=actual_variant_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            delta=quantity,
            transaction_type="RECEIPT",
            reference_code=reference_code,
            reason=receipt_reason_code or "NK_MUA",
            note=line.get("note") or note,
            supplier_name=supplier_name,
            unit_cost=line.get("unitCost"),
            location_code=line.get("storageLocationCode") or location_code or "MAIN",
            location_name=line.get("storageLocationName") or location_name or "Kho chính",
        )
        touched_products.add(product_id)
        posted_lines.append(
            {
                "productId": str(product_id),
                "variantId": str(actual_variant_id),
                "oldQuantity": old_quantity,
                "newQuantity": new_quantity,
                "quantity": quantity,
                "imeiCount": len(imeis),
                "tracksImei": tracks_imei,
                "serialNumberCount": len(serial_numbers),
                "tracksSerialNumber": tracks_serial_number,
            }
        )

    for product_id in touched_products:
        await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.activate_pending_inbound_identifiers(session, reference_code)
    return posted_lines


async def _receipt_imei_summary(session: AsyncSession, document_id: UUID) -> dict:
    lines = await inventory_repo.list_inventory_receipt_lines(session, document_id)
    tracked_lines = [line for line in lines if bool(line.get("tracksImei")) or bool(line.get("tracksSerialNumber"))]
    planned = sum(int(line.get("quantity") or 0) for line in tracked_lines)
    received = sum(int(line.get("receivedQuantity") or 0) for line in tracked_lines)
    has_shortage = any(int(line.get("receivedQuantity") or 0) < int(line.get("quantity") or 0) for line in tracked_lines)
    all_complete = all(int(line.get("receivedQuantity") or 0) == int(line.get("quantity") or 0) for line in tracked_lines)
    return {
        "lines": lines,
        "trackedLines": tracked_lines,
        "trackedLineCount": len(tracked_lines),
        "plannedIdentifierQuantity": planned,
        "receivedIdentifierQuantity": received,
        "hasShortage": has_shortage,
        "allImeiComplete": all_complete,
    }


async def submit_inventory_receipt_imeis(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptImeiPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt["status"] != "PROCESSING_IMEI":
        raise HTTPException(status_code=400, detail="Chỉ phiếu ở trạng thái xử lý IMEI mới được xác nhận danh sách IMEI.")

    lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    tracked_lines = [line for line in lines if bool(line.get("tracksImei")) or bool(line.get("tracksSerialNumber"))]
    if not tracked_lines:
        raise HTTPException(status_code=400, detail="Phiếu nhập này không có dòng cần quản lý IMEI hoặc serial number.")

    payload_by_line = {str(item.lineId): _clean_imeis(item.imeis) for item in payload.lines}
    payload_serials_by_line = {str(item.lineId): _clean_serial_numbers(item.serialNumbers) for item in payload.lines}
    accepted_shortages_by_line = {str(item.lineId): bool(item.acceptShortage) for item in payload.lines}
    shortage_reasons_by_line = {str(item.lineId): (item.shortageReason or "").strip() for item in payload.lines}
    seen_imeis: set[str] = set()
    seen_serial_numbers_by_product: dict[UUID, set[str]] = {}
    has_shortage = False
    shortage_reasons: list[str] = []
    total_planned = 0
    total_received = 0

    for index, line in enumerate(tracked_lines, start=1):
        line_id = str(line["id"])
        planned_quantity = int(line.get("quantity") or 0)
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        imeis = payload_by_line.get(line_id, [])
        serial_numbers = payload_serials_by_line.get(line_id, [])
        if tracks_imei:
            _validate_imei_format(imeis)
        elif imeis:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không bật quản lý IMEI.")
        if tracks_serial_number:
            _validate_serial_number_format(serial_numbers)
        elif serial_numbers:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không bật quản lý serial number.")
        if len(imeis) > planned_quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI vượt quá số lượng dự kiến.")
        if len(serial_numbers) > planned_quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số serial number vượt quá số lượng dự kiến.")
        if tracks_imei and tracks_serial_number and len(imeis) != len(serial_numbers):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI và serial number phải khớp nhau theo từng máy.")
        duplicate_in_line = len(set(imeis)) != len(imeis)
        duplicate_in_receipt = any(imei in seen_imeis for imei in imeis)
        if duplicate_in_line or duplicate_in_receipt:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách IMEI có mã bị trùng.")
        product_serials = seen_serial_numbers_by_product.setdefault(line["productId"], set())
        duplicate_serial_in_line = len(set(serial_numbers)) != len(serial_numbers)
        duplicate_serial_in_receipt = any(serial_number in product_serials for serial_number in serial_numbers)
        if duplicate_serial_in_line or duplicate_serial_in_receipt:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách serial number có mã bị trùng trong cùng sản phẩm.")
        seen_imeis.update(imeis)
        product_serials.update(serial_numbers)
        line_received_counts = []
        if tracks_imei:
            line_received_counts.append(len(imeis))
        if tracks_serial_number:
            line_received_counts.append(len(serial_numbers))
        received_quantity = min(line_received_counts) if line_received_counts else planned_quantity
        if received_quantity < planned_quantity:
            has_shortage = True
            if not accepted_shortages_by_line.get(line_id):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: phải xác nhận nhập thiếu trước khi gửi danh sách thiếu.")
            shortage_reason = shortage_reasons_by_line.get(line_id) or (payload.shortageReason or "").strip()
            if not shortage_reason:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: thiếu IMEI/serial number phải nhập lý do thiếu.")
            shortage_reasons.append(shortage_reason)
        total_planned += planned_quantity
        total_received += received_quantity

    await inventory_repo.release_pending_inbound_identifiers(session, reference_code)

    existing_imeis = await inventory_repo.list_existing_imeis(session, list(seen_imeis))
    if existing_imeis:
        raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {', '.join(existing_imeis[:5])}")
    for product_id, serial_numbers in seen_serial_numbers_by_product.items():
        existing_serial_numbers = await inventory_repo.list_existing_serial_numbers(session, list(serial_numbers), product_id=product_id)
        if existing_serial_numbers:
            raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {', '.join(existing_serial_numbers[:5])}")

    for line in tracked_lines:
        imeis = payload_by_line.get(str(line["id"]), [])
        serial_numbers = payload_serials_by_line.get(str(line["id"]), [])
        line_received_counts = []
        if bool(line.get("tracksImei")):
            line_received_counts.append(len(imeis))
        if bool(line.get("tracksSerialNumber")):
            line_received_counts.append(len(serial_numbers))
        received_quantity = min(line_received_counts) if line_received_counts else int(line.get("quantity") or 0)
        line_shortage_reason = shortage_reasons_by_line.get(str(line["id"])) or (payload.shortageReason or "").strip()
        await inventory_repo.update_inventory_receipt_line_imeis(
            session,
            line_id=line["id"],
            imeis=imeis,
            serial_numbers=serial_numbers,
            received_quantity=received_quantity,
            shortage_reason=line_shortage_reason if received_quantity < int(line.get("quantity") or 0) else None,
        )
        for imei in imeis:
            await inventory_repo.insert_pending_product_imei(
                session,
                product_id=line["productId"],
                variant_id=line["variantId"],
                imei=imei,
                source_reference=reference_code,
            )
        for serial_number in serial_numbers:
            await inventory_repo.insert_pending_product_serial_number(
                session,
                product_id=line["productId"],
                variant_id=line["variantId"],
                serial_number=serial_number,
                source_reference=reference_code,
            )

    pending_imei_statuses = await inventory_repo.list_imei_statuses(session, list(seen_imeis))
    if len(pending_imei_statuses) != len(seen_imeis) or any(
        str(item.get("status")) != "PENDING_INBOUND" or str(item.get("source_reference")) != reference_code
        for item in pending_imei_statuses
    ):
        raise HTTPException(status_code=409, detail="Không thể giữ chỗ một số IMEI cho phiếu nhập này. Vui lòng kiểm tra mã trùng.")
    for product_id, serial_numbers in seen_serial_numbers_by_product.items():
        pending_serial_statuses = await inventory_repo.list_product_serial_number_statuses(
            session,
            product_id=product_id,
            serial_numbers=list(serial_numbers),
        )
        if len(pending_serial_statuses) != len(serial_numbers) or any(
            str(item.get("status")) != "PENDING_INBOUND" or str(item.get("source_reference")) != reference_code
            for item in pending_serial_statuses
        ):
            raise HTTPException(status_code=409, detail="Không thể giữ chỗ một số serial number cho phiếu nhập này. Vui lòng kiểm tra mã trùng.")

    next_status = "PENDING_SHORTAGE_APPROVAL" if has_shortage else "PENDING_APPROVAL"
    document_shortage_note = "; ".join(dict.fromkeys(shortage_reasons)) if has_shortage else None
    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=receipt["id"],
        status=next_status,
        note=document_shortage_note,
        actor_id=current_user_id,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="identifiers_submitted",
        reference_code=reference_code,
        metadata={
            "fromStatus": receipt["status"],
            "toStatus": next_status,
            "plannedIdentifierQuantity": total_planned,
            "receivedIdentifierQuantity": total_received,
            "hasShortage": has_shortage,
            "shortageReasons": list(dict.fromkeys(shortage_reasons)),
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": next_status,
        "plannedIdentifierQuantity": total_planned,
        "receivedIdentifierQuantity": total_received,
        "hasShortage": has_shortage,
    }


async def update_inventory_receipt_status(
    session: AsyncSession,
    reference_code: str,
    status_payload,
    current_user_id: UUID | None = None,
    current_role_code: str | None = None,
) -> dict:
    target_status = status_payload.status
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    current_status = receipt["status"]
    allowed = RECEIPT_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Không thể chuyển phiếu nhập từ {current_status} sang {target_status}.")
    note = status_payload.cancelReason if target_status == "CANCELLED" else None
    summary = await _receipt_imei_summary(session, receipt["id"])

    if target_status in {"APPROVED", "COMPLETED", "CANCELLED"}:
        _ensure_super_admin_inventory_action(
            current_role_code,
            {
                "APPROVED": "duyệt phiếu nhập kho",
                "COMPLETED": "hoàn tất nhập kho và cập nhật tồn",
                "CANCELLED": "hủy phiếu nhập kho",
            }[target_status],
        )
    if target_status == "CANCELLED":
        await inventory_repo.release_pending_inbound_identifiers(session, reference_code)
    if target_status == "PROCESSING_IMEI" and summary["trackedLineCount"] == 0:
        raise HTTPException(status_code=400, detail="Phiếu nhập này không có dòng cần quản lý IMEI hoặc serial number.")
    if target_status == "APPROVED":
        _ensure_receipt_approval_allowed(receipt, current_user_id)
        if summary["trackedLineCount"] > 0 and current_status == "DRAFT":
            raise HTTPException(status_code=400, detail="Phiếu có sản phẩm cần IMEI/serial number phải qua bước xử lý mã định danh trước khi duyệt.")
        if current_status == "PROCESSING_IMEI" and not summary["allImeiComplete"]:
            raise HTTPException(status_code=400, detail="Phiếu chưa đủ IMEI/serial number. Vui lòng bổ sung hoặc chốt thiếu để chờ duyệt.")
        if current_status == "PENDING_APPROVAL" and not summary["allImeiComplete"]:
            raise HTTPException(status_code=400, detail="Phiếu chưa đủ IMEI/serial number, không thể duyệt.")

    posted_lines: list[dict] = []
    if target_status == "COMPLETED":
        if receipt.get("posted_at"):
            raise HTTPException(status_code=409, detail="Phiếu nhập kho này đã được hoàn tất trước đó.")
        if str(receipt.get("qualityStatus") or "PENDING").upper() != "PASSED":
            raise HTTPException(status_code=400, detail="Phiếu nhập phải có kết quả kiểm tra chất lượng Đạt trước khi hoàn tất.")
        if bool(receipt.get("quarantine")):
            raise HTTPException(status_code=400, detail="Phiếu nhập đang ở khu cách ly, chưa thể cập nhật vào tồn khả dụng.")
        posted_lines = await _post_inventory_receipt(
            session,
            receipt["id"],
            receipt["document_no"],
            receipt.get("reason"),
            receipt.get("supplier_name"),
            receipt.get("note"),
            receipt.get("target_location_id"),
            receipt.get("locationCode"),
            receipt.get("locationName"),
        )
    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=receipt["id"],
        status=target_status,
        note=note,
        actor_id=current_user_id,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="status_changed",
        reference_code=reference_code,
        metadata={
            "fromStatus": current_status,
            "toStatus": target_status,
            "postedLineCount": len(posted_lines),
            "cancelReason": note,
        },
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": target_status, "postedLineCount": len(posted_lines)}


async def reverse_inventory_receipt(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptReversePayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt["status"] != "COMPLETED" or not receipt.get("posted_at"):
        raise HTTPException(status_code=400, detail="Chỉ có thể đảo phiếu nhập đã hoàn tất.")
    if await inventory_repo.inventory_receipt_has_reversal(session, receipt["id"]):
        raise HTTPException(status_code=409, detail="Phiếu nhập này đã có chứng từ đảo.")

    document_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    reversal_code = f"REV-{reference_code[:48]}-{datetime.utcnow().strftime('%H%M%S')}"
    touched_products: set[UUID] = set()
    reversed_lines: list[dict] = []

    for index, line in enumerate(document_lines, start=1):
        product_id = line["productId"]
        variant_id = line["variantId"]
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line.get("receivedQuantity") or 0) if (tracks_imei or tracks_serial_number) else int(line.get("quantity") or 0)
        if quantity <= 0:
            continue

        row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy biến thể hợp lệ để đảo phiếu.")
        old_quantity = int(row["stock_quantity"] or 0)
        if old_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: tồn kho hiện tại không đủ để đảo phiếu nhập.")

        imeis = _clean_imeis(line.get("imeis") or [])
        serial_numbers = _clean_serial_numbers(line.get("serialNumbers") or [])
        if tracks_imei and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: dữ liệu IMEI của phiếu không khớp số lượng thực nhận, không thể đảo tự động.")
        if tracks_serial_number and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: dữ liệu serial number của phiếu không khớp số lượng thực nhận, không thể đảo tự động.")

        imei_statuses = await inventory_repo.list_imei_statuses(session, imeis)
        if len(imei_statuses) != len(imeis) or any(str(item["status"]) != "IN_STOCK" for item in imei_statuses):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: chỉ có thể đảo IMEI còn ở trạng thái trong kho.")
        serial_statuses = await inventory_repo.list_product_serial_number_statuses(
            session,
            product_id=product_id,
            serial_numbers=serial_numbers,
        )
        if len(serial_statuses) != len(serial_numbers) or any(str(item["status"]) != "IN_STOCK" for item in serial_statuses):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: chỉ có thể đảo serial number còn ở trạng thái trong kho.")

        new_quantity = old_quantity - quantity
        await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_quantity)
        line_location_id = line.get("locationId") or receipt.get("target_location_id")
        if line_location_id:
            await inventory_repo.post_inventory_level_reversal(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=line_location_id,
                quantity=quantity,
            )
            try:
                await inventory_repo.reverse_inventory_lots_for_receipt(
                    session,
                    document_id=receipt["id"],
                    location_id=line_location_id,
                    product_id=product_id,
                    variant_id=variant_id,
                    quantity=quantity,
                    reversal_reference=reversal_code,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: {exc}") from exc
        await inventory_repo.mark_imeis_reversed(session, imeis)
        await inventory_repo.mark_serial_numbers_reversed(session, serial_numbers, product_id=product_id)
        await inventory_repo.insert_inventory_adjustment_log(
            session,
            log_id=uuid4(),
            product_id=product_id,
            variant_id=variant_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            delta=-quantity,
            transaction_type="REVERSAL",
            reference_code=reversal_code,
            reason=payload.reason,
            note=payload.note or f"Đảo phiếu nhập {reference_code}",
            supplier_name=receipt.get("supplier_name"),
            unit_cost=line.get("unitCost"),
            location_code=line.get("storageLocationCode") or receipt.get("locationCode") or "MAIN",
            location_name=line.get("storageLocationName") or receipt.get("locationName") or "Kho chính",
        )
        touched_products.add(product_id)
        reversed_lines.append(
            {
                "productId": str(product_id),
                "variantId": str(variant_id),
                "oldQuantity": old_quantity,
                "newQuantity": new_quantity,
                "quantity": quantity,
                "imeiCount": len(imeis),
                "serialNumberCount": len(serial_numbers),
            }
        )

    if not reversed_lines:
        raise HTTPException(status_code=400, detail="Phiếu nhập không có dòng thực nhận để đảo.")

    reversal_document_id = uuid4()
    await inventory_repo.insert_inventory_reversal_document(
        session,
        document_id=reversal_document_id,
        reference_code=reversal_code,
        original_document_id=receipt["id"],
        reason=payload.reason,
        note=payload.note,
        location_id=receipt.get("target_location_id"),
        created_by=current_user_id,
    )
    for line in document_lines:
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line.get("receivedQuantity") or 0) if (tracks_imei or tracks_serial_number) else int(line.get("quantity") or 0)
        if quantity <= 0:
            continue
        await inventory_repo.insert_inventory_receipt_line(
            session,
            line_id=uuid4(),
            document_id=reversal_document_id,
            product_id=line["productId"],
            variant_id=line["variantId"],
            location_id=line.get("locationId") or receipt.get("target_location_id"),
            quantity=quantity,
            unit_cost=line.get("unitCost"),
            note=payload.note or f"Đảo dòng phiếu nhập {reference_code}",
            imeis=_clean_imeis(line.get("imeis") or []),
            tracks_imei=tracks_imei,
            serial_numbers=_clean_serial_numbers(line.get("serialNumbers") or []),
            tracks_serial_number=tracks_serial_number,
            storage_location_code=line.get("storageLocationCode"),
            storage_location_name=line.get("storageLocationName"),
        )

    await inventory_repo.mark_inventory_receipt_reversed(
        session,
        document_id=receipt["id"],
        actor_id=current_user_id,
        note=payload.note or f"Đã đảo bằng chứng từ {reversal_code}",
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="reversed",
        reference_code=reference_code,
        metadata={
            "fromStatus": receipt["status"],
            "toStatus": "REVERSED",
            "reversalReferenceCode": reversal_code,
            "reason": payload.reason,
            "reversedLineCount": len(reversed_lines),
            "lines": reversed_lines,
        },
    )
    for product_id in touched_products:
        await sync_parent_price_from_variants(session, product_id)
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "reversalReferenceCode": reversal_code,
        "status": "REVERSED",
        "reversedLineCount": len(reversed_lines),
        "lines": reversed_lines,
    }


async def set_variant_inventory(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID,
    payload: VariantInventoryPayload,
) -> dict:
    return await adjust_product_inventory(
        session,
        product_id,
        InventoryAdjustmentPayload(
            variantId=variant_id,
            quantity=payload.quantity,
            transactionType=payload.transactionType,
            referenceCode=payload.referenceCode,
            reason=payload.reason,
            note=payload.note,
        ),
        idempotency_key=payload.referenceCode,
    )
