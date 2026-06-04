from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.infrastructure.database.session import get_session


router = APIRouter()


class FlashSalePayload(BaseModel):
    productId: UUID
    discountType: str = Field(default="PERCENT")
    discountValue: float = Field(gt=0)
    startsAt: datetime | None = None
    endsAt: datetime | None = None
    status: str = Field(default="ACTIVE")

    @model_validator(mode="after")
    def validate_window(self):
        if self.endsAt and self.startsAt and self.endsAt <= self.startsAt:
            raise ValueError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu.")
        self.discountType = self.discountType.upper()
        if self.discountType not in {"FIXED", "PERCENT"}:
            raise ValueError("Kiểu giảm giá không hợp lệ.")
        if self.discountType == "PERCENT" and self.discountValue >= 100:
            raise ValueError("Giảm theo phần trăm phải nhỏ hơn 100%.")
        self.status = self.status.upper()
        if self.status not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("Trạng thái flash sale không hợp lệ.")
        return self


def sale_price(base_price: float, discount_type: str, discount_value: float) -> float:
    if discount_type == "PERCENT":
        return round(base_price * (1 - discount_value / 100))
    return round(base_price - discount_value)


async def validate_flash_sale_price(session: AsyncSession, payload: FlashSalePayload) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id,
                    COALESCE(NULLIF(sale_price, 0), price, 0) AS current_price
                FROM products
                WHERE id = :product_id AND deleted_at IS NULL
                """
            ),
            {"product_id": payload.productId},
        )
    ).mappings().first()
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


@router.get("/flash-sales", dependencies=[Depends(require_permission("product:read"))])
async def list_flash_sales(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                fs.id::text AS id,
                fs.product_id::text AS "productId",
                p.name AS "productName",
                p.sku AS "productSku",
                p.image_url AS "imageUrl",
                COALESCE(NULLIF(p.sale_price, 0), p.price, 0) AS "currentPrice",
                fs.discount_type AS "discountType",
                fs.discount_value AS "discountValue",
                fs.starts_at AS "startsAt",
                fs.ends_at AS "endsAt",
                fs.status,
                (
                    fs.status = 'ACTIVE'
                    AND (fs.starts_at IS NULL OR fs.starts_at <= NOW())
                    AND (fs.ends_at IS NULL OR fs.ends_at >= NOW())
                ) AS "isRunning"
            FROM flash_sales fs
            JOIN products p ON p.id = fs.product_id
            WHERE p.deleted_at IS NULL
            ORDER BY "isRunning" DESC, fs.updated_at DESC
            """
        )
    )
    return [flash_sale_row(row) for row in result]


@router.post("/flash-sales", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("product:update"))])
async def create_flash_sale(payload: FlashSalePayload, session: AsyncSession = Depends(get_session)) -> dict:
    await validate_flash_sale_price(session, payload)
    sale_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO flash_sales (id, product_id, discount_type, discount_value, starts_at, ends_at, status)
            VALUES (:id, :product_id, :discount_type, :discount_value, :starts_at, :ends_at, :status)
            """
        ),
        {
            "id": sale_id,
            "product_id": payload.productId,
            "discount_type": payload.discountType,
            "discount_value": payload.discountValue,
            "starts_at": payload.startsAt,
            "ends_at": payload.endsAt,
            "status": payload.status,
        },
    )
    await session.commit()
    return {"id": str(sale_id)}


@router.patch("/flash-sales/{sale_id}", dependencies=[Depends(require_permission("product:update"))])
async def update_flash_sale(sale_id: UUID, payload: FlashSalePayload, session: AsyncSession = Depends(get_session)) -> dict:
    await validate_flash_sale_price(session, payload)
    result = await session.execute(
        text(
            """
            UPDATE flash_sales
            SET product_id = :product_id,
                discount_type = :discount_type,
                discount_value = :discount_value,
                starts_at = :starts_at,
                ends_at = :ends_at,
                status = :status,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": sale_id,
            "product_id": payload.productId,
            "discount_type": payload.discountType,
            "discount_value": payload.discountValue,
            "starts_at": payload.startsAt,
            "ends_at": payload.endsAt,
            "status": payload.status,
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy flash sale.")
    await session.commit()
    return {"ok": True}


@router.delete("/flash-sales/{sale_id}", dependencies=[Depends(require_permission("product:update"))])
async def delete_flash_sale(sale_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("DELETE FROM flash_sales WHERE id = :id"), {"id": sale_id})
    await session.commit()
    return {"ok": True}
