"""Category repository helpers split by subdomain."""

import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def preview_identifier_policy_change(
    session: AsyncSession,
    *,
    category_id: UUID,
    identifier_type: str,
) -> list[dict]:
    inherit_key = "inheritImeiPolicy" if identifier_type == "IMEI" else "inheritSerialPolicy"
    policy_key = "imeiPolicy" if identifier_type == "IMEI" else "serialPolicy"
    identifier_table = "product_imeis" if identifier_type == "IMEI" else "product_serial_numbers"
    result = await session.execute(
        text(
            f"""
            WITH RECURSIVE affected_categories AS (
                SELECT id
                FROM categories
                WHERE id = :category_id
                  AND COALESCE(is_deleted, FALSE) = FALSE

                UNION ALL

                SELECT child.id
                FROM categories child
                JOIN affected_categories parent ON child.parent_id = parent.id
                WHERE COALESCE(child.is_deleted, FALSE) = FALSE
                  AND COALESCE((child.inventory_policy->>:inherit_key)::boolean, TRUE) = TRUE
            ),
            affected_stock AS (
                SELECT
                    levels.product_id,
                    levels.variant_id,
                    SUM(levels.on_hand_quantity)::integer AS physical_stock
                FROM inventory_levels levels
                JOIN products product ON product.id = levels.product_id
                WHERE levels.on_hand_quantity > 0
                  AND (
                        product.category_id IN (SELECT id FROM affected_categories)
                     OR product.subcategory_id IN (SELECT id FROM affected_categories)
                  )
                  AND UPPER(COALESCE(product.sales_config->:policy_key->>'mode', 'CATEGORY')) <> 'MANUAL'
                GROUP BY levels.product_id, levels.variant_id
            )
            SELECT
                stock.product_id::text AS "productId",
                stock.variant_id::text AS "variantId",
                product.name AS "productName",
                variant.sku AS "variantName",
                stock.physical_stock AS "physicalStock",
                (
                    SELECT COUNT(*)::integer
                    FROM {identifier_table} identifier
                    WHERE identifier.product_id = stock.product_id
                      AND (
                            identifier.variant_id = stock.variant_id
                         OR (identifier.variant_id IS NULL AND stock.variant_id IS NULL)
                      )
                      AND identifier.status = 'IN_STOCK'
                ) AS "existingIdentifierCount"
            FROM affected_stock stock
            JOIN products product ON product.id = stock.product_id
            LEFT JOIN product_variants variant ON variant.id = stock.variant_id
            ORDER BY product.name, variant.sku NULLS FIRST
            """
        ),
        {
            "category_id": category_id,
            "inherit_key": inherit_key,
            "policy_key": policy_key,
        },
    )
    rows: list[dict] = []
    for row in result.mappings().all():
        item = dict(row)
        item["requiredIdentifierCount"] = max(
            int(item["physicalStock"] or 0) - int(item["existingIdentifierCount"] or 0),
            0,
        )
        rows.append(item)
    return rows


async def find_active_identifier_policy_migration(
    session: AsyncSession,
    *,
    category_id: UUID,
    identifier_type: str,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id::text, status
                FROM inventory_policy_migrations
                WHERE category_id = :category_id
                  AND identifier_type = :identifier_type
                  AND status IN ('PENDING', 'IN_PROGRESS')
                LIMIT 1
                """
            ),
            {"category_id": category_id, "identifier_type": identifier_type},
        )
    ).mappings().first()
    return dict(row) if row else None


async def create_identifier_policy_migration(
    session: AsyncSession,
    *,
    migration_id: UUID,
    category_id: UUID,
    identifier_type: str,
    target_inventory_policy: dict,
    lines: list[dict],
    actor_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_policy_migrations (
                id, category_id, identifier_type, status, target_inventory_policy,
                affected_product_count, required_identifier_count, created_by
            )
            VALUES (
                :id, :category_id, :identifier_type, 'PENDING', CAST(:target_inventory_policy AS jsonb),
                :affected_product_count, :required_identifier_count, :created_by
            )
            """
        ),
        {
            "id": migration_id,
            "category_id": category_id,
            "identifier_type": identifier_type,
            "target_inventory_policy": json.dumps(target_inventory_policy, ensure_ascii=False),
            "affected_product_count": len({line["productId"] for line in lines}),
            "required_identifier_count": sum(int(line["requiredIdentifierCount"]) for line in lines),
            "created_by": actor_id,
        },
    )
    for line in lines:
        if int(line["requiredIdentifierCount"]) <= 0:
            continue
        await session.execute(
            text(
                """
                INSERT INTO inventory_policy_migration_lines (
                    migration_id, product_id, variant_id, product_name, variant_name,
                    physical_stock, existing_identifier_count, required_identifier_count
                )
                VALUES (
                    :migration_id, :product_id, :variant_id, :product_name, :variant_name,
                    :physical_stock, :existing_identifier_count, :required_identifier_count
                )
                """
            ),
            {
                "migration_id": migration_id,
                "product_id": line["productId"],
                "variant_id": line["variantId"],
                "product_name": line["productName"],
                "variant_name": line["variantName"],
                "physical_stock": line["physicalStock"],
                "existing_identifier_count": line["existingIdentifierCount"],
                "required_identifier_count": line["requiredIdentifierCount"],
            },
        )


async def list_identifier_policy_migrations(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                migration.id::text,
                migration.category_id::text AS "categoryId",
                migration.identifier_type AS "identifierType",
                migration.status,
                migration.affected_product_count AS "affectedProductCount",
                migration.required_identifier_count AS "requiredIdentifierCount",
                migration.staged_identifier_count AS "stagedIdentifierCount",
                migration.created_at AS "createdAt",
                migration.completed_at AS "completedAt",
                migration.cancellation_reason AS "cancellationReason"
            FROM inventory_policy_migrations migration
            WHERE migration.category_id = :category_id
            ORDER BY migration.created_at DESC
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_identifier_policy_migration(session: AsyncSession, migration_id: UUID, *, for_update: bool = False) -> dict | None:
    suffix = " FOR UPDATE" if for_update else ""
    row = (
        await session.execute(
            text(
                f"""
                SELECT
                    id::text,
                    category_id::text AS "categoryId",
                    identifier_type AS "identifierType",
                    status,
                    target_inventory_policy AS "targetInventoryPolicy",
                    required_identifier_count AS "requiredIdentifierCount",
                    staged_identifier_count AS "stagedIdentifierCount"
                FROM inventory_policy_migrations
                WHERE id = :migration_id{suffix}
                """
            ),
            {"migration_id": migration_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_identifier_policy_migration_lines(session: AsyncSession, migration_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                migration_id::text AS "migrationId",
                product_id::text AS "productId",
                variant_id::text AS "variantId",
                product_name AS "productName",
                variant_name AS "variantName",
                physical_stock AS "physicalStock",
                existing_identifier_count AS "existingIdentifierCount",
                required_identifier_count AS "requiredIdentifierCount",
                staged_identifier_count AS "stagedIdentifierCount"
            FROM inventory_policy_migration_lines
            WHERE migration_id = :migration_id
            ORDER BY product_name, variant_name NULLS FIRST
            """
        ),
        {"migration_id": migration_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_identifier_policy_migration_line(session: AsyncSession, migration_id: UUID, line_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    product_id::text AS "productId",
                    variant_id::text AS "variantId",
                    required_identifier_count AS "requiredIdentifierCount",
                    staged_identifier_count AS "stagedIdentifierCount"
                FROM inventory_policy_migration_lines
                WHERE id = :line_id AND migration_id = :migration_id
                FOR UPDATE
                """
            ),
            {"migration_id": migration_id, "line_id": line_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_existing_identifier_values(session: AsyncSession, identifier_type: str, values: list[str]) -> set[str]:
    if not values:
        return set()
    if identifier_type == "IMEI":
        result = await session.execute(text("SELECT imei FROM product_imeis WHERE imei = ANY(:values)"), {"values": values})
    else:
        result = await session.execute(text("SELECT serial_number FROM product_serial_numbers WHERE serial_number = ANY(:values)"), {"values": values})
    return {str(row[0]) for row in result.all()}


async def list_staged_identifier_values(session: AsyncSession, values: list[str]) -> set[str]:
    if not values:
        return set()
    result = await session.execute(
        text(
            """
            SELECT identifier_value
            FROM inventory_policy_migration_identifiers
            WHERE identifier_value = ANY(:values)
              AND status = 'STAGED'
            """
        ),
        {"values": values},
    )
    return {str(row[0]) for row in result.all()}


async def stage_identifier_policy_values(
    session: AsyncSession,
    *,
    migration_id: UUID,
    line_id: UUID,
    values: list[str],
    actor_id: UUID,
) -> int:
    inserted = 0
    for value in values:
        result = await session.execute(
            text(
                """
                INSERT INTO inventory_policy_migration_identifiers (
                    migration_id, line_id, identifier_value, status, scanned_by
                )
                VALUES (:migration_id, :line_id, :identifier_value, 'STAGED', :scanned_by)
                ON CONFLICT (migration_id, identifier_value) DO NOTHING
                """
            ),
            {
                "migration_id": migration_id,
                "line_id": line_id,
                "identifier_value": value,
                "scanned_by": actor_id,
            },
        )
        inserted += int(result.rowcount or 0)
    if inserted:
        await session.execute(
            text(
                """
                UPDATE inventory_policy_migration_lines
                SET staged_identifier_count = staged_identifier_count + :inserted
                WHERE id = :line_id
                """
            ),
            {"line_id": line_id, "inserted": inserted},
        )
        await session.execute(
            text(
                """
                UPDATE inventory_policy_migrations
                SET staged_identifier_count = staged_identifier_count + :inserted,
                    status = 'IN_PROGRESS',
                    updated_at = NOW()
                WHERE id = :migration_id
                """
            ),
            {"migration_id": migration_id, "inserted": inserted},
        )
    return inserted


async def activate_identifier_policy_migration_values(
    session: AsyncSession,
    *,
    migration_id: UUID,
    identifier_type: str,
) -> None:
    if identifier_type == "IMEI":
        await session.execute(
            text(
                """
                INSERT INTO product_imeis (
                    id, product_id, variant_id, imei, is_primary, status, source_reference, received_at
                )
                SELECT
                    gen_random_uuid(), line.product_id, line.variant_id, staged.identifier_value,
                    FALSE, 'IN_STOCK', 'POLICY-BACKFILL-' || :migration_id, NOW()
                FROM inventory_policy_migration_identifiers staged
                JOIN inventory_policy_migration_lines line ON line.id = staged.line_id
                WHERE staged.migration_id = :migration_id AND staged.status = 'STAGED'
                ON CONFLICT (imei) DO NOTHING
                """
            ),
            {"migration_id": str(migration_id)},
        )
    else:
        await session.execute(
            text(
                """
                INSERT INTO product_serial_numbers (
                    id, product_id, variant_id, serial_number, status, source_reference, received_at
                )
                SELECT
                    gen_random_uuid(), line.product_id, line.variant_id, staged.identifier_value,
                    'IN_STOCK', 'POLICY-BACKFILL-' || :migration_id, NOW()
                FROM inventory_policy_migration_identifiers staged
                JOIN inventory_policy_migration_lines line ON line.id = staged.line_id
                WHERE staged.migration_id = :migration_id AND staged.status = 'STAGED'
                ON CONFLICT DO NOTHING
                """
            ),
            {"migration_id": str(migration_id)},
        )
    await session.execute(
        text(
            """
            UPDATE inventory_policy_migration_identifiers
            SET status = 'ACTIVATED', activated_at = NOW()
            WHERE migration_id = :migration_id AND status = 'STAGED'
            """
        ),
        {"migration_id": migration_id},
    )


async def complete_identifier_policy_migration(
    session: AsyncSession,
    *,
    migration_id: UUID,
    category_id: UUID,
    target_inventory_policy: dict,
    identifier_type: str,
    actor_id: UUID,
) -> None:
    policy_key = "trackImei" if identifier_type == "IMEI" else "trackSerialNumber"
    inherit_key = "inheritImeiPolicy" if identifier_type == "IMEI" else "inheritSerialPolicy"
    policy_value = bool(target_inventory_policy.get(policy_key))
    inherit_value = bool(target_inventory_policy.get(inherit_key, True))
    await session.execute(
        text(
            """
            UPDATE categories
            SET inventory_policy = jsonb_set(
                    jsonb_set(
                        COALESCE(inventory_policy, '{}'::jsonb),
                        CAST(:policy_path AS text[]),
                        to_jsonb(CAST(:policy_value AS boolean)),
                        TRUE
                    ),
                    CAST(:inherit_path AS text[]),
                    to_jsonb(CAST(:inherit_value AS boolean)),
                    TRUE
                ),
                version = version + 1,
                updated_at = NOW()
            WHERE id = :category_id
            """
        ),
        {
            "category_id": category_id,
            "policy_path": [policy_key],
            "policy_value": policy_value,
            "inherit_path": [inherit_key],
            "inherit_value": inherit_value,
        },
    )
    await session.execute(
        text(
            """
            UPDATE inventory_policy_migrations
            SET status = 'COMPLETED', completed_by = :actor_id,
                completed_at = NOW(), updated_at = NOW()
            WHERE id = :migration_id
            """
        ),
        {"migration_id": migration_id, "actor_id": actor_id},
    )


async def cancel_identifier_policy_migration(
    session: AsyncSession,
    *,
    migration_id: UUID,
    actor_id: UUID,
    reason: str,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_policy_migration_identifiers
            SET status = 'CANCELLED'
            WHERE migration_id = :migration_id AND status = 'STAGED'
            """
        ),
        {"migration_id": migration_id},
    )
    await session.execute(
        text(
            """
            UPDATE inventory_policy_migrations
            SET status = 'CANCELLED', cancelled_by = :actor_id,
                cancellation_reason = :reason, cancelled_at = NOW(), updated_at = NOW()
            WHERE id = :migration_id
            """
        ),
        {"migration_id": migration_id, "actor_id": actor_id, "reason": reason},
    )
