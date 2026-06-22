from datetime import datetime
from decimal import Decimal
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


async def get_database_now(session: AsyncSession) -> datetime:
    result = await session.execute(text("SELECT NOW()"))
    return result.scalar_one()


async def get_user_created_at(session: AsyncSession, user_id: UUID) -> datetime | None:
    result = await session.execute(select(User.created_at).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_voucher_by_id(session: AsyncSession, voucher_id: UUID) -> Voucher | None:
    return await session.scalar(select(Voucher).where(Voucher.id == voucher_id))


async def get_active_voucher(session: AsyncSession, code: str) -> Voucher | None:
    result = await session.execute(
        select(Voucher).where(Voucher.code == code.upper()).where(Voucher.status == "ACTIVE")
    )
    return result.scalar_one_or_none()


async def get_active_voucher_for_update(session: AsyncSession, code: str) -> Voucher | None:
    return await session.scalar(
        select(Voucher)
        .where(Voucher.code == code.upper())
        .where(Voucher.status == "ACTIVE")
        .with_for_update()
    )


async def get_voucher_by_order_code_for_update(session: AsyncSession, voucher_code: str) -> Voucher | None:
    return await session.scalar(select(Voucher).where(Voucher.code == voucher_code.upper()).with_for_update())


async def get_existing_user_voucher(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
    return await session.scalar(
        select(UserVoucher)
        .where(UserVoucher.user_id == user_id)
        .where(UserVoucher.voucher_id == voucher_id)
        .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED", "USED"]))
    )


async def add_user_voucher(session: AsyncSession, wallet_voucher: UserVoucher) -> None:
    session.add(wallet_voucher)
    await session.flush()


async def list_user_vouchers_with_voucher(session: AsyncSession, user_id: UUID) -> list[tuple[UserVoucher, Voucher]]:
    result = await session.execute(
        select(UserVoucher, Voucher)
        .join(Voucher, Voucher.id == UserVoucher.voucher_id)
        .where(UserVoucher.user_id == user_id)
        .order_by(UserVoucher.claimed_at.desc())
    )
    return list(result.all())


async def get_claimed_voucher(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
    result = await session.execute(
        select(UserVoucher)
        .where(UserVoucher.user_id == user_id)
        .where(UserVoucher.voucher_id == voucher_id)
        .order_by(UserVoucher.claimed_at.desc())
    )
    return result.scalar_one_or_none()


async def get_claimed_voucher_for_update(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
    return await session.scalar(
        select(UserVoucher)
        .where(UserVoucher.user_id == user_id)
        .where(UserVoucher.voucher_id == voucher_id)
        .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED"]))
        .order_by(UserVoucher.claimed_at.desc())
        .with_for_update()
    )


async def get_user_voucher_for_update(session: AsyncSession, wallet_voucher_id: UUID) -> UserVoucher | None:
    return await session.scalar(select(UserVoucher).where(UserVoucher.id == wallet_voucher_id).with_for_update())


def save_model(session: AsyncSession, item) -> None:
    session.add(item)


async def count_user_orders(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(text("SELECT COUNT(*) FROM orders WHERE user_id = :user_id"), {"user_id": user_id})
    return int(result.scalar() or 0)


async def count_user_voucher_usage(session: AsyncSession, *, user_id: UUID, code: str) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM orders WHERE user_id = :user_id AND voucher_code = :code"),
        {"user_id": user_id, "code": code.upper()},
    )
    return int(result.scalar() or 0)


async def count_voucher_usage_by_identity(session: AsyncSession, *, column: str, value: str, code: str) -> int:
    if column not in {"voucher_device_id", "voucher_ip_address"}:
        return 0
    result = await session.execute(
        text(f"SELECT COUNT(*) FROM orders WHERE voucher_code = :code AND {column} = :value"),
        {"code": code.upper(), "value": value},
    )
    return int(result.scalar() or 0)


async def get_order_by_idempotency_key(session: AsyncSession, idempotency_key: str) -> Order | None:
    return await session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))


async def get_user_for_update(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id).with_for_update())


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id))


async def list_product_categories(session: AsyncSession, product_ids: list[UUID]) -> list:
    result = await session.execute(
        select(Product.id, Product.category_id, Product.subcategory_id).where(Product.id.in_(product_ids))
    )
    return list(result)


async def get_variant_inventory_for_update(
    session: AsyncSession,
    *,
    variant_id: UUID,
    product_id: UUID | None,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, product_id, stock_quantity
                FROM product_variants
                WHERE id = :variant_id
                  AND (:product_id IS NULL OR product_id = :product_id)
                  AND is_active = TRUE
                FOR UPDATE
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_inventory_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity
                FROM products
                WHERE id = :product_id AND status = 'ACTIVE'
                FOR UPDATE
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
                        (:variant_id_marker = 'BASE' AND product_id = :product_id AND variant_id IS NULL)
                     OR (:variant_id_marker = 'VALUE' AND variant_id = CAST(:variant_id AS UUID))
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
                "variant_id_marker": "VALUE" if variant_id else "BASE",
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
        raise ValueError("Không đủ số lượng lô nội bộ tại kệ để xuất kho.")
    return consumed


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
                    GREATEST(il.on_hand_quantity - il.reserved_quantity, 0)::int AS "availableQuantity"
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                WHERE (
                        (:variant_id_marker = 'BASE' AND il.product_id = :product_id AND il.variant_id IS NULL)
                     OR (:variant_id_marker = 'VALUE' AND il.variant_id = CAST(:variant_id AS UUID))
                  )
                  AND GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0
                ORDER BY il.updated_at ASC, loc.code ASC
                FOR UPDATE OF il
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "variant_id_marker": "VALUE" if variant_id else "BASE",
            },
        )
    ).mappings().all()

    remaining = quantity
    allocations: list[dict] = []
    for row in rows:
        if remaining <= 0:
            break
        take_quantity = min(remaining, int(row["availableQuantity"] or 0))
        if take_quantity <= 0:
            continue
        old_quantity = int(row["onHandQuantity"] or 0)
        new_quantity = old_quantity - take_quantity
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
                "quantity": take_quantity,
            }
        )
        remaining -= take_quantity

    if remaining > 0:
        raise ValueError("Không đủ tồn khả dụng ở các kệ để xuất kho.")
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
                    WHERE (
                            (:variant_id_marker = 'BASE' AND il.product_id = :product_id AND il.variant_id IS NULL)
                         OR (:variant_id_marker = 'VALUE' AND il.variant_id = CAST(:variant_id AS UUID))
                      )
                      AND il.location_id = :location_id
                    FOR UPDATE OF il
                    """
                ),
                {
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "variant_id_marker": "VALUE" if variant_id else "BASE",
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


async def get_checkout_url(session: AsyncSession, order_id: UUID) -> str | None:
    result = await session.execute(
        select(PaymentTransaction.checkout_url).where(PaymentTransaction.order_id == order_id).limit(1)
    )
    return result.scalar_one_or_none()


async def get_order_for_update(session: AsyncSession, order_id: UUID) -> Order | None:
    return await session.scalar(select(Order).where(Order.id == order_id).with_for_update())


async def list_pending_order_ids_to_expire(
    session: AsyncSession,
    *,
    online_timeout_minutes: int,
    cod_timeout_hours: int,
) -> list[UUID]:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM orders
            WHERE status = 'PENDING'
              AND (
                (payment_method <> 'COD' AND created_at < NOW() - make_interval(mins => :online_timeout_minutes))
                OR
                (payment_method = 'COD' AND created_at < NOW() - make_interval(hours => :cod_timeout_hours))
              )
            ORDER BY created_at ASC
            """
        ),
        {"online_timeout_minutes": online_timeout_minutes, "cod_timeout_hours": cod_timeout_hours},
    )
    return [row[0] for row in result.all()]


async def list_payment_transactions_for_update(session: AsyncSession, order_id: UUID) -> list[PaymentTransaction]:
    payment_rows = await session.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order_id).with_for_update()
    )
    return list(payment_rows.scalars().all())


async def list_restock_items(session: AsyncSession, *, order_id: UUID, order_code: str) -> list[dict]:
    item_rows = await session.execute(
        text(
            """
            SELECT
                oi.id,
                oi.product_id,
                oi.variant_id AS order_variant_id,
                oi.product_name,
                oi.quantity,
                logs.variant_id
            FROM order_items oi
            LEFT JOIN LATERAL (
                SELECT ial.variant_id
                FROM inventory_adjustment_logs ial
                WHERE ial.reference_code = :reference_code
                  AND ial.product_id IS NOT DISTINCT FROM oi.product_id
                  AND ial.reason = 'ORDER_CREATED'
                ORDER BY ial.created_at ASC
                LIMIT 1
            ) logs ON TRUE
            WHERE oi.order_id = :order_id
            """
        ),
        {"order_id": order_id, "reference_code": order_code},
    )
    return [dict(item) for item in item_rows.mappings().all()]


async def get_variant_stock_for_update(session: AsyncSession, variant_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, product_id, stock_quantity
                FROM product_variants
                WHERE id = :variant_id
                FOR UPDATE
                """
            ),
            {"variant_id": variant_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_stock_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity
                FROM products
                WHERE id = :product_id
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_revenue_report(session: AsyncSession) -> dict:
    total_orders = await session.scalar(select(func.count(Order.id)))
    completed_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == "COMPLETED"))
    total_revenue = await session.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == "COMPLETED")
    )
    ai_interactions = await session.scalar(select(func.count(AIContextLog.id)))
    loyalty_points_used = await session.scalar(select(func.coalesce(func.sum(Order.loyalty_points_used), 0)))
    return {
        "total_orders": total_orders or 0,
        "completed_orders": completed_orders or 0,
        "total_revenue": total_revenue or Decimal("0"),
        "ai_interactions": ai_interactions or 0,
        "loyalty_points_used": loyalty_points_used or 0,
    }
