from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin.purchase_order import PurchaseOrderPayload, PurchaseOrderStatusPayload
from app.infrastructure.database.repositories import purchase_order_repo, supplier_repo


async def list_purchase_orders(session: AsyncSession, search: str = "", status: str = "") -> list[dict]:
    rows = await purchase_order_repo.list_purchase_orders(session, search.strip(), status.strip().upper())
    for row in rows:
        row["totalAmount"] = float(row.get("subtotal") or 0) - float(row.get("discountAmount") or 0) + float(row.get("shippingFee") or 0)
    return rows


async def get_purchase_order(session: AsyncSession, order_id: UUID) -> dict:
    order = await purchase_order_repo.get_purchase_order(session, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn mua hàng.")
    return order


async def create_purchase_order(
    session: AsyncSession, payload: PurchaseOrderPayload, current_user_id: UUID | None
) -> dict:
    code = payload.code.strip().upper()
    if not await supplier_repo.supplier_exists(session, payload.supplierId):
        raise HTTPException(status_code=400, detail="Nhà cung cấp không tồn tại hoặc đã ngừng hoạt động.")
    seen: set[tuple[str, str]] = set()
    lines = []
    subtotal = 0.0
    order_id = uuid4()
    for index, line in enumerate(payload.lines, start=1):
        key = (str(line.productId), str(line.variantId or ""))
        if key in seen:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng.")
        seen.add(key)
        subtotal += line.quantity * line.unitCost
        lines.append({
            "id": uuid4(), "purchase_order_id": order_id, "product_id": line.productId,
            "variant_id": line.variantId, "quantity": line.quantity, "unit_cost": line.unitCost,
            "note": (line.note or "").strip() or None,
        })
    if payload.discountAmount > subtotal:
        raise HTTPException(status_code=400, detail="Chiết khấu không được lớn hơn tiền hàng.")
    try:
        await purchase_order_repo.insert_purchase_order(session, {
            "id": order_id, "code": code, "supplier_id": payload.supplierId,
            "expected_date": payload.expectedDate, "note": (payload.note or "").strip() or None,
            "discount_amount": payload.discountAmount, "shipping_fee": payload.shippingFee,
            "created_by": current_user_id,
        }, lines)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if "purchase_orders_code_key" in str(exc) or "duplicate key" in str(exc).lower():
            raise HTTPException(status_code=409, detail="Mã đơn mua hàng đã tồn tại.") from exc
        raise
    return await get_purchase_order(session, order_id)


async def update_purchase_order(
    session: AsyncSession, order_id: UUID, payload: PurchaseOrderPayload, current_user_id: UUID | None
) -> dict:
    order = await purchase_order_repo.get_purchase_order(session, order_id, for_update=True)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn mua hàng.")
    if order["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ được sửa đơn mua hàng ở trạng thái Nháp.")
    if payload.code.strip().upper() != str(order["code"]).upper():
        raise HTTPException(status_code=400, detail="Không được đổi mã đơn mua hàng.")
    if not await supplier_repo.supplier_exists(session, payload.supplierId):
        raise HTTPException(status_code=400, detail="Nhà cung cấp không tồn tại hoặc đã ngừng hoạt động.")
    seen: set[tuple[str, str]] = set()
    subtotal = 0.0
    lines = []
    for index, line in enumerate(payload.lines, start=1):
        key = (str(line.productId), str(line.variantId or ""))
        if key in seen:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng.")
        seen.add(key)
        subtotal += line.quantity * line.unitCost
        lines.append({"id": uuid4(), "purchase_order_id": order_id, "product_id": line.productId,
                      "variant_id": line.variantId, "quantity": line.quantity, "unit_cost": line.unitCost,
                      "note": (line.note or "").strip() or None})
    if payload.discountAmount > subtotal:
        raise HTTPException(status_code=400, detail="Chiết khấu không được lớn hơn tiền hàng.")
    await purchase_order_repo.replace_purchase_order(session, order_id, {
        "supplier_id": payload.supplierId, "expected_date": payload.expectedDate,
        "note": (payload.note or "").strip() or None, "discount_amount": payload.discountAmount,
        "shipping_fee": payload.shippingFee,
    }, lines)
    await session.commit()
    return await get_purchase_order(session, order_id)


async def update_purchase_order_status(
    session: AsyncSession, order_id: UUID, payload: PurchaseOrderStatusPayload,
    current_user_id: UUID | None, current_role_code: str | None,
) -> dict:
    order = await purchase_order_repo.get_purchase_order(session, order_id, for_update=True)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn mua hàng.")
    target = payload.status
    allowed = {
        "DRAFT": {"PENDING_APPROVAL", "CANCELLED"},
        "PENDING_APPROVAL": {"APPROVED", "CANCELLED"},
        "APPROVED": {"CANCELLED"},
    }.get(str(order["status"]), set())
    if target not in allowed:
        raise HTTPException(status_code=400, detail=f"Không thể chuyển đơn mua từ {order['status']} sang {target}.")
    if target in {"APPROVED", "CANCELLED"} and str(current_role_code or "").upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Super Admin được duyệt hoặc hủy đơn mua hàng.")
    if (
        target == "APPROVED"
        and str(current_role_code or "").upper() != "SUPER_ADMIN"
        and str(order.get("createdBy")) == str(current_user_id)
    ):
        raise HTTPException(status_code=403, detail="Người lập không được tự duyệt đơn mua hàng.")
    await purchase_order_repo.update_purchase_order_status(session, order_id, target, current_user_id, payload.note)
    await session.commit()
    return await get_purchase_order(session, order_id)
