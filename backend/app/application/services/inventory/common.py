import csv
import io
import re
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status, Response
from sqlalchemy import text
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
        return bool(serial_policy.get("trackSerialNumber")) or _policy_tracks_imei(policy_row)
    child_policy = policy_row.get("child_policy") if isinstance(policy_row.get("child_policy"), dict) else {}
    parent_policy = policy_row.get("parent_policy") if isinstance(policy_row.get("parent_policy"), dict) else {}
    if child_policy and not child_policy.get("inheritSerialPolicy", True):
        return bool(child_policy.get("trackSerialNumber")) or _policy_tracks_imei(policy_row)
    return bool(parent_policy.get("trackSerialNumber")) or _policy_tracks_imei(policy_row)


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
        return bool(child_policy.get("trackSerialNumber")) or _inventory_row_tracks_imei(row)
    return bool(parent_policy.get("trackSerialNumber")) or _inventory_row_tracks_imei(row)


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
        "displayPrice": float(row.get("displayPrice") or 0),
        "productPrice": float(row.get("productPrice") or 0),
        "productSalePrice": float(row.get("productSalePrice") or 0),
        "variantPrice": float(row.get("variantPrice") or 0),
        "variantSalePrice": float(row.get("variantSalePrice") or 0),
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

__all__ = [name for name in globals() if not name.startswith("__")]
