from .stock_mutation_common import *


async def list_stock_count_imeis(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
) -> list[str]:
    result = await session.execute(
        text(
            """
            SELECT imei
            FROM product_imeis
            WHERE product_id = :product_id
              AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
              AND location_id = :location_id
              AND status = 'IN_STOCK'
              AND NOT EXISTS (
                    SELECT 1
                    FROM product_identifier_pairs pair
                    WHERE pair.product_id = product_imeis.product_id
                      AND pair.variant_id IS NOT DISTINCT FROM product_imeis.variant_id
                      AND pair.imei2 = product_imeis.imei
              )
            ORDER BY imei
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
        },
    )
    return [str(row[0]) for row in result.all()]


async def list_stock_count_serial_numbers(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
) -> list[str]:
    result = await session.execute(
        text(
            """
            SELECT serial_number
            FROM product_serial_numbers
            WHERE product_id = :product_id
              AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
              AND location_id = :location_id
              AND status = 'IN_STOCK'
            ORDER BY serial_number
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
        },
    )
    return [str(row[0]) for row in result.all()]


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
