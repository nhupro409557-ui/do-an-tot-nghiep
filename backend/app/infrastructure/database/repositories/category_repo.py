"""Repository boundary for category data access.

This module is intentionally introduced before moving every query out of
``category_service``. Keep new category SQL here so the next refactor phase can
move existing queries in small, testable steps.
"""

import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_category_by_id(session: AsyncSession, category_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT *
            FROM categories
            WHERE id = :category_id
              AND COALESCE(is_deleted, FALSE) = FALSE
            """
        ),
        {"category_id": category_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def category_descendant_contains(session: AsyncSession, *, category_id: UUID, parent_id: UUID) -> bool:
    row = (
        await session.execute(
            text(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id
                    FROM categories
                    WHERE parent_id = :category_id
                      AND COALESCE(is_deleted, FALSE) = FALSE
                    UNION ALL
                    SELECT child.id
                    FROM categories child
                    JOIN descendants d ON child.parent_id = d.id
                    WHERE COALESCE(child.is_deleted, FALSE) = FALSE
                )
                SELECT 1
                FROM descendants
                WHERE id = :parent_id
                LIMIT 1
                """
            ),
            {"category_id": category_id, "parent_id": parent_id},
        )
    ).first()
    return bool(row)


async def get_category_path_depth(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text("SELECT COALESCE(nlevel(path), 1) FROM categories WHERE id = :parent_id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"parent_id": category_id},
    )
    return int(result.scalar() or 0)


async def get_category_subtree_depth(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            SELECT COALESCE(MAX(nlevel(child.path) - nlevel(parent.path) + 1), 1)
            FROM categories parent
            LEFT JOIN categories child ON child.path <@ parent.path
            WHERE parent.id = :category_id
              AND COALESCE(child.is_deleted, FALSE) = FALSE
            """
        ),
        {"category_id": category_id},
    )
    return int(result.scalar() or 1)


async def list_ancestor_spec_fields(session: AsyncSession, *, parent_id: UUID, category_id: UUID | None) -> list[list[dict]]:
    rows = (
        await session.execute(
            text(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, spec_fields
                    FROM categories
                    WHERE id = :parent_id
                      AND COALESCE(is_deleted, FALSE) = FALSE
                    UNION ALL
                    SELECT parent.id, parent.parent_id, parent.spec_fields
                    FROM categories parent
                    JOIN ancestors child ON child.parent_id = parent.id
                    WHERE COALESCE(parent.is_deleted, FALSE) = FALSE
                )
                SELECT spec_fields
                FROM ancestors
                WHERE (CAST(:category_id AS UUID) IS NULL OR id <> CAST(:category_id AS UUID))
                """
            ),
            {"parent_id": parent_id, "category_id": category_id},
        )
    ).mappings().all()
    return [row["spec_fields"] for row in rows]


async def count_products_using_spec_keys(session: AsyncSession, *, category_id: UUID, keys: list[str]) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM products p
            WHERE (p.category_id = :category_id OR p.subcategory_id = :category_id)
              AND p.specifications ?| CAST(:keys AS text[])
            """
        ),
        {"category_id": category_id, "keys": keys},
    )
    return int(result.scalar() or 0)


async def find_running_migration_for_category_branch(session: AsyncSession, ids: list[UUID]) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                WITH target AS (
                    SELECT id, path
                    FROM categories
                    WHERE id IN :ids
                      AND COALESCE(is_deleted, FALSE) = FALSE
                ),
                running AS (
                    SELECT jobs.id, jobs.category_id, jobs.status, c.path
                    FROM category_migration_jobs jobs
                    JOIN categories c ON c.id = jobs.category_id
                    WHERE jobs.status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')
                )
                SELECT running.category_id::text AS category_id, running.id::text AS job_id, running.status
                FROM running
                JOIN target ON running.path @> target.path OR target.path @> running.path
                LIMIT 1
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_stale_category_migration_jobs(session: AsyncSession, *, stale_after_minutes: int) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT jobs.id, jobs.category_id
                FROM category_migration_jobs jobs
                WHERE jobs.status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')
                  AND jobs.updated_at < NOW() - make_interval(mins => :stale_after_minutes)
                """
            ),
            {"stale_after_minutes": stale_after_minutes},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def mark_category_migration_failed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE category_migration_jobs
            SET status = 'FAILED',
                error_message = COALESCE(error_message, 'Migration watchdog released stale job after timeout.'),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": job_id},
    )


async def unlock_category_workflow_status(session: AsyncSession, category_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE categories
            SET workflow_status = CASE
                WHEN status = 'ACTIVE' THEN 'APPROVED'
                WHEN status = 'INACTIVE' THEN 'APPROVED'
                ELSE status
            END,
            updated_at = NOW()
            WHERE id = :category_id
            """
        ),
        {"category_id": category_id},
    )


async def list_root_ids_for_categories(session: AsyncSession, ids: list[UUID]) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, path::text AS path
                FROM categories
                WHERE id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_visible_root_category_ids(session: AsyncSession) -> list[UUID]:
    return list(
        (
            await session.execute(
                text(
                    """
                    SELECT id
                    FROM categories
                    WHERE parent_id IS NULL
                      AND is_active = TRUE
                      AND status = 'ACTIVE'
                      AND COALESCE(is_deleted, FALSE) = FALSE
                    ORDER BY sort_order, name
                    """
                )
            )
        ).scalars().all()
    )


async def fetch_visible_category_branch(session: AsyncSession, root_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    c.id::text,
                    c.parent_id::text AS "parentId",
                    c.code,
                    c.slug,
                    c.name,
                    c.icon,
                    c.icon_url AS "iconUrl",
                    c.banner_url AS "bannerUrl",
                    COALESCE(c.spec_fields, '[]'::jsonb) AS "specFields",
                    c.filter_config AS "filterConfig",
                    c.sort_order AS "order",
                    COALESCE(
                        jsonb_agg(
                            DISTINCT jsonb_build_object(
                                'id', child.id::text,
                                'code', child.code,
                                'slug', child.slug,
                                'name', child.name,
                                'sortOrder', child.sort_order
                            )
                        ) FILTER (
                            WHERE child.id IS NOT NULL
                              AND COALESCE(child.is_deleted, FALSE) = FALSE
                              AND child.status = 'ACTIVE'
                        ),
                        '[]'::jsonb
                    ) AS children
                FROM categories c
                LEFT JOIN categories child ON child.parent_id = c.id
                WHERE c.id = :root_id
                  AND c.parent_id IS NULL
                  AND c.is_active = TRUE
                  AND c.status = 'ACTIVE'
                  AND COALESCE(c.is_deleted, FALSE) = FALSE
                GROUP BY c.id
                """
            ),
            {"root_id": root_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_visible_product_ids_in_category_branch(session: AsyncSession, category_id: UUID) -> list[UUID]:
    result = await session.execute(
        text(
            """
            WITH branch AS (
                SELECT path
                FROM categories
                WHERE id = :category_id
            )
            SELECT DISTINCT p.id
            FROM products p
            JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
            JOIN branch b ON c.path <@ b.path
            WHERE p.status = 'ACTIVE'
            """
        ),
        {"category_id": category_id},
    )
    return list(result.scalars().all())


async def hide_products_by_category(session: AsyncSession, product_ids: list[UUID]) -> None:
    await session.execute(
        text(
            """
            UPDATE products
            SET status = 'INACTIVE',
                hidden_by_category = TRUE,
                updated_at = NOW()
            WHERE id IN :ids
              AND status = 'ACTIVE'
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )


async def restore_products_hidden_by_category(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            WITH branch AS (
                SELECT path
                FROM categories
                WHERE id = :category_id
            ),
            restored AS (
                UPDATE products p
                SET status = 'ACTIVE',
                    hidden_by_category = FALSE,
                    updated_at = NOW()
                FROM categories c, branch branch_row
                WHERE c.id = COALESCE(p.subcategory_id, p.category_id)
                  AND c.path <@ branch_row.path
                  AND p.hidden_by_category = TRUE
                  AND p.hidden_by_brand = FALSE
                  AND p.status = 'INACTIVE'
                  AND c.status = 'ACTIVE'
                  AND c.is_active = TRUE
                  AND COALESCE(c.is_deleted, FALSE) = FALSE
                  AND NOT EXISTS (
                    SELECT 1
                    FROM brands b
                    WHERE b.id = p.brand_id
                      AND b.is_active = FALSE
                  )
                RETURNING p.id
            )
            SELECT id FROM restored
            """
        ),
        {"category_id": category_id},
    )
    product_ids = list(result.scalars().all())
    if product_ids:
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET is_active = TRUE,
                    updated_at = NOW()
                WHERE product_id IN :ids
                  AND deleted_at IS NULL
                  AND status NOT IN ('deleted', 'archived')
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": product_ids},
        )
    return len(product_ids)


async def enqueue_sitemap_refresh(session: AsyncSession, entity_type: str, entity_id: UUID | None, reason: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO sitemap_refresh_events (entity_type, entity_id, reason)
            VALUES (:entity_type, :entity_id, :reason)
            """
        ),
        {"entity_type": entity_type, "entity_id": entity_id, "reason": reason},
    )


async def audit_product_event(
    session: AsyncSession,
    product_id: UUID,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor_id: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_audit_logs (product_id, actor_id, action, old_value, new_value)
            VALUES (:product_id, :actor_id, :action, CAST(:old_value AS jsonb), CAST(:new_value AS jsonb))
            """
        ),
        {
            "product_id": product_id,
            "actor_id": actor_id,
            "action": action,
            "old_value": json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
            "new_value": json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
        },
    )


async def audit_category_event(
    session: AsyncSession,
    category_id: UUID,
    action_type: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor_id: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO category_audit_logs (category_id, actor_id, action_type, old_value, new_value)
            VALUES (:category_id, :actor_id, :action_type, CAST(:old_value AS jsonb), CAST(:new_value AS jsonb))
            """
        ),
        {
            "category_id": category_id,
            "actor_id": actor_id,
            "action_type": action_type,
            "old_value": json.dumps(old_value, ensure_ascii=False) if old_value is not None else None,
            "new_value": json.dumps(new_value, ensure_ascii=False) if new_value is not None else None,
        },
    )


async def category_redirect_loop_exists(session: AsyncSession, *, source_path: str, target_path: str) -> bool:
    return bool(
        (
            await session.execute(
                text(
                    """
                    WITH RECURSIVE chain AS (
                        SELECT source_path, target_path, ARRAY[source_path::text] AS visited
                        FROM url_redirects
                        WHERE source_path = :target_path
                          AND entity_type = 'category'
                        UNION ALL
                        SELECT r.source_path, r.target_path, chain.visited || r.source_path::text
                        FROM url_redirects r
                        JOIN chain ON r.source_path = chain.target_path
                        WHERE r.entity_type = 'category'
                          AND NOT r.source_path = ANY(chain.visited)
                          AND array_length(chain.visited, 1) < 20
                    )
                    SELECT 1
                    FROM chain
                    WHERE target_path = :source_path
                    LIMIT 1
                    """
                ),
                {"source_path": source_path, "target_path": target_path},
            )
        ).first()
    )


async def update_upstream_category_redirects(session: AsyncSession, *, category_id: UUID, source_path: str, target_path: str) -> None:
    await session.execute(
        text(
            """
            UPDATE url_redirects
            SET target_path = :target_path,
                entity_id = :entity_id,
                updated_at = NOW()
            WHERE source_path IN (
                WITH RECURSIVE upstream AS (
                    SELECT source_path, target_path, ARRAY[source_path::text] AS visited
                    FROM url_redirects
                    WHERE target_path = :source_path
                      AND entity_type = 'category'
                    UNION ALL
                    SELECT r.source_path, r.target_path, upstream.visited || r.source_path::text
                    FROM url_redirects r
                    JOIN upstream ON r.target_path = upstream.source_path
                    WHERE r.entity_type = 'category'
                      AND NOT r.source_path = ANY(upstream.visited)
                      AND array_length(upstream.visited, 1) < 20
                )
                SELECT source_path
                FROM upstream
            )
              AND entity_type = 'category'
            """
        ),
        {"source_path": source_path, "target_path": target_path, "entity_id": category_id},
    )


async def delete_category_redirect_by_source(session: AsyncSession, target_path: str) -> None:
    await session.execute(
        text("DELETE FROM url_redirects WHERE source_path = :target_path AND entity_type = 'category'"),
        {"target_path": target_path},
    )


async def upsert_category_redirect(session: AsyncSession, *, category_id: UUID, source_path: str, target_path: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO url_redirects (source_path, target_path, status_code, entity_type, entity_id)
            VALUES (:source_path, :target_path, 301, 'category', :entity_id)
            ON CONFLICT (source_path)
            DO UPDATE SET target_path = EXCLUDED.target_path, entity_id = EXCLUDED.entity_id, updated_at = NOW()
            """
        ),
        {"source_path": source_path, "target_path": target_path, "entity_id": category_id},
    )


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
            UPDATE categories
            SET is_active = TRUE,
                status = 'ACTIVE',
                previous_status = NULL,
                hidden_by_parent = FALSE,
                updated_at = NOW()
            WHERE parent_id = :id
              AND hidden_by_parent = TRUE
              AND previous_status = 'ACTIVE'
              AND COALESCE(is_deleted, FALSE) = FALSE
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
            UPDATE categories
            SET previous_status = status,
                is_active = FALSE,
                status = 'INACTIVE',
                hidden_by_parent = TRUE,
                updated_at = NOW()
            WHERE parent_id = :id
              AND is_active = TRUE
              AND COALESCE(is_deleted, FALSE) = FALSE
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
            WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE
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


async def insert_category_migration_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    category_id: UUID,
    old_parent_id: UUID | None,
    new_parent_id: UUID | None,
    total_products: int,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO category_migration_jobs (id, category_id, old_parent_id, new_parent_id, total_products)
            VALUES (:id, :category_id, :old_parent_id, :new_parent_id, :total_products)
            """
        ),
        {
            "id": job_id,
            "category_id": category_id,
            "old_parent_id": old_parent_id,
            "new_parent_id": new_parent_id,
            "total_products": total_products,
        },
    )


async def mark_category_workflow_migrating(session: AsyncSession, category_id: UUID) -> None:
    await session.execute(
        text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :id"),
        {"id": category_id},
    )


async def list_category_audit_logs(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                category_id::text AS "categoryId",
                actor_id::text AS "actorId",
                action_type AS "actionType",
                old_value AS "oldValue",
                new_value AS "newValue",
                created_at AS "createdAt"
            FROM category_audit_logs
            WHERE category_id = :category_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row._mapping) for row in result]


async def list_category_migration_jobs(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                category_id::text AS "categoryId",
                old_parent_id::text AS "oldParentId",
                new_parent_id::text AS "newParentId",
                status,
                total_products AS "totalProducts",
                processed_products AS "processedProducts",
                error_message AS "errorMessage",
                created_at AS "createdAt",
                updated_at AS "updatedAt",
                completed_at AS "completedAt"
            FROM category_migration_jobs
            WHERE category_id = :category_id
            ORDER BY created_at DESC
            LIMIT 50
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row._mapping) for row in result]


async def get_category_migration_job_metrics(session: AsyncSession, *, stale_after_minutes: int) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_jobs,
                    COUNT(*) FILTER (WHERE status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')) AS running_jobs,
                    COUNT(*) FILTER (
                        WHERE status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')
                          AND updated_at < NOW() - make_interval(mins => :stale_after_minutes)
                    ) AS stale_jobs,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) FILTER (WHERE completed_at IS NOT NULL), 0) AS avg_duration_seconds
                FROM category_migration_jobs
                """
            ),
            {"stale_after_minutes": stale_after_minutes},
        )
    ).mappings().one()
    return dict(row)


async def get_category_business_metrics(session: AsyncSession) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE c.status IN ('ACTIVE', 'APPROVED') AND COALESCE(c.is_deleted, FALSE) = FALSE) AS active_categories,
                    COUNT(*) FILTER (
                        WHERE c.status IN ('ACTIVE', 'APPROVED')
                          AND COALESCE(c.is_deleted, FALSE) = FALSE
                          AND COALESCE(product_counts.product_count, 0) = 0
                    ) AS empty_active_categories,
                    COALESCE(AVG(product_counts.product_count) FILTER (
                        WHERE c.status IN ('ACTIVE', 'APPROVED') AND COALESCE(c.is_deleted, FALSE) = FALSE
                    ), 0) AS avg_products_per_active_category
                FROM categories c
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS product_count
                    FROM products p
                    WHERE p.category_id = c.id OR p.subcategory_id = c.id
                ) product_counts ON TRUE
                """
            )
        )
    ).mappings().one()
    return dict(row)
