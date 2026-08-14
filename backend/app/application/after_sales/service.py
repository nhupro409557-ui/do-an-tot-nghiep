import json
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.attachments import add_attachments, schedule_attachment_cleanup
from app.application.after_sales.common import build_request_code, money
from app.application.after_sales.inspection import inspect_request
from app.application.after_sales.maintenance import run_maintenance
from app.application.after_sales.refunds import create_refunds
from app.application.after_sales.schemas import AfterSalesTimelineNoteRequest, CreateAfterSalesRequest, UpdateAfterSalesStatusRequest
from app.application.after_sales.transitions import label_for, transitions_for
from app.infrastructure.database.repositories import after_sales_repo, inventory_repo, used_product_repo


DAY_SECONDS = 24 * 60 * 60
DEFAULT_EXCHANGE_FEE_RATE = Decimal("0.05")
EXCHANGE_PAYMENT_DUE_HOURS = 24


async def list_warranty_replacement_candidates(
    session: AsyncSession,
    *,
    request_id: UUID,
) -> dict:
    exists = await session.scalar(
        text("SELECT 1 FROM warranty_requests WHERE id = :id"),
        {"id": request_id},
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu bảo hành.")

    items = await after_sales_repo.get_request_items(
        session,
        kind="WARRANTY",
        request_id=request_id,
    )
    result_items: list[dict] = []
    for item in items:
        product_id = item["product_id"]
        variant_id = item.get("product_variant_id")
        pairs = await inventory_repo.list_product_identifier_pairs_for_inventory(
            session,
            product_id,
            variant_id,
        )
        imeis = await inventory_repo.list_product_imeis_for_inventory(
            session,
            product_id,
            variant_id,
        )
        serials = await inventory_repo.list_product_serial_numbers_for_inventory(
            session,
            product_id,
            variant_id,
        )

        candidates: list[dict] = []
        paired_imeis: set[str] = set()
        paired_serials: set[str] = set()
        for pair in pairs:
            pair_imeis = [value for value in [pair.get("imei1"), pair.get("imei2")] if value]
            pair_serials = [pair["serialNumber"]] if pair.get("serialNumber") else []
            paired_imeis.update(pair_imeis)
            paired_serials.update(pair_serials)
            candidates.append({
                "key": f"PAIR:{pair['id']}",
                "imeis": [pair["imei1"]],
                "secondaryImei": pair.get("imei2"),
                "serialNumbers": pair_serials,
                "locationId": str(pair["locationId"]),
                "locationCode": pair.get("locationCode"),
                "locationName": pair.get("locationName"),
            })

        for imei in imeis:
            value = str(imei.get("value") or "").strip()
            if (
                not value
                or value in paired_imeis
                or imei.get("status") != "IN_STOCK"
                or not imei.get("locationId")
                or str(imei.get("locationCode") or "").upper() == "MAIN"
            ):
                continue
            candidates.append({
                "key": f"IMEI:{imei['id']}",
                "imeis": [value],
                "serialNumbers": [],
                "locationId": str(imei["locationId"]),
                "locationCode": imei.get("locationCode"),
                "locationName": imei.get("locationName"),
            })

        for serial in serials:
            value = str(serial.get("value") or "").strip()
            if (
                not value
                or value in paired_serials
                or serial.get("status") != "IN_STOCK"
                or not serial.get("locationId")
                or str(serial.get("locationCode") or "").upper() == "MAIN"
            ):
                continue
            candidates.append({
                "key": f"SERIAL:{serial['id']}",
                "imeis": [],
                "serialNumbers": [value],
                "locationId": str(serial["locationId"]),
                "locationCode": serial.get("locationCode"),
                "locationName": serial.get("locationName"),
            })

        result_items.append({
            "requestItemId": str(item["id"]),
            "productName": item.get("product_name"),
            "quantity": int(item.get("quantity") or 1),
            "candidates": candidates,
        })
    return {"requestId": str(request_id), "items": result_items}


def _json_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _service_return_extension_days(value: object) -> int:
    total = 0
    for service in _json_list(value):
        if not isinstance(service, dict):
            continue
        metadata = service.get("metadata") if isinstance(service.get("metadata"), dict) else {}
        raw = (
            service.get("returnExtensionDays")
            or service.get("return_extension_days")
            or metadata.get("returnExtensionDays")
            or metadata.get("return_extension_days")
            or 0
        )
        try:
            total += max(0, int(raw))
        except (TypeError, ValueError):
            continue
    return total


async def get_return_period_days(session: AsyncSession, item: dict) -> int:
    if item.get("used_device_id") is not None:
        return 30 + _service_return_extension_days(item.get("attached_services") or item.get("attachedServices"))
    product_id = item.get("product_id")
    if not product_id:
        return 15 + _service_return_extension_days(item.get("attached_services") or item.get("attachedServices"))
    slug = await session.scalar(
        text(
            """
            SELECT c.slug FROM categories c
            JOIN products p ON p.category_id = c.id
            WHERE p.id = :pid
            """
        ),
        {"pid": product_id},
    )
    if not slug:
        return 15
    slug_lower = slug.lower()
    slug_normalized = slug_lower.replace("-", "").replace("_", "")
    if any(k in slug_normalized for k in ["dienthoai", "smartphone", "tablet", "maytinhbang", "laptop", "wearable", "donghothongminh"]):
        days = 30
    elif "phukien" in slug_normalized or "accessory" in slug_normalized:
        price = float(item.get("unit_price") or 0)
        if price >= 1000000:
            days = 15
        else:
            days = 0
    else:
        days = 15
    return days + _service_return_extension_days(item.get("attached_services") or item.get("attachedServices"))


async def create_request(
    session: AsyncSession,
    *,
    kind: str,
    user_id: UUID,
    payload: CreateAfterSalesRequest,
) -> dict:
    order = await after_sales_repo.lock_order(session, payload.order_id, user_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng thuộc tài khoản này.")

    if order.get("status") != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể tạo yêu cầu đổi trả hoặc bảo hành cho đơn hàng đã giao thành công."
        )

    completed_at = order.get("completed_at")
    if not completed_at:
        raise HTTPException(
            status_code=400,
            detail="Đơn hàng chưa được ghi nhận thời gian hoàn thành."
        )

    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    time_diff = now - completed_at

    request_id = uuid4()
    request_code = build_request_code(kind)
    subtotal = money(order["subtotal_amount"])
    paid_items_total = max(money(order["total_amount"]) - money(order.get("shipping_fee", 0)), Decimal("0"))
    prepared: list[dict] = []
    exchange_target: dict | None = None

    has_exchange_target = bool(payload.exchange_product_id or payload.exchange_variant_id)
    if kind != "RETURN" and has_exchange_target:
        raise HTTPException(status_code=400, detail="Bảo hành không nhận thông tin sản phẩm đổi sang.")
    if kind == "RETURN" and payload.exchange_variant_id and not payload.exchange_product_id:
        raise HTTPException(status_code=400, detail="Cần gửi sản phẩm đổi sang khi chọn biến thể đổi sang.")
    if kind == "RETURN" and payload.exchange_product_id:
        if len(payload.items) != 1:
            raise HTTPException(
                status_code=400,
                detail="Đổi sang sản phẩm khác chỉ hỗ trợ một dòng thiết bị cũ trong mỗi hồ sơ.",
            )
        exchange_target = await after_sales_repo.get_exchange_target(
            session,
            product_id=payload.exchange_product_id,
            variant_id=payload.exchange_variant_id,
        )
        if not exchange_target:
            raise HTTPException(status_code=400, detail="Không tìm thấy sản phẩm hoặc biến thể muốn đổi sang.")
        if exchange_target.get("product_status") != "ACTIVE" or not exchange_target.get("variant_active", True):
            raise HTTPException(status_code=400, detail="Sản phẩm muốn đổi sang hiện không còn kinh doanh.")
        if money(exchange_target.get("unit_price") or 0) <= 0:
            raise HTTPException(status_code=400, detail="Sản phẩm muốn đổi sang chưa có giá bán hợp lệ.")

    if kind == "RETURN":
        if not (payload.has_accessories and payload.good_appearance and payload.account_unlocked and payload.has_vat_invoice):
            raise HTTPException(
                status_code=400,
                detail="Yêu cầu đổi trả chỉ được chấp nhận khi thiết bị có đầy đủ phụ kiện, ngoại quan nguyên vẹn, đã mở khóa tài khoản và có hóa đơn VAT đi kèm."
            )

    payload_item_totals: dict[UUID, int] = {}
    for source in payload.items:
        payload_item_totals[source.order_item_id] = payload_item_totals.get(source.order_item_id, 0) + source.quantity
    if exchange_target and payload.exchange_quantity != sum(payload_item_totals.values()):
        raise HTTPException(
            status_code=400,
            detail="Số lượng sản phẩm đổi sang phải bằng số lượng thiết bị cũ trong hồ sơ.",
        )

    seen_items = set()
    for source in payload.items:
        # Check duplicate items in payload
        key = (source.order_item_id, source.imei, source.serial_number)
        if key in seen_items:
            raise HTTPException(
                status_code=400,
                detail="Mỗi sản phẩm hoặc IMEI/serial chỉ được khai báo một lần trong yêu cầu."
            )
        seen_items.add(key)

        item = await after_sales_repo.get_order_item(session, payload.order_id, source.order_item_id)
        if not item:
            raise HTTPException(status_code=400, detail="Sản phẩm không thuộc đơn hàng đã chọn.")

        # Ràng buộc thời hạn đổi trả
        return_days = await get_return_period_days(session, item)
        if kind == "RETURN":
            if return_days <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm {item['product_name']} không hỗ trợ chính sách đổi trả."
                )
            if time_diff.days > return_days:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm {item['product_name']} đã quá thời hạn hỗ trợ đổi trả (Thời hạn đổi trả cho nhóm hàng này: {return_days} ngày)."
                )

        if kind == "WARRANTY":
            warranty_months = int(item.get("warrantyMonths") or 0)
            prod_name = item.get("product_name") or item.get("currentProductName") or "sản phẩm"
            if warranty_months <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm {prod_name} không hỗ trợ chế độ bảo hành chính hãng."
                )
            if time_diff.days > warranty_months * 30:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm {prod_name} đã hết thời hạn bảo hành chính hãng (Thời hạn bảo hành: {warranty_months} tháng)."
                )

        # Ràng buộc số lượng và mã định danh
        if (source.imei or source.serial_number) and source.quantity != 1:
            raise HTTPException(
                status_code=400,
                detail=f"Sản phẩm có mã định danh (IMEI hoặc Serial) bắt buộc phải có số lượng yêu cầu là 1."
            )

        if source.imei or source.serial_number:
            if await after_sales_repo.has_completed_return_for_identifier(session, imei=source.imei, serial_number=source.serial_number):
                raise HTTPException(
                    status_code=400,
                    detail="Thiết bị có IMEI/serial này đã được trả hàng/hoàn tiền thành công trước đó."
                )

        # Ràng buộc số lượng tích lũy
        total_returned = await after_sales_repo.get_total_returned_quantity(session, source.order_item_id)
        payload_qty = payload_item_totals[source.order_item_id]
        if kind == "RETURN":
            if total_returned + payload_qty > item["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tổng số lượng đổi trả đã xử lý và đang yêu cầu ({total_returned + payload_qty}) vượt số lượng đã mua ({item['quantity']}) của sản phẩm {item['product_name']}."
                )
        elif kind == "WARRANTY":
            active_warranties = await after_sales_repo.get_active_warranty_quantity(session, source.order_item_id)
            if active_warranties + total_returned + payload_qty > item["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tổng số lượng bảo hành và đổi trả ({active_warranties + total_returned + payload_qty}) vượt số lượng đã mua ({item['quantity']}) của sản phẩm {item['product_name']}."
                )

        if not await after_sales_repo.identifier_belongs_to_item(
            session,
            order_id=payload.order_id,
            product_id=item["product_id"],
            variant_id=item["variant_id"],
            imei=source.imei,
            serial_number=source.serial_number,
        ):
            raise HTTPException(status_code=400, detail="IMEI/serial không thuộc sản phẩm đã bán trong đơn hàng.")
        if await after_sales_repo.has_active_conflict(
            session,
            order_item_id=source.order_item_id,
            imei=source.imei,
            serial_number=source.serial_number,
        ):
            raise HTTPException(
                status_code=409,
                detail="Sản phẩm hoặc IMEI/serial đang có một hồ sơ hậu mãi hoạt động.",
            )
        line_gross = money(Decimal(str(item["unit_price"])) * source.quantity)
        refundable = money((line_gross / subtotal) * paid_items_total) if subtotal > 0 else Decimal("0")
        prepared.append({
            "id": uuid4(),
            "request_id": request_id,
            "order_item_id": source.order_item_id,
            "product_id": item["product_id"],
            "variant_id": item["variant_id"],
            "quantity": source.quantity,
            "imei": source.imei,
            "serial_number": source.serial_number,
            "unit_price": money(item["unit_price"]),
            "discount_allocation": max(line_gross - refundable, Decimal("0")),
            "refundable_amount": refundable,
        })
    await after_sales_repo.insert_request(
        session,
        kind=kind,
        request_id=request_id,
        request_code=request_code,
        user_id=user_id,
        order_id=payload.order_id,
        reason=payload.reason.strip(),
        has_accessories=payload.has_accessories,
        good_appearance=payload.good_appearance,
        account_unlocked=payload.account_unlocked,
        has_vat_invoice=payload.has_vat_invoice,
        exchange_product_id=payload.exchange_product_id if kind == "RETURN" else None,
        exchange_variant_id=payload.exchange_variant_id if kind == "RETURN" else None,
        exchange_quantity=payload.exchange_quantity if kind == "RETURN" else 1,
        exchange_unit_price=float(exchange_target["unit_price"]) if exchange_target else 0,
    )
    for item in prepared:
        await after_sales_repo.insert_item(session, kind=kind, values=item)
    await after_sales_repo.insert_event(
        session,
        kind=kind,
        reference_id=request_id,
        old_status=None,
        new_status="SUBMITTED",
        actor_id=user_id,
        note="Khách hàng tạo yêu cầu.",
    )
    await session.commit()
    return {"id": str(request_id), "requestCode": request_code, "status": "SUBMITTED"}


def _aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _remaining_days(end_at: datetime, now: datetime) -> int:
    seconds = (end_at - now).total_seconds()
    if seconds < 0:
        return -int(abs(seconds) // DAY_SECONDS) - 1
    return int((seconds + DAY_SECONDS - 1) // DAY_SECONDS)


def _eligibility_status(start_at: datetime | None, *, days: int = 0, months: int = 0) -> dict:
    if days <= 0 and months <= 0:
        return {
            "eligible": False,
            "status": "UNSUPPORTED",
            "remainingDays": 0,
            "endsAt": None,
            "tone": "slate",
        }
    if start_at is None:
        return {
            "eligible": True,
            "status": "UNKNOWN_END_DATE",
            "remainingDays": None,
            "endsAt": None,
            "tone": "blue",
        }
    total_days = days if days > 0 else months * 30
    end_at = start_at.timestamp() + total_days * DAY_SECONDS
    end_dt = datetime.fromtimestamp(end_at, timezone.utc)
    remaining = _remaining_days(end_dt, datetime.now(timezone.utc))
    return {
        "eligible": remaining >= 0,
        "status": "ACTIVE" if remaining >= 0 else "EXPIRED",
        "remainingDays": max(remaining, 0),
        "endsAt": end_dt.isoformat(),
        "tone": "emerald" if remaining >= 0 else "rose",
    }


async def get_purchased_items(session: AsyncSession, *, user_id: UUID) -> list[dict]:
    rows = await after_sales_repo.list_purchased_items(session, user_id)
    items: list[dict] = []
    for row in rows:
        completed_at = _aware_datetime(row.get("completedAt"))
        warranty_months = int(row.get("warrantyMonths") or 0)
        return_days = await get_return_period_days(session, row)
        warranty = _eligibility_status(completed_at, months=warranty_months)
        warranty.update({"months": warranty_months})
        return_policy = _eligibility_status(completed_at, days=return_days)
        return_policy.update({"days": return_days})
        identifiers = _json_list(row.get("identifiers"))
        recovered_statuses = {"DEFECTIVE_RETURNED", "RETURNED", "RETIRED", "SCRAP"}
        is_recovered = bool(identifiers) and all(
            str(identifier.get("deviceStatus") or "").upper() in recovered_statuses
            for identifier in identifiers
        )
        if is_recovered:
            warranty.update({"eligible": False, "status": "RECOVERED", "remainingDays": 0, "tone": "slate"})
            return_policy.update({"eligible": False, "status": "RECOVERED", "remainingDays": 0, "tone": "slate"})
        items.append({
            "id": row["orderItemId"],
            "orderId": row["orderId"],
            "orderCode": row["orderCode"],
            "orderItemId": row["orderItemId"],
            "productId": row["productId"],
            "variantId": row["variantId"],
            "usedDeviceId": row["usedDeviceId"],
            "productName": row["productName"],
            "quantity": int(row.get("quantity") or 0),
            "unitPrice": float(row.get("unitPrice") or 0),
            "totalPrice": float(row.get("totalPrice") or 0),
            "completedAt": row.get("completedAt"),
            "attachedServices": _json_list(row.get("attachedServices")),
            "identifiers": identifiers,
            "deviceLifecycle": "RECOVERED" if is_recovered else "ACTIVE",
            "warrantyMonthsSnapshot": warranty_months,
            "warrantySnapshotMissing": bool(row.get("warrantySnapshotMissing")),
            "warranty": warranty,
            "returnPolicy": return_policy,
        })
    return items


async def list_requests(
    session: AsyncSession,
    *,
    kind: str,
    user_id: UUID | None,
    status_value: str | None,
    page: int,
    limit: int,
    sort: str,
) -> dict:
    result = await after_sales_repo.list_requests(
        session,
        kind=kind,
        user_id=user_id,
        status_value=status_value,
        page=max(1, page),
        limit=min(max(1, limit), 100),
        descending=sort != "created_at",
    )
    if user_id is None:
        return result
    result["items"] = [_to_customer_after_sales_request(item) for item in result.get("items", [])]
    return result


_CUSTOMER_REQUEST_FIELDS = {
    "id", "requestCode", "orderId", "orderCode", "status", "reason", "resolutionType",
    "customerFault", "depreciationFee", "exchangeProductId", "exchangeVariantId",
    "exchangeQuantity", "exchangeUnitPrice", "exchangeFee", "exchangeShippingFee",
    "balanceAmount", "paymentStatus", "paymentDueAt", "exchangeProductName",
    "exchangeVariantSku", "exchangeVariantLabel", "slaDueAt", "createdAt",
    "repairChannel", "repairProviderName", "repairSentAt", "returnFulfillmentMethod",
}
_CUSTOMER_FULFILLMENT_FIELDS = {
    "id", "orderCode", "status", "shippingProvider", "trackingCode", "fulfillmentMethod",
    "recipientName", "recipientPhone", "shippingAddress",
}
_CUSTOMER_ITEM_FIELDS = {
    "id", "orderItemId", "productId", "variantId", "productName", "quantity", "imei",
    "serialNumber", "replacementImei", "replacementImeis", "replacementSecondaryImeis",
    "replacementSerialNumbers",
}
_CUSTOMER_ATTACHMENT_FIELDS = {"id", "originalName", "url", "contentType", "sizeBytes", "createdAt"}
_CUSTOMER_REPAIR_FIELDS = {"diagnosis", "action", "stage", "updatedAt"}


def _public_fields(source: dict | None, allowed: set[str]) -> dict | None:
    if not source:
        return None
    return {key: source.get(key) for key in allowed if key in source}


def _to_customer_after_sales_request(item: dict) -> dict:
    public = {key: item.get(key) for key in _CUSTOMER_REQUEST_FIELDS if key in item}
    public["items"] = [
        _public_fields(dict(line), _CUSTOMER_ITEM_FIELDS) or {}
        for line in (item.get("items") or [])
    ]
    public["attachments"] = [
        _public_fields(dict(attachment), _CUSTOMER_ATTACHMENT_FIELDS) or {}
        for attachment in (item.get("attachments") or [])
    ]
    public["repairSummary"] = _public_fields(
        dict(item.get("repairSummary") or {}),
        _CUSTOMER_REPAIR_FIELDS,
    ) or {}
    fulfillment = _public_fields(
        dict(item.get("fulfillmentOrder") or {}),
        _CUSTOMER_FULFILLMENT_FIELDS,
    )
    if fulfillment:
        public["fulfillmentOrder"] = fulfillment
    return public


async def list_request_events(session: AsyncSession, *, kind: str, request_id: UUID) -> list[dict]:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hậu mãi.")
    return await after_sales_repo.list_events(session, kind=kind, reference_id=request_id)


async def add_request_timeline_note(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    actor_id: UUID,
    payload: AfterSalesTimelineNoteRequest,
) -> dict:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ hậu mãi.")
    note = payload.note.strip()
    await after_sales_repo.insert_event(
        session,
        kind=kind,
        reference_id=request_id,
        old_status=request["status"],
        new_status=request["status"],
        actor_id=actor_id,
        note=note,
        metadata={"manualNote": True},
    )
    await session.commit()
    return {"ok": True}


async def cancel_request(session: AsyncSession, *, kind: str, request_id: UUID, user_id: UUID) -> None:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request or request["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    if request["status"] not in {"SUBMITTED", "WAITING_FOR_STOCK", "WAITING_FOR_EXCHANGE_PAYMENT"}:
        raise HTTPException(status_code=409, detail="Yêu cầu đã được tiếp nhận nên không thể tự hủy.")
    await after_sales_repo.update_request_status(
        session,
        kind=kind,
        request_id=request_id,
        status_value="CANCELLED",
        resolution_type=None,
        note="Khách hàng hủy yêu cầu.",
        customer_fault=False,
    )
    await after_sales_repo.release_allocations(session, kind=kind, request_id=request_id)
    await schedule_attachment_cleanup(session, kind, request_id)
    await after_sales_repo.insert_event(
        session,
        kind=kind,
        reference_id=request_id,
        old_status=request["status"],
        new_status="CANCELLED",
        actor_id=user_id,
        note="Khách hàng hủy yêu cầu.",
    )
    await session.commit()


async def admin_update_status(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    actor_id: UUID,
    payload: UpdateAfterSalesStatusRequest,
) -> dict:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hậu mãi.")
    target = payload.status.upper()
    if kind == "WARRANTY" and target == "QC_IN_PROGRESS" and request["status"] != "RECEIVED":
        reopenable_statuses = {"WARRANTY_ACCEPTED", "REPLACEMENT_APPROVED", "WAITING_FOR_STOCK"}
        if request["status"] not in reopenable_statuses:
            raise HTTPException(
                status_code=409,
                detail="Chỉ có thể đánh giá lại QC trước khi bắt đầu sửa chữa hoặc xử lý máy thay thế.",
            )
        reason = (payload.note or "").strip()
        if len(reason) < 10:
            raise HTTPException(
                status_code=400,
                detail="Cần nhập lý do đánh giá lại QC tối thiểu 10 ký tự.",
            )
        from app.application.after_sales.fulfillment import cancel_after_sales_order_for_reinspection
        await cancel_after_sales_order_for_reinspection(
            session,
            kind=kind,
            request_id=request_id,
            reason=f"Đánh giá lại QC: {reason}",
        )
        await after_sales_repo.release_allocations(session, kind=kind, request_id=request_id)
        await session.execute(
            text(
                """
                UPDATE warranty_requests
                SET status = 'QC_IN_PROGRESS',
                    resolution_type = NULL,
                    qc_note = NULL,
                    replacement_approved_at = NULL,
                    admin_note = :reason,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": request_id, "reason": reason},
        )
        await after_sales_repo.insert_event(
            session,
            kind=kind,
            reference_id=request_id,
            old_status=request["status"],
            new_status="QC_IN_PROGRESS",
            actor_id=actor_id,
            note=reason,
            metadata={
                "action": "REOPEN_QC",
                "previousResolutionType": request.get("resolution_type"),
            },
        )
        await session.commit()
        return {"id": str(request_id), "status": "QC_IN_PROGRESS"}
    if target not in transitions_for(kind).get(request["status"], set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển từ {request['status']} sang {target}.",
        )
    if request["status"] == "QC_IN_PROGRESS":
        raise HTTPException(
            status_code=400,
            detail="Hồ sơ đang ở trạng thái kiểm tra chất lượng (QC_IN_PROGRESS). Vui lòng sử dụng tính năng Đánh giá QC chuyên dụng để chuyển bước."
        )
    if target in {"QC_APPROVED", "WARRANTY_ACCEPTED"}:
        raise HTTPException(
            status_code=400,
            detail="Không thể chuyển trực tiếp sang trạng thái duyệt QC. Vui lòng sử dụng Đánh giá QC chuyên dụng."
        )
    if target == "REJECTED" and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="Cần nhập lý do khi từ chối yêu cầu hậu mãi.")
    if kind == "RETURN" and request["status"] == "WAITING_FOR_EXCHANGE_PAYMENT" and target == "EXCHANGE_PROCESSING":
        if request.get("payment_status") != "PAID" and not (payload.exchange_payment_reference or payload.note or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Cần nhập mã giao dịch hoặc ghi chú xác nhận thanh toán chênh lệch trước khi xử lý đổi máy.",
            )
    if (
        kind == "RETURN"
        and target == "EXCHANGE_PROCESSING"
        and float(request.get("balance_amount") or 0) > 0
        and request.get("payment_status") not in {"PAID"}
        and request["status"] != "WAITING_FOR_EXCHANGE_PAYMENT"
    ):
        raise HTTPException(
            status_code=409,
            detail="Hồ sơ còn tiền chênh lệch cần thanh toán, phải chuyển qua bước chờ thanh toán trước.",
        )
    repair_channel = (payload.repair_channel or request.get("repair_channel") or "").strip().upper()
    repair_provider_name = (payload.repair_provider_name or request.get("repair_provider_name") or "").strip()
    if (
        kind == "WARRANTY"
        and request.get("resolution_type") == "REPAIR"
        and request["status"] in {"REPAIRING", "REPAIR_COMPLETED", "READY_TO_RETURN", "RETURNING_TO_CUSTOMER"}
    ):
        existing_channel = str(request.get("repair_channel") or "").strip().upper()
        existing_provider = str(request.get("repair_provider_name") or "").strip()
        if payload.repair_channel and existing_channel and repair_channel != existing_channel:
            raise HTTPException(status_code=409, detail="Không thể đổi kênh sửa chữa sau khi đã bắt đầu sửa máy.")
        if payload.repair_provider_name and existing_provider and repair_provider_name != existing_provider:
            raise HTTPException(status_code=409, detail="Không thể đổi đơn vị bảo hành sau khi đã gửi sửa máy.")
    if kind == "WARRANTY" and target == "REPAIRING" and request.get("resolution_type") == "REPAIR":
        if repair_channel not in {"INTERNAL", "MANUFACTURER"}:
            raise HTTPException(status_code=400, detail="Vui lòng chọn sửa tại cửa hàng hoặc gửi bảo hành hãng.")
        if repair_channel == "MANUFACTURER" and not repair_provider_name:
            raise HTTPException(status_code=400, detail="Vui lòng nhập tên hãng hoặc trung tâm bảo hành.")
    if kind == "WARRANTY" and target == "REPAIR_COMPLETED" and request.get("resolution_type") == "REPAIR":
        if not (payload.repair_diagnosis or "").strip() or not (payload.repair_action or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Cần nhập chẩn đoán lỗi và nội dung đã sửa trước khi xác nhận sửa xong."
            )
    if target == "COMPLETED" and kind == "RETURN" and request.get("resolution_type") == "REFUND":
        refund_proof_url = (payload.refund_proof_url or "").strip()
        if not refund_proof_url:
            raise HTTPException(
                status_code=400,
                detail="Cần cung cấp link hình ảnh/chứng từ hoàn tiền (proof URL) trước khi hoàn tất hồ sơ.",
            )

    requires_receipt_confirmation = target == "COMPLETED" and (
        (
            kind == "WARRANTY"
            and request.get("resolution_type") in {"REPAIR", "REPLACEMENT"}
            and request["status"] in {"REPAIR_COMPLETED", "READY_TO_RETURN", "RETURNING_TO_CUSTOMER", "REPLACEMENT_PROCESSING"}
        )
        or (
            kind == "RETURN"
            and request.get("resolution_type") == "EXCHANGE"
            and request["status"] == "EXCHANGE_PROCESSING"
        )
    )
    if requires_receipt_confirmation and not payload.customer_receipt_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Cần xác nhận khách đã nhận máy trước khi hoàn tất hồ sơ hậu mãi.",
        )

    items = await after_sales_repo.get_request_items(session, kind=kind, request_id=request_id)
    if (
        kind == "WARRANTY"
        and request.get("resolution_type") == "REPLACEMENT"
        and target in {"READY_TO_RETURN", "COMPLETED"}
    ):
        fulfillment_order = (
            await session.execute(
                text(
                    """
                    SELECT status, fulfillment_method
                    FROM orders
                    WHERE warranty_request_id = :request_id
                    FOR UPDATE
                    """
                ),
                {"request_id": request_id},
            )
        ).mappings().first()
        outbound_completed = bool(
            await session.scalar(
                text(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM inventory_documents
                        WHERE warranty_request_id = :request_id
                          AND document_type = 'OUTBOUND'
                          AND status = 'COMPLETED'
                    )
                    """
                ),
                {"request_id": request_id},
            )
        )
        if not fulfillment_order or not outbound_completed:
            raise HTTPException(
                status_code=409,
                detail="Kho chưa hoàn tất phiếu xuất máy thay thế.",
            )
        if target == "READY_TO_RETURN" and fulfillment_order["fulfillment_method"] != "STORE_PICKUP":
            raise HTTPException(
                status_code=409,
                detail="Đơn giao tận nơi phải chờ đơn vị vận chuyển giao máy, không thể chuyển sang chờ nhận tại cửa hàng.",
            )
        if (
            target == "COMPLETED"
            and fulfillment_order["fulfillment_method"] == "DELIVERY"
            and fulfillment_order["status"] != "COMPLETED"
        ):
            raise HTTPException(
                status_code=409,
                detail="Máy thay thế chưa được giao thành công; chưa thể hoàn tất hồ sơ bảo hành.",
            )
    allocation_trigger = (
        (kind == "RETURN" and target == "EXCHANGE_PROCESSING")
        or (kind == "WARRANTY" and target == "REPLACEMENT_APPROVED")
    )
    if allocation_trigger:
        if kind == "RETURN" and request.get("exchange_product_id"):
            locked = await after_sales_repo.create_exchange_allocation(session, request=request)
        else:
            locked = await after_sales_repo.create_allocations(
                session,
                kind=kind,
                request_id=request_id,
                items=items,
            )
        if not locked:
            target = "WAITING_FOR_STOCK"
    if kind == "RETURN" and request["status"] == "WAITING_FOR_EXCHANGE_PAYMENT" and target == "EXCHANGE_PROCESSING":
        await after_sales_repo.mark_exchange_payment_paid(
            session,
            request_id=request_id,
            reference=(payload.exchange_payment_reference or payload.note or "").strip() or None,
        )

    if kind == "RETURN" and target == "REFUND_PROCESSING":
        await after_sales_repo.release_allocations(session, kind=kind, request_id=request_id)

    if target in {"EXCHANGE_PROCESSING", "REPLACEMENT_PROCESSING", "REPLACEMENT_APPROVED"}:
        from app.application.after_sales.fulfillment import ensure_after_sales_outbound
        fulfillment_request = dict(request)
        if payload.return_fulfillment_method:
            fulfillment_request["fulfillment_method"] = payload.return_fulfillment_method
        for field in ("recipient_name", "recipient_phone", "shipping_address", "shipping_provider"):
            value = getattr(payload, field, None)
            if value:
                fulfillment_request[field] = value.strip()
        if kind == "RETURN":
            fulfillment_request["payment_status"] = "PAID" if request["status"] == "WAITING_FOR_EXCHANGE_PAYMENT" else request.get("payment_status")
        await ensure_after_sales_outbound(
            session,
            kind=kind,
            request=fulfillment_request,
            items=items,
        )

    if kind == "WARRANTY" and target == "RETURNING_TO_CUSTOMER" and request.get("resolution_type") == "REPAIR":
        from app.application.after_sales.fulfillment import ensure_after_sales_order
        delivery_request = dict(request)
        delivery_request["fulfillment_method"] = "DELIVERY"
        for field in ("recipient_name", "recipient_phone", "shipping_address", "shipping_provider"):
            value = getattr(payload, field, None)
            if value:
                delivery_request[field] = value.strip()
        await ensure_after_sales_order(
            session,
            kind="WARRANTY",
            request=delivery_request,
            items=items,
            order_purpose="WARRANTY_RETURN",
        )

    replacement_imei = (payload.replacement_imei or "").strip()
    replacement_already_assigned = bool(items) and all(
        bool(item.get("replacement_imeis"))
        or bool(item.get("replacement_serial_numbers"))
        or bool((item.get("replacement_imei") or "").strip())
        for item in items
    )
    replacement_items = [item.model_dump() for item in payload.replacement_items]
    if not replacement_items and replacement_imei and len(items) == 1:
        replacement_items = [
            {
                "request_item_id": items[0]["id"],
                "imeis": [replacement_imei],
                "serial_numbers": [],
            }
        ]
    assigns_replacement = (
        kind == "RETURN"
        and request["status"] == "EXCHANGE_PROCESSING"
        and target == "COMPLETED"
    ) or (
        kind == "WARRANTY"
        and (
            (
                request["status"] == "REPLACEMENT_PROCESSING"
                and target in {"READY_TO_RETURN", "COMPLETED"}
            )
            or (
                request["status"] == "READY_TO_RETURN"
                and target == "COMPLETED"
                and request.get("resolution_type") == "REPLACEMENT"
            )
        )
    )
    if assigns_replacement and not replacement_already_assigned:
        request_column = "return_request_id" if kind == "RETURN" else "warranty_request_id"
        outbound_completed = bool(
            await session.scalar(
                text(
                    f"""
                    SELECT EXISTS(
                        SELECT 1 FROM inventory_documents
                        WHERE {request_column} = :request_id
                          AND document_type = 'OUTBOUND'
                          AND status = 'COMPLETED'
                    )
                    """
                ),
                {"request_id": request_id},
            )
        )
        if not outbound_completed:
            raise HTTPException(
                status_code=409,
                detail="Kho chưa hoàn tất phiếu xuất máy thay thế. Vui lòng đóng đủ hàng và hoàn tất phiếu xuất trước.",
            )

    if target == "COMPLETED" and kind == "RETURN" and request.get("resolution_type") == "REFUND":
        refund_transaction_ref = (payload.refund_transaction_ref or "").strip()
        if not refund_transaction_ref:
            raise HTTPException(
                status_code=400,
                detail="Cần nhập mã giao dịch hoặc chứng từ hoàn tiền trước khi hoàn tất hồ sơ.",
            )
        await after_sales_repo.release_allocations(session, kind=kind, request_id=request_id)
        depreciation_fee = payload.depreciation_fee or float(request.get("depreciation_fee") or 0)
        await create_refunds(
            session,
            request,
            items,
            payload.shipping_deduction,
            depreciation_fee,
            status_value="COMPLETED",
            transaction_ref=refund_transaction_ref,
            proof_url=(payload.refund_proof_url or "").strip() or None,
            processed_by=actor_id,
            processed_note=(payload.refund_note or payload.note or "").strip() or None,
        )

    depreciation_to_store = None
    if kind == "RETURN" and target in {"REFUND_PROCESSING", "COMPLETED"}:
        existing_depreciation = float(request.get("depreciation_fee") or 0)
        depreciation_to_store = payload.depreciation_fee if payload.depreciation_fee > 0 or existing_depreciation == 0 else existing_depreciation

    resolution_type = payload.resolution_type
    if kind == "RETURN" and resolution_type is None:
        if target == "REFUND_PROCESSING":
            resolution_type = "REFUND"
        elif target in {"EXCHANGE_PROCESSING", "WAITING_FOR_STOCK"} and allocation_trigger:
            resolution_type = "EXCHANGE"

    await after_sales_repo.update_request_status(
        session,
        kind=kind,
        request_id=request_id,
        status_value=target,
        resolution_type=resolution_type,
        note=payload.note,
        customer_fault=payload.customer_fault,
        depreciation_fee=depreciation_to_store,
        repair_channel=repair_channel or None,
        repair_provider_name=repair_provider_name or None,
        return_fulfillment_method=(
            "DELIVERY" if target == "RETURNING_TO_CUSTOMER"
            else "STORE_PICKUP" if target == "READY_TO_RETURN" and request.get("resolution_type") == "REPAIR"
            else payload.return_fulfillment_method
        ),
    )
    if kind == "RETURN" and target == "COMPLETED":
        from app.application.after_sales.return_disposition import (
            finalize_returned_identifier_disposition,
        )

        await finalize_returned_identifier_disposition(
            session,
            request_id=request_id,
            actor_id=actor_id,
        )
    repair_metadata = None
    if kind == "WARRANTY":
        repair_metadata = _repair_metadata_from_payload(payload, target)
    if requires_receipt_confirmation:
        repair_metadata = {
            **(repair_metadata or {}),
            "customerReceiptConfirmed": True,
            "confirmationSource": "ADMIN",
        }
    await after_sales_repo.insert_event(
        session,
        kind=kind,
        reference_id=request_id,
        old_status=request["status"],
        new_status=target,
        actor_id=actor_id,
        note=payload.note,
        metadata=repair_metadata,
    )
    if kind == "WARRANTY":
        await sync_warranty_imei_status(session, items=items, target=target, replacement_imei=payload.replacement_imei)
    if target == "REPAIRING" and kind == "WARRANTY":
        for item in items:
            if item.get("used_device_id"):
                transitioned = await used_product_repo.transition_after_sales_device(
                    session,
                    device_id=item["used_device_id"],
                    target_status="REPAIRING",
                    allowed_statuses={"SOLD", "REPAIRING"},
                    event_type="DEVICE_WARRANTY_REPAIRING",
                    note=f"Thiết bị được tiếp nhận sửa chữa theo yêu cầu bảo hành {request['request_code']}.",
                    metadata={"requestId": str(request_id), "requestCode": request["request_code"]},
                )
                if not transitioned:
                    raise HTTPException(status_code=409, detail="Trạng thái thiết bị cũ không hợp lệ để tiếp nhận bảo hành.")
    if target == "COMPLETED" and kind == "WARRANTY" and request.get("resolution_type") == "REPAIR":
        for item in items:
            if item.get("used_device_id"):
                transitioned = await used_product_repo.transition_after_sales_device(
                    session,
                    device_id=item["used_device_id"],
                    target_status="SOLD",
                    allowed_statuses={"REPAIRING", "SOLD"},
                    event_type="DEVICE_WARRANTY_REPAIRED",
                    note=f"Hoàn tất sửa chữa bảo hành theo yêu cầu {request['request_code']}.",
                    metadata={"requestId": str(request_id), "requestCode": request["request_code"]},
                )
                if not transitioned:
                    raise HTTPException(status_code=409, detail="Trạng thái thiết bị cũ không hợp lệ để hoàn tất bảo hành.")
    label = label_for(kind)
    customer_status_labels = {
        "WARRANTY_ACCEPTED": "chờ sửa chữa",
        "REPAIRING": "đã gửi bảo hành hãng" if repair_channel == "MANUFACTURER" else "đang sửa chữa",
        "REPAIR_COMPLETED": "đã sửa xong",
        "READY_TO_RETURN": "sẵn sàng trả máy tại cửa hàng",
        "RETURNING_TO_CUSTOMER": "đang gửi máy về cho khách",
        "COMPLETED": "hoàn tất",
    }
    await after_sales_repo.notify(
        session,
        user_id=request["user_id"],
        type_value="after_sales",
        title=f"Cập nhật yêu cầu {label}",
        message=f"Yêu cầu {request['request_code']} đã chuyển sang trạng thái {customer_status_labels.get(target, target)}.",
        entity_type=kind,
        entity_id=request_id,
        immediate=target in {"REJECTED", "COMPLETED"},
        key=f"{kind}:{request_id}:{target}",
    )
    await session.commit()
    return {"id": str(request_id), "status": target}


def _repair_metadata_from_payload(payload: UpdateAfterSalesStatusRequest, target: str) -> dict | None:
    diagnosis = (payload.repair_diagnosis or "").strip()
    action = (payload.repair_action or "").strip()
    parts = (payload.repair_parts or "").strip()
    repair_cost = float(payload.repair_cost or 0)
    has_repair_data = bool(diagnosis or action or parts or repair_cost > 0)
    if not has_repair_data and target != "REPAIRING":
        return None
    return {
        "repair": {
            "diagnosis": diagnosis or None,
            "action": action or None,
            "parts": parts or None,
            "cost": repair_cost,
            "stage": target,
            "channel": payload.repair_channel,
            "providerName": (payload.repair_provider_name or "").strip() or None,
        }
    }


async def sync_warranty_imei_status(
    session: AsyncSession,
    *,
    items: list[dict],
    target: str,
    replacement_imei: str | None = None,
) -> None:
    from app.application.after_sales.identifier_groups import (
        lock_identifier_group,
        update_locked_identifier_group_status,
    )

    if not items or target not in {"WARRANTY_ACCEPTED", "COMPLETED", "REJECTED", "CANCELLED"}:
        return
    has_replacement = bool((replacement_imei or "").strip()) or any(
        bool(item.get("replacement_imei"))
        or bool(item.get("replacement_imeis"))
        or bool(item.get("replacement_serial_numbers"))
        for item in items
    )
    if target == "COMPLETED" and has_replacement:
        # Hoàn tất theo hướng đổi máy không được đưa định danh lỗi trở lại trạng thái bán.
        return

    for item in items:
        imei_val = item.get("imei")
        serial_val = item.get("serial_number")
        if not imei_val and not serial_val:
            continue
        group = await lock_identifier_group(
            session,
            product_id=item["product_id"],
            variant_id=item.get("product_variant_id"),
            imei=imei_val,
            serial_number=serial_val,
        )
        if target == "WARRANTY_ACCEPTED":
            await update_locked_identifier_group_status(
                session,
                group=group,
                target_status="WARRANTY",
                allowed_statuses={"SOLD"},
            )
        elif target == "COMPLETED":
            await update_locked_identifier_group_status(
                session,
                group=group,
                target_status="SOLD",
                allowed_statuses={"WARRANTY"},
                clear_location=True,
            )
        elif target in {"REJECTED", "CANCELLED"}:
            await update_locked_identifier_group_status(
                session,
                group=group,
                target_status="SOLD",
                allowed_statuses={"WARRANTY"},
                clear_location=True,
            )
