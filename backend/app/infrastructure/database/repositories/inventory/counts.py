from .stock_mutation_common import *

async def set_inventory_level_counted_quantity(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    counted_quantity: int,
) -> None:
    if variant_id:
        await session.execute(
            text(
                """
                WITH updated AS (
                    UPDATE inventory_levels
                    SET on_hand_quantity = :counted_quantity,
                        last_counted_at = NOW(),
                        updated_at = NOW()
                    WHERE product_id IS NULL
                      AND variant_id = :variant_id
                      AND location_id = :location_id
                    RETURNING id
                )
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost, last_counted_at
                )
                SELECT gen_random_uuid(), NULL, :variant_id, :location_id, :counted_quantity, 0, 0, NOW()
                WHERE NOT EXISTS (SELECT 1 FROM updated)
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "counted_quantity": counted_quantity,
            },
        )
        return
    await session.execute(
        text(
            """
            WITH updated AS (
                UPDATE inventory_levels
                SET on_hand_quantity = :counted_quantity,
                    last_counted_at = NOW(),
                    updated_at = NOW()
                WHERE product_id = :product_id
                  AND variant_id IS NULL
                  AND location_id = :location_id
                RETURNING id
            )
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost, last_counted_at
            )
            SELECT gen_random_uuid(), :product_id, NULL, :location_id, :counted_quantity, 0, 0, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """
        ),
        {
            "product_id": product_id,
            "location_id": location_id,
            "counted_quantity": counted_quantity,
        },
    )
