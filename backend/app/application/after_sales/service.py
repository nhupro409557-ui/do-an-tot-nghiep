import hashlib
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.schemas import CreateAfterSalesRequest, UpdateAfterSalesStatusRequest
from app.infrastructure.database.repositories import after_sales_repo


RETURN_TRANSITIONS = {
    "SUBMITTED": {"RECEIVED", "CANCELLED", "CLOSED_EXPIRED"},
    "RECEIVED": {"QC_IN_PROGRESS", "REJECTED"},
    "QC_IN_PROGRESS": {"QC_APPROVED", "REJECTED"},
    "QC_APPROVED": {"WAITING_FOR_STOCK", "EXCHANGE_PROCESSING", "REFUND_PROCESSING"},
    "WAITING_FOR_STOCK": {"QC_APPROVED", "EXCHANGE_PROCESSING", "CANCELLED"},
    "EXCHANGE_PROCESSING": {"COMPLETED"},
    "REFUND_PROCESSING": {"COMPLETED"},
}
WARRANTY_TRANSITIONS = {
    "SUBMITTED": {"RECEIVED", "CANCELLED", "CLOSED_EXPIRED"},
    "RECEIVED": {"QC_IN_PROGRESS", "REJECTED"},
    "QC_IN_PROGRESS": {"WARRANTY_ACCEPTED", "REPLACEMENT_APPROVED", "REJECTED"},
    "WARRANTY_ACCEPTED": {"REPAIRING", "READY_TO_RETURN"},
    "REPAIRING": {"READY_TO_RETURN"},
    "REPLACEMENT_APPROVED": {"WAITING_FOR_STOCK", "REPLACEMENT_PROCESSING"},
    "WAITING_FOR_STOCK": {"REPLACEMENT_APPROVED", "REPLACEMENT_PROCESSING", "CANCELLED"},
    "REPLACEMENT_PROCESSING": {"READY_TO_RETURN", "COMPLETED"},
    "READY_TO_RETURN": {"COMPLETED"},
}

ALLOWED_UPLOAD_TYPES = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _code(kind: str) -> str:
    prefix = "RT" if kind == "RETURN" else "WR"
    return f"{prefix}{datetime.now(timezone.utc):%Y%m%d%H%M%S}{str(uuid4())[:4].upper()}"


async def create_request(
    session: AsyncSession, *, kind: str, user_id: UUID, payload: CreateAfterSalesRequest,
) -> dict:
    order = await after_sales_repo.lock_order(session, payload.order_id, user_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng thuộc tài khoản này.")
    request_id = uuid4()
    request_code = _code(kind)
    subtotal = _money(order["subtotal_amount"])
    paid_items_total = max(_money(order["total_amount"]) - _money(order.get("shipping_fee", 0)), Decimal("0"))
    prepared: list[dict] = []
    for source in payload.items:
        item = await after_sales_repo.get_order_item(session, payload.order_id, source.order_item_id)
        if not item:
            raise HTTPException(status_code=400, detail="Sản phẩm không thuộc đơn hàng đã chọn.")
        if source.quantity > item["quantity"]:
            raise HTTPException(status_code=400, detail=f"Số lượng yêu cầu của {item['product_name']} vượt số lượng đã mua.")
        if not await after_sales_repo.identifier_belongs_to_item(
            session, order_id=payload.order_id, product_id=item["product_id"],
            variant_id=item["variant_id"], imei=source.imei, serial_number=source.serial_number,
        ):
            raise HTTPException(status_code=400, detail="IMEI/serial không thuộc sản phẩm đã bán trong đơn hàng.")
        if await after_sales_repo.has_active_conflict(
            session, order_item_id=source.order_item_id, imei=source.imei,
            serial_number=source.serial_number,
        ):
            raise HTTPException(status_code=409, detail="Sản phẩm hoặc IMEI/serial đang có một hồ sơ hậu mãi hoạt động.")
        line_gross = _money(Decimal(str(item["unit_price"])) * source.quantity)
        refundable = _money((line_gross / subtotal) * paid_items_total) if subtotal > 0 else Decimal("0")
        prepared.append({
            "id": uuid4(), "request_id": request_id, "order_item_id": source.order_item_id,
            "product_id": item["product_id"], "variant_id": item["variant_id"],
            "quantity": source.quantity, "imei": source.imei, "serial_number": source.serial_number,
            "unit_price": _money(item["unit_price"]),
            "discount_allocation": max(line_gross - refundable, Decimal("0")),
            "refundable_amount": refundable,
        })
    await after_sales_repo.insert_request(
        session, kind=kind, request_id=request_id, request_code=request_code,
        user_id=user_id, order_id=payload.order_id, reason=payload.reason.strip(),
    )
    for item in prepared:
        await after_sales_repo.insert_item(session, kind=kind, values=item)
    await after_sales_repo.insert_event(
        session, kind=kind, reference_id=request_id, old_status=None,
        new_status="SUBMITTED", actor_id=user_id, note="Khách hàng tạo yêu cầu.",
    )
    await session.commit()
    return {"id": str(request_id), "requestCode": request_code, "status": "SUBMITTED"}


async def list_requests(
    session: AsyncSession, *, kind: str, user_id: UUID | None, status_value: str | None,
    page: int, limit: int, sort: str,
) -> dict:
    return await after_sales_repo.list_requests(
        session, kind=kind, user_id=user_id, status_value=status_value,
        page=max(1, page), limit=min(max(1, limit), 100), descending=sort != "created_at",
    )


async def cancel_request(session: AsyncSession, *, kind: str, request_id: UUID, user_id: UUID) -> None:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request or request["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    if request["status"] not in {"SUBMITTED", "WAITING_FOR_STOCK"}:
        raise HTTPException(status_code=409, detail="Yêu cầu đã được tiếp nhận nên không thể tự hủy.")
    await after_sales_repo.update_request_status(
        session, kind=kind, request_id=request_id, status_value="CANCELLED",
        resolution_type=None, note="Khách hàng hủy yêu cầu.", customer_fault=False,
    )
    await after_sales_repo.release_allocations(session, kind=kind, request_id=request_id)
    await _schedule_attachment_cleanup(session, kind, request_id)
    await after_sales_repo.insert_event(
        session, kind=kind, reference_id=request_id, old_status=request["status"],
        new_status="CANCELLED", actor_id=user_id, note="Khách hàng hủy yêu cầu.",
    )
    await session.commit()


async def admin_update_status(
    session: AsyncSession, *, kind: str, request_id: UUID, actor_id: UUID,
    payload: UpdateAfterSalesStatusRequest,
) -> dict:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hậu mãi.")
    transitions = RETURN_TRANSITIONS if kind == "RETURN" else WARRANTY_TRANSITIONS
    target = payload.status.upper()
    if target not in transitions.get(request["status"], set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển từ {request['status']} sang {target}.",
        )
    items = await after_sales_repo.get_request_items(session, kind=kind, request_id=request_id)
    allocation_trigger = target == ("QC_APPROVED" if kind == "RETURN" else "REPLACEMENT_APPROVED")
    if allocation_trigger:
        locked = await after_sales_repo.create_allocations(
            session, kind=kind, request_id=request_id, items=items,
        )
        if not locked:
            target = "WAITING_FOR_STOCK"
    if target == "COMPLETED":
        if kind == "RETURN" and request.get("resolution_type") == "REFUND":
            await _create_refunds(session, request, items, payload.shipping_deduction)
        elif payload.replacement_imei:
            await _complete_replacement(
                session, kind=kind, request_id=request_id, items=items,
                replacement_imei=payload.replacement_imei, actor_id=actor_id,
            )
    await after_sales_repo.update_request_status(
        session, kind=kind, request_id=request_id, status_value=target,
        resolution_type=payload.resolution_type, note=payload.note,
        customer_fault=payload.customer_fault,
    )
    await after_sales_repo.insert_event(
        session, kind=kind, reference_id=request_id, old_status=request["status"],
        new_status=target, actor_id=actor_id, note=payload.note,
    )
    # Đồng bộ trạng thái IMEI trong vòng đời bảo hành sửa chữa
    if kind == "WARRANTY" and items:
        for item in items:
            imei_val = item.get("imei")
            if imei_val:
                if target == "WARRANTY_ACCEPTED":
                    await session.execute(
                        text("UPDATE product_imeis SET status='WARRANTY', updated_at=NOW() WHERE imei=:imei AND status='SOLD'"),
                        {"imei": imei_val},
                    )
                elif target == "COMPLETED" and not payload.replacement_imei:
                    await session.execute(
                        text("UPDATE product_imeis SET status='SOLD', updated_at=NOW() WHERE imei=:imei AND status='WARRANTY'"),
                        {"imei": imei_val},
                    )
                elif target in {"REJECTED", "CANCELLED"}:
                    await session.execute(
                        text("UPDATE product_imeis SET status='SOLD', updated_at=NOW() WHERE imei=:imei AND status='WARRANTY'"),
                        {"imei": imei_val},
                    )
    immediate = target in {"REJECTED", "COMPLETED"}
    label = "đổi trả" if kind == "RETURN" else "bảo hành"
    await after_sales_repo.notify(
        session, user_id=request["user_id"], type_value="after_sales",
        title=f"Cập nhật yêu cầu {label}",
        message=f"Yêu cầu {request['request_code']} đã chuyển sang trạng thái {target}.",
        entity_type=kind, entity_id=request_id, immediate=immediate,
        key=f"{kind}:{request_id}:{target}",
    )
    await session.commit()
    return {"id": str(request_id), "status": target}


async def _create_refunds(session: AsyncSession, request: dict, items: list[dict], shipping_deduction: float) -> None:
    total_gross = sum((_money(item["refundable_amount_snapshot"]) for item in items), Decimal("0"))
    deduction = min(_money(shipping_deduction), total_gross)
    remaining_deduction = deduction
    for index, item in enumerate(items):
        gross = _money(item["refundable_amount_snapshot"])
        item_deduction = remaining_deduction if index == len(items) - 1 else _money(
            deduction * gross / total_gross
        ) if total_gross else Decimal("0")
        remaining_deduction -= item_deduction
        await session.execute(
            text(
                """
                INSERT INTO refund_transactions
                    (id, order_id, order_item_id, return_request_id, user_id, provider,
                     status, gross_amount, shipping_deduction, refund_amount,
                     idempotency_key, metadata)
                VALUES
                    (:id, :order_id, :order_item_id, :request_id, :user_id, :provider,
                     'PROCESSING', :gross, :deduction, :refund,
                     :key, jsonb_build_object('snapshotVersion', 1))
                ON CONFLICT (idempotency_key) DO NOTHING
                """
            ),
            {
                "id": uuid4(), "order_id": request["order_id"], "order_item_id": item["order_item_id"],
                "request_id": request["id"], "user_id": request["user_id"],
                "provider": "MANUAL", "gross": gross, "deduction": item_deduction,
                "refund": max(gross - item_deduction, Decimal("0")),
                "key": f"return:{request['id']}:item:{item['order_item_id']}",
            },
        )
    order_item_count = int(await session.scalar(
        text("SELECT COUNT(*) FROM order_items WHERE order_id=:order_id"),
        {"order_id": request["order_id"]},
    ) or 0)
    returned_item_count = len({item["order_item_id"] for item in items})
    order_discount = _money(await session.scalar(
        text("SELECT discount_amount FROM orders WHERE id=:order_id"),
        {"order_id": request["order_id"]},
    ) or 0)
    if returned_item_count == order_item_count and order_discount > 0 and not request.get("customer_fault"):
        await _issue_compensation_voucher(session, request=request, amount=order_discount)


async def _issue_compensation_voucher(session: AsyncSession, *, request: dict, amount: Decimal) -> None:
    existing = await session.scalar(
        text(
            """
            SELECT EXISTS(
                SELECT 1 FROM compensation_vouchers cv
                JOIN refund_transactions rt ON rt.id=cv.refund_transaction_id
                WHERE rt.return_request_id=:request_id
            )
            """
        ),
        {"request_id": request["id"]},
    )
    if existing:
        return
    refund_id = await session.scalar(
        text(
            """
            SELECT id FROM refund_transactions
            WHERE return_request_id=:request_id
            ORDER BY created_at LIMIT 1
            """
        ),
        {"request_id": request["id"]},
    )
    if not refund_id:
        return
    voucher_id = uuid4()
    user_voucher_id = uuid4()
    code = f"BD{str(request['id']).replace('-', '')[:10].upper()}"
    await session.execute(
        text(
            """
            INSERT INTO vouchers
                (id, code, discount_type, discount_value, min_order_value,
                 usage_limit, per_user_limit, campaign_type, audience_type,
                 assigned_user_id, validity_days_after_claim, hidden_code,
                 refund_policy, internal_note, status, starts_at, ends_at)
            VALUES
                (:id, :code, 'FIXED', :amount, 0, 1, 1, 'CUSTOMER_SERVICE',
                 'SPECIFIC_USER', :user_id, 30, TRUE, 'SHOP_FAULT_ONLY',
                 :note, 'ACTIVE', NOW(), NOW() + INTERVAL '30 days')
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {
            "id": voucher_id, "code": code, "amount": amount, "user_id": request["user_id"],
            "note": f"Voucher đền bù từ yêu cầu {request['request_code']}.",
        },
    )
    actual_voucher_id = await session.scalar(text("SELECT id FROM vouchers WHERE code=:code"), {"code": code})
    await session.execute(
        text(
            """
            INSERT INTO user_vouchers
                (id, user_id, voucher_id, status, claimed_at, expires_at)
            VALUES (:id, :user_id, :voucher_id, 'AVAILABLE', NOW(), NOW() + INTERVAL '30 days')
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": user_voucher_id, "user_id": request["user_id"], "voucher_id": actual_voucher_id},
    )
    actual_user_voucher_id = await session.scalar(
        text(
            """
            SELECT id FROM user_vouchers
            WHERE user_id=:user_id AND voucher_id=:voucher_id
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"user_id": request["user_id"], "voucher_id": actual_voucher_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO compensation_vouchers
                (id, refund_transaction_id, voucher_id, user_voucher_id, source_order_id)
            VALUES (:id, :refund_id, :voucher_id, :user_voucher_id, :order_id)
            ON CONFLICT (refund_transaction_id) DO NOTHING
            """
        ),
        {
            "id": uuid4(), "refund_id": refund_id, "voucher_id": actual_voucher_id,
            "user_voucher_id": actual_user_voucher_id, "order_id": request["order_id"],
        },
    )
    await after_sales_repo.notify(
        session, user_id=request["user_id"], type_value="voucher",
        title="Bạn nhận được voucher đền bù",
        message=f"Voucher {code} trị giá {int(amount):,}đ có hiệu lực trong 30 ngày.",
        entity_type="VOUCHER", entity_id=actual_voucher_id, immediate=True,
        key=f"compensation-voucher:{request['id']}",
    )


async def _complete_replacement(
    session: AsyncSession, *, kind: str, request_id: UUID, items: list[dict],
    replacement_imei: str, actor_id: UUID,
) -> None:
    if len(items) != 1:
        raise HTTPException(status_code=400, detail="Quét IMEI thay thế hiện hỗ trợ từng sản phẩm một.")
    item = items[0]
    new_identifier = await session.execute(
        text(
            """
            SELECT id, status, location_id FROM product_imeis
            WHERE imei=:imei AND product_id=:product_id
              AND variant_id IS NOT DISTINCT FROM :variant_id
            FOR UPDATE
            """
        ),
        {
            "imei": replacement_imei, "product_id": item["product_id"],
            "variant_id": item["product_variant_id"],
        },
    )
    row = new_identifier.first()
    if not row or row.status != "IN_STOCK":
        raise HTTPException(status_code=409, detail="IMEI thay thế không còn ở trạng thái sẵn sàng trong kho.")
    level = (await session.execute(
        text(
            """
            SELECT id, on_hand_quantity
            FROM inventory_levels
            WHERE location_id=:location_id
              AND ((:variant_id IS NOT NULL AND variant_id=:variant_id)
                   OR (:variant_id IS NULL AND product_id=:product_id))
            FOR UPDATE
            """
        ),
        {
            "location_id": row.location_id, "variant_id": item["product_variant_id"],
            "product_id": item["product_id"],
        },
    )).first()
    if not level or level.on_hand_quantity < 1:
        raise HTTPException(status_code=409, detail="Tồn kho vật lý tại vị trí của IMEI không đủ để xuất đổi.")
    await session.execute(
        text("UPDATE inventory_levels SET on_hand_quantity=on_hand_quantity-1, updated_at=NOW() WHERE id=:id"),
        {"id": level.id},
    )
    if item["product_variant_id"]:
        await session.execute(
            text("UPDATE product_variants SET stock_quantity=GREATEST(stock_quantity-1,0), updated_at=NOW() WHERE id=:id"),
            {"id": item["product_variant_id"]},
        )
    await session.execute(
        text("UPDATE products SET stock_quantity=GREATEST(stock_quantity-1,0), updated_at=NOW() WHERE id=:id"),
        {"id": item["product_id"]},
    )
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs
                (id, product_id, variant_id, old_quantity, new_quantity, delta, reason, note)
            VALUES
                (:id, :product_id, :variant_id, :old_quantity, :new_quantity, -1,
                 'AFTER_SALES_REPLACEMENT', :note)
            """
        ),
        {
            "id": uuid4(), "product_id": item["product_id"], "variant_id": item["product_variant_id"],
            "old_quantity": level.on_hand_quantity, "new_quantity": level.on_hand_quantity - 1,
            "note": f"Xuất máy thay thế cho yêu cầu {kind} {request_id}.",
        },
    )
    await session.execute(
        text("UPDATE product_imeis SET status='SOLD', sold_at=NOW(), sold_order_id=:order_id, updated_at=NOW() WHERE id=:id"),
        {"id": row.id, "order_id": request["order_id"]},
    )
    if item.get("imei"):
        await session.execute(
            text("UPDATE product_imeis SET status='DEFECTIVE_RETURNED', updated_at=NOW() WHERE imei=:imei"),
            {"imei": item["imei"]},
        )
    await session.execute(
        text(
            """
            UPDATE after_sales_allocations SET status='CONSUMED', consumed_at=NOW()
            WHERE reference_type=:kind AND reference_id=:request_id AND status='LOCKED'
            """
        ),
        {"kind": kind, "request_id": request_id},
    )
    _, item_table = after_sales_repo._table(kind)
    await session.execute(
        text(f"UPDATE {item_table} SET replacement_imei=:imei WHERE request_id=:id"),
        {"imei": replacement_imei, "id": request_id},
    )
    if item.get("imei"):
        old_id = await session.scalar(text("SELECT id FROM product_imeis WHERE imei=:imei"), {"imei": item["imei"]})
        if old_id:
            await session.execute(
                text(
                    """
                    INSERT INTO imei_disposition_events
                        (id, imei_id, after_sales_type, after_sales_id, old_status,
                         new_status, reason, actor_id)
                    VALUES (:id, :imei_id, :kind, :request_id, 'SOLD',
                            'DEFECTIVE_RETURNED', 'Thu hồi từ yêu cầu hậu mãi.', :actor_id)
                    """
                ),
                {
                    "id": uuid4(), "imei_id": old_id, "kind": kind,
                    "request_id": request_id, "actor_id": actor_id,
                },
            )


async def add_attachments(
    session: AsyncSession, *, kind: str, request_id: UUID, user_id: UUID, files: list[UploadFile],
) -> list[dict]:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request or request["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu.")
    if request["status"] not in {"SUBMITTED", "RECEIVED"}:
        raise HTTPException(status_code=409, detail="Không thể bổ sung tệp sau khi QC đã bắt đầu.")
    current = int(await session.scalar(
        text(
            """
            SELECT COUNT(*) FROM after_sales_attachments
            WHERE reference_type=:kind AND reference_id=:id AND status='ACTIVE'
            """
        ),
        {"kind": kind, "id": request_id},
    ) or 0)
    if current + len(files) > 5:
        raise HTTPException(status_code=400, detail="Mỗi yêu cầu chỉ được tối đa 5 tệp.")
    root = Path("uploads") / "after-sales" / kind.lower() / str(request_id)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for upload in files:
        content_type = (upload.content_type or "").lower()
        if content_type not in ALLOWED_UPLOAD_TYPES:
            raise HTTPException(status_code=400, detail=f"Định dạng tệp {upload.filename} không được hỗ trợ.")
        data = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail=f"Tệp {upload.filename} vượt quá 20 MB.")
        digest = hashlib.sha256(data).hexdigest()
        attachment_id = uuid4()
        filename = f"{attachment_id}{ALLOWED_UPLOAD_TYPES[content_type]}"
        path = root / filename
        path.write_bytes(data)
        storage_key = path.as_posix()
        await session.execute(
            text(
                """
                INSERT INTO after_sales_attachments
                    (id, reference_type, reference_id, uploaded_by, original_name,
                     storage_key, content_type, size_bytes, checksum_sha256)
                VALUES (:id, :kind, :reference_id, :user_id, :name,
                        :key, :content_type, :size, :checksum)
                """
            ),
            {
                "id": attachment_id, "kind": kind, "reference_id": request_id,
                "user_id": user_id, "name": upload.filename or filename,
                "key": storage_key, "content_type": content_type,
                "size": len(data), "checksum": digest,
            },
        )
        results.append({"id": str(attachment_id), "url": f"/{storage_key}"})
    await session.commit()
    return results


async def _schedule_attachment_cleanup(session: AsyncSession, kind: str, request_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE after_sales_attachments
            SET status='PENDING_DELETE', delete_after=NOW() + INTERVAL '30 days'
            WHERE reference_type=:kind AND reference_id=:id AND status='ACTIVE'
            """
        ),
        {"kind": kind, "id": request_id},
    )


async def run_maintenance(session: AsyncSession) -> dict:
    released = await session.execute(
        text(
            """
            UPDATE after_sales_allocations
            SET status='RELEASED', released_at=NOW()
            WHERE status='LOCKED' AND expires_at <= NOW()
            RETURNING reference_type, reference_id
            """
        )
    )
    expired_requests = 0
    for kind, table in (("RETURN", "return_requests"), ("WARRANTY", "warranty_requests")):
        result = await session.execute(
            text(
                f"""
                UPDATE {table}
                SET status='CLOSED_EXPIRED', closed_at=NOW(), updated_at=NOW()
                WHERE status='SUBMITTED' AND created_at <= NOW() - INTERVAL '15 days'
                RETURNING id
                """
            )
        )
        ids = [row.id for row in result]
        expired_requests += len(ids)
        for request_id in ids:
            await _schedule_attachment_cleanup(session, kind, request_id)
    sla = 0
    for table in ("return_requests", "warranty_requests"):
        result = await session.execute(
            text(
                f"""
                UPDATE {table} SET sla_breached_at=NOW(), updated_at=NOW()
                WHERE sla_breached_at IS NULL AND sla_due_at < NOW()
                  AND status NOT IN ('COMPLETED','REJECTED','CANCELLED','CLOSED_EXPIRED')
                RETURNING id
                """
            )
        )
        sla += len(result.all())
    allocated_waiting = 0
    waiting = await session.execute(
        text(
            """
            SELECT kind, id FROM (
                SELECT 'RETURN' kind, id, sla_due_at, qc_approved_at approved_at
                FROM return_requests WHERE status='WAITING_FOR_STOCK'
                UNION ALL
                SELECT 'WARRANTY' kind, id, sla_due_at, replacement_approved_at approved_at
                FROM warranty_requests WHERE status='WAITING_FOR_STOCK'
            ) queue
            ORDER BY (sla_due_at <= NOW()) DESC, sla_due_at ASC NULLS LAST, approved_at ASC NULLS LAST
            """
        )
    )
    for row in waiting:
        locked_request = await after_sales_repo.get_request_for_update(
            session, kind=row.kind, request_id=row.id,
        )
        if not locked_request or locked_request["status"] != "WAITING_FOR_STOCK":
            continue
        items = await after_sales_repo.get_request_items(session, kind=row.kind, request_id=row.id)
        if await after_sales_repo.create_allocations(session, kind=row.kind, request_id=row.id, items=items):
            table = "return_requests" if row.kind == "RETURN" else "warranty_requests"
            next_status = "QC_APPROVED" if row.kind == "RETURN" else "REPLACEMENT_APPROVED"
            await session.execute(
                text(f"UPDATE {table} SET status=:status, updated_at=NOW() WHERE id=:id AND status='WAITING_FOR_STOCK'"),
                {"status": next_status, "id": row.id},
            )
            allocated_waiting += 1
    voucher_notifications = await session.execute(
        text(
            """
            INSERT INTO notifications
                (id, user_id, type, title, message, entity_type, entity_id,
                 action_url, idempotency_key, available_at)
            SELECT gen_random_uuid(), uv.user_id, 'voucher', 'Voucher sắp hết hạn',
                   'Voucher ' || v.code || ' sẽ hết hạn vào ' || to_char(uv.expires_at, 'DD/MM/YYYY') || '.',
                   'VOUCHER', v.id, '/dashboard',
                   'voucher-expiry:' || uv.id::text, NOW()
            FROM user_vouchers uv
            JOIN vouchers v ON v.id=uv.voucher_id
            WHERE uv.status='AVAILABLE'
              AND uv.expires_at > NOW()
              AND uv.expires_at <= NOW() + INTERVAL '3 days'
            ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
            RETURNING id
            """
        )
    )
    deleted_files = 0
    for attachment in await after_sales_repo.cleanup_due_attachments(session):
        try:
            path = Path(attachment["storage_key"])
            if path.exists():
                os.remove(path)
            await after_sales_repo.mark_attachment_deleted(session, attachment["id"])
            deleted_files += 1
        except OSError:
            continue
    await session.commit()
    return {
        "releasedAllocations": len(released.all()),
        "expiredRequests": expired_requests,
        "slaBreaches": sla,
        "allocatedWaitingRequests": allocated_waiting,
        "voucherExpiryNotifications": len(voucher_notifications.all()),
        "deletedAttachments": deleted_files,
    }
