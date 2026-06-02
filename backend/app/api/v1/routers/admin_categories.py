import json
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.routers.admin_schemas import *
from app.api.v1.routers.admin_utils import (
    category_branch_cache_key,
    category_is_active,
    category_path_label,
    category_root_id_from_path,
    category_workflow_status,
    slugify,
)
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import AsyncSessionFactory, get_session


router = APIRouter()
CATEGORY_CACHE_ROOT_ORDER_KEY = "catalog:categories:roots:active"
CATEGORY_CACHE_ROOT_ORDER_STALE_KEY = "catalog:categories:roots:stale"
CATEGORY_MIGRATION_STALE_MINUTES = 30

def category_filter_config(spec_fields: list[dict], manual_filters: list[dict]) -> list[dict]:
    filters: list[dict] = []
    seen: set[str] = set()
    for field in spec_fields:
        key = str(field.get("key") or "").strip()
        if not key or key in seen or not field.get("isFilterable"):
            continue
        filters.append(
            {
                "key": key,
                "label": field.get("label") or key,
                "type": field.get("filterType") or ("range" if field.get("type") == "number" else "checkbox"),
                "enabled": field.get("filterEnabled", True),
                "source": "attribute",
            }
        )
        seen.add(key)
    for field in manual_filters:
        key = str(field.get("key") or "").strip()
        if not key or key in seen:
            continue
        filters.append({**field, "source": field.get("source") or "manual"})
        seen.add(key)
    return filters


def spec_type_changes(old_fields: list[dict] | None, new_fields: list[dict] | None) -> list[dict]:
    old_by_key = {str(field.get("key")): field for field in (old_fields or []) if field.get("key")}
    changes: list[dict] = []
    for field in new_fields or []:
        key = str(field.get("key") or "")
        old_field = old_by_key.get(key)
        if old_field and old_field.get("type") != field.get("type"):
            changes.append({"key": key, "from": old_field.get("type"), "to": field.get("type")})
    return changes


def spec_keys(fields: list[dict] | None) -> set[str]:
    return {str(field.get("key")).strip() for field in (fields or []) if str(field.get("key") or "").strip()}


async def ensure_no_category_cycle(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None) -> None:
    if not category_id or not parent_id:
        return
    if category_id == parent_id:
        raise HTTPException(status_code=422, detail="Danh mục không thể là cha của chính nó.")
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
    if row:
        raise HTTPException(status_code=422, detail="Không thể chọn danh mục con làm danh mục cha vì sẽ tạo vòng lặp.")


async def ensure_category_depth(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None, max_depth: int = 5) -> None:
    parent_depth = 0
    if parent_id:
        parent_depth = int(
            await session.execute(
                text("SELECT COALESCE(nlevel(path), 1) FROM categories WHERE id = :parent_id AND COALESCE(is_deleted, FALSE) = FALSE"),
                {"parent_id": parent_id},
            ).scalar()
            or 0
        )
        if parent_depth == 0:
            raise HTTPException(status_code=422, detail="Parent category not found.")
    subtree_depth = 1
    if category_id:
        subtree_depth = int(
            await session.execute(
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
            ).scalar()
            or 1
        )
    if parent_depth + subtree_depth > max_depth:
        raise HTTPException(status_code=422, detail=f"Category tree cannot exceed {max_depth} levels.")


async def ensure_spec_inheritance_safe(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None, own_fields: list[dict]) -> None:
    own_keys = spec_keys(own_fields)
    if not parent_id or not own_keys:
        return
    ancestor_rows = (
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
                WHERE (:category_id IS NULL OR id <> :category_id)
                """
            ),
            {"parent_id": parent_id, "category_id": category_id},
        )
    ).mappings().all()
    inherited_keys: set[str] = set()
    for row in ancestor_rows:
        inherited_keys.update(spec_keys(row["spec_fields"]))
    collisions = sorted(own_keys.intersection(inherited_keys))
    if collisions:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SPEC_INHERITANCE_COLLISION",
                "message": "Own spec fields must not duplicate keys inherited from parent categories.",
                "keys": collisions,
            },
        )


async def count_products_using_spec_keys(session: AsyncSession, category_id: UUID, keys: list[str]) -> int:
    if not keys:
        return 0
    return int(
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM products p
                WHERE (p.category_id = :category_id OR p.subcategory_id = :category_id)
                  AND p.specifications ?| CAST(:keys AS text[])
                """
            ),
            {"category_id": category_id, "keys": keys},
        ).scalar()
        or 0
    )


async def ensure_categories_not_migrating(session: AsyncSession, category_ids: list[UUID | None]) -> None:
    await recover_stale_category_migrations(session)
    ids = [item for item in category_ids if item]
    if not ids:
        return
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
    if row:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CATEGORY_MIGRATING",
                "message": "This category branch is migrating. Write actions are locked until the job completes.",
                "categoryId": row["category_id"],
                "jobId": row["job_id"],
                "status": row["status"],
            },
        )


async def recover_stale_category_migrations(session: AsyncSession, stale_after_minutes: int = CATEGORY_MIGRATION_STALE_MINUTES) -> list[str]:
    # Self-healing guard: nếu worker bị crash giữa chừng, job stale sẽ được
    # chuyển sang FAILED và category được mở khóa để admin không bị kẹt vô thời hạn.
    stale_rows = (
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
    if not stale_rows:
        return []
    released_ids: list[str] = []
    for row in stale_rows:
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
            {"id": row["id"]},
        )
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
            {"category_id": row["category_id"]},
        )
        released_ids.append(str(row["id"]))
    return released_ids


async def find_root_ids_for_categories(session: AsyncSession, category_ids: list[UUID | None]) -> list[UUID]:
    ids = [item for item in category_ids if item]
    if not ids:
        return []
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
    root_ids: list[UUID] = []
    for row in rows:
        root_id = category_root_id_from_path(row["path"])
        if root_id and root_id not in root_ids:
            root_ids.append(root_id)
    return root_ids


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
                    c.seo_title AS "seoTitle",
                    c.seo_description AS "seoDescription",
                    c.seo_keywords AS "seoKeywords",
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


async def rebuild_category_branch_cache(
    session: AsyncSession,
    redis: Redis,
    affected_root_ids: list[UUID] | None = None,
    removed_root_ids: list[UUID] | None = None,
) -> None:
    visible_root_ids = await list_visible_root_category_ids(session)
    await redis.setex(
        CATEGORY_CACHE_ROOT_ORDER_KEY,
        30 * 60,
        json.dumps([str(root_id) for root_id in visible_root_ids], ensure_ascii=False),
    )
    await redis.setex(
        CATEGORY_CACHE_ROOT_ORDER_STALE_KEY,
        24 * 60 * 60,
        json.dumps([str(root_id) for root_id in visible_root_ids], ensure_ascii=False),
    )

    target_root_ids = visible_root_ids if affected_root_ids is None else [root_id for root_id in visible_root_ids if root_id in affected_root_ids]
    for root_id in target_root_ids:
        branch = await fetch_visible_category_branch(session, root_id)
        if branch is None:
            await redis.delete(category_branch_cache_key(root_id), category_branch_cache_key(root_id, stale=True))
            continue
        payload = json.dumps(branch, ensure_ascii=False, default=str)
        await redis.setex(category_branch_cache_key(root_id), 30 * 60, payload)
        await redis.setex(category_branch_cache_key(root_id, stale=True), 24 * 60 * 60, payload)

    for root_id in removed_root_ids or []:
        await redis.delete(category_branch_cache_key(root_id), category_branch_cache_key(root_id, stale=True))

    branches: list[dict] = []
    for root_id in visible_root_ids:
        cached = await redis.get(category_branch_cache_key(root_id))
        if not cached:
            branch = await fetch_visible_category_branch(session, root_id)
            if branch is None:
                continue
            cached = json.dumps(branch, ensure_ascii=False, default=str)
            await redis.setex(category_branch_cache_key(root_id), 30 * 60, cached)
            await redis.setex(category_branch_cache_key(root_id, stale=True), 24 * 60 * 60, cached)
        branches.append(json.loads(cached))
    await redis.set("catalog:categories:tree:active", "catalog:categories:tree:branch-cache")
    await redis.setex("catalog:categories:tree:stale", 24 * 60 * 60, json.dumps(branches, ensure_ascii=False, default=str))


async def deactivate_products_in_category_branch(session: AsyncSession, category_id: UUID) -> int:
    # Khi một nhánh danh mục bị ẩn/xóa mềm, toàn bộ sản phẩm trong nhánh được chuyển
    # sang INACTIVE để storefront không giữ trạng thái "active nhưng không còn taxonomy".
    product_ids = list(
        (
            await session.execute(
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
                    WHERE p.status <> 'INACTIVE'
                    """
                ),
                {"category_id": category_id},
            )
        ).scalars().all()
    )
    if not product_ids:
        return 0
    await session.execute(
        text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id IN :ids").bindparams(bindparam("ids", expanding=True)),
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


async def record_category_redirect(session: AsyncSession, category_id: UUID, old_slug: str | None, new_slug: str | None) -> None:
    if not old_slug or not new_slug or old_slug == new_slug:
        return
    source_path = f"/category/{old_slug}"
    target_path = f"/category/{new_slug}"
    if (
        await session.execute(
            text(
                """
                WITH RECURSIVE chain AS (
                    SELECT source_path, target_path, ARRAY[source_path] AS visited
                    FROM url_redirects
                    WHERE source_path = :target_path
                      AND entity_type = 'category'
                    UNION ALL
                    SELECT r.source_path, r.target_path, chain.visited || r.source_path
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
    ).first():
        raise HTTPException(status_code=409, detail="Category redirect loop detected.")
    await session.execute(
        text(
            """
            UPDATE url_redirects
            SET target_path = :target_path,
                entity_id = :entity_id,
                updated_at = NOW()
            WHERE source_path IN (
                WITH RECURSIVE upstream AS (
                    SELECT source_path, target_path, ARRAY[source_path] AS visited
                    FROM url_redirects
                    WHERE target_path = :source_path
                      AND entity_type = 'category'
                    UNION ALL
                    SELECT r.source_path, r.target_path, upstream.visited || r.source_path
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
    await session.execute(
        text("DELETE FROM url_redirects WHERE source_path = :target_path AND entity_type = 'category'"),
        {"target_path": target_path},
    )
    await session.execute(
        text(
            """
            INSERT INTO url_redirects (source_path, target_path, status_code, entity_type, entity_id)
            VALUES (:source_path, :target_path, 301, 'category', :entity_id)
            ON CONFLICT (source_path)
            DO UPDATE SET target_path = EXCLUDED.target_path, entity_id = EXCLUDED.entity_id, updated_at = NOW()
            """
        ),
        {
            "source_path": source_path,
            "target_path": target_path,
            "entity_id": category_id,
        },
    )



@router.get("/categories", dependencies=[Depends(require_permission("category:read"))])
async def list_admin_categories(session: AsyncSession = Depends(get_session)) -> list[dict]:
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
                c.seo_title AS "seoTitle",
                c.seo_description AS "seoDescription",
                c.seo_keywords AS "seoKeywords",
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


@router.post("/categories/check-slug", dependencies=[Depends(require_permission("category:read"))])
async def check_category_slug(payload: CategorySlugCheckPayload, session: AsyncSession = Depends(get_session)) -> dict:
    params = {"slug": payload.slug, "exclude_id": payload.excludeId}
    row = (
        await session.execute(
            text(
                """
                SELECT 1
                FROM categories
                WHERE slug = :slug
                  AND COALESCE(is_deleted, FALSE) = FALSE
                  AND (:exclude_id IS NULL OR id <> :exclude_id)
                """
            ),
            params,
        )
    ).first()
    if row:
        raise HTTPException(status_code=409, detail="Slug danh mục đã tồn tại.")
    return {"available": True}


@router.post("/categories", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("category:create"))])
async def create_category(
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    category_id = uuid4()
    slug = payload.slug or f"{slugify(payload.name)}-{category_id.hex[:5]}"
    code = payload.code or slug
    category_status = payload.status
    is_active = category_is_active(category_status, payload.isActive)
    filter_config = category_filter_config(payload.specFields, payload.filterConfig)
    duplicate = (
        await session.execute(text("SELECT 1 FROM categories WHERE (slug = :slug OR code = :code) AND COALESCE(is_deleted, FALSE) = FALSE"), {"slug": slug, "code": code})
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Slug hoặc mã danh mục đã tồn tại.")
    await ensure_categories_not_migrating(session, [payload.parentId])
    await ensure_category_depth(session, None, payload.parentId)
    await ensure_spec_inheritance_safe(session, None, payload.parentId, payload.specFields)
    ensure_not_data_url(payload.iconUrl, "iconUrl")
    ensure_not_data_url(payload.bannerUrl, "bannerUrl")
    await session.execute(
        text(
            """
            INSERT INTO categories (
                id, parent_id, code, slug, name, icon, icon_url, banner_url,
                seo_title, seo_description, seo_keywords, spec_fields, filter_config,
                inventory_policy, warranty_policy, sort_order, status, workflow_status, is_active, path
            )
            VALUES (
                :id, :parent_id, :code, :slug, :name, :icon, :icon_url, :banner_url,
                :seo_title, :seo_description, :seo_keywords, CAST(:spec_fields AS jsonb),
                CAST(:filter_config AS jsonb), CAST(:inventory_policy AS jsonb), CAST(:warranty_policy AS jsonb),
                :sort_order, :status, :workflow_status, :is_active,
                CASE
                    WHEN :parent_id IS NULL THEN CAST(:path_label AS ltree)
                    ELSE (SELECT path FROM categories WHERE id = :parent_id) || CAST(:path_label AS ltree)
                END
            )
            """
        ),
        {
            "id": category_id,
            "parent_id": payload.parentId,
            "code": code,
            "slug": slug,
            "name": payload.name,
            "icon": payload.icon,
            "icon_url": payload.iconUrl,
            "banner_url": payload.bannerUrl,
            "seo_title": payload.seoTitle,
            "seo_description": payload.seoDescription,
            "seo_keywords": payload.seoKeywords,
            "spec_fields": json.dumps(payload.specFields),
            "filter_config": json.dumps(filter_config),
            "inventory_policy": json.dumps(payload.inventoryPolicy),
            "warranty_policy": json.dumps(payload.warrantyPolicy),
            "sort_order": payload.order,
            "status": category_status,
            "workflow_status": category_workflow_status(category_status),
            "is_active": is_active,
            "path_label": category_path_label(category_id),
        },
    )
    await audit_category_event(session, category_id, "CATEGORY_CREATED", new_value={"name": payload.name, "slug": slug, "status": category_status}, actor_id=actor_id)
    await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_CREATED")
    await session.commit()
    affected_root_ids = [category_id] if payload.parentId is None else await find_root_ids_for_categories(session, [payload.parentId])
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
    return {"id": str(category_id)}


@router.patch("/categories/reorder", dependencies=[Depends(require_permission("category:update"))])
async def reorder_categories(
    payload: CategoryReorderPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    ids = [item.id for item in payload.items]
    await ensure_categories_not_migrating(session, ids)
    rows = (
        await session.execute(
            text("SELECT id, parent_id FROM categories WHERE id IN :ids AND COALESCE(is_deleted, FALSE) = FALSE").bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
    ).mappings().all()
    if len(rows) != len(set(ids)):
        raise HTTPException(status_code=404, detail="Một hoặc nhiều danh mục không tồn tại.")
    parent_by_id = {row["id"]: row["parent_id"] for row in rows}
    for item in payload.items:
        if parent_by_id[item.id] != item.parentId:
            raise HTTPException(status_code=422, detail="Chỉ được sắp xếp danh mục trong cùng một cấp.")
    parent_keys = {str(item.parentId or "root") for item in payload.items}
    if len(parent_keys) != 1:
        raise HTTPException(status_code=422, detail="Chỉ được sắp xếp một nhóm danh mục trong mỗi lần thao tác.")
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"category-reorder:{next(iter(parent_keys))}"})
    for item in payload.items:
        await session.execute(
            text("UPDATE categories SET sort_order = :sort_order, updated_at = NOW() WHERE id = :id"),
            {"id": item.id, "sort_order": item.order},
        )
        await audit_category_event(session, item.id, "CATEGORY_REORDERED", new_value={"order": item.order, "parentId": str(item.parentId) if item.parentId else None}, actor_id=actor_id)
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=await find_root_ids_for_categories(session, ids))
    return {"ok": True}


@router.put("/categories/bulk", dependencies=[Depends(require_permission("category:update"))])
async def bulk_update_categories(
    payload: CategoryBulkPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    updated = 0
    impacted_ids: list[UUID] = []
    if payload.items:
        ids = [item.id for item in payload.items]
        impacted_ids.extend(ids)
        await ensure_categories_not_migrating(session, ids)
        rows = (
            await session.execute(
                text("SELECT id, parent_id FROM categories WHERE id IN :ids AND COALESCE(is_deleted, FALSE) = FALSE").bindparams(bindparam("ids", expanding=True)),
                {"ids": ids},
            )
        ).mappings().all()
        if len(rows) != len(set(ids)):
            raise HTTPException(status_code=404, detail="Một hoặc nhiều danh mục không tồn tại.")
        parent_by_id = {row["id"]: row["parent_id"] for row in rows}
        for item in payload.items:
            if parent_by_id[item.id] != item.parentId:
                raise HTTPException(status_code=422, detail="Chỉ được cập nhật thứ tự trong cùng một cấp.")
        for item in payload.items:
            result = await session.execute(
                text("UPDATE categories SET sort_order = :sort_order, updated_at = NOW() WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE"),
                {"id": item.id, "sort_order": item.order},
            )
            updated += result.rowcount or 0
            await audit_category_event(session, item.id, "CATEGORY_BULK_REORDERED", new_value={"order": item.order}, actor_id=actor_id)
    if payload.status and payload.ids:
        impacted_ids.extend(payload.ids)
        await ensure_categories_not_migrating(session, payload.ids)
        is_active = category_is_active(payload.status, True)
        result = await session.execute(
            text("UPDATE categories SET status = :status, workflow_status = :workflow_status, is_active = :is_active, version = version + 1, updated_at = NOW() WHERE id IN :ids AND COALESCE(is_deleted, FALSE) = FALSE").bindparams(bindparam("ids", expanding=True)),
            {"ids": payload.ids, "status": payload.status, "workflow_status": category_workflow_status(payload.status), "is_active": is_active},
        )
        updated += result.rowcount or 0
        for category_id in payload.ids:
            await audit_category_event(session, category_id, "CATEGORY_BULK_STATUS_CHANGED", new_value={"status": payload.status}, actor_id=actor_id)
            await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_BULK_STATUS_CHANGED")
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=await find_root_ids_for_categories(session, impacted_ids))
    return {"updated": updated}


@router.patch("/categories/{category_id}", dependencies=[Depends(require_permission("category:update"))])
async def update_category(
    category_id: UUID,
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    slug = payload.slug or f"{slugify(payload.name)}-{str(category_id)[:5]}"
    code = payload.code or slug
    category_status = payload.status
    is_active = category_is_active(category_status, payload.isActive)
    spec_fields = payload.specFields
    filter_config = category_filter_config(spec_fields, payload.filterConfig)
    existing = (
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
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found.")
    if payload.version is not None and int(existing["version"] or 0) != payload.version:
        raise HTTPException(status_code=409, detail="Category was updated by another admin. Reload before saving.")
    old_root_id = category_root_id_from_path(existing["path"])
    await ensure_categories_not_migrating(session, [category_id, existing["parent_id"], payload.parentId])
    await ensure_no_category_cycle(session, category_id, payload.parentId)
    await ensure_category_depth(session, category_id, payload.parentId)
    await ensure_spec_inheritance_safe(session, category_id, payload.parentId, spec_fields)
    changed_spec_types = spec_type_changes(existing["specFields"], spec_fields)
    impacted_spec_products = await count_products_using_spec_keys(session, category_id, [item["key"] for item in changed_spec_types])
    if changed_spec_types and impacted_spec_products > 0 and not payload.allowSpecTypeMigration:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SPEC_TYPE_CHANGE_REQUIRES_CONFIRMATION",
                "message": f"Thay đổi kiểu thông số sẽ ảnh hưởng {impacted_spec_products} sản phẩm hiện tại.",
                "impactedProducts": impacted_spec_products,
                "changes": changed_spec_types,
            },
        )
    duplicate = (
        await session.execute(
            text("SELECT 1 FROM categories WHERE id <> :id AND (slug = :slug OR code = :code) AND COALESCE(is_deleted, FALSE) = FALSE"),
            {"id": category_id, "slug": slug, "code": code},
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Slug hoặc mã danh mục đã tồn tại.")
    ensure_not_data_url(payload.iconUrl, "iconUrl")
    ensure_not_data_url(payload.bannerUrl, "bannerUrl")
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
                seo_title = :seo_title,
                seo_description = :seo_description,
                seo_keywords = :seo_keywords,
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
                    WHEN :parent_id IS NULL THEN CAST(:path_label AS ltree)
                    ELSE (SELECT parent.path FROM categories parent WHERE parent.id = :parent_id) || CAST(:path_label AS ltree)
                END,
                hidden_by_parent = CASE WHEN :is_active THEN FALSE ELSE hidden_by_parent END,
                updated_at = NOW()
            WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE
            """
        ),
        {
            "id": category_id,
            "parent_id": payload.parentId,
            "code": code,
            "slug": slug,
            "name": payload.name,
            "icon": payload.icon,
            "icon_url": payload.iconUrl,
            "banner_url": payload.bannerUrl,
            "seo_title": payload.seoTitle,
            "seo_description": payload.seoDescription,
            "seo_keywords": payload.seoKeywords,
            "spec_fields": json.dumps(spec_fields),
            "filter_config": json.dumps(filter_config),
            "inventory_policy": json.dumps(payload.inventoryPolicy),
            "warranty_policy": json.dumps(payload.warrantyPolicy),
            "sort_order": payload.order,
            "status": category_status,
            "workflow_status": category_workflow_status(category_status),
            "is_active": is_active,
            "spec_version_delta": 1 if changed_spec_types else 0,
            "path_label": category_path_label(category_id),
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
    if existing["parent_id"] != payload.parentId and existing["path"]:
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
            {"id": category_id, "old_path": existing["path"]},
        )
    await record_category_redirect(session, category_id, existing["slug"], slug)
    if existing["slug"] != slug:
        await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_SLUG_CHANGED")
    if existing["parent_id"] != payload.parentId and int(existing["product_count"] or 0) > 0:
        job_id = uuid4()
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
                "old_parent_id": existing["parent_id"],
                "new_parent_id": payload.parentId,
                "total_products": int(existing["product_count"] or 0),
            },
        )
        await session.execute(
            text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :id"),
            {"id": category_id},
        )
        background_tasks.add_task(process_category_migration_job, job_id, category_id, existing["parent_id"], payload.parentId)
    await audit_category_event(
        session,
        category_id,
        "CATEGORY_UPDATED",
        old_value={
            "name": existing["name"],
            "slug": existing["slug"],
            "status": existing["status"],
            "isActive": existing["is_active"],
            "specFields": existing["specFields"],
            "filterConfig": existing["filterConfig"],
        },
        new_value={
            "name": payload.name,
            "slug": slug,
            "status": category_status,
            "isActive": is_active,
            "specFields": spec_fields,
            "filterConfig": filter_config,
            "specTypeChanges": changed_spec_types,
        },
        actor_id=actor_id,
    )
    await session.commit()
    new_root_ids = [category_id] if payload.parentId is None else await find_root_ids_for_categories(session, [payload.parentId, category_id])
    affected_root_ids = [root_id for root_id in [old_root_id, *new_root_ids] if root_id]
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
    return {"ok": True}


@router.patch("/categories/{category_id}/restore", dependencies=[Depends(require_permission("category:update"))])
async def restore_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    affected_root_ids = await find_root_ids_for_categories(session, [category_id])
    result = await session.execute(
        text("UPDATE categories SET is_active = TRUE, status = 'ACTIVE', hidden_by_parent = FALSE, updated_at = NOW() WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"id": category_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
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
    await audit_category_event(session, category_id, "CATEGORY_RESTORED", new_value={"status": "ACTIVE"}, actor_id=actor_id)
    await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_RESTORED")
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
    return {"ok": True}


@router.delete("/categories/{category_id}", dependencies=[Depends(require_permission("category:delete"))])
async def deactivate_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    affected_root_ids = await find_root_ids_for_categories(session, [category_id])
    await ensure_categories_not_migrating(session, [category_id])
    result = await session.execute(
        text("UPDATE categories SET is_active = FALSE, status = 'INACTIVE', is_deleted = TRUE, deleted_at = NOW(), hidden_by_parent = FALSE, updated_at = NOW() WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"id": category_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
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
    affected_products = await deactivate_products_in_category_branch(session, category_id)
    await audit_category_event(
        session,
        category_id,
        "CATEGORY_SOFT_DELETED",
        new_value={"isDeleted": True, "status": "INACTIVE", "affectedProducts": affected_products},
        actor_id=actor_id,
    )
    await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_SOFT_DELETED")
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids, removed_root_ids=affected_root_ids)
    return {"ok": True, "action": "soft_deleted", "affectedProducts": affected_products}


@router.get("/categories/{category_id}/audit-logs", dependencies=[Depends(require_permission("category:read"))])
async def list_category_audit_logs(category_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
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


@router.get("/categories/{category_id}/migration-jobs", dependencies=[Depends(require_permission("category:read"))])
async def list_category_migration_jobs(category_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    await recover_stale_category_migrations(session)
    await session.commit()
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


@router.get("/categories/ops/metrics", dependencies=[Depends(require_permission("category:read"))])
async def category_operational_metrics(session: AsyncSession = Depends(get_session), redis: Redis = Depends(get_redis)) -> dict:
    recovered_jobs = await recover_stale_category_migrations(session)
    if recovered_jobs:
        await session.commit()
    try:
        hits = int(await redis.get("metrics:catalog_categories:cache_hit") or 0)
        misses = int(await redis.get("metrics:catalog_categories:cache_miss") or 0)
        samples = [int(item) for item in await redis.lrange("metrics:catalog_categories:latency_ms", 0, 499)]
    except Exception:
        hits = 0
        misses = 0
        samples = []
    total = hits + misses
    sorted_samples = sorted(samples)
    p99_index = max(0, min(len(sorted_samples) - 1, int(len(sorted_samples) * 0.99) - 1)) if sorted_samples else 0
    job_metrics = (
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
            {"stale_after_minutes": CATEGORY_MIGRATION_STALE_MINUTES},
        )
    ).mappings().one()
    business_metrics = (
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
    return {
        "cacheHits": hits,
        "cacheMisses": misses,
        "cacheHitRatio": hits / total if total else 0,
        "latencyP99Ms": sorted_samples[p99_index] if sorted_samples else 0,
        "sampleSize": len(samples),
        "migrationFailedJobs": int(job_metrics["failed_jobs"] or 0),
        "migrationRunningJobs": int(job_metrics["running_jobs"] or 0),
        "migrationStaleJobs": int(job_metrics["stale_jobs"] or 0),
        "migrationWatchdogRecoveredJobs": len(recovered_jobs),
        "migrationAverageDurationSeconds": float(job_metrics["avg_duration_seconds"] or 0),
        "activeCategories": int(business_metrics["active_categories"] or 0),
        "emptyActiveCategories": int(business_metrics["empty_active_categories"] or 0),
        "averageProductsPerActiveCategory": float(business_metrics["avg_products_per_active_category"] or 0),
    }


