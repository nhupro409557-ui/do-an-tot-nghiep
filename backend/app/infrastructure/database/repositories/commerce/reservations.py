from datetime import datetime
from decimal import Decimal
import json
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AIContextLog,
    LoyaltyTransaction,
    Order,
    OrderHistoryLog,
    OrderItem,
    PaymentTransaction,
    Product,
    User,
    UserVoucher,
    Voucher,
)


async def get_order_by_idempotency_key(session: AsyncSession, idempotency_key: str) -> Order | None:
    return await session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))


async def get_user_for_update(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id).with_for_update())


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id))


async def list_product_categories(session: AsyncSession, product_ids: list[UUID]) -> list:
    result = await session.execute(
        select(Product.id, Product.category_id, Product.subcategory_id, Product.brand_id).where(Product.id.in_(product_ids))
    )
    return list(result)


async def get_variant_inventory_for_update(
    session: AsyncSession,
    *,
    variant_id: UUID,
    product_id: UUID | None,
    for_update: bool = True,
) -> dict | None:
    lock_clause = "FOR UPDATE OF pv, p" if for_update else ""
    row = (
        await session.execute(
            text(
                f"""
                SELECT
                    pv.id,
                    pv.product_id,
                    pv.stock_quantity,
                    p.name AS product_name,
                    pv.color_name,
                    pv.storage,
                    pv.ram,
                    pv.configuration,
                    p.category_id,
                    p.subcategory_id,
                    p.brand_id,
                    GREATEST(COALESCE(p.warranty_period, 0), 0) AS warranty_months_snapshot,
                    COALESCE(NULLIF(pv.sale_price, 0), NULLIF(pv.price, 0), NULLIF(p.sale_price, 0), p.price, 0) AS regular_unit_price,
                    COALESCE(vfs.id, fs.id)::text AS flash_sale_id,
                    COALESCE(vfs.discount_type, fs.discount_type) AS flash_sale_discount_type,
                    COALESCE(vfs.discount_value, fs.discount_value) AS flash_sale_discount_value,
                    COALESCE(vfs.quantity_limit, fs.quantity_limit) AS flash_sale_quantity_limit,
                    COALESCE(vfs.sold_quantity, fs.sold_quantity) AS flash_sale_sold_quantity,
                    CASE
                        WHEN COALESCE(vfs.quantity_limit, fs.quantity_limit) IS NULL THEN NULL
                        ELSE GREATEST(COALESCE(vfs.quantity_limit, fs.quantity_limit) - COALESCE(vfs.sold_quantity, fs.sold_quantity), 0)
                    END AS flash_sale_remaining_quantity
                FROM product_variants pv
                JOIN products p ON p.id = pv.product_id
                LEFT JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN LATERAL (
                    SELECT id, discount_type, discount_value, quantity_limit, sold_quantity
                    FROM flash_sales
                    WHERE product_id = p.id
                      AND variant_id = pv.id
                      AND status = 'ACTIVE'
                      AND (starts_at IS NULL OR starts_at <= NOW())
                      AND (ends_at IS NULL OR ends_at >= NOW())
                      AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
                    ORDER BY updated_at DESC
                    LIMIT 1
                ) vfs ON TRUE
                LEFT JOIN LATERAL (
                    SELECT id, discount_type, discount_value, quantity_limit, sold_quantity
                    FROM flash_sales
                    WHERE product_id = p.id
                      AND variant_id IS NULL
                      AND status = 'ACTIVE'
                      AND (starts_at IS NULL OR starts_at <= NOW())
                      AND (ends_at IS NULL OR ends_at >= NOW())
                      AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
                    ORDER BY updated_at DESC
                    LIMIT 1
                ) fs ON TRUE
                WHERE pv.id = CAST(:variant_id AS uuid)
                  AND (CAST(:product_id AS uuid) IS NULL OR pv.product_id = CAST(:product_id AS uuid))
                  AND pv.is_active = TRUE
                  AND pv.deleted_at IS NULL
                  AND LOWER(COALESCE(pv.status, 'active')) = 'active'
                  AND p.status = 'ACTIVE'
                  AND p.deleted_at IS NULL
                  AND COALESCE(p.hidden_by_category, FALSE) = FALSE
                  AND COALESCE(p.hidden_by_brand, FALSE) = FALSE
                  AND (c.id IS NULL OR (c.status = 'ACTIVE' AND COALESCE(c.is_active, TRUE) = TRUE AND COALESCE(c.is_deleted, FALSE) = FALSE))
                  AND (b.id IS NULL OR COALESCE(b.is_active, TRUE) = TRUE)
                {lock_clause}
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_inventory_for_update(
    session: AsyncSession,
    product_id: UUID,
    *,
    for_update: bool = True,
) -> dict | None:
    lock_clause = "FOR UPDATE OF p" if for_update else ""
    row = (
        await session.execute(
            text(
                f"""
                SELECT
                    p.id,
                    p.stock_quantity,
                    p.name AS product_name,
                    p.category_id,
                    p.subcategory_id,
                    p.brand_id,
                    GREATEST(COALESCE(p.warranty_period, 0), 0) AS warranty_months_snapshot,
                    COALESCE(NULLIF(p.sale_price, 0), p.price, 0) AS regular_unit_price,
                    fs.id::text AS flash_sale_id,
                    fs.discount_type AS flash_sale_discount_type,
                    fs.discount_value AS flash_sale_discount_value,
                    fs.quantity_limit AS flash_sale_quantity_limit,
                    fs.sold_quantity AS flash_sale_sold_quantity,
                    CASE
                        WHEN fs.quantity_limit IS NULL THEN NULL
                        ELSE GREATEST(fs.quantity_limit - fs.sold_quantity, 0)
                    END AS flash_sale_remaining_quantity
                FROM products p
                LEFT JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN LATERAL (
                    SELECT id, discount_type, discount_value, quantity_limit, sold_quantity
                    FROM flash_sales
                    WHERE product_id = p.id
                      AND variant_id IS NULL
                      AND status = 'ACTIVE'
                      AND (starts_at IS NULL OR starts_at <= NOW())
                      AND (ends_at IS NULL OR ends_at >= NOW())
                      AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
                    ORDER BY updated_at DESC
                    LIMIT 1
                ) fs ON TRUE
                WHERE p.id = :product_id
                  AND p.status = 'ACTIVE'
                  AND p.deleted_at IS NULL
                  AND COALESCE(p.hidden_by_category, FALSE) = FALSE
                  AND COALESCE(p.hidden_by_brand, FALSE) = FALSE
                  AND (c.id IS NULL OR (c.status = 'ACTIVE' AND COALESCE(c.is_active, TRUE) = TRUE AND COALESCE(c.is_deleted, FALSE) = FALSE))
                  AND (b.id IS NULL OR COALESCE(b.is_active, TRUE) = TRUE)
                {lock_clause}
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": variant_id, "quantity": quantity},
    )


async def update_product_stock(session: AsyncSession, *, product_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "quantity": quantity},
    )


async def get_active_reserved_quantity(
    session: AsyncSession,
    *,
    product_id: UUID | None,
    variant_id: UUID | None,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(reserved_quantity), 0)::int
            FROM inventory_reservations
            WHERE status = 'ACTIVE'
              AND (expires_at IS NULL OR expires_at > NOW())
              AND product_id IS NOT DISTINCT FROM :product_id
              AND variant_id IS NOT DISTINCT FROM :variant_id
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    return int(result.scalar() or 0)


async def get_main_inventory_location_id(session: AsyncSession) -> UUID:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM inventory_locations
            WHERE code = 'MAIN'
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
    )
    location_id = result.scalar_one_or_none()
    if location_id:
        return location_id

    new_location_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO inventory_locations (id, code, name, type, is_active)
            VALUES (:id, 'MAIN', 'Kho chính', 'WAREHOUSE', TRUE)
            """
        ),
        {"id": new_location_id},
    )
    return new_location_id


async def create_inventory_reservation(
    session: AsyncSession,
    *,
    order_id: UUID,
    order_code: str,
    product_id: UUID | None,
    variant_id: UUID | None,
    quantity: int,
) -> None:
    location_id = await get_main_inventory_location_id(session)
    reservation_code = f"ORDER-{order_code}-{variant_id or product_id}"
    await session.execute(
        text(
            """
            INSERT INTO inventory_reservations (
                id, product_id, variant_id, location_id, order_id,
                reservation_code, reserved_quantity, status, expires_at
            )
            VALUES (
                :id, :product_id, :variant_id, :location_id, :order_id,
                :reservation_code, :reserved_quantity, 'ACTIVE', NOW() + INTERVAL '24 hours'
            )
            ON CONFLICT (reservation_code) DO UPDATE
            SET reserved_quantity = EXCLUDED.reserved_quantity,
                status = 'ACTIVE',
                expires_at = EXCLUDED.expires_at,
                released_at = NULL
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "order_id": order_id,
            "reservation_code": reservation_code,
            "reserved_quantity": quantity,
        },
    )


async def close_active_order_reservations(session: AsyncSession, *, order_id: UUID, status: str) -> None:
    if status not in {"CONSUMED", "RELEASED", "EXPIRED", "CANCELLED"}:
        return
    await session.execute(
        text(
            """
            UPDATE inventory_reservations
            SET status = :status,
                released_at = NOW()
            WHERE order_id = :order_id
              AND status = 'ACTIVE'
            """
        ),
        {"order_id": order_id, "status": status},
    )


async def order_has_inventory_adjustment_reason(
    session: AsyncSession,
    *,
    order_code: str,
    reason: str,
) -> bool:
    result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM inventory_adjustment_logs
                WHERE reference_code = :order_code
                  AND reason = :reason
            )
            """
        ),
        {"order_code": order_code, "reason": reason},
    )
    return bool(result.scalar())


async def insert_inventory_adjustment(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    old_quantity: int,
    new_quantity: int,
    delta: int,
    transaction_type: str,
    reference_code: str,
    reason: str,
    note: str,
    location_code: str | None = None,
    location_name: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs (
                id, product_id, variant_id, old_quantity, new_quantity, delta,
                transaction_type, reference_code, reason, note, location_code, location_name
            )
            VALUES (
                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta,
                :transaction_type, :reference_code, :reason, :note, :location_code, :location_name
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": variant_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
            "transaction_type": transaction_type,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "location_code": location_code,
            "location_name": location_name,
        },
    )
