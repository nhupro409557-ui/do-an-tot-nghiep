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
from app.application.after_sales.replacements import complete_replacement
from app.application.after_sales.schemas import AfterSalesTimelineNoteRequest, CreateAfterSalesRequest, UpdateAfterSalesStatusRequest
from app.application.after_sales.transitions import label_for, transitions_for
from app.infrastructure.database.repositories import after_sales_repo


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

    # Ràng buộc đơn hàng phải hoàn thành thành công mới được tạo yêu cầu
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

    # Ràng buộc thời hạn đổi trả (RETURN) tối đa 7 ngày
    if kind == "RETURN":
        if time_diff.days > 7:
            raise HTTPException(
                status_code=400,
                detail="Đã quá thời hạn hỗ trợ đổi trả của đơn hàng này (tối đa 7 ngày kể từ lúc nhận hàng)."
            )

    request_id = uuid4()
    request_code = build_request_code(kind)
    subtotal = money(order["subtotal_amount"])
    paid_items_total = max(money(order["total_amount"]) - money(order.get("shipping_fee", 0)), Decimal("0"))
    prepared: list[dict] = []
    for source in payload.items:
        item = await after_sales_repo.get_order_item(session, payload.order_id, source.order_item_id)
        if not item:
            raise HTTPException(status_code=400, detail="Sản phẩm không thuộc đơn hàng đã chọn.")

        # Ràng buộc thời hạn bảo hành (WARRANTY) cho từng sản phẩm
        prod_res = await session.execute(
            text("SELECT warranty_period, name FROM products WHERE id = :id"),
            {"id": item["product_id"]}
        )
        prod_row = prod_res.first()
        if not prod_row:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông tin sản phẩm.")

        warranty_months = prod_row[0]
        prod_name = prod_row[1]

        if kind == "WARRANTY":
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
        if source.quantity > item["quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Số lượng yêu cầu của {item['product_name']} vượt số lượng đã mua.",
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

    items = await after_sales_repo.get_request_items(session, kind=kind, request_id=request_id)
    allocation_trigger = target == ("QC_APPROVED" if kind == "RETURN" else "REPLACEMENT_APPROVED")
    if allocation_trigger:
        locked = await after_sales_repo.create_allocations(
            session,
            kind=kind,
            request_id=request_id,
            items=items,
        )
        if not locked:
            target = "WAITING_FOR_STOCK"

    if target == "COMPLETED":
        if kind == "RETURN" and request.get("resolution_type") == "REFUND":
            depreciation_fee = payload.depreciation_fee or float(request.get("depreciation_fee") or 0)
            await create_refunds(session, request, items, payload.shipping_deduction, depreciation_fee)
        elif payload.replacement_imei:
            await complete_replacement(
                session,
                kind=kind,
                request=request,
                request_id=request_id,
                items=items,
                replacement_imei=payload.replacement_imei,
                actor_id=actor_id,
            )

    depreciation_to_store = None
    if kind == "RETURN" and target in {"REFUND_PROCESSING", "COMPLETED"}:
        existing_depreciation = float(request.get("depreciation_fee") or 0)
        depreciation_to_store = payload.depreciation_fee if payload.depreciation_fee > 0 or existing_depreciation == 0 else existing_depreciation

    await after_sales_repo.update_request_status(
        session,
        kind=kind,
        request_id=request_id,
        status_value=target,
        resolution_type=payload.resolution_type,
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
    replacement_imei: str | None,
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
                text("UPDATE product_imeis SET status='SOLD', updated_at=NOW() WHERE imei=:imei AND status='WARRANTY'"),
                {"imei": imei_val},
            )
        elif target in {"REJECTED", "CANCELLED"}:
            await session.execute(
                text("UPDATE product_imeis SET status='SOLD', updated_at=NOW() WHERE imei=:imei AND status='WARRANTY'"),
                {"imei": imei_val},
            )
