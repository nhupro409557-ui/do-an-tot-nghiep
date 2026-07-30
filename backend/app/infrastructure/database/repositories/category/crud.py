"""Category repository helpers split by subdomain."""

import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_admin_categories(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                c.id::text,
                c.parent_id::text AS "parentId",
                parent.name AS "parentName",
                c.code,
                c.slug,
                c.name,
                c.icon,
                c.icon_url AS "iconUrl",
                c.banner_url AS "bannerUrl",
                c.spec_fields AS "ownSpecFields",
                COALESCE(parent.spec_fields, '[]'::jsonb) || c.spec_fields AS "specFields",
                c.filter_config AS "ownFilterConfig",
                COALESCE(parent.filter_config, '[]'::jsonb) || c.filter_config AS "filterConfig",
                COALESCE(c.inventory_policy, '{}'::jsonb) AS "inventoryPolicy",
                COALESCE(c.warranty_policy, '{}'::jsonb) AS "warrantyPolicy",
                c.sort_order AS "order",
                c.status,
                COALESCE(c.workflow_status, 'APPROVED') AS "workflowStatus",
                COALESCE(c.version, 1) AS version,
                c.is_active AS "isActive",
                COALESCE(c.hidden_by_parent, FALSE) AS "hiddenByParent",
                COALESCE(c.is_deleted, FALSE) AS "isDeleted",
                (
                    SELECT COUNT(*)
                    FROM products p
                    WHERE p.category_id = c.id
                       OR p.subcategory_id = c.id
                       OR p.category IN (c.code, c.slug, c.name)
                ) AS "productCount"
            FROM categories c
            LEFT JOIN categories parent ON parent.id = c.parent_id
            WHERE COALESCE(c.is_deleted, FALSE) = FALSE
            ORDER BY c.parent_id NULLS FIRST, c.sort_order, c.name
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def category_slug_exists(session: AsyncSession, *, slug: str, exclude_id: UUID | None) -> bool:
    row = (
        await session.execute(
            text(
                """
                SELECT 1
                FROM categories
                WHERE slug = :slug
                  AND (CAST(:exclude_id AS UUID) IS NULL OR id <> CAST(:exclude_id AS UUID))
                """
            ),
            {"slug": slug, "exclude_id": exclude_id},
        )
    ).first()
    return bool(row)


async def find_category_slug_or_code_duplicate(
    session: AsyncSession,
    *,
    slug: str,
    code: str,
    exclude_id: UUID | None = None,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT slug = :slug AS slug_match, code = :code AS code_match
                FROM categories
                WHERE (CAST(:exclude_id AS UUID) IS NULL OR id <> CAST(:exclude_id AS UUID))
                  AND (slug = :slug OR code = :code)
                LIMIT 1
                """
            ),
            {"exclude_id": exclude_id, "slug": slug, "code": code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def insert_category(
    session: AsyncSession,
    *,
    category_id: UUID,
    parent_id: UUID | None,
    code: str,
    slug: str,
    name: str,
    icon: str | None,
    icon_url: str | None,
    banner_url: str | None,
    spec_fields: list[dict],
    filter_config: list[dict],
    inventory_policy: dict,
    warranty_policy: dict,
    sort_order: int,
    status: str,
    workflow_status: str,
    is_active: bool,
    path_label: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO categories (
                id, parent_id, code, slug, name, icon, icon_url, banner_url,
                spec_fields, filter_config,
                inventory_policy, warranty_policy, sort_order, status, workflow_status, is_active, path
            )
            VALUES (
                :id, :parent_id, :code, :slug, :name, :icon, :icon_url, :banner_url,
                CAST(:spec_fields AS jsonb),
                CAST(:filter_config AS jsonb), CAST(:inventory_policy AS jsonb), CAST(:warranty_policy AS jsonb),
                :sort_order, :status, :workflow_status, :is_active,
                CASE
                    WHEN CAST(:parent_id AS uuid) IS NULL THEN CAST(:path_label AS ltree)
                    ELSE (SELECT path FROM categories WHERE id = CAST(:parent_id AS uuid)) || CAST(:path_label AS ltree)
                END
            )
            """
        ),
        {
            "id": category_id,
            "parent_id": parent_id,
            "code": code,
            "slug": slug,
            "name": name,
            "icon": icon,
            "icon_url": icon_url,
            "banner_url": banner_url,
            "spec_fields": json.dumps(spec_fields),
            "filter_config": json.dumps(filter_config),
            "inventory_policy": json.dumps(inventory_policy),
            "warranty_policy": json.dumps(warranty_policy),
            "sort_order": sort_order,
            "status": status,
            "workflow_status": workflow_status,
            "is_active": is_active,
            "path_label": path_label,
        },
    )


async def list_category_parent_rows(session: AsyncSession, ids: list[UUID]) -> list[dict]:
    rows = (
        await session.execute(
            text("SELECT id, parent_id FROM categories WHERE id IN :ids AND COALESCE(is_deleted, FALSE) = FALSE").bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def lock_category_reorder_group(session: AsyncSession, key: str) -> None:
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


async def update_category_sort_order(session: AsyncSession, *, category_id: UUID, sort_order: int, require_not_deleted: bool = False) -> int:
    where = "WHERE id = :id"
    if require_not_deleted:
        where += " AND COALESCE(is_deleted, FALSE) = FALSE"
    result = await session.execute(
        text(f"UPDATE categories SET sort_order = :sort_order, updated_at = NOW() {where}"),
        {"id": category_id, "sort_order": sort_order},
    )
    return int(result.rowcount or 0)


async def bulk_update_category_status(
    session: AsyncSession,
    *,
    ids: list[UUID],
    status: str,
    workflow_status: str,
    is_active: bool,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE categories
            SET status = :status,
                workflow_status = :workflow_status,
                is_active = :is_active,
                version = version + 1,
                updated_at = NOW()
            WHERE id IN :ids
              AND COALESCE(is_deleted, FALSE) = FALSE
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": ids, "status": status, "workflow_status": workflow_status, "is_active": is_active},
    )
    return int(result.rowcount or 0)


async def restore_category(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text("UPDATE categories SET is_active = TRUE, status = 'ACTIVE', hidden_by_parent = FALSE, updated_at = NOW() WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"id": category_id},
    )
    return int(result.rowcount or 0)


async def restore_hidden_children(session: AsyncSession, category_id: UUID) -> None:
    await session.execute(
        text(
            """
            WITH branch AS (
                SELECT path
                FROM categories
                WHERE id = :id
            )
            UPDATE categories
            SET is_active = TRUE,
                status = 'ACTIVE',
                previous_status = NULL,
                hidden_by_parent = FALSE,
                updated_at = NOW()
            FROM branch
            WHERE categories.path <@ branch.path
              AND categories.id != :id
              AND categories.hidden_by_parent = TRUE
              AND categories.previous_status = 'ACTIVE'
              AND COALESCE(categories.is_deleted, FALSE) = FALSE
            """
        ),
        {"id": category_id},
    )


async def soft_delete_category(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text("UPDATE categories SET is_active = FALSE, status = 'INACTIVE', is_deleted = TRUE, deleted_at = NOW(), hidden_by_parent = FALSE, updated_at = NOW() WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"id": category_id},
    )
    return int(result.rowcount or 0)


async def get_category_delete_blockers(session: AsyncSession, category_id: UUID) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    EXISTS(SELECT 1 FROM categories child WHERE child.parent_id = c.id) AS has_children,
                    EXISTS(
                        SELECT 1
                        FROM products p
                        WHERE p.category_id = c.id
                           OR p.subcategory_id = c.id
                           OR p.category IN (c.code, c.slug, c.name)
                    ) AS has_products,
                    EXISTS(SELECT 1 FROM brand_categories bc WHERE bc.category_id = c.id) AS has_brands,
                    EXISTS(SELECT 1 FROM content_category_relations ccr WHERE ccr.category_id = c.id) AS has_content,
                    EXISTS(SELECT 1 FROM category_migration_jobs jobs WHERE jobs.category_id = c.id) AS has_migration_jobs,
                    EXISTS(SELECT 1 FROM url_redirects redirects WHERE redirects.entity_type = 'category' AND redirects.entity_id = c.id) AS has_redirects
                FROM categories c
                WHERE c.id = :id
                  AND COALESCE(c.is_deleted, FALSE) = FALSE
                """
            ),
            {"id": category_id},
        )
    ).mappings().first()
    if not row:
        return {"exists": False}
    blockers = dict(row)
    blockers["exists"] = True
    blockers["can_hard_delete"] = not any(
        blockers[key]
        for key in ("has_children", "has_products", "has_brands", "has_content", "has_migration_jobs")
    )
    return blockers


async def hard_delete_category(session: AsyncSession, category_id: UUID) -> int:
    await session.execute(
        text("DELETE FROM url_redirects WHERE entity_type = 'category' AND entity_id = :id"),
        {"id": category_id},
    )
    await session.execute(
        text("DELETE FROM category_audit_logs WHERE category_id = :id"),
        {"id": category_id},
    )
    result = await session.execute(
        text("DELETE FROM categories WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"id": category_id},
    )
    return int(result.rowcount or 0)

async def hide_active_child_categories(session: AsyncSession, category_id: UUID) -> None:
    await session.execute(
        text(
            """
            WITH branch AS (
                SELECT path
                FROM categories
                WHERE id = :id
            )
            UPDATE categories
            SET previous_status = status,
                is_active = FALSE,
                status = 'INACTIVE',
                hidden_by_parent = TRUE,
                updated_at = NOW()
            FROM branch
            WHERE categories.path <@ branch.path
              AND categories.id != :id
              AND categories.is_active = TRUE
              AND COALESCE(categories.is_deleted, FALSE) = FALSE
            """
        ),
        {"id": category_id},
    )


async def get_category_for_update(session: AsyncSession, category_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    parent_id,
                    slug,
                    name,
                    status,
                    path::text AS path,
                    COALESCE(workflow_status, 'APPROVED') AS workflow_status,
                    COALESCE(version, 1) AS version,
                    is_active,
                    spec_fields AS "specFields",
                    filter_config AS "filterConfig",
                    COALESCE(inventory_policy, '{}'::jsonb) AS "inventoryPolicy",
                    (
                        SELECT COUNT(*)
                        FROM products p
                        JOIN categories c ON c.id = :id
                        WHERE p.category_id = :id
                           OR p.subcategory_id = :id
                           OR p.category IN (c.code, c.slug, c.name)
                    ) AS product_count
                FROM categories
                WHERE id = :id
                  AND COALESCE(is_deleted, FALSE) = FALSE
                FOR UPDATE
                """
            ),
            {"id": category_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_category(
    session: AsyncSession,
    *,
    category_id: UUID,
    expected_version: int,
    parent_id: UUID | None,
    code: str,
    slug: str,
    name: str,
    icon: str | None,
    icon_url: str | None,
    banner_url: str | None,
    spec_fields: list[dict],
    filter_config: list[dict],
    inventory_policy: dict,
    warranty_policy: dict,
    sort_order: int,
    status: str,
    workflow_status: str,
    is_active: bool,
    spec_version_delta: int,
    path_label: str,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE categories
            SET parent_id = :parent_id,
                code = :code,
                slug = :slug,
                name = :name,
                icon = :icon,
                icon_url = :icon_url,
                banner_url = :banner_url,
                spec_fields = CAST(:spec_fields AS jsonb),
                filter_config = CAST(:filter_config AS jsonb),
                inventory_policy = CAST(:inventory_policy AS jsonb),
                warranty_policy = CAST(:warranty_policy AS jsonb),
                sort_order = :sort_order,
                status = :status,
                workflow_status = :workflow_status,
                is_active = :is_active,
                spec_schema_version = spec_schema_version + :spec_version_delta,
                version = version + 1,
                path = CASE
                    WHEN CAST(:parent_id AS uuid) IS NULL THEN CAST(:path_label AS ltree)
                    ELSE (SELECT parent.path FROM categories parent WHERE parent.id = CAST(:parent_id AS uuid)) || CAST(:path_label AS ltree)
                END,
                hidden_by_parent = CASE WHEN :is_active THEN FALSE ELSE hidden_by_parent END,
                updated_at = NOW()
            WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE AND version = :expected_version
            """
        ),
        {
            "id": category_id,
            "expected_version": expected_version,
            "parent_id": parent_id,
            "code": code,
            "slug": slug,
            "name": name,
            "icon": icon,
            "icon_url": icon_url,
            "banner_url": banner_url,
            "spec_fields": json.dumps(spec_fields),
            "filter_config": json.dumps(filter_config),
            "inventory_policy": json.dumps(inventory_policy),
            "warranty_policy": json.dumps(warranty_policy),
            "sort_order": sort_order,
            "status": status,
            "workflow_status": workflow_status,
            "is_active": is_active,
            "spec_version_delta": spec_version_delta,
            "path_label": path_label,
        },
    )
    return int(result.rowcount or 0)


async def update_moved_category_children_paths(session: AsyncSession, *, category_id: UUID, old_path: str) -> None:
    await session.execute(
        text(
            """
            WITH moved AS (
                SELECT path AS new_path
                FROM categories
                WHERE id = :id
            )
            UPDATE categories child
            SET path = moved.new_path || subpath(child.path, nlevel(CAST(:old_path AS ltree))),
                updated_at = NOW()
            FROM moved
            WHERE child.path <@ CAST(:old_path AS ltree)
              AND child.id <> :id
            """
        ),
        {"id": category_id, "old_path": old_path},
    )
