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


async def consume_inventory_lots_fifo(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    quantity: int,
    reference_code: str,
    order_id: UUID,
) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, lot_code, remaining_quantity
                FROM inventory_lots
                WHERE (
                        (CAST(:variant_id AS uuid) IS NULL AND product_id = CAST(:product_id AS uuid) AND variant_id IS NULL)
                     OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = CAST(:variant_id AS uuid))
                  )
                  AND location_id = :location_id
                  AND status = 'ACTIVE'
                  AND remaining_quantity > 0
                ORDER BY received_at ASC, created_at ASC, lot_code ASC
                FOR UPDATE
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
            },
        )
    ).mappings().all()

    remaining = quantity
    consumed: list[dict] = []
    for row in rows:
        if remaining <= 0:
            break
        take_quantity = min(remaining, int(row["remaining_quantity"] or 0))
        if take_quantity <= 0:
            continue
        new_remaining = int(row["remaining_quantity"] or 0) - take_quantity
        await session.execute(
            text(
                """
                UPDATE inventory_lots
                SET remaining_quantity = :remaining_quantity,
                    status = CASE WHEN :remaining_quantity = 0 THEN 'DEPLETED' ELSE 'ACTIVE' END,
                    updated_at = NOW()
                WHERE id = :lot_id
                """
            ),
            {"lot_id": row["id"], "remaining_quantity": new_remaining},
        )
        await session.execute(
            text(
                """
                INSERT INTO inventory_lot_movements (
                    id, lot_id, movement_type, quantity,
                    reference_code, order_id, note
                )
                VALUES (
                    :id, :lot_id, 'SALE', :quantity,
                    :reference_code, :order_id, 'Tự động xuất lô cũ trước khi giao hàng.'
                )
                """
            ),
            {
                "id": uuid4(),
                "lot_id": row["id"],
                "quantity": take_quantity,
                "reference_code": reference_code,
                "order_id": order_id,
            },
        )
        consumed.append(
            {
                "lotId": row["id"],
                "lotCode": row["lot_code"],
                "quantity": take_quantity,
            }
        )
        remaining -= take_quantity

    if remaining > 0:
        raise ValueError("Không đủ tồn kho khả dụng ở các kệ để xuất kho.")


async def deduct_inventory_levels_fifo(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    quantity: int,
) -> list[dict]:
    if quantity <= 0:
        return []

    rows = (
        await session.execute(
            text(
                """
                SELECT
                    il.id,
                    il.location_id,
                    loc.code AS "locationCode",
                    loc.name AS "locationName",
                    il.on_hand_quantity::int AS "onHandQuantity",
                    il.reserved_quantity::int AS "reservedQuantity",
                    GREATEST(il.on_hand_quantity - il.reserved_quantity, 0)::int AS "availableQuantity",
                    (
                        SELECT MIN(lot.received_at)
                        FROM inventory_lots lot
                        WHERE lot.product_id = :product_id
                          AND lot.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                          AND lot.location_id = il.location_id
                          AND lot.status = 'ACTIVE'
                          AND lot.remaining_quantity > 0
                    ) AS "oldestLotReceivedAt"
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                WHERE (
                        (CAST(:variant_id AS uuid) IS NULL AND il.product_id = :product_id AND il.variant_id IS NULL)
                     OR (CAST(:variant_id AS uuid) IS NOT NULL AND il.variant_id = CAST(:variant_id AS uuid))
                  )
                  AND GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0
                ORDER BY "oldestLotReceivedAt" ASC NULLS LAST, il.updated_at ASC, loc.code ASC
                FOR UPDATE OF il
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
            },
        )
    ).mappings().all()

    remaining = quantity
    allocations: list[dict] = []
    for row in rows:
        if remaining <= 0:
            break

        available = int(row["availableQuantity"] or 0)
        if available <= 0:
            continue

        take = min(remaining, available)
        old_quantity = int(row["onHandQuantity"] or 0)
        new_quantity = old_quantity - take
        await session.execute(
            text(
                """
                UPDATE inventory_levels
                SET on_hand_quantity = :new_quantity,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "new_quantity": new_quantity,
            },
        )
        allocations.append(
            {
                "locationId": row["location_id"],
                "locationCode": row["locationCode"],
                "locationName": row["locationName"],
                "oldQuantity": old_quantity,
                "newQuantity": new_quantity,
                "quantity": take,
            }
        )
        remaining -= take

    if remaining > 0:
        raise ValueError("Không đủ tồn kho khả dụng ở các kệ để xuất kho.")

    return allocations


async def deduct_inventory_levels_from_locations(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_quantities: list[dict],
) -> list[dict]:
    allocations: list[dict] = []
    for location_quantity in location_quantities:
        location_id = location_quantity.get("location_id") or location_quantity.get("locationId")
        quantity = int(location_quantity.get("quantity") or 0)
        if not location_id or quantity <= 0:
            continue

        if variant_id is None:
            # Fetch all levels at this location for this product
            result = await session.execute(
                text(
                    """
                    SELECT
                        il.id,
                        il.location_id,
                        il.variant_id,
                        loc.code AS "locationCode",
                        loc.name AS "locationName",
                        il.on_hand_quantity::int AS "onHandQuantity",
                        il.reserved_quantity::int AS "reservedQuantity",
                        GREATEST(il.on_hand_quantity - il.reserved_quantity, 0)::int AS "availableQuantity"
                    FROM inventory_levels il
                    JOIN inventory_locations loc ON loc.id = il.location_id
                    WHERE il.product_id = :product_id
                      AND il.location_id = :location_id
                    FOR UPDATE OF il
                    """
                ),
                {
                    "product_id": product_id,
                    "location_id": location_id,
                },
            )
            rows = [dict(r) for r in result.mappings().all()]
            if not rows:
                raise ValueError("Kệ nhân viên chọn không đủ tồn khả dụng để xuất kho.")

            total_available = sum(row["availableQuantity"] for row in rows)
            if total_available < quantity:
                raise ValueError("Kệ nhân viên chọn không đủ tồn khả dụng để xuất kho.")

            remaining_to_deduct = quantity
            # Sort rows by availableQuantity descending to deduct from the largest stock first
            rows.sort(key=lambda r: r["availableQuantity"], reverse=True)

            for row in rows:
                if remaining_to_deduct <= 0:
                    break
                available = row["availableQuantity"]
                if available <= 0:
                    continue

                take = min(remaining_to_deduct, available)
                old_quantity = row["onHandQuantity"]
                new_quantity = old_quantity - take

                await session.execute(
                    text(
                        """
                        UPDATE inventory_levels
                        SET on_hand_quantity = :new_quantity,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": row["id"], "new_quantity": new_quantity},
                )

                if row.get("variant_id"):
                    # Update variant stock in product_variants table
                    v_row = await session.execute(
                        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id FOR UPDATE"),
                        {"variant_id": row["variant_id"]}
                    )
                    v_stock = v_row.scalar()
                    if v_stock is not None:
                        new_v_stock = max(0, v_stock - take)
                        await session.execute(
                            text("UPDATE product_variants SET stock_quantity = :qty, updated_at = NOW() WHERE id = :variant_id"),
                            {"qty": new_v_stock, "variant_id": row["variant_id"]}
                        )

                allocations.append(
                    {
                        "locationId": row["location_id"],
                        "locationCode": row["locationCode"],
                        "locationName": row["locationName"],
                        "oldQuantity": old_quantity,
                        "newQuantity": new_quantity,
                        "quantity": take,
                    }
                )
                remaining_to_deduct -= take

            if remaining_to_deduct > 0:
                raise ValueError("Kệ nhân viên chọn không đủ tồn khả dụng để xuất kho.")
        else:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT
                            il.id,
                            il.location_id,
                            loc.code AS "locationCode",
                            loc.name AS "locationName",
                            il.on_hand_quantity::int AS "onHandQuantity",
                            il.reserved_quantity::int AS "reservedQuantity",
                            GREATEST(il.on_hand_quantity - il.reserved_quantity, 0)::int AS "availableQuantity"
                        FROM inventory_levels il
                        JOIN inventory_locations loc ON loc.id = il.location_id
                        WHERE il.variant_id = CAST(:variant_id AS UUID)
                          AND il.location_id = :location_id
                        FOR UPDATE OF il
                        """
                    ),
                    {
                        "variant_id": variant_id,
                        "location_id": location_id,
                    },
                )
            ).mappings().first()
            if not row or int(row["availableQuantity"] or 0) < quantity:
                raise ValueError("Kệ nhân viên chọn không đủ tồn khả dụng để xuất kho.")

            old_quantity = int(row["onHandQuantity"] or 0)
            new_quantity = old_quantity - quantity
            await session.execute(
                text(
                    """
                    UPDATE inventory_levels
                    SET on_hand_quantity = :new_quantity,
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": row["id"], "new_quantity": new_quantity},
            )
            allocations.append(
                {
                    "locationId": row["location_id"],
                    "locationCode": row["locationCode"],
                    "locationName": row["locationName"],
                    "oldQuantity": old_quantity,
                    "newQuantity": new_quantity,
                    "quantity": quantity,
                }
            )
    return allocations


async def restock_inventory_levels(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    allocations: list[dict],
) -> None:
    for allocation in allocations:
        location_id = allocation.get("locationId")
        quantity = int(allocation.get("quantity") or 0)
        if not location_id or quantity <= 0:
            continue
        await session.execute(
            text(
                """
                WITH updated AS (
                    UPDATE inventory_levels
                    SET on_hand_quantity = on_hand_quantity + :quantity,
                        updated_at = NOW()
                    WHERE (
                            (:variant_id_marker = 'BASE' AND product_id = :product_id AND variant_id IS NULL)
                         OR (:variant_id_marker = 'VALUE' AND variant_id = CAST(:variant_id AS UUID))
                      )
                      AND location_id = :location_id
                    RETURNING id
                )
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
                )
                SELECT
                    gen_random_uuid(),
                    CASE WHEN :variant_id_marker = 'BASE' THEN :product_id ELSE NULL END,
                    CASE WHEN :variant_id_marker = 'VALUE' THEN CAST(:variant_id AS UUID) ELSE NULL END,
                    :location_id,
                    :quantity,
                    0,
                    0
                WHERE NOT EXISTS (SELECT 1 FROM updated)
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "variant_id_marker": "VALUE" if variant_id else "BASE",
                "location_id": location_id,
                "quantity": quantity,
            },
        )
