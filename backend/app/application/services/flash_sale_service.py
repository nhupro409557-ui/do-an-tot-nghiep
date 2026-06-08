from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import FlashSalePayload
from app.infrastructure.database.repositories import flash_sale_repo


def sale_price(base_price: float, discount_type: str, discount_value: float) -> float:
    if discount_type == "PERCENT":
        return round(base_price * (1 - discount_value / 100))
    return round(base_price - discount_value)


async def validate_flash_sale_price(session: AsyncSession, payload: FlashSalePayload) -> None:
    row = await flash_sale_repo.get_product_current_price(session, payload.productId)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm.")

    current_price = float(row["current_price"] or 0)
    computed_price = sale_price(current_price, payload.discountType, payload.discountValue)
    if current_price <= 0 or computed_price <= 0 or computed_price >= current_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giá flash sale phải lớn hơn 0 và nhỏ hơn giá bán hiện tại của sản phẩm.",
        )


def flash_sale_row(row) -> dict:
    item = dict(row._mapping)
    current_price = float(item.get("currentPrice") or 0)
    final_price = sale_price(current_price, item.get("discountType") or "PERCENT", float(item.get("discountValue") or 0))
    return {
        "id": item["id"],
        "productId": item["productId"],
        "productName": item.get("productName"),
        "productSku": item.get("productSku"),
        "imageUrl": item.get("imageUrl"),
        "currentPrice": current_price,
        "salePrice": final_price,
        "discountType": item.get("discountType"),
        "discountValue": float(item.get("discountValue") or 0),
        "startsAt": item.get("startsAt").isoformat() if item.get("startsAt") else None,
        "endsAt": item.get("endsAt").isoformat() if item.get("endsAt") else None,
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
        "discount_type": payload.discountType,
        "discount_value": payload.discountValue,
        "starts_at": payload.startsAt,
        "ends_at": payload.endsAt,
        "status": payload.status,
    }


async def create_flash_sale(session: AsyncSession, payload: FlashSalePayload) -> dict:
    await validate_flash_sale_price(session, payload)
    sale_id = uuid4()
    await flash_sale_repo.insert_flash_sale(session, flash_sale_params(sale_id, payload))
    await session.commit()
    return {"id": str(sale_id)}


async def update_flash_sale(session: AsyncSession, sale_id: UUID, payload: FlashSalePayload) -> dict:
    await validate_flash_sale_price(session, payload)
    updated = await flash_sale_repo.update_flash_sale(session, flash_sale_params(sale_id, payload))
    if updated == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy flash sale.")
    await session.commit()
    return {"ok": True}


async def delete_flash_sale(session: AsyncSession, sale_id: UUID) -> dict:
    deleted = await flash_sale_repo.delete_flash_sale(session, sale_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy flash sale.")
    await session.commit()
    return {"ok": True}
