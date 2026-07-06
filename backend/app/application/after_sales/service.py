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
from app.application.after_sales.replacements import complete_replacements
from app.application.after_sales.schemas import AfterSalesTimelineNoteRequest, CreateAfterSalesRequest, UpdateAfterSalesStatusRequest
from app.application.after_sales.transitions import label_for, transitions_for
from app.infrastructure.database.repositories import after_sales_repo


async def get_return_period_days(session: AsyncSession, item: dict) -> int:
    if item.get("used_device_id") is not None:
        return 30
    product_id = item.get("product_id")
    if not product_id:
        return 15
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
        return 30
    elif "phukien" in slug_normalized or "accessory" in slug_normalized:
        price = float(item.get("unit_price") or 0)
        if price >= 1000000:
            return 15
        return 0
    else:
        return 15


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

    if kind == "RETURN":
        if not (payload.has_accessories and payload.good_appearance and payload.account_unlocked and payload.has_vat_invoice):
            raise HTTPException(
                status_code=400,
                detail="Yêu cầu đổi trả chỉ được chấp nhận khi thiết bị có đầy đủ phụ kiện, ngoại quan nguyên vẹn, đã mở khóa tài khoản và có hóa đơn VAT đi kèm."
            )

    payload_item_totals: dict[UUID, int] = {}
    for source in payload.items:
        payload_item_totals[source.order_item_id] = payload_item_totals.get(source.order_item_id, 0) + source.quantity

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
    return await after_sales_repo.list_requests(
        session,
        kind=kind,
        user_id=user_id,
        status_value=status_value,
        page=max(1, page),
        limit=min(max(1, limit), 100),
        descending=sort != "created_at",
    )


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
    if request["status"] not in {"SUBMITTED", "WAITING_FOR_STOCK"}:
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
    if kind == "WARRANTY" and target in {"READY_TO_RETURN", "COMPLETED"} and request.get("resolution_type") == "REPAIR":
        if not (payload.repair_diagnosis or "").strip() or not (payload.repair_action or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Luồng sửa chữa bảo hành bắt buộc phải nhập chẩn đoán lỗi và hướng xử lý."
            )
    if target == "COMPLETED" and kind == "RETURN" and request.get("resolution_type") == "REFUND":
        refund_proof_url = (payload.refund_proof_url or "").strip()
        if not refund_proof_url:
            raise HTTPException(
                status_code=400,
                detail="Cần cung cấp link hình ảnh/chứng từ hoàn tiền (proof URL) trước khi hoàn tất hồ sơ.",
            )

    items = await after_sales_repo.get_request_items(session, kind=kind, request_id=request_id)
    allocation_trigger = (
        (kind == "RETURN" and target == "EXCHANGE_PROCESSING")
        or (kind == "WARRANTY" and target == "REPLACEMENT_APPROVED")
    )
    if allocation_trigger:
        locked = await after_sales_repo.create_allocations(
            session,
            kind=kind,
            request_id=request_id,
            items=items,
        )
        if not locked:
            target = "WAITING_FOR_STOCK"

    if kind == "RETURN" and target == "REFUND_PROCESSING":
        await after_sales_repo.release_allocations(session, kind=kind, request_id=request_id)

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
    if assigns_replacement and not replacement_already_assigned and not replacement_items:
        raise HTTPException(
            status_code=400,
            detail="Cần nhập IMEI hoặc serial của từng thiết bị thay thế trước khi chuyển bước xử lý.",
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
    elif assigns_replacement and not replacement_already_assigned:
        await complete_replacements(
            session,
            kind=kind,
            request=request,
            request_id=request_id,
            items=items,
            replacement_items=replacement_items,
            actor_id=actor_id,
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
    )
    repair_metadata = None
    if kind == "WARRANTY":
        repair_metadata = _repair_metadata_from_payload(payload, target)
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
                await session.execute(
                    text("UPDATE used_devices SET status = 'REPAIRING', updated_at = NOW() WHERE id = :uid"),
                    {"uid": item["used_device_id"]},
                )
    if target == "COMPLETED" and kind == "WARRANTY" and request.get("resolution_type") == "REPAIR":
        for item in items:
            if item.get("used_device_id"):
                await session.execute(
                    text("UPDATE used_devices SET status = 'SOLD', updated_at = NOW() WHERE id = :uid"),
                    {"uid": item["used_device_id"]},
                )
    label = label_for(kind)
    await after_sales_repo.notify(
        session,
        user_id=request["user_id"],
        type_value="after_sales",
        title=f"Cập nhật yêu cầu {label}",
        message=f"Yêu cầu {request['request_code']} đã chuyển sang trạng thái {target}.",
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
    if not has_repair_data and target not in {"REPAIRING", "READY_TO_RETURN"}:
        return None
    return {
        "repair": {
            "diagnosis": diagnosis or None,
            "action": action or None,
            "parts": parts or None,
            "cost": repair_cost,
            "stage": target,
        }
    }


async def sync_warranty_imei_status(
    session: AsyncSession,
    *,
    items: list[dict],
    target: str,
    replacement_imei: str | None = None,
) -> None:
    if not items:
        return
    for item in items:
        imei_val = item.get("imei")
        if not imei_val:
            continue
        if target == "WARRANTY_ACCEPTED":
            await session.execute(
                text("UPDATE product_imeis SET status='WARRANTY', updated_at=NOW() WHERE imei=:imei AND status='SOLD'"),
                {"imei": imei_val},
            )
        elif target == "COMPLETED" and not replacement_imei:
            await session.execute(
                text("UPDATE product_imeis SET status='SOLD', location_id=NULL, updated_at=NOW() WHERE imei=:imei AND status='WARRANTY'"),
                {"imei": imei_val},
            )
        elif target in {"REJECTED", "CANCELLED"}:
            await session.execute(
                text("UPDATE product_imeis SET status='SOLD', location_id=NULL, updated_at=NOW() WHERE imei=:imei AND status='WARRANTY'"),
                {"imei": imei_val},
            )
