from .stock_mutation_common import *

async def post_inventory_level_receipt(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
    location_id: UUID,
    quantity: int,
    unit_cost: float | int | None,
) -> None:
    await session.execute(
        text(
            """
            WITH updated AS (
                UPDATE inventory_levels
                SET average_unit_cost = CASE
                        WHEN on_hand_quantity + :quantity <= 0 THEN average_unit_cost
                        WHEN CAST(:unit_cost AS NUMERIC) IS NULL THEN average_unit_cost
                        ELSE ROUND(
                            (
                                on_hand_quantity * average_unit_cost
                                + :quantity * CAST(:unit_cost AS NUMERIC)
                            ) / NULLIF(on_hand_quantity + :quantity, 0),
                            2
                        )
                    END,
                    on_hand_quantity = on_hand_quantity + :quantity,
                    updated_at = NOW()
                WHERE product_id IS NULL
                  AND variant_id = :variant_id
                  AND location_id = :location_id
                RETURNING id
            )
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
            )
            SELECT
                gen_random_uuid(),
                NULL,
                :variant_id,
                :location_id,
                :quantity,
                0,
                COALESCE(CAST(:unit_cost AS NUMERIC), 0)
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "quantity": quantity,
            "unit_cost": unit_cost,
        },
    )


async def create_inventory_lot_for_receipt(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    quantity: int,
    unit_cost: float | int | None,
) -> UUID | None:
    if quantity <= 0:
        return None

    lot_id = uuid4()
    lot_code = f"LOT-{reference_code[:40]}-{str(lot_id)[:8]}".upper()
    await session.execute(
        text(
            """
            INSERT INTO inventory_lots (
                id, lot_code, product_id, variant_id, location_id,
                source_document_id, source_reference,
                initial_quantity, remaining_quantity, unit_cost,
                received_at, status
            )
            VALUES (
                :id, :lot_code,
                CASE
                    WHEN CAST(:variant_id AS UUID) IS NULL
                    THEN CAST(:product_id AS UUID)
                    ELSE NULL
                END,
                CAST(:variant_id AS UUID),
                :location_id,
                :document_id,
                :reference_code,
                :quantity,
                :quantity,
                CAST(:unit_cost AS NUMERIC),
                NOW(),
                'ACTIVE'
            )
            """
        ),
        {
            "id": lot_id,
            "lot_code": lot_code,
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "document_id": document_id,
            "reference_code": reference_code,
            "quantity": quantity,
            "unit_cost": unit_cost,
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO inventory_lot_movements (
                id, lot_id, movement_type, quantity,
                reference_code, inventory_document_id, note
            )
            VALUES (
                :id, :lot_id, 'RECEIPT', :quantity,
                :reference_code, :document_id, 'Tự động tạo lô khi hoàn tất phiếu nhập.'
            )
            """
        ),
        {
            "id": uuid4(),
            "lot_id": lot_id,
            "quantity": quantity,
            "reference_code": reference_code,
            "document_id": document_id,
        },
    )
    return lot_id


async def reverse_inventory_lots_for_receipt(
    session: AsyncSession,
    *,
    document_id: UUID,
    location_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    quantity: int,
    reversal_reference: str,
) -> None:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, remaining_quantity
                FROM inventory_lots
                WHERE source_document_id = :document_id
                  AND location_id = :location_id
                  AND (
                        (:variant_id_marker = 'BASE' AND product_id = :product_id AND variant_id IS NULL)
                     OR (:variant_id_marker = 'VALUE' AND variant_id = CAST(:variant_id AS UUID))
                  )
                  AND remaining_quantity > 0
                ORDER BY received_at DESC, created_at DESC
                FOR UPDATE
                """
            ),
            {
                "document_id": document_id,
                "location_id": location_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "variant_id_marker": "VALUE" if variant_id else "BASE",
            },
        )
    ).mappings().all()
    if sum(int(row["remaining_quantity"] or 0) for row in rows) < quantity:
        raise ValueError("Lô của phiếu nhập đã được xuất một phần nên không thể đảo đủ số lượng.")

    remaining = quantity
    for row in rows:
        if remaining <= 0:
            break
        reverse_quantity = min(remaining, int(row["remaining_quantity"] or 0))
        new_remaining = int(row["remaining_quantity"] or 0) - reverse_quantity
        await session.execute(
            text(
                """
                UPDATE inventory_lots
                SET remaining_quantity = :remaining_quantity,
                    status = CASE WHEN :remaining_quantity = 0 THEN 'CANCELLED' ELSE 'ACTIVE' END,
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
                    reference_code, inventory_document_id, note
                )
                VALUES (
                    :id, :lot_id, 'REVERSAL', :quantity,
                    :reference_code, :document_id, 'Đảo lô theo phiếu nhập.'
                )
                """
            ),
            {
                "id": uuid4(),
                "lot_id": row["id"],
                "quantity": reverse_quantity,
                "reference_code": reversal_reference,
                "document_id": document_id,
            },
        )
        remaining -= reverse_quantity


async def post_inventory_level_reversal(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
    location_id: UUID,
    quantity: int,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_levels
            SET on_hand_quantity = GREATEST(on_hand_quantity - :quantity, 0),
                updated_at = NOW()
            WHERE product_id IS NULL
              AND variant_id = :variant_id
              AND location_id = :location_id
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "quantity": quantity,
        },
    )
