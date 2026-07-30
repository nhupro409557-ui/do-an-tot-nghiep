from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import FlashSalePayload
from app.infrastructure.database.repositories import flash_sale_repo


def sale_price(base_price: float, discount_type: str, discount_value: float) -> float:
    if discount_type == "PERCENT":
        return round(base_price * (1 - discount_value / 100))
    return round(base_price - discount_value)


async def validate_flash_sale_price(session: AsyncSession, payload: FlashSalePayload) -> None:
    row = await flash_sale_repo.get_target_current_price(session, payload.productId, payload.variantId)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm hoặc biến thể hợp lệ.")

    current_price = float(row["current_price"] or 0)
    computed_price = sale_price(current_price, payload.discountType, payload.discountValue)
    if current_price <= 0 or computed_price <= 0 or computed_price >= current_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá flash sale phải lớn hơn 0 và nhỏ hơn giá bán hiện tại của sản phẩm.",
        )


async def validate_flash_sale_quantity(
    session: AsyncSession,
    payload: FlashSalePayload,
    *,
    sale_id: UUID | None = None,
) -> None:
    if payload.quantityLimit is None or sale_id is None or payload.status != "ACTIVE":
        return
    sold_quantity = await flash_sale_repo.get_flash_sale_sold_quantity(session, sale_id)
    if sold_quantity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy flash sale.")
    if sold_quantity >= payload.quantityLimit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số lượng sale phải lớn hơn số lượng đã giữ nếu muốn bật flash sale.",
        )


async def validate_flash_sale_overlap(
    session: AsyncSession,
    payload: FlashSalePayload,
    *,
    exclude_id: UUID | None = None,
) -> None:
    if payload.status != "ACTIVE":
        return
    overlap = await flash_sale_repo.find_overlapping_flash_sale(
        session,
        product_id=payload.productId,
        variant_id=payload.variantId,
        starts_at=payload.startsAt,
        ends_at=payload.endsAt,
        exclude_id=exclude_id,
    )
    if overlap:
        target = "biến thể này" if payload.variantId else "toàn bộ sản phẩm này"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Đã có Flash Sale đang bật cho {target} trong khung thời gian bị trùng. Vui lòng chọn khung giờ khác.",
        )


def raise_flash_sale_integrity_error(error: IntegrityError) -> None:
    original_error = error.orig
    cause = getattr(original_error, "__cause__", None)
    constraint_name = (
        getattr(getattr(original_error, "diag", None), "constraint_name", "")
        or getattr(getattr(cause, "diag", None), "constraint_name", "")
    )
    overlap_constraints = {
        "exclude_overlapping_product_flash_sales",
        "exclude_overlapping_variant_flash_sales",
    }
    if constraint_name in overlap_constraints or any(name in str(error) for name in overlap_constraints):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Khung thời gian Flash Sale bị trùng với một chương trình vừa được lưu. Vui lòng tải lại và chọn khung giờ khác.",
        ) from error
    raise error


def flash_sale_row(row) -> dict:
    item = dict(row._mapping)
    current_price = float(item.get("currentPrice") or 0)
    final_price = sale_price(current_price, item.get("discountType") or "PERCENT", float(item.get("discountValue") or 0))
    quantity_limit = item.get("quantityLimit")
    sold_quantity = int(item.get("soldQuantity") or 0)
    remaining_quantity = None
    if quantity_limit is not None:
        remaining_quantity = max(int(quantity_limit or 0) - sold_quantity, 0)
    quota_exhausted_at = item.get("quotaExhaustedAt")
    return {
        "id": item["id"],
        "productId": item["productId"],
        "variantId": item.get("variantId"),
        "productName": item.get("productName"),
        "productSku": item.get("productSku"),
        "variantSku": item.get("variantSku"),
        "variantName": item.get("variantName"),
        "imageUrl": item.get("imageUrl"),
        "currentPrice": current_price,
        "salePrice": final_price,
        "discountType": item.get("discountType"),
        "discountValue": float(item.get("discountValue") or 0),
        "startsAt": item.get("startsAt").isoformat() if item.get("startsAt") else None,
        "endsAt": item.get("endsAt").isoformat() if item.get("endsAt") else None,
        "quantityLimit": int(quantity_limit) if quantity_limit is not None else None,
        "perUserLimit": int(item["perUserLimit"]) if item.get("perUserLimit") is not None else None,
        "soldQuantity": sold_quantity,
        "remainingQuantity": remaining_quantity,
        "isLimited": quantity_limit is not None,
        "isExhausted": remaining_quantity == 0 if quantity_limit is not None else False,
        "quotaExhaustedAt": quota_exhausted_at.isoformat() if quota_exhausted_at else None,
        "status": item.get("status"),
        "isRunning": bool(item.get("isRunning")),
    }


async def list_flash_sales(session: AsyncSession) -> list[dict]:
    result = await flash_sale_repo.list_flash_sale_rows(session)
    return [flash_sale_row(row) for row in result]


def flash_sale_params(sale_id: UUID, payload: FlashSalePayload) -> dict:
    return {
        "id": sale_id,
        "product_id": payload.productId,
        "variant_id": payload.variantId,
        "discount_type": payload.discountType,
        "discount_value": payload.discountValue,
        "starts_at": payload.startsAt,
        "ends_at": payload.endsAt,
        "quantity_limit": payload.quantityLimit,
        "per_user_limit": payload.perUserLimit,
        "status": payload.status,
    }


async def create_flash_sale(session: AsyncSession, payload: FlashSalePayload) -> dict:
    await validate_flash_sale_price(session, payload)
    await validate_flash_sale_overlap(session, payload)
    sale_id = uuid4()
    try:
        await flash_sale_repo.insert_flash_sale(session, flash_sale_params(sale_id, payload))
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise_flash_sale_integrity_error(error)
    return {"id": str(sale_id)}


async def update_flash_sale(session: AsyncSession, sale_id: UUID, payload: FlashSalePayload) -> dict:
    await validate_flash_sale_price(session, payload)
    await validate_flash_sale_quantity(session, payload, sale_id=sale_id)
    await validate_flash_sale_overlap(session, payload, exclude_id=sale_id)
    try:
        updated = await flash_sale_repo.update_flash_sale(session, flash_sale_params(sale_id, payload))
        if updated == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy flash sale.")
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise_flash_sale_integrity_error(error)
    return {"ok": True}


async def delete_flash_sale(session: AsyncSession, sale_id: UUID) -> dict:
    deleted = await flash_sale_repo.delete_flash_sale(session, sale_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy flash sale.")
    await session.commit()
    return {"ok": True}
