import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_inventory_location_by_code(session: AsyncSession, code: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id, code, name, zone, purpose,
                    sort_order AS "sortOrder",
                    allow_mixed_sku AS "allowMixedSku",
                    description, status, is_default AS "isDefault"
                FROM inventory_locations
                WHERE code = :code
                """
            ),
            {"code": code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_inventory_location_by_id(session: AsyncSession, location_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id, code, name, zone, purpose,
                    sort_order AS "sortOrder",
                    allow_mixed_sku AS "allowMixedSku",
                    description, status, is_default AS "isDefault"
                FROM inventory_locations
                WHERE id = :location_id
                """
            ),
            {"location_id": location_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_inventory_locations(
    session: AsyncSession,
    search: str = "",
    include_inactive: bool = True,
    zone: str = "",
    purpose: str = "",
    status: str = "",
    aisle: str = "",
    shelf: str = "",
    bin: str = "",
) -> list[dict]:
    search_value = f"%{search.strip()}%" if search.strip() else ""
    zone_value = zone.strip()
    purpose_value = purpose.strip().upper()
    status_value = status.strip().upper()
    aisle_value = aisle.strip().upper()
    shelf_value = shelf.strip()
    bin_value = bin.strip()
    result = await session.execute(
        text(
            """
            SELECT
                loc.id::text AS id,
                loc.code,
                loc.name,
                loc.zone,
                loc.purpose,
                loc.sort_order AS "sortOrder",
                loc.allow_mixed_sku AS "allowMixedSku",
                loc.length_cm::float AS "lengthCm",
                loc.width_cm::float AS "widthCm",
                loc.height_cm::float AS "heightCm",
                loc.usable_ratio::float AS "usableRatio",
                CASE
                    WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                    THEN (loc.length_cm * loc.width_cm * loc.height_cm)::float
                    ELSE NULL
                END AS "capacityVolumeCm3",
                CASE
                    WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                    THEN (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio)::float
                    ELSE NULL
                END AS "usableVolumeCm3",
                loc.description,
                loc.status,
                loc.is_default AS "isDefault",
                COALESCE(levels.sku_count, 0)::int AS "skuCount",
                COALESCE(levels.on_hand_quantity, 0)::int AS "onHandQuantity",
                COALESCE(levels.used_volume_cm3, 0)::float AS "usedVolumeCm3",
                CASE
                    WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                    THEN GREATEST((loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio) - COALESCE(levels.used_volume_cm3, 0), 0)::float
                    ELSE NULL
                END AS "availableVolumeCm3",
                CASE
                    WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                         AND (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio) > 0
                    THEN LEAST(COALESCE(levels.used_volume_cm3, 0) / (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio), 9.9999)::float
                    ELSE NULL
                END AS "fillRatio",
                loc.created_at AS "createdAt",
                loc.updated_at AS "updatedAt"
            FROM inventory_locations loc
            LEFT JOIN (
                SELECT
                    il.location_id,
                    COUNT(*) FILTER (WHERE il.on_hand_quantity <> 0)::int AS sku_count,
                    COALESCE(SUM(il.on_hand_quantity), 0)::int AS on_hand_quantity,
                    COALESCE(SUM(
                        il.on_hand_quantity
                        * COALESCE(
                            NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN (child.inventory_policy->>'packageLengthCm')::numeric
                                    ELSE (parent.inventory_policy->>'packageLengthCm')::numeric
                                END,
                                0
                            ),
                            16
                        )
                        * COALESCE(
                            NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN (child.inventory_policy->>'packageWidthCm')::numeric
                                    ELSE (parent.inventory_policy->>'packageWidthCm')::numeric
                                END,
                                0
                            ),
                            9
                        )
                        * COALESCE(
                            NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN (child.inventory_policy->>'packageHeightCm')::numeric
                                    ELSE (parent.inventory_policy->>'packageHeightCm')::numeric
                                END,
                                0
                            ),
                            6
                        )
                        / GREATEST(COALESCE(
                            NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN (child.inventory_policy->>'packingRatio')::numeric
                                    ELSE (parent.inventory_policy->>'packingRatio')::numeric
                                END,
                                0
                            ),
                            0.70
                        ), 0.01)
                    ), 0)::float AS used_volume_cm3
                FROM inventory_levels il
                LEFT JOIN product_variants pv ON pv.id = il.variant_id
                LEFT JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
                LEFT JOIN categories child ON child.id = p.subcategory_id
                LEFT JOIN categories parent ON parent.id = COALESCE(p.category_id, child.parent_id)
                GROUP BY il.location_id
            ) levels ON levels.location_id = loc.id
            WHERE (:include_inactive OR loc.status = 'ACTIVE')
              AND (:status = '' OR loc.status = :status)
              AND (:purpose = '' OR loc.purpose = :purpose)
              AND (:zone = '' OR COALESCE(loc.zone, '') = :zone)
              AND (:aisle = '' OR split_part(loc.code, '-', 1) = :aisle)
              AND (:shelf = '' OR split_part(loc.code, '-', 2) = :shelf)
              AND (:bin = '' OR split_part(loc.code, '-', 3) = :bin)
              AND (
                  :search = ''
                  OR loc.code ILIKE :search
                  OR loc.name ILIKE :search
                  OR COALESCE(loc.zone, '') ILIKE :search
              )
            ORDER BY loc.is_default DESC, loc.status, loc.sort_order, loc.code
            """
        ),
        {
            "search": search_value,
            "include_inactive": include_inactive,
            "zone": zone_value,
            "purpose": purpose_value,
            "status": status_value,
            "aisle": aisle_value,
            "shelf": shelf_value,
            "bin": bin_value,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def get_inventory_location_capacity_usage(session: AsyncSession, location_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    loc.id::text AS id,
                    loc.code,
                    loc.name,
                    loc.length_cm::float AS "lengthCm",
                    loc.width_cm::float AS "widthCm",
                    loc.height_cm::float AS "heightCm",
                    loc.usable_ratio::float AS "usableRatio",
                    CASE
                        WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                        THEN (loc.length_cm * loc.width_cm * loc.height_cm)::float
                        ELSE NULL
                    END AS "capacityVolumeCm3",
                    CASE
                        WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                        THEN (loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio)::float
                        ELSE NULL
                    END AS "usableVolumeCm3",
                    COALESCE(levels.used_volume_cm3, 0)::float AS "usedVolumeCm3",
                    CASE
                        WHEN loc.length_cm IS NOT NULL AND loc.width_cm IS NOT NULL AND loc.height_cm IS NOT NULL
                        THEN GREATEST((loc.length_cm * loc.width_cm * loc.height_cm * loc.usable_ratio) - COALESCE(levels.used_volume_cm3, 0), 0)::float
                        ELSE NULL
                    END AS "availableVolumeCm3"
                FROM inventory_locations loc
                LEFT JOIN (
                    SELECT
                        il.location_id,
                        COALESCE(SUM(
                            il.on_hand_quantity
                            * COALESCE(NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN NULLIF(child.inventory_policy->>'packageLengthCm', '')::numeric
                                    ELSE NULLIF(parent.inventory_policy->>'packageLengthCm', '')::numeric
                                END, 0), 16)
                            * COALESCE(NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN NULLIF(child.inventory_policy->>'packageWidthCm', '')::numeric
                                    ELSE NULLIF(parent.inventory_policy->>'packageWidthCm', '')::numeric
                                END, 0), 9)
                            * COALESCE(NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN NULLIF(child.inventory_policy->>'packageHeightCm', '')::numeric
                                    ELSE NULLIF(parent.inventory_policy->>'packageHeightCm', '')::numeric
                                END, 0), 6)
                            / GREATEST(COALESCE(NULLIF(
                                CASE
                                    WHEN child.id IS NOT NULL
                                         AND COALESCE((child.inventory_policy->>'inheritStorageDimensions')::boolean, TRUE) = FALSE
                                    THEN NULLIF(child.inventory_policy->>'packingRatio', '')::numeric
                                    ELSE NULLIF(parent.inventory_policy->>'packingRatio', '')::numeric
                                END, 0), 0.70), 0.01)
                        ), 0)::float AS used_volume_cm3
                    FROM inventory_levels il
                    LEFT JOIN product_variants pv ON pv.id = il.variant_id
                    LEFT JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
                    LEFT JOIN categories child ON child.id = p.subcategory_id
                    LEFT JOIN categories parent ON parent.id = COALESCE(p.category_id, child.parent_id)
                    GROUP BY il.location_id
                ) levels ON levels.location_id = loc.id
                WHERE loc.id = :location_id
                """
            ),
            {"location_id": location_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def create_inventory_location(
    session: AsyncSession,
    *,
    location_id: UUID,
    code: str,
    name: str,
    zone: str | None,
    purpose: str,
    sort_order: int,
    allow_mixed_sku: bool,
    length_cm: float | None,
    width_cm: float | None,
    height_cm: float | None,
    usable_ratio: float,
    description: str | None,
) -> dict:
    row = (
        await session.execute(
            text(
                """
                INSERT INTO inventory_locations (
                    id, code, name, zone, purpose, sort_order, allow_mixed_sku,
                    length_cm, width_cm, height_cm, usable_ratio, description, location_type, status, is_default
                )
                VALUES (
                    :id, :code, :name, :zone, :purpose, :sort_order, :allow_mixed_sku,
                    :length_cm, :width_cm, :height_cm, :usable_ratio, :description, 'WAREHOUSE', 'ACTIVE', FALSE
                )
                RETURNING id, code, name, zone, purpose, sort_order AS "sortOrder",
                    allow_mixed_sku AS "allowMixedSku", length_cm::float AS "lengthCm",
                    width_cm::float AS "widthCm", height_cm::float AS "heightCm",
                    usable_ratio::float AS "usableRatio",
                    CASE
                        WHEN length_cm IS NOT NULL AND width_cm IS NOT NULL AND height_cm IS NOT NULL
                        THEN (length_cm * width_cm * height_cm)::float
                        ELSE NULL
                    END AS "capacityVolumeCm3",
                    description, status, is_default AS "isDefault"
                """
            ),
            {
                "id": location_id,
                "code": code,
                "name": name,
                "zone": zone,
                "purpose": purpose,
                "sort_order": sort_order,
                "allow_mixed_sku": allow_mixed_sku,
                "length_cm": length_cm,
                "width_cm": width_cm,
                "height_cm": height_cm,
                "usable_ratio": usable_ratio,
                "description": description,
            },
        )
    ).mappings().first()
    return dict(row) if row else {}


async def update_inventory_location(
    session: AsyncSession,
    *,
    location_id: UUID,
    code: str,
    name: str,
    zone: str | None,
    purpose: str,
    sort_order: int,
    allow_mixed_sku: bool,
    length_cm: float | None,
    width_cm: float | None,
    height_cm: float | None,
    usable_ratio: float,
    description: str | None,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE inventory_locations
                SET code = :code,
                    name = :name,
                    zone = :zone,
                    purpose = :purpose,
                    sort_order = :sort_order,
                    allow_mixed_sku = :allow_mixed_sku,
                    length_cm = :length_cm,
                    width_cm = :width_cm,
                    height_cm = :height_cm,
                    usable_ratio = :usable_ratio,
                    description = :description,
                    updated_at = NOW()
                WHERE id = :location_id
                RETURNING id, code, name, zone, purpose, sort_order AS "sortOrder",
                    allow_mixed_sku AS "allowMixedSku", length_cm::float AS "lengthCm",
                    width_cm::float AS "widthCm", height_cm::float AS "heightCm",
                    usable_ratio::float AS "usableRatio",
                    CASE
                        WHEN length_cm IS NOT NULL AND width_cm IS NOT NULL AND height_cm IS NOT NULL
                        THEN (length_cm * width_cm * height_cm)::float
                        ELSE NULL
                    END AS "capacityVolumeCm3",
                    description, status, is_default AS "isDefault"
                """
            ),
            {
                "location_id": location_id,
                "code": code,
                "name": name,
                "zone": zone,
                "purpose": purpose,
                "sort_order": sort_order,
                "allow_mixed_sku": allow_mixed_sku,
                "length_cm": length_cm,
                "width_cm": width_cm,
                "height_cm": height_cm,
                "usable_ratio": usable_ratio,
                "description": description,
            },
        )
    ).mappings().first()
    return dict(row) if row else None


async def set_inventory_location_status(session: AsyncSession, *, location_id: UUID, status: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE inventory_locations
                SET status = :status,
                    updated_at = NOW()
                WHERE id = :location_id
                RETURNING id, code, name, zone, purpose, sort_order AS "sortOrder",
                    allow_mixed_sku AS "allowMixedSku", description, status, is_default AS "isDefault"
                """
            ),
            {"location_id": location_id, "status": status},
        )
    ).mappings().first()
    return dict(row) if row else None


async def inventory_location_has_stock(session: AsyncSession, location_id: UUID) -> bool:
    value = (
        await session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM inventory_levels
                    WHERE location_id = :location_id
                      AND on_hand_quantity > 0
                )
                """
            ),
            {"location_id": location_id},
        )
    ).scalar_one()
    return bool(value)


async def ensure_inventory_location(session: AsyncSession, *, code: str, name: str) -> dict:
    await session.execute(
        text(
            """
            INSERT INTO inventory_locations (code, name, location_type, status, is_default)
            VALUES (:code, :name, 'WAREHOUSE', 'ACTIVE', :is_default)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                status = 'ACTIVE',
                updated_at = NOW()
            """
        ),
        {"code": code, "name": name, "is_default": code == "MAIN"},
    )
    row = await get_inventory_location_by_code(session, code)
    if not row:
        raise RuntimeError("Inventory location was not created.")
    return row
