import io
import json
import re
import csv
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.application.brands.import_jobs import audit_brand_event, bump_brand_cache_versions, enqueue_brand_import_job
from app.config import settings
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import AsyncSessionFactory, get_session
from app.shared.reviews import sanitize_review_text, sync_product_review_stats


router = APIRouter(prefix="/admin", tags=["Admin"])

# Cache danh mục được tách theo root branch để các thay đổi trong một nhánh
# không bắt buộc phải rebuild lại toàn bộ cây danh mục.
CATEGORY_CACHE_ROOT_ORDER_KEY = "catalog:categories:roots:active"
CATEGORY_CACHE_ROOT_ORDER_STALE_KEY = "catalog:categories:roots:stale"
CATEGORY_MIGRATION_STALE_MINUTES = 30


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip()).replace("đ", "d").replace("Đ", "D")
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in normalized)
    return "-".join(part for part in slug.split("-") if part) or uuid4().hex[:8]


def category_path_label(category_id: UUID) -> str:
    return f"c_{str(category_id).replace('-', '')}"


def category_root_id_from_path(path_value: str | None) -> UUID | None:
    if not path_value:
        return None
    label = str(path_value).split(".", 1)[0].strip()
    if not label.startswith("c_"):
        return None
    raw = label[2:]
    if len(raw) != 32:
        return None
    try:
        return UUID(f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}")
    except ValueError:
        return None


def category_branch_cache_key(root_id: UUID | str, stale: bool = False) -> str:
    suffix = "stale" if stale else "active"
    return f"catalog:categories:branch:{root_id}:{suffix}"


def category_is_active(status_value: str, requested_active: bool) -> bool:
    return status_value in {"ACTIVE", "APPROVED"} and requested_active


def category_workflow_status(status_value: str) -> str:
    if status_value == "ACTIVE":
        return "APPROVED"
    if status_value == "INACTIVE":
        return "APPROVED"
    return status_value


DATA_URL_PATTERN = re.compile(r"^data:", re.IGNORECASE)
ALLOWED_UPLOAD_FOLDERS = {"products", "brands", "categories", "content"}
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024


def ensure_not_data_url(value: str | None, field_name: str) -> None:
    if value and DATA_URL_PATTERN.match(value):
        raise HTTPException(status_code=400, detail=f"{field_name} must be an uploaded URL, not a Base64 data URL.")


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


def normalize_status(value: str) -> str:
    return value if value in {"DRAFT", "REVISION_DRAFT", "PENDING", "ACTIVE", "INACTIVE", "ARCHIVED"} else "DRAFT"


def stock_state(quantity: int | None) -> str:
    return "IN_STOCK" if int(quantity or 0) > 0 else "OUT_OF_STOCK"


def display_status(status_value: str | None, quantity: int | None) -> str:
    if status_value == "ACTIVE" and stock_state(quantity) == "OUT_OF_STOCK":
        return "Hết hàng"
    labels = {
        "DRAFT": "Nháp",
        "PENDING": "Chờ duyệt",
        "ACTIVE": "Đang bán",
        "INACTIVE": "Tạm ẩn",
        "ARCHIVED": "Lưu trữ",
    }
    return labels.get(status_value or "", status_value or "Nháp")


async def resolve_catalog_labels(session: AsyncSession, payload: "ProductPayload") -> tuple[str, str]:
    category = payload.category or "ACCESSORY"
    brand = payload.brand or "Khac"
    if payload.categoryId:
        category_row = (
            await session.execute(
                text("SELECT COALESCE(code, slug, name) AS label FROM categories WHERE id = :id"),
                {"id": payload.categoryId},
            )
        ).mappings().first()
        if not category_row:
            raise HTTPException(status_code=400, detail="Category not found.")
        category = str(category_row["label"] or category).upper()
    if payload.subcategoryId:
        subcategory_exists = (
            await session.execute(text("SELECT 1 FROM categories WHERE id = :id"), {"id": payload.subcategoryId})
        ).first()
        if not subcategory_exists:
            raise HTTPException(status_code=400, detail="Subcategory not found.")
    if payload.brandId:
        brand_row = (
            await session.execute(text("SELECT name FROM brands WHERE id = :id"), {"id": payload.brandId})
        ).mappings().first()
        if not brand_row:
            raise HTTPException(status_code=400, detail="Brand not found.")
        brand = str(brand_row["name"] or brand)
    return category, brand


async def upsert_product_variants(session: AsyncSession, product_id: UUID, variants: list["ProductVariantPayload"]) -> None:
    incoming_ids = [variant.id for variant in variants if variant.id]
    if incoming_ids:
        existing_rows = (
            await session.execute(
                text(
                    """
                    SELECT id
                    FROM product_variants
                    WHERE id IN :ids AND product_id = :product_id
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": incoming_ids, "product_id": product_id},
            )
        ).scalars().all()
        if {str(item) for item in existing_rows} != {str(item) for item in incoming_ids}:
            raise HTTPException(status_code=400, detail="One or more variants do not belong to this product.")
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET is_active = FALSE, updated_at = NOW()
                WHERE product_id = :product_id
                  AND id NOT IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"product_id": product_id, "ids": incoming_ids},
        )
    else:
        await session.execute(
            text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"),
            {"product_id": product_id},
        )
    for index, variant in enumerate(variants, start=1):
        ensure_not_data_url(variant.imageUrl, "variant.imageUrl")
        values = {
            "id": variant.id or uuid4(),
            "product_id": product_id,
            "sku": variant.sku or f"VAR-{product_id.hex[:8].upper()}-{index}",
            "color_name": variant.colorName,
            "color_code": variant.colorCode,
            "storage": variant.storage,
            "ram": variant.ram,
            "configuration": variant.configuration,
            "specs": json.dumps(variant.specs),
            "image_url": variant.imageUrl,
            "price": variant.price,
            "sale_price": variant.salePrice,
            "stock_quantity": 0,
            "is_active": variant.isActive,
        }
        if variant.id:
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET sku = :sku, color_name = :color_name, color_code = :color_code,
                        storage = :storage, ram = :ram, configuration = :configuration,
                        specs = CAST(:specs AS jsonb), image_url = :image_url,
                        price = :price, sale_price = :sale_price,
                        is_active = :is_active,
                        updated_at = NOW()
                    WHERE id = :id AND product_id = :product_id
                    """
                ),
                values,
            )
        else:
            await session.execute(
                text(
                    """
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, price, sale_price, stock_quantity, is_active
                    )
                    VALUES (
                        :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                        CAST(:specs AS jsonb), :image_url, :price, :sale_price, :stock_quantity, :is_active
                    )
                    """
                ),
                values,
            )


def split_relation_tokens(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def extract_product_metadata(specifications: dict) -> tuple[dict, dict, dict]:
    specs = dict(specifications or {})
    raw_accessory_offers = specs.pop("_accessoryOffers", [])
    accessory_offers = raw_accessory_offers if isinstance(raw_accessory_offers, list) else []
    seo = {
        "title": specs.pop("_seoTitle", "") or "",
        "description": specs.pop("_seoDescription", "") or "",
        "slug": specs.pop("_seoSlug", "") or "",
    }
    sales_config = {
        "warrantyPolicy": specs.pop("_warrantyPolicy", "") or "",
        "bundleRefs": split_relation_tokens(specs.pop("_bundleProducts", "")),
        "accessoryRefs": split_relation_tokens(specs.pop("_accessoryProducts", "")),
        "accessoryOffers": accessory_offers,
        "variantSpecKeys": specs.get("_variantSpecKeys", []),
    }
    return specs, seo, sales_config


def persisted_sales_config(sales_config: dict) -> dict:
    normalized_accessory_offers: list[dict] = []
    for item in sales_config.get("accessoryOffers", []) or []:
        if not isinstance(item, dict):
            continue
        product_id = str(item.get("productId") or "").strip()
        discount_type = str(item.get("discountType") or "PERCENT").upper()
        if not product_id or discount_type not in {"FIXED", "PERCENT"}:
            continue
        normalized_accessory_offers.append(
            {
                "productId": product_id,
                "discountType": discount_type,
                "discountValue": max(0, float(item.get("discountValue") or 0)),
                "maxQuantity": max(1, int(item.get("maxQuantity") or 1)),
            }
        )
    return {
        "warrantyPolicy": sales_config.get("warrantyPolicy", "") or "",
        "variantSpecKeys": sales_config.get("variantSpecKeys", []) or [],
        "accessoryOffers": normalized_accessory_offers,
        "minimumStock": max(0, int(sales_config.get("minimumStock") or 0)),
        "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
        "preferredLocationCode": sales_config.get("preferredLocationCode", "") or "",
        "preferredLocationName": sales_config.get("preferredLocationName", "") or "",
        "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
    }


def validate_optimized_media(payload: "ProductPayload") -> None:
    media = payload.mediaMetadata or {}
    images = media.get("images") if isinstance(media.get("images"), list) else []
    for item in images:
        if not isinstance(item, dict):
            continue
        size = int(item.get("size") or 0)
        content_type = str(item.get("contentType") or "")
        variants = item.get("variants") if isinstance(item.get("variants"), dict) else {}
        if size > MAX_PRODUCT_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail="Product image must be optimized before saving.")
        if content_type and content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported product image type.")
        if item.get("url") and not variants:
            raise HTTPException(status_code=400, detail="Product media must include optimized thumbnail/medium/large URLs.")


async def resolve_product_refs(session: AsyncSession, refs: list[str], owner_id: UUID) -> list[UUID]:
    if not refs:
        return []
    result = await session.execute(
        text(
            """
            SELECT id
            FROM products
            WHERE id::text IN :refs OR sku IN :refs
            """
        ).bindparams(bindparam("refs", expanding=True)),
        {"refs": refs},
    )
    ids = [item for item in result.scalars().all() if item != owner_id]
    return list(dict.fromkeys(ids))


async def sync_product_relations(session: AsyncSession, product_id: UUID, sales_config: dict) -> None:
    bundle_ids = await resolve_product_refs(session, split_relation_tokens(sales_config.get("bundleRefs")), product_id)
    accessory_offer_refs = [
        str(item.get("productId")).strip()
        for item in sales_config.get("accessoryOffers", []) or []
        if isinstance(item, dict) and str(item.get("productId") or "").strip()
    ]
    accessory_ids = await resolve_product_refs(
        session,
        accessory_offer_refs or split_relation_tokens(sales_config.get("accessoryRefs")),
        product_id,
    )
    await session.execute(text("DELETE FROM product_bundles WHERE product_id = :product_id"), {"product_id": product_id})
    await session.execute(text("DELETE FROM product_accessories WHERE product_id = :product_id"), {"product_id": product_id})
    for bundled_id in bundle_ids:
        await session.execute(
            text(
                """
                INSERT INTO product_bundles (product_id, bundled_product_id)
                VALUES (:product_id, :related_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"product_id": product_id, "related_id": bundled_id},
        )
    for accessory_id in accessory_ids:
        await session.execute(
            text(
                """
                INSERT INTO product_accessories (product_id, accessory_product_id)
                VALUES (:product_id, :related_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"product_id": product_id, "related_id": accessory_id},
        )


async def sync_parent_price_from_variants(session: AsyncSession, product_id: UUID) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    MIN(price) FILTER (WHERE stock_quantity > 0) AS min_in_stock_price,
                    MIN(COALESCE(sale_price, price)) FILTER (WHERE stock_quantity > 0) AS min_in_stock_sale_price,
                    MIN(price) AS min_price,
                    MIN(COALESCE(sale_price, price)) AS min_sale_price
                FROM product_variants
                WHERE product_id = :product_id AND is_active = TRUE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    if row and (row["min_in_stock_price"] is not None or row["min_price"] is not None):
        price = row["min_in_stock_price"] if row["min_in_stock_price"] is not None else row["min_price"]
        sale_price = row["min_in_stock_sale_price"] if row["min_in_stock_sale_price"] is not None else row["min_sale_price"]
        await session.execute(
            text(
                """
                UPDATE products
                SET price = :price,
                    sale_price = :sale_price,
                    is_price_out_of_stock = :is_price_out_of_stock,
                    updated_at = NOW()
                WHERE id = :product_id
                """
            ),
            {
                "product_id": product_id,
                "price": price,
                "sale_price": sale_price,
                "is_price_out_of_stock": row["min_in_stock_price"] is None,
            },
        )


async def process_brand_status_job(job_id: UUID, brand_id: UUID, target_is_active: bool) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("UPDATE brand_status_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
            total = (
                await session.execute(text("SELECT COUNT(*) FROM products WHERE brand_id = :brand_id"), {"brand_id": brand_id})
            ).scalar_one()
            await session.execute(text("UPDATE brand_status_jobs SET total_products = :total WHERE id = :id"), {"id": job_id, "total": total})
            if not target_is_active:
                product_rows = (
                    await session.execute(text("SELECT id FROM products WHERE brand_id = :brand_id AND status = 'ACTIVE'"), {"brand_id": brand_id})
                ).scalars().all()
                for index in range(0, len(product_rows), 100):
                    chunk = product_rows[index:index + 100]
                    if not chunk:
                        continue
                    await session.execute(
                        text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
                        {"ids": chunk},
                    )
                    await session.execute(
                        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id IN :ids").bindparams(bindparam("ids", expanding=True)),
                        {"ids": chunk},
                    )
                    await session.execute(
                        text("UPDATE brand_status_jobs SET processed_products = processed_products + :count, updated_at = NOW() WHERE id = :id"),
                        {"id": job_id, "count": len(chunk)},
                    )
                    await session.commit()
            await session.execute(text("UPDATE brand_status_jobs SET status = 'COMPLETED', processed_products = total_products, updated_at = NOW() WHERE id = :id"), {"id": job_id})
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE brand_status_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.commit()


class CategoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    icon: str | None = Field(default=None, max_length=80)
    iconUrl: str | None = None
    bannerUrl: str | None = None
    parentId: UUID | None = None
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    status: str = Field(default="ACTIVE", pattern="^(DRAFT|PENDING_REVIEW|APPROVED|ACTIVE|INACTIVE|REJECTED)$")
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None
    seoKeywords: str | None = None
    specFields: list[dict] = Field(default_factory=list)
    filterConfig: list[dict] = Field(default_factory=list)
    allowSpecTypeMigration: bool = False
    version: int | None = Field(default=None, ge=1)


class CategorySlugCheckPayload(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    excludeId: UUID | None = None


class CategoryReorderItem(BaseModel):
    id: UUID
    order: int = Field(ge=0)
    parentId: UUID | None = None


class CategoryReorderPayload(BaseModel):
    items: list[CategoryReorderItem] = Field(min_length=1)


class CategoryBulkPayload(BaseModel):
    items: list[CategoryReorderItem] | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, pattern="^(DRAFT|ACTIVE|INACTIVE)$")
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=200)


class BrandPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    categoryIds: list[UUID] = Field(default_factory=list)
    logoUrl: str | None = None
    logoAltText: str | None = Field(default=None, max_length=255)
    landingTitle: str | None = Field(default=None, max_length=255)
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None


class BrandCodeCheckPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    excludeId: UUID | None = None


class BrandImportItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    logoUrl: str | None = None
    order: int = Field(default=0, ge=0)


class BrandImportPayload(BaseModel):
    items: list[BrandImportItem] = Field(min_length=1, max_length=500)
    mode: str = Field(default="skip", pattern="^(skip|upsert)$")
    sourceFilename: str | None = Field(default=None, max_length=255)


class BrandStatusPayload(BaseModel):
    isActive: bool


class BrandBulkStatusPayload(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    isActive: bool


class ProductBulkActionPayload(BaseModel):
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    productIds: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    action: str = Field(default="APPROVE", pattern="^(APPROVE|ARCHIVE|DELETE)$")


class ProductImportPayload(BaseModel):
    sourceFilename: str


class ProductVariantPayload(BaseModel):
    id: UUID | None = None
    sku: str | None = Field(default=None, max_length=120)
    colorName: str | None = Field(default=None, max_length=100)
    colorCode: str | None = Field(default=None, max_length=30)
    storage: str | None = Field(default=None, max_length=80)
    ram: str | None = Field(default=None, max_length=80)
    configuration: str | None = Field(default=None, max_length=160)
    specs: dict = Field(default_factory=dict)
    imageUrl: str | None = None
    price: float = Field(ge=0)
    salePrice: float | None = Field(default=None, ge=0)
    stockQuantity: int = Field(default=0, ge=0)
    isActive: bool = True


class ProductAccessoryOfferPayload(BaseModel):
    productId: UUID
    discountType: str = Field(default="PERCENT", pattern="^(FIXED|PERCENT)$")
    discountValue: float = Field(ge=0)
    maxQuantity: int = Field(default=1, ge=1, le=999)


class ProductPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(ge=0)
    discountPrice: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    brand: str = Field(default="Khac", max_length=100)
    category: str = Field(default="ACCESSORY", max_length=50)
    categoryId: UUID | None = None
    subcategoryId: UUID | None = None
    brandId: UUID | None = None
    imageUrl: str | None = None
    images: list[str] = Field(default_factory=list)
    mediaMetadata: dict = Field(default_factory=dict)
    videoUrl: str | None = None
    description: str | None = None
    specifications: dict = Field(default_factory=dict)
    variants: list[ProductVariantPayload] = Field(default_factory=list)
    isFeatured: bool = False
    isFlashSale: bool = False
    status: str = Field(default="DRAFT", max_length=30)
    updatedAt: str | None = None
    version: int | None = Field(default=None, ge=1)


class PresignedUploadPayload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    contentType: str = Field(min_length=1, max_length=120)
    size: int = Field(gt=0)
    folder: str = Field(default="products", max_length=40)


class InventoryAdjustmentPayload(BaseModel):
    variantId: UUID | None = None
    delta: int | None = None
    quantity: int | None = Field(default=None, ge=0)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    supplierName: str | None = Field(default=None, max_length=160)
    unitCost: float | None = Field(default=None, ge=0)
    locationCode: str | None = Field(default=None, max_length=60)
    locationName: str | None = Field(default=None, max_length=160)


class InventoryPolicyPayload(BaseModel):
    minimumStock: int = Field(default=0, ge=0)
    blockSaleWhenOutOfStock: bool = True
    preferredLocationCode: str | None = Field(default=None, max_length=60)
    preferredLocationName: str | None = Field(default=None, max_length=160)
    cycleCountDays: int | None = Field(default=None, ge=1, le=365)


class VariantInventoryPayload(BaseModel):
    quantity: int = Field(ge=0)
    referenceCode: str = Field(min_length=1, max_length=120)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    reason: str = Field(default="MANUAL_SET", max_length=80)
    note: str | None = Field(default=None, max_length=500)


class VoucherPayload(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    discountType: str = Field(default="FIXED", max_length=20)
    discountAmount: float = Field(gt=0)
    minOrderValue: float = Field(default=0, ge=0)
    maxDiscount: float | None = Field(default=None, ge=0)
    usageLimit: int = Field(default=0, ge=0)
    totalBudgetCap: float | None = Field(default=None, ge=0)
    perUserLimit: int = Field(default=0, ge=0)
    perDeviceLimit: int = Field(default=0, ge=0)
    perIpLimit: int = Field(default=0, ge=0)
    campaignType: str = Field(default="CONVERSION", max_length=40)
    audienceType: str = Field(default="PUBLIC", max_length=40)
    eligibleTiers: list[str] = Field(default_factory=list)
    eligibleUserRegisteredAfter: str | None = None
    assignedUserId: UUID | None = None
    includeProductIds: list[str] = Field(default_factory=list)
    excludeProductIds: list[str] = Field(default_factory=list)
    includeCategoryIds: list[str] = Field(default_factory=list)
    excludeCategoryIds: list[str] = Field(default_factory=list)
    firstOrderOnly: bool = False
    hiddenCode: bool = False
    abandonedCartOnly: bool = False
    validityDaysAfterClaim: int = Field(default=0, ge=0)
    stackable: bool = False
    refundPolicy: str = Field(default="SHOP_FAULT_ONLY", max_length=40)
    startsAt: str | None = None
    endsAt: str | None = None
    internalNote: str | None = None
    status: str = Field(default="ACTIVE", max_length=30)


class PolicyPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(default="", max_length=1000)
    content: str = ""
    isActive: bool = True
    status: str = Field(default="DRAFT", max_length=30)
    scheduledAt: str | None = None
    publishedAt: str | None = None
    seoTitle: str = Field(default="", max_length=255)
    seoDescription: str = Field(default="", max_length=500)
    seoKeywords: str = Field(default="", max_length=500)
    scopeType: str = Field(default="GLOBAL", max_length=30)
    productIds: list[str] = Field(default_factory=list)
    categoryIds: list[str] = Field(default_factory=list)
    version: int | None = Field(default=None, ge=1)


class ContentCommentPayload(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    userName: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=1000)
    parentId: str | None = Field(default=None, max_length=80)
    isHidden: bool = False


class ContentPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    contentType: str = Field(default="VIDEO", max_length=30)
    status: str = Field(default="DRAFT", max_length=30)
    videoUrl: str | None = None
    thumbnailUrl: str | None = None
    bannerImageUrl: str | None = None
    contentBody: str = ""
    ctaLabel: str | None = Field(default=None, max_length=160)
    ctaUrl: str | None = None
    productIds: list[str] = Field(default_factory=list)
    categoryIds: list[str] = Field(default_factory=list)
    comments: list[ContentCommentPayload] = Field(default_factory=list)
    likeCount: int = Field(default=0, ge=0)
    viewCount: int = Field(default=0, ge=0)
    sortOrder: int = Field(default=0, ge=0)
    scheduledAt: str | None = None
    publishedAt: str | None = None
    isActive: bool = True
    version: int | None = Field(default=None, ge=1)


class ReviewStatusPayload(BaseModel):
    status: str | None = Field(default=None, pattern="^(PENDING|PUBLISHED|HIDDEN|REJECTED)$")
    moderationNote: str | None = Field(default=None, max_length=1000)
    shopReply: str | None = Field(default=None, max_length=2000)
    flaggedReason: str | None = Field(default=None, max_length=1000)
    isSpam: bool | None = None
    spamReason: str | None = Field(default=None, max_length=1000)


class UserRolePayload(BaseModel):
    role: str = Field(pattern="^(CUSTOMER|STAFF_ADMIN|SUPER_ADMIN)$")
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED)$")


class RolePermissionsPayload(BaseModel):
    permissionCodes: list[str] = Field(default_factory=list)


class CustomerTagsPayload(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)


class CustomerBulkTagsPayload(BaseModel):
    userIds: list[UUID] = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=20)


class CustomerNotePayload(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CustomerLoyaltyAdjustmentPayload(BaseModel):
    delta: int = Field(ge=-500000, le=500000)
    reason: str = Field(min_length=3, max_length=255)


class CustomerVoucherIssuePayload(BaseModel):
    voucherId: UUID
    note: str | None = Field(default=None, max_length=255)


class CustomerBulkStatusPayload(BaseModel):
    userIds: list[UUID] = Field(min_length=1, max_length=200)
    status: str = Field(pattern="^(ACTIVE|SUSPENDED)$")


async def clear_permission_cache(redis: Redis, user_ids: list[UUID]) -> None:
    if not user_ids:
        return
    await redis.delete(*[f"admin_permissions:{user_id}" for user_id in user_ids])


def normalize_customer_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = str(tag or "").strip()
        if not value:
            continue
        value = value[:60]
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return normalized[:20]


async def audit_admin_event(
    session: AsyncSession,
    *,
    actor_id: UUID,
    event_type: str,
    resource: str,
    target_user_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    payload = {"resource": resource, **(metadata or {})}
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:actor_id, :event_type, CAST(:metadata AS jsonb))
            """
        ),
        {
            "actor_id": actor_id,
            "event_type": event_type,
            "metadata": json.dumps(
                {
                    **payload,
                    **({"targetUserId": str(target_user_id)} if target_user_id else {}),
                },
                ensure_ascii=False,
            ),
        },
    )


async def ensure_manual_loyalty_limit(
    session: AsyncSession,
    *,
    actor_id: UUID,
    requested_delta: int,
    daily_limit: int = 100000,
) -> None:
    today_total = await session.scalar(
        text(
            """
            SELECT COALESCE(SUM(ABS((metadata->>'delta')::int)), 0)
            FROM loyalty_transactions
            WHERE type = 'ADJUST'
              AND metadata->>'adjustedBy' = :actor_id
              AND created_at >= date_trunc('day', NOW())
            """
        ),
        {"actor_id": str(actor_id)},
    )
    if int(today_total or 0) + abs(requested_delta) > daily_limit:
        raise HTTPException(
            status_code=429,
            detail="Daily manual loyalty adjustment limit exceeded for this admin.",
        )


async def refresh_category_cache(
    session: AsyncSession,
    redis: Redis | None = None,
    affected_root_ids: list[UUID] | None = None,
    removed_root_ids: list[UUID] | None = None,
) -> None:
    if not redis:
        return
    try:
        await rebuild_category_branch_cache(session, redis, affected_root_ids=affected_root_ids, removed_root_ids=removed_root_ids)
    except Exception:
        pass


def enqueue_category_cache_refresh(
    background_tasks: BackgroundTasks,
    redis: Redis | None = None,
    affected_root_ids: list[UUID] | None = None,
    removed_root_ids: list[UUID] | None = None,
) -> None:
    async def _refresh() -> None:
        async with AsyncSessionFactory() as session:
            await refresh_category_cache(session, redis, affected_root_ids=affected_root_ids, removed_root_ids=removed_root_ids)

    background_tasks.add_task(_refresh)


async def process_category_migration_job(job_id: UUID, category_id: UUID, old_parent_id: UUID | None, new_parent_id: UUID | None) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("UPDATE category_migration_jobs SET status = 'RUNNING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
            await session.execute(text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :category_id"), {"category_id": category_id})
            fields_result = await session.execute(
                text(
                    """
                    SELECT COALESCE(parent.spec_fields, '[]'::jsonb) || COALESCE(c.spec_fields, '[]'::jsonb) AS fields
                    FROM categories c
                    LEFT JOIN categories parent ON parent.id = c.parent_id
                    WHERE c.id = :category_id
                    """
                ),
                {"category_id": category_id},
            )
            allowed_fields = fields_result.scalar() or []
            allowed_keys = {str(field.get("key")) for field in allowed_fields if field.get("key")}
            products = (
                await session.execute(
                    text(
                        """
                        SELECT id, specifications
                        FROM products
                        WHERE category_id = :category_id OR subcategory_id = :category_id
                        """
                    ),
                    {"category_id": category_id},
                )
            ).mappings().all()
            await session.execute(
                text("UPDATE category_migration_jobs SET total_products = :total, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "total": len(products)},
            )
            for product in products:
                specs = dict(product["specifications"] or {})
                legacy_specs = dict(specs.get("_legacySpecs") or {})
                for key in list(specs.keys()):
                    if key.startswith("_"):
                        continue
                    if key not in allowed_keys:
                        legacy_specs[key] = specs.pop(key)
                if legacy_specs:
                    specs["_legacySpecs"] = legacy_specs
                await session.execute(
                    text("UPDATE products SET specifications = CAST(:specifications AS jsonb), updated_at = NOW() WHERE id = :id"),
                    {"id": product["id"], "specifications": json.dumps(specs, ensure_ascii=False)},
                )
                await session.execute(
                    text("UPDATE category_migration_jobs SET processed_products = processed_products + 1, updated_at = NOW() WHERE id = :id"),
                    {"id": job_id},
                )
            await session.execute(
                text("UPDATE category_migration_jobs SET status = 'COMPLETED', completed_at = NOW(), updated_at = NOW() WHERE id = :id"),
                {"id": job_id},
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
                {"category_id": category_id},
            )
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE category_migration_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
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
                {"category_id": category_id},
            )
            await session.commit()


async def revoke_users(session: AsyncSession, user_ids: list[UUID], reason: str) -> None:
    for user_id in user_ids:
        await session.execute(
            text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
                VALUES (:user_id, NOW(), :reason)
                ON CONFLICT (user_id)
                DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
                """
            ),
            {"user_id": user_id, "reason": reason},
        )


@router.get("/overview", dependencies=[Depends(require_permission("overview:read"))])
async def overview(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM products WHERE status = 'ACTIVE') AS products,
                (SELECT COUNT(*) FROM categories WHERE is_active = TRUE AND status = 'ACTIVE' AND COALESCE(is_deleted, FALSE) = FALSE) AS categories,
                (SELECT COUNT(*) FROM brands WHERE is_active = TRUE) AS brands,
                (SELECT COUNT(*) FROM orders) AS orders,
                (SELECT COUNT(*) FROM vouchers WHERE status = 'ACTIVE') AS vouchers,
                (SELECT COUNT(*) FROM policies WHERE is_active = TRUE) AS policies
            """
        )
    )
    return dict(result.one()._mapping)


@router.post("/uploads/presigned-url", dependencies=[Depends(require_permission("product:create"))])
async def create_presigned_upload(payload: PresignedUploadPayload) -> dict:
    if payload.folder not in ALLOWED_UPLOAD_FOLDERS:
        raise HTTPException(status_code=400, detail="Invalid upload folder.")
    allowed_types = {**ALLOWED_IMAGE_TYPES, **ALLOWED_VIDEO_TYPES}
    extension = allowed_types.get(payload.contentType)
    if not extension:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    if payload.folder == "content":
        if payload.contentType in ALLOWED_VIDEO_TYPES:
            max_size = min(MAX_VIDEO_UPLOAD_BYTES, 500 * 1024 * 1024)
        else:
            max_size = min(MAX_IMAGE_UPLOAD_BYTES, 5 * 1024 * 1024)
        if payload.contentType not in {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"}:
            raise HTTPException(status_code=400, detail="Content module only accepts JPG, PNG, WEBP, MP4, WEBM.")
    else:
        max_size = MAX_VIDEO_UPLOAD_BYTES if payload.contentType in ALLOWED_VIDEO_TYPES else MAX_IMAGE_UPLOAD_BYTES
    if payload.size > max_size:
        raise HTTPException(status_code=400, detail="File is too large.")
    if not all([settings.s3_bucket, settings.s3_access_key_id, settings.s3_secret_access_key, settings.s3_public_base_url]):
        raise HTTPException(status_code=503, detail="S3 upload is not configured.")

    import boto3

    file_key = f"{payload.folder}/{uuid4().hex}{extension}"
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": file_key, "ContentType": payload.contentType},
        ExpiresIn=settings.s3_presign_expires_seconds,
        HttpMethod="PUT",
    )
    return {
        "uploadUrl": upload_url,
        "fileKey": file_key,
        "publicUrl": f"{settings.s3_public_base_url.rstrip('/')}/{file_key}",
        "expiresIn": settings.s3_presign_expires_seconds,
    }


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
                sort_order, status, workflow_status, is_active, path
            )
            VALUES (
                :id, :parent_id, :code, :slug, :name, :icon, :icon_url, :banner_url,
                :seo_title, :seo_description, :seo_keywords, CAST(:spec_fields AS jsonb),
                CAST(:filter_config AS jsonb), :sort_order, :status, :workflow_status, :is_active,
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
    hits = int(await redis.get("metrics:catalog_categories:cache_hit") or 0)
    misses = int(await redis.get("metrics:catalog_categories:cache_miss") or 0)
    samples = [int(item) for item in await redis.lrange("metrics:catalog_categories:latency_ms", 0, 499)]
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


@router.get("/brands", dependencies=[Depends(require_permission("brand:read"))])
async def list_admin_brands(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=120),
    status_filter: str = Query(default="all", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    where_clauses = []
    params: dict = {"limit": limit, "offset": (page - 1) * limit}
    if search:
        where_clauses.append("(b.name ILIKE :search OR b.code ILIKE :search OR b.slug ILIKE :search)")
        params["search"] = f"%{search.strip()}%"
    if status_filter == "active":
        where_clauses.append("b.is_active = TRUE")
    elif status_filter == "inactive":
        where_clauses.append("b.is_active = FALSE")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    total = (
        await session.execute(text(f"SELECT COUNT(*) FROM brands b {where_sql}"), params)
    ).scalar_one()
    result = await session.execute(
        text(
            f"""
            SELECT
                b.id::text,
                b.code,
                b.slug,
                b.name,
                b.logo_url AS "logoUrl",
                b.logo_alt_text AS "logoAltText",
                b.landing_title AS "landingTitle",
                b.seo_title AS "seoTitle",
                b.seo_description AS "seoDescription",
                b.sort_order AS "order",
                b.is_active AS "isActive",
                b.created_at AS "createdAt",
                b.updated_at AS "updatedAt",
                COUNT(DISTINCT p.id) AS "productCount",
                COALESCE(
                    jsonb_agg(DISTINCT c.id::text) FILTER (WHERE c.id IS NOT NULL),
                    '[]'::jsonb
                ) AS "categoryIds"
            FROM brands b
            LEFT JOIN brand_categories bc ON bc.brand_id = b.id
            LEFT JOIN categories c ON c.id = bc.category_id
            LEFT JOIN products p ON p.brand_id = b.id OR p.brand = b.name
            {where_sql}
            GROUP BY b.id
            ORDER BY b.sort_order, b.name
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return {
        "items": [dict(row._mapping) for row in result],
        "page": page,
        "limit": limit,
        "total": total,
    }


async def sync_brand_categories(session: AsyncSession, brand_id: UUID, category_ids: list[UUID]) -> None:
    if category_ids:
        valid_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM categories WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
                {"ids": category_ids},
            )
        ).scalar_one()
        if valid_count != len(set(category_ids)):
            raise HTTPException(status_code=400, detail="One or more categories do not exist.")
    await session.execute(text("DELETE FROM brand_categories WHERE brand_id = :brand_id"), {"brand_id": brand_id})
    for category_id in category_ids:
        await session.execute(
            text("INSERT INTO brand_categories (brand_id, category_id) VALUES (:brand_id, :category_id) ON CONFLICT DO NOTHING"),
            {"brand_id": brand_id, "category_id": category_id},
        )


async def ensure_brand_code_available(session: AsyncSession, code: str, exclude_id: UUID | None = None) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT id
                FROM brands
                WHERE lower(code) = lower(:code)
                  AND (:exclude_id IS NULL OR id != :exclude_id)
                """
            ),
            {"code": code.strip(), "exclude_id": exclude_id},
        )
    ).first()
    if row:
        raise HTTPException(status_code=409, detail="Mã thương hiệu đã tồn tại.")


async def ensure_brand_slug_available(session: AsyncSession, slug: str, exclude_id: UUID | None = None) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT id
                FROM brands
                WHERE lower(slug) = lower(:slug)
                  AND (:exclude_id IS NULL OR id != :exclude_id)
                """
            ),
            {"slug": slug.strip(), "exclude_id": exclude_id},
        )
    ).first()
    if row:
        raise HTTPException(status_code=409, detail="Slug thương hiệu đã tồn tại.")


async def invalidate_brand_cache(redis: Redis, *slugs: str | None) -> None:
    return


async def resolve_redirect_chain(session: AsyncSession, slug: str, max_hops: int = 5) -> list[str]:
    chain: list[str] = []
    current = slug
    for _ in range(max_hops):
        next_slug = (
            await session.execute(
                text("SELECT new_slug FROM brand_slug_redirects WHERE old_slug = :slug"),
                {"slug": current},
            )
        ).scalar_one_or_none()
        if not next_slug:
            return chain
        chain.append(str(next_slug))
        current = str(next_slug)
    return chain


async def upsert_brand_redirect(session: AsyncSession, brand_id: UUID, old_slug: str, new_slug: str) -> None:
    if old_slug == new_slug:
        return
    chain = await resolve_redirect_chain(session, new_slug)
    if old_slug in chain or new_slug in chain:
        await session.execute(
            text("DELETE FROM brand_slug_redirects WHERE brand_id = :brand_id OR old_slug = :new_slug OR new_slug = :old_slug"),
            {"brand_id": brand_id, "new_slug": new_slug, "old_slug": old_slug},
        )
    await session.execute(
        text(
            """
            INSERT INTO brand_slug_redirects (id, brand_id, old_slug, new_slug)
            VALUES (:id, :brand_id, :old_slug, :new_slug)
            ON CONFLICT (old_slug) DO UPDATE
            SET brand_id = EXCLUDED.brand_id, new_slug = EXCLUDED.new_slug, created_at = NOW()
            """
        ),
        {"id": uuid4(), "brand_id": brand_id, "old_slug": old_slug, "new_slug": new_slug},
    )


@router.post("/brands/check-code", dependencies=[Depends(require_permission("brand:read"))])
async def check_brand_code(payload: BrandCodeCheckPayload, session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT 1
                FROM brands
                WHERE lower(code) = lower(:code)
                  AND (:exclude_id IS NULL OR id != :exclude_id)
                """
            ),
            {"code": payload.code.strip(), "exclude_id": payload.excludeId},
        )
    ).first()
    return {"available": row is None}


@router.post("/brands", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("brand:create"))])
async def create_brand(
    payload: BrandPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    ensure_not_data_url(payload.logoUrl, "logoUrl")
    brand_id = uuid4()
    code = payload.code.strip()
    slug = slugify(payload.slug or payload.name)
    await ensure_brand_code_available(session, code)
    await ensure_brand_slug_available(session, slug)
    await session.execute(
        text(
            """
            INSERT INTO brands (
                id, code, slug, name, logo_url, logo_alt_text, landing_title, seo_title, seo_description, sort_order, is_active
            )
            VALUES (
                :id, :code, :slug, :name, :logo_url, :logo_alt_text, :landing_title, :seo_title, :seo_description, :sort_order, :is_active
            )
            """
        ),
        {
            "id": brand_id,
            "code": code,
            "slug": slug,
            "name": payload.name,
            "logo_url": payload.logoUrl,
            "logo_alt_text": payload.logoAltText,
            "landing_title": payload.landingTitle,
            "seo_title": payload.seoTitle,
            "seo_description": payload.seoDescription,
            "sort_order": payload.order,
            "is_active": payload.isActive,
        },
    )
    await sync_brand_categories(session, brand_id, payload.categoryIds)
    await session.commit()
    await invalidate_brand_cache(redis, slug)
    return {"id": str(brand_id)}


@router.patch("/brands/{brand_id}", dependencies=[Depends(require_permission("brand:update"))])
async def update_brand(
    brand_id: UUID,
    payload: BrandPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    ensure_not_data_url(payload.logoUrl, "logoUrl")
    old_brand = (
        await session.execute(text("SELECT slug FROM brands WHERE id = :id"), {"id": brand_id})
    ).mappings().first()
    if not old_brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    code = payload.code.strip()
    slug = slugify(payload.slug or payload.name)
    await ensure_brand_code_available(session, code, brand_id)
    await ensure_brand_slug_available(session, slug, brand_id)
    result = await session.execute(
        text(
            """
            UPDATE brands
                SET code = :code, slug = :slug, name = :name, logo_url = :logo_url, logo_alt_text = :logo_alt_text,
                landing_title = :landing_title, seo_title = :seo_title, seo_description = :seo_description,
                sort_order = :sort_order, is_active = :is_active, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": brand_id,
            "code": code,
            "slug": slug,
            "name": payload.name,
            "logo_url": payload.logoUrl,
            "logo_alt_text": payload.logoAltText,
            "landing_title": payload.landingTitle,
            "seo_title": payload.seoTitle,
            "seo_description": payload.seoDescription,
            "sort_order": payload.order,
            "is_active": payload.isActive,
        },
    )
    if old_brand["slug"] and old_brand["slug"] != slug:
        await upsert_brand_redirect(session, brand_id, old_brand["slug"], slug)
    await sync_brand_categories(session, brand_id, payload.categoryIds)
    await audit_brand_event(
        session,
        "BRAND_UPDATED",
        {"brandId": str(brand_id), "oldSlug": old_brand["slug"], "newSlug": slug, "code": code, "name": payload.name},
        current_user_id,
    )
    await bump_brand_cache_versions(session, old_brand["slug"], slug)
    await session.commit()
    await invalidate_brand_cache(redis, old_brand["slug"], slug)
    return {"ok": True}


@router.post("/brands/import", dependencies=[Depends(require_permission("brand:create"))])
async def import_brands(
    mode: str = Form(default="skip"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    if mode not in {"skip", "upsert"}:
        raise HTTPException(status_code=400, detail="Mode must be skip or upsert.")
    filename = file.filename or "brands.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file CSV.")
    import_dir = Path(settings.brand_import_dir)
    if not import_dir.is_absolute():
        import_dir = Path.cwd() / import_dir
    import_dir.mkdir(parents=True, exist_ok=True)
    job_file_id = uuid4()
    source_path = import_dir / f"{job_file_id}.csv"
    size = 0
    with source_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 50 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="File import vượt quá 50MB.")
            output.write(chunk)
    with source_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    total_rows = len(rows)
    if rows and rows[0] and rows[0][0].strip().lower() in {"tên", "ten", "name"}:
        total_rows -= 1
    if total_rows <= 0:
        raise HTTPException(status_code=400, detail="File cần có ít nhất một dòng dữ liệu.")
    job_id = await enqueue_brand_import_job(
        session,
        redis,
        source_path=str(source_path),
        total_rows=total_rows,
        mode=mode,
        source_filename=filename,
        user_id=current_user_id,
    )
    await session.commit()
    return {"jobId": str(job_id), "status": "QUEUED"}

    job_id = uuid4()
    imported = 0
    updated = 0
    skipped: list[dict] = []
    changed_slugs: list[str] = []
    seen_codes: set[str] = set()
    for index, item in enumerate(payload.items, start=1):
        ensure_not_data_url(item.logoUrl, "logoUrl")
        brand_id = uuid4()
        code = item.code.strip()
        if code.lower() in seen_codes:
            skipped.append({"row": index, "name": item.name, "reason": "Mã bị trùng trong file import."})
            continue
        seen_codes.add(code.lower())
        exists = (
            await session.execute(
                text("SELECT id, slug FROM brands WHERE lower(code) = lower(:code)"),
                {"code": code},
            )
        ).mappings().first()
        if exists:
            if payload.mode == "skip":
                skipped.append({"row": index, "name": item.name, "code": code, "reason": "Mã thương hiệu đã tồn tại."})
                continue
            await session.execute(
                text(
                    """
                    UPDATE brands
                    SET name = :name, logo_url = COALESCE(:logo_url, logo_url),
                        sort_order = :sort_order, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": exists["id"], "name": item.name.strip(), "logo_url": item.logoUrl, "sort_order": item.order},
            )
            updated += 1
            changed_slugs.append(exists["slug"])
            continue
        result = await session.execute(
            text(
                """
                INSERT INTO brands (id, code, slug, name, logo_url, sort_order, is_active)
                VALUES (:id, :code, :slug, :name, :logo_url, :sort_order, TRUE)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "id": brand_id,
                "code": code,
                "slug": f"{slugify(item.name)}-{brand_id.hex[:5]}",
                "name": item.name.strip(),
                "logo_url": item.logoUrl,
                "sort_order": item.order,
            },
        )
        if result.rowcount:
            imported += 1
            changed_slugs.append(f"{slugify(item.name)}-{brand_id.hex[:5]}")
        else:
            skipped.append({"row": index, "name": item.name, "reason": "Tên thương hiệu đã tồn tại."})
    await session.execute(
        text(
            """
            INSERT INTO brand_import_jobs (
                id, mode, source_filename, total_rows, imported_rows, updated_rows, skipped_rows, status, report
            )
            VALUES (
                :id, :mode, :source_filename, :total_rows, :imported_rows, :updated_rows, :skipped_rows, 'COMPLETED', CAST(:report AS jsonb)
            )
            """
        ),
        {
            "id": job_id,
            "mode": payload.mode,
            "source_filename": payload.sourceFilename,
            "total_rows": len(payload.items),
            "imported_rows": imported,
            "updated_rows": updated,
            "skipped_rows": len(skipped),
            "report": json.dumps(skipped, ensure_ascii=False),
        },
    )
    await session.commit()
    await invalidate_brand_cache(redis, *changed_slugs)
    return {"jobId": str(job_id), "imported": imported, "updated": updated, "skipped": skipped}


@router.get("/brands/import-jobs", dependencies=[Depends(require_permission("brand:read"))])
async def list_brand_import_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                mode,
                source_filename AS "sourceFilename",
                total_rows AS "totalRows",
                imported_rows AS "importedRows",
                updated_rows AS "updatedRows",
                skipped_rows AS "skippedRows",
                status,
                progress,
                processed_rows AS "processedRows",
                error_message AS "errorMessage",
                report,
                started_at AS "startedAt",
                completed_at AS "completedAt",
                created_at AS "createdAt"
            FROM brand_import_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/brands/import-jobs/{job_id}", dependencies=[Depends(require_permission("brand:read"))])
async def get_brand_import_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    rate_key = f"rate:brand-import-job:{client_ip}:{job_id}"
    try:
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, 60)
        if count > 30:
            raise HTTPException(status_code=429, detail="Bạn đang kiểm tra tiến trình quá thường xuyên.")
    except HTTPException:
        raise
    except Exception:
        pass


    row = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    mode,
                    source_filename AS "sourceFilename",
                    total_rows AS "totalRows",
                    processed_rows AS "processedRows",
                    imported_rows AS "importedRows",
                    updated_rows AS "updatedRows",
                    skipped_rows AS "skippedRows",
                    status,
                    progress,
                    error_message AS "errorMessage",
                    report,
                    started_at AS "startedAt",
                    completed_at AS "completedAt",
                    created_at AS "createdAt"
                FROM brand_import_jobs
                WHERE id = :id
                """
            ),
            {"id": job_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return dict(row)


@router.patch("/brands/{brand_id}/status", dependencies=[Depends(require_permission("brand:update"))])
async def update_brand_status(
    brand_id: UUID,
    payload: BrandStatusPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    brand = (
        await session.execute(text("SELECT slug FROM brands WHERE id = :id"), {"id": brand_id})
    ).mappings().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    result = await session.execute(
        text("UPDATE brands SET is_active = :is_active, updated_at = NOW() WHERE id = :id"),
        {"id": brand_id, "is_active": payload.isActive},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brand not found.")
    job_id = None
    if not payload.isActive:
        job_id = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO brand_status_jobs (id, brand_id, target_is_active, status)
                VALUES (:id, :brand_id, FALSE, 'PENDING')
                """
            ),
            {"id": job_id, "brand_id": brand_id},
        )
    await audit_brand_event(
        session,
        "BRAND_STATUS_CHANGED",
        {"brandIds": [str(brand_id)], "isActive": payload.isActive},
        current_user_id,
    )
    await bump_brand_cache_versions(session, brand["slug"])
    await session.commit()
    await invalidate_brand_cache(redis, brand["slug"])
    if job_id:
        background_tasks.add_task(process_brand_status_job, job_id, brand_id, payload.isActive)
        return {"ok": True, "action": "deactivated", "status": "PROCESSING", "jobId": str(job_id)}
    return {"ok": True, "action": "activated"}


@router.patch("/brands/status", dependencies=[Depends(require_permission("brand:update"))])
async def update_brands_status(
    payload: BrandBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    rows = (
        await session.execute(
            text("SELECT id, slug FROM brands WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": payload.ids},
        )
    ).mappings().all()
    found_ids = {row["id"] for row in rows}
    failed = [{"id": str(brand_id), "reason": "Brand not found."} for brand_id in payload.ids if brand_id not in found_ids]
    if rows:
        await session.execute(
            text("UPDATE brands SET is_active = :is_active, updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": [row["id"] for row in rows], "is_active": payload.isActive},
        )
        await audit_brand_event(
            session,
            "BRAND_STATUS_CHANGED",
            {"brandIds": [str(row["id"]) for row in rows], "isActive": payload.isActive, "bulk": True},
            current_user_id,
        )
        await bump_brand_cache_versions(session, *[row["slug"] for row in rows])
        await session.commit()
        await invalidate_brand_cache(redis, *[row["slug"] for row in rows])
    return {"updated": len(rows), "failed": failed}


@router.delete("/brands/{brand_id}", dependencies=[Depends(require_permission("brand:delete"))])
async def deactivate_brand(
    brand_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    brand = (
        await session.execute(
            text("SELECT id::text, code, slug, name FROM brands WHERE id = :id"),
            {"id": brand_id},
        )
    ).mappings().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    product_count = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM products p
                JOIN brands b ON b.id = :id
                WHERE p.brand_id = :id OR p.brand = b.name
                """
            ),
            {"id": brand_id},
        )
    ).scalar_one()
    if product_count > 0:
        raise HTTPException(status_code=409, detail="Không thể xóa thương hiệu đang có sản phẩm. Hãy ẩn thương hiệu nếu cần.")

    result = await session.execute(text("DELETE FROM brands WHERE id = :id"), {"id": brand_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brand not found.")
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:user_id, 'BRAND_HARD_DELETED', CAST(:metadata AS jsonb))
            """
        ),
        {"user_id": current_user_id, "metadata": json.dumps({"brand": dict(brand)}, ensure_ascii=False)},
    )
    await session.commit()
    await invalidate_brand_cache(redis, brand["slug"])
    return {"ok": True, "action": "deleted"}


@router.get("/products", dependencies=[Depends(require_permission("product:read"))])
async def list_admin_products(
    page: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=80),
    search: str = Query(default="", max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    categoryId: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict] | dict:
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text,
                p.sku,
                p.name,
                p.slug,
                p.category,
                p.brand,
                p.category_id::text AS "categoryId",
                p.subcategory_id::text AS "subcategoryId",
                p.brand_id::text AS "brandId",
                c.name AS "categoryName",
                sc.name AS "subcategoryName",
                p.description,
                p.specifications,
                p.price,
                p.sale_price AS "discountPrice",
                p.stock_quantity AS stock,
                p.stock_quantity AS "stockQuantity",
                CASE WHEN p.stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END AS "stockState",
                CASE
                    WHEN p.status = 'ACTIVE' AND p.stock_quantity <= 0 THEN 'Hết hàng'
                    WHEN p.status = 'DRAFT' THEN 'Nháp'
                    WHEN p.status = 'PENDING' THEN 'Chờ duyệt'
                    WHEN p.status = 'ACTIVE' THEN 'Đang bán'
                    WHEN p.status = 'INACTIVE' THEN 'Tạm ẩn'
                    WHEN p.status = 'ARCHIVED' THEN 'Lưu trữ'
                    ELSE p.status
                END AS "displayStatus",
                p.image_url AS "imageUrl",
                p.images,
                p.video_url AS "videoUrl",
                p.status,
                p.seo_metadata AS "seoMetadata",
                p.sales_config AS "salesConfig",
                p.is_price_out_of_stock AS "isPriceOutOfStock",
                p.parent_product_id::text AS "parentProductId",
                p.updated_at AS "updatedAt",
                p.version,
                p.is_featured AS "isFeatured",
                p.is_flash_sale AS "isFlashSale",
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', pv.id::text,
                            'sku', pv.sku,
                            'colorName', pv.color_name,
                            'colorCode', pv.color_code,
                            'storage', pv.storage,
                            'ram', pv.ram,
                            'configuration', pv.configuration,
                            'specs', pv.specs,
                            'imageUrl', pv.image_url,
                            'price', pv.price,
                            'salePrice', pv.sale_price,
                            'stockQuantity', pv.stock_quantity,
                            'stockState', CASE WHEN pv.stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END,
                            'isActive', pv.is_active
                        )
                    ) FILTER (WHERE pv.id IS NOT NULL),
                    '[]'::jsonb
                ) AS variants
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            LEFT JOIN product_variants pv ON pv.product_id = p.id
            GROUP BY p.id, c.id, sc.id
            ORDER BY p.created_at DESC
            """
        )
    )
    rows = [dict(row._mapping) for row in result]
    if rows:
        product_ids = [UUID(item["id"]) for item in rows]
        bundle_rows = (
            await session.execute(
                text(
                    """
                    SELECT pb.product_id::text AS product_id, p.sku
                    FROM product_bundles pb
                    JOIN products p ON p.id = pb.bundled_product_id
                    WHERE pb.product_id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": product_ids},
            )
        ).mappings().all()
        accessory_rows = (
            await session.execute(
                text(
                    """
                    SELECT pa.product_id::text AS product_id, p.id::text AS accessory_id, p.sku, p.name, p.image_url AS image_url
                    FROM product_accessories pa
                    JOIN products p ON p.id = pa.accessory_product_id
                    WHERE pa.product_id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": product_ids},
            )
        ).mappings().all()
        bundles: dict[str, list[str]] = {}
        accessories: dict[str, list[str]] = {}
        accessory_lookup: dict[str, list[dict]] = {}
        for item in bundle_rows:
            bundles.setdefault(item["product_id"], []).append(item["sku"])
        for item in accessory_rows:
            accessories.setdefault(item["product_id"], []).append(item["sku"])
            accessory_lookup.setdefault(item["product_id"], []).append(
                {
                    "productId": item["accessory_id"],
                    "sku": item["sku"],
                    "name": item["name"],
                    "imageUrl": item["image_url"],
                }
            )
        for item in rows:
            sales_config = item.get("salesConfig") if isinstance(item.get("salesConfig"), dict) else {}
            offers = sales_config.get("accessoryOffers") if isinstance(sales_config.get("accessoryOffers"), list) else []
            resolved_accessory_by_id = {
                accessory["productId"]: accessory for accessory in accessory_lookup.get(item["id"], [])
            }
            accessory_offers = []
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                product_id = str(offer.get("productId") or "")
                accessory_meta = resolved_accessory_by_id.get(product_id, {})
                accessory_offers.append(
                    {
                        **offer,
                        "productId": product_id,
                        "productName": accessory_meta.get("name", ""),
                        "productSku": accessory_meta.get("sku", ""),
                        "imageUrl": accessory_meta.get("imageUrl", ""),
                    }
                )
            item["salesConfig"] = {
                **sales_config,
                "bundleRefs": bundles.get(item["id"], []),
                "accessoryRefs": accessories.get(item["id"], []),
                "accessoryOffers": accessory_offers,
            }
    if search:
        needle = search.strip().lower()
        rows = [
            item for item in rows
            if needle in " ".join(str(item.get(key) or "") for key in ["name", "sku", "brand", "categoryName", "category"]).lower()
        ]
    if status_filter:
        rows = [item for item in rows if item.get("status") == status_filter]
    if categoryId:
        rows = [item for item in rows if item.get("categoryId") == str(categoryId) or item.get("subcategoryId") == str(categoryId)]
    if cursor:
        rows = [item for item in rows if str(item.get("id")) < cursor]
        paged = rows[:limit]
        return {"items": paged, "nextCursor": paged[-1]["id"] if len(paged) == limit else None, "limit": limit}
    if page is None:
        return rows
    total = len(rows)
    start = (page - 1) * limit
    paged = rows[start:start + limit]
    return {"items": paged, "totalRecords": total, "totalPages": (total + limit - 1) // limit, "page": page, "limit": limit}


@router.get("/products/suggestions", dependencies=[Depends(require_permission("product:read"))])
async def suggest_admin_products(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
    excludeId: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, sku, name, image_url AS "imageUrl", status
            FROM products
            WHERE (:exclude_id IS NULL OR id <> :exclude_id)
              AND (
                :search = ''
                OR LOWER(name) LIKE LOWER(:pattern)
                OR LOWER(sku) LIKE LOWER(:pattern)
                OR LOWER(brand) LIKE LOWER(:pattern)
              )
            ORDER BY status = 'ACTIVE' DESC, name
            LIMIT :limit
            """
        ),
        {"search": search.strip(), "pattern": f"%{search.strip()}%", "limit": limit, "exclude_id": excludeId},
    )
    return [dict(row._mapping) for row in result]


async def process_product_import_job(job_id: UUID, csv_text: str) -> None:
    async with AsyncSessionFactory() as session:
        try:
            rows = list(csv.DictReader(csv_text.splitlines()))
            await session.execute(
                text("UPDATE product_import_jobs SET status = 'PROCESSING', total_rows = :total, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "total": len(rows)},
            )
            await session.commit()
            imported = 0
            failed = 0
            for row in rows:
                try:
                    product_id = uuid4()
                    name = (row.get("name") or "").strip()
                    if not name:
                        failed += 1
                        continue
                    specs, seo_metadata, sales_config = extract_product_metadata({
                        "_seoTitle": row.get("seoTitle") or "",
                        "_seoDescription": row.get("seoDescription") or "",
                        "_seoSlug": row.get("seoSlug") or "",
                        "_warrantyPolicy": row.get("warrantyPolicy") or "",
                    })
                    await session.execute(
                        text(
                            """
                            INSERT INTO products (
                                id, sku, name, slug, category, brand, description, specifications,
                                seo_metadata, sales_config, price, sale_price, stock_quantity,
                                image_url, images, colors, capacities, promotions, status
                            )
                            VALUES (
                                :id, :sku, :name, :slug, :category, :brand, :description, '{}'::jsonb,
                                CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb), :price,
                                :sale_price, 0, :image_url, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                                '[]'::jsonb, :status
                            )
                            """
                        ),
                        {
                            "id": product_id,
                            "sku": f"SKU-{product_id.hex[:10].upper()}",
                            "name": name,
                            "slug": f"{slugify(name)}-{product_id.hex[:6]}",
                            "category": row.get("category") or "ACCESSORY",
                            "brand": row.get("brand") or "Khac",
                            "description": row.get("description") or "",
                            "seo_metadata": json.dumps(seo_metadata),
                            "sales_config": json.dumps(persisted_sales_config(sales_config)),
                            "price": float(row.get("price") or 0),
                            "sale_price": float(row["discountPrice"]) if row.get("discountPrice") else None,
                            "image_url": row.get("imageUrl") or None,
                            "status": normalize_status(row.get("status") or "DRAFT"),
                        },
                    )
                    imported += 1
                except Exception:
                    failed += 1
                await session.execute(
                    text(
                        """
                        UPDATE product_import_jobs
                        SET processed_rows = processed_rows + 1,
                            imported_rows = :imported,
                            failed_rows = :failed,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": job_id, "imported": imported, "failed": failed},
                )
                await session.commit()
            await session.execute(
                text("UPDATE product_import_jobs SET status = 'COMPLETED', updated_at = NOW() WHERE id = :id"),
                {"id": job_id},
            )
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE product_import_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.commit()


async def create_product_revision(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductPayload,
    clean_specs: dict,
    seo_metadata: dict,
    sales_config: dict,
    category: str,
    brand: str,
) -> dict:
    revision_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO products (
                id, parent_product_id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale
            )
            VALUES (
                :id, :parent_product_id, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb),
                :price, :sale_price, 0, :image_url, CAST(:images AS jsonb), :video_url,
                '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'REVISION_DRAFT', :is_featured, :is_flash_sale
            )
            """
        ),
        {
            "id": revision_id,
            "parent_product_id": product_id,
            "sku": f"REV-{revision_id.hex[:10].upper()}",
            "name": payload.name,
            "slug": f"{slugify(payload.name)}-revision-{revision_id.hex[:6]}",
            "category": category,
            "brand": brand,
            "category_id": payload.categoryId,
            "subcategory_id": payload.subcategoryId,
            "brand_id": payload.brandId,
            "description": payload.description or "",
            "specifications": json.dumps(clean_specs),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(persisted_sales_config(sales_config)),
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
        },
    )
    await upsert_product_variants(session, revision_id, payload.variants)
    await sync_parent_price_from_variants(session, revision_id)
    await sync_product_relations(session, revision_id, sales_config)
    await session.commit()
    return {"ok": True, "revisionId": str(revision_id), "status": "REVISION_DRAFT"}


@router.post("/products/import", dependencies=[Depends(require_permission("product:create"))])
async def import_products(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV product import is supported.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CSV file is too large.")
    job_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO product_import_jobs (id, source_filename, status)
            VALUES (:id, :source_filename, 'PENDING')
            """
        ),
        {"id": job_id, "source_filename": file.filename},
    )
    await session.commit()
    background_tasks.add_task(process_product_import_job, job_id, content.decode("utf-8-sig"))
    return {"jobId": str(job_id), "status": "PENDING"}


@router.get("/products/import-jobs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_import_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, source_filename AS "sourceFilename", status, total_rows AS "totalRows",
                   processed_rows AS "processedRows", imported_rows AS "importedRows",
                   failed_rows AS "failedRows", error_message AS "errorMessage",
                   created_at AS "createdAt", updated_at AS "updatedAt"
            FROM product_import_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def process_product_export_job(job_id: UUID, filters: dict) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("UPDATE product_export_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
            result = await session.execute(
                text(
                    """
                    SELECT id::text, sku, name, brand, category, price, sale_price AS "discountPrice",
                           stock_quantity AS stock, status, seo_metadata, sales_config
                    FROM products
                    WHERE (:search = '' OR LOWER(name) LIKE LOWER(:pattern) OR LOWER(sku) LIKE LOWER(:pattern) OR LOWER(brand) LIKE LOWER(:pattern))
                      AND (:status = '' OR status = :status)
                    ORDER BY created_at DESC
                    """
                ),
                {
                    "search": filters.get("search", ""),
                    "pattern": f"%{filters.get('search', '')}%",
                    "status": filters.get("status", ""),
                },
            )
            rows = [dict(row._mapping) for row in result]
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "sku", "name", "brand", "category", "price", "discountPrice", "stock", "status", "seoTitle", "seoDescription", "seoSlug", "warrantyPolicy"])
            writer.writeheader()
            for row in rows:
                seo = row.get("seo_metadata") if isinstance(row.get("seo_metadata"), dict) else {}
                sales = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
                writer.writerow({
                    "id": row.get("id"),
                    "sku": row.get("sku"),
                    "name": row.get("name"),
                    "brand": row.get("brand"),
                    "category": row.get("category"),
                    "price": row.get("price"),
                    "discountPrice": row.get("discountPrice"),
                    "stock": row.get("stock"),
                    "status": row.get("status"),
                    "seoTitle": seo.get("title", ""),
                    "seoDescription": seo.get("description", ""),
                    "seoSlug": seo.get("slug", ""),
                    "warrantyPolicy": sales.get("warrantyPolicy", ""),
                })
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            export_path = export_dir / f"products-{job_id}.csv"
            export_path.write_text(output.getvalue(), encoding="utf-8-sig")
            download_url = f"/exports/{export_path.name}"
            await session.execute(
                text(
                    """
                    UPDATE product_export_jobs
                    SET status = 'COMPLETED', total_rows = :total, processed_rows = :total,
                        file_path = :file_path, download_url = :download_url,
                        expires_at = :expires_at, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": job_id,
                    "total": len(rows),
                    "file_path": str(export_path),
                    "download_url": download_url,
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
                },
            )
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE product_export_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.commit()


@router.post("/products/export", dependencies=[Depends(require_permission("product:read"))])
async def export_products(
    background_tasks: BackgroundTasks,
    filters: dict | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    job_id = uuid4()
    export_filters = filters or {}
    await session.execute(
        text("INSERT INTO product_export_jobs (id, status, filters) VALUES (:id, 'PENDING', CAST(:filters AS jsonb))"),
        {"id": job_id, "filters": json.dumps(export_filters)},
    )
    await session.commit()
    background_tasks.add_task(process_product_export_job, job_id, export_filters)
    return {"jobId": str(job_id), "status": "PENDING"}


@router.get("/products/export-jobs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_export_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, status, filters, total_rows AS "totalRows", processed_rows AS "processedRows",
                   download_url AS "downloadUrl", expires_at AS "expiresAt", error_message AS "errorMessage",
                   created_at AS "createdAt", updated_at AS "updatedAt"
            FROM product_export_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/products/kpis", dependencies=[Depends(require_permission("product:read"))])
async def product_catalog_kpis(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
                AVG(EXTRACT(EPOCH FROM (active_product.updated_at - draft_product.created_at)) / 3600) AS time_to_market_hours,
                COUNT(*) FILTER (WHERE active_product.status = 'DRAFT' AND active_product.updated_at < NOW() - INTERVAL '30 days') AS orphaned_products,
                COUNT(*) FILTER (WHERE active_product.status = 'INACTIVE') AS inactive_products,
                COUNT(*) FILTER (WHERE active_product.status = 'ACTIVE') AS active_products
            FROM products active_product
            LEFT JOIN products draft_product ON draft_product.id = active_product.id
            """
        )
    )
    row = dict(result.mappings().one())
    import_jobs = (
        await session.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(imported_rows), 0) AS imported_rows,
                    COALESCE(SUM(total_rows), 0) AS total_rows
                FROM product_import_jobs
                WHERE status IN ('COMPLETED', 'FAILED')
                """
            )
        )
    ).mappings().one()
    total_rows = int(import_jobs["total_rows"] or 0)
    return {
        "timeToMarketHours": float(row["time_to_market_hours"] or 0),
        "catalogAccuracyRate": 1 - (int(row["inactive_products"] or 0) / max(int(row["active_products"] or 0) + int(row["inactive_products"] or 0), 1)),
        "orphanedProducts": int(row["orphaned_products"] or 0),
        "importSuccessRate": (int(import_jobs["imported_rows"] or 0) / total_rows) if total_rows else 1,
    }


@router.get("/products/{product_id}/audit-logs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_audit_logs(product_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, product_id::text AS "productId", actor_id::text AS "actorId",
                   action, old_value AS "oldValue", new_value AS "newValue", created_at AS "createdAt"
            FROM product_audit_logs
            WHERE product_id = :product_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"product_id": product_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/brands/status-jobs", dependencies=[Depends(require_permission("brand:read"))])
async def list_brand_status_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, brand_id::text AS "brandId", target_is_active AS "targetIsActive",
                   status, total_products AS "totalProducts", processed_products AS "processedProducts",
                   error_message AS "errorMessage", created_at AS "createdAt", updated_at AS "updatedAt"
            FROM brand_status_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/products", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("product:create"))])
async def create_product(payload: ProductPayload, session: AsyncSession = Depends(get_session)) -> dict:
    product_id = uuid4()
    validate_optimized_media(payload)
    ensure_not_data_url(payload.imageUrl, "imageUrl")
    ensure_not_data_url(payload.videoUrl, "videoUrl")
    for image in payload.images:
        ensure_not_data_url(image, "images")
    await ensure_categories_not_migrating(session, [payload.categoryId, payload.subcategoryId])
    category, brand = await resolve_catalog_labels(session, payload)
    clean_specs, seo_metadata, sales_config = extract_product_metadata(payload.specifications)
    await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale
            )
            VALUES (
                :id, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb), :price, :sale_price, 0, :image_url,
                CAST(:images AS jsonb), :video_url, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, :status, :is_featured, :is_flash_sale
            )
            """
        ),
        {
            "id": product_id,
            "sku": f"SKU-{product_id.hex[:10].upper()}",
            "name": payload.name,
            "slug": f"{slugify(payload.name)}-{product_id.hex[:6]}",
            "category": category,
            "brand": brand,
            "category_id": payload.categoryId,
            "subcategory_id": payload.subcategoryId,
            "brand_id": payload.brandId,
            "description": payload.description or "",
            "specifications": json.dumps(clean_specs),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(persisted_sales_config(sales_config)),
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "status": normalize_status(payload.status),
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
        },
    )
    await upsert_product_variants(session, product_id, payload.variants)
    await sync_parent_price_from_variants(session, product_id)
    await sync_product_relations(session, product_id, sales_config)
    await audit_product_event(session, product_id, "PRODUCT_CREATED", new_value={"name": payload.name, "status": normalize_status(payload.status)})
    await session.commit()
    return {"id": str(product_id)}


@router.patch("/products/{product_id}", dependencies=[Depends(require_permission("product:update"))])
async def update_product(product_id: UUID, payload: ProductPayload, session: AsyncSession = Depends(get_session)) -> dict:
    validate_optimized_media(payload)
    ensure_not_data_url(payload.imageUrl, "imageUrl")
    ensure_not_data_url(payload.videoUrl, "videoUrl")
    for image in payload.images:
        ensure_not_data_url(image, "images")
    await ensure_categories_not_migrating(session, [payload.categoryId, payload.subcategoryId])
    category, brand = await resolve_catalog_labels(session, payload)
    clean_specs, seo_metadata, sales_config = extract_product_metadata(payload.specifications)
    current = (
        await session.execute(
            text("SELECT status, version, updated_at, name, price, sale_price, category_id, subcategory_id FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Product not found.")
    await ensure_categories_not_migrating(session, [current["category_id"], current["subcategory_id"], payload.categoryId, payload.subcategoryId])
    if payload.version is not None and int(current["version"] or 0) != payload.version:
        raise HTTPException(status_code=409, detail="Product was updated by another admin. Reload before saving.")
    if payload.updatedAt and payload.version is None:
        if str(current["updated_at"].isoformat())[:19] != str(payload.updatedAt)[:19]:
            raise HTTPException(status_code=409, detail="Product was updated by another admin. Reload before saving.")
    if current["status"] == "ACTIVE":
        return await create_product_revision(session, product_id, payload, clean_specs, seo_metadata, sales_config, category, brand)
    if False:
        current = (
            await session.execute(
                text("SELECT updated_at FROM products WHERE id = :id"),
                {"id": product_id},
            )
        ).mappings().first()
        if not current:
            raise HTTPException(status_code=404, detail="Product not found.")
        if str(current["updated_at"].isoformat())[:19] != str(payload.updatedAt)[:19]:
            raise HTTPException(status_code=409, detail="Product was updated by another admin. Reload before saving.")
    result = await session.execute(
        text(
            """
            UPDATE products
            SET name = :name,
                category = :category,
                brand = :brand,
                category_id = :category_id,
                subcategory_id = :subcategory_id,
                brand_id = :brand_id,
                description = :description,
                specifications = CAST(:specifications AS jsonb),
                seo_metadata = CAST(:seo_metadata AS jsonb),
                sales_config = CAST(:sales_config AS jsonb),
                price = :price,
                sale_price = :sale_price,
                image_url = :image_url,
                images = CAST(:images AS jsonb),
                video_url = :video_url,
                status = :status,
                is_featured = :is_featured,
                is_flash_sale = :is_flash_sale,
                version = version + 1,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": product_id,
            "name": payload.name,
            "category": category,
            "brand": brand,
            "category_id": payload.categoryId,
            "subcategory_id": payload.subcategoryId,
            "brand_id": payload.brandId,
            "description": payload.description or "",
            "specifications": json.dumps(clean_specs),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(persisted_sales_config(sales_config)),
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "status": normalize_status(payload.status),
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Product not found.")
    await upsert_product_variants(session, product_id, payload.variants)
    await sync_parent_price_from_variants(session, product_id)
    if normalize_status(payload.status) == "INACTIVE":
        await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"), {"product_id": product_id})
    await sync_product_relations(session, product_id, sales_config)
    await audit_product_event(
        session,
        product_id,
        "PRODUCT_UPDATED",
        old_value={"name": current["name"], "price": str(current["price"]), "salePrice": str(current["sale_price"])},
        new_value={"name": payload.name, "price": payload.price, "salePrice": payload.discountPrice, "status": normalize_status(payload.status)},
    )
    await session.commit()
    return {"ok": True}


async def transition_product_status(
    session: AsyncSession,
    product_id: UUID,
    *,
    allowed_from: set[str],
    next_status: str,
) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT id, parent_product_id, status, name, sku, category_id, image_url, price, sale_price,
                       subcategory_id, stock_quantity, specifications, sales_config, is_flash_sale
                FROM products
                WHERE id = :id
                FOR UPDATE
                """
            ),
            {"id": product_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found.")
    await ensure_categories_not_migrating(session, [row["category_id"], row["subcategory_id"]])
    current_status = str(row["status"])
    if current_status not in allowed_from:
        raise HTTPException(status_code=400, detail=f"Cannot change product from {current_status} to {next_status}.")
    variants = (
        await session.execute(
            text("SELECT price, sale_price, stock_quantity, is_active FROM product_variants WHERE product_id = :product_id"),
            {"product_id": product_id},
        )
    ).mappings().all()
    if next_status == "PENDING":
        missing = []
        if not row["name"]:
            missing.append("name")
        if not row["sku"]:
            missing.append("sku")
        if not row["category_id"]:
            missing.append("category")
        if not row["image_url"]:
            missing.append("imageUrl")
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields before submit: {', '.join(missing)}.")
    if next_status == "ACTIVE":
        variant_keys = []
        sales_config = row["sales_config"] or {}
        if isinstance(sales_config, dict):
            variant_keys = sales_config.get("variantSpecKeys") or []
        active_variants = [variant for variant in variants if variant["is_active"] is not False]
        if variant_keys and not active_variants:
            raise HTTPException(status_code=400, detail="Product needs at least one active variant before approval.")
        if active_variants:
            invalid_variant = next((variant for variant in active_variants if float(variant["sale_price"] or variant["price"] or 0) <= 0), None)
            if invalid_variant:
                raise HTTPException(status_code=400, detail="Each active variant needs a valid price before approval.")
        elif float(row["sale_price"] or row["price"] or 0) <= 0:
            raise HTTPException(status_code=400, detail="Single product needs a valid price before approval.")
        await sync_parent_price_from_variants(session, product_id)
        if row["parent_product_id"]:
            parent_id = row["parent_product_id"]
            await session.execute(
                text(
                    """
                    UPDATE products parent
                    SET name = revision.name,
                        category = revision.category,
                        brand = revision.brand,
                        category_id = revision.category_id,
                        subcategory_id = revision.subcategory_id,
                        brand_id = revision.brand_id,
                        description = revision.description,
                        specifications = revision.specifications,
                        seo_metadata = revision.seo_metadata,
                        sales_config = revision.sales_config,
                        image_url = revision.image_url,
                        images = revision.images,
                        video_url = revision.video_url,
                        is_featured = revision.is_featured,
                        is_flash_sale = revision.is_flash_sale,
                        version = parent.version + 1,
                        updated_at = NOW()
                    FROM products revision
                    WHERE parent.id = :parent_id AND revision.id = :revision_id
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await session.execute(text("DELETE FROM product_variants WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(
                text(
                    """
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, price, sale_price, stock_quantity, is_active
                    )
                    SELECT gen_random_uuid(), :parent_id, sku, color_name, color_code, storage, ram, configuration,
                           specs, image_url, price, sale_price, 0, is_active
                    FROM product_variants
                    WHERE product_id = :revision_id
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await session.execute(text("DELETE FROM product_bundles WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(
                text(
                    """
                    INSERT INTO product_bundles (product_id, bundled_product_id)
                    SELECT :parent_id, bundled_product_id
                    FROM product_bundles
                    WHERE product_id = :revision_id
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await session.execute(text("DELETE FROM product_accessories WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(
                text(
                    """
                    INSERT INTO product_accessories (product_id, accessory_product_id)
                    SELECT :parent_id, accessory_product_id
                    FROM product_accessories
                    WHERE product_id = :revision_id
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await sync_parent_price_from_variants(session, parent_id)
            await audit_product_event(session, parent_id, "REVISION_PUBLISHED", old_value={"revisionId": str(product_id)}, new_value={"publishedProductId": str(parent_id)})
            await session.execute(text("UPDATE products SET status = 'ARCHIVED', updated_at = NOW() WHERE id = :revision_id"), {"revision_id": product_id})
            await session.commit()
            return {"ok": True, "status": "ACTIVE", "publishedProductId": str(parent_id)}
    if next_status == "ARCHIVED":
        relation_count = (
            await session.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM product_bundles WHERE bundled_product_id = :id) +
                        (SELECT COUNT(*) FROM product_accessories WHERE accessory_product_id = :id) AS total
                    """
                ),
                {"id": product_id},
            )
        ).scalar_one()
        if int(relation_count or 0) > 0 or row["is_flash_sale"]:
            raise HTTPException(status_code=409, detail="Product is used in bundle/accessory relations or flash sale. Review dependencies before archiving.")
    await session.execute(
        text("UPDATE products SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "status": next_status},
    )
    if next_status == "INACTIVE":
        await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"), {"product_id": product_id})
    await audit_product_event(session, product_id, "PRODUCT_STATUS_CHANGED", old_value={"status": current_status}, new_value={"status": next_status})
    await session.commit()
    return {"ok": True, "status": next_status}


@router.post("/products/{product_id}/submit", dependencies=[Depends(require_permission("product:update"))])
async def submit_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "REVISION_DRAFT"}, next_status="PENDING")


@router.post("/products/{product_id}/approve", dependencies=[Depends(require_permission("product:update"))])
async def approve_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"PENDING"}, next_status="ACTIVE")


@router.post("/products/bulk-approve", dependencies=[Depends(require_permission("product:update"))])
async def bulk_approve_products(payload: ProductBulkActionPayload, session: AsyncSession = Depends(get_session)) -> dict:
    ids = payload.ids or payload.productIds or []
    updated = 0
    skipped: list[str] = []
    for product_id in ids:
        try:
            await transition_product_status(session, product_id, allowed_from={"PENDING"}, next_status="ACTIVE")
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "updated": updated, "skipped": skipped}


@router.post("/products/bulk-action", dependencies=[Depends(require_permission("product:update"))])
async def product_bulk_action(payload: ProductBulkActionPayload, session: AsyncSession = Depends(get_session)) -> dict:
    ids = payload.productIds or payload.ids or []
    updated = 0
    skipped: list[str] = []
    for product_id in ids:
        try:
            if payload.action == "APPROVE":
                await transition_product_status(session, product_id, allowed_from={"PENDING"}, next_status="ACTIVE")
            elif payload.action == "ARCHIVE":
                await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE"}, next_status="ARCHIVED")
            elif payload.action == "DELETE":
                result = await session.execute(
                    text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id AND status <> 'ARCHIVED'"),
                    {"id": product_id},
                )
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Product not found.")
                await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :id"), {"id": product_id})
                await session.commit()
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "action": payload.action, "updated": updated, "skipped": skipped}


@router.post("/products/{product_id}/duplicate", dependencies=[Depends(require_permission("product:create"))])
async def duplicate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    source = (
        await session.execute(
            text("SELECT id, name FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not source:
        raise HTTPException(status_code=404, detail="Product not found.")

    new_id = uuid4()
    suffix = new_id.hex[:6]
    insert_result = await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale
            )
            SELECT
                :new_id,
                :sku,
                CONCAT(name, ' (Copy)'),
                :slug,
                category,
                brand,
                category_id,
                subcategory_id,
                brand_id,
                description,
                specifications,
                seo_metadata,
                sales_config,
                price,
                sale_price,
                0,
                image_url,
                images,
                video_url,
                colors,
                capacities,
                promotions,
                'DRAFT',
                is_featured,
                is_flash_sale
            FROM products
            WHERE id = :source_id
            RETURNING id::text
            """
        ),
        {
            "new_id": new_id,
            "source_id": product_id,
            "sku": f"SKU-{new_id.hex[:10].upper()}",
            "slug": f"{slugify(str(source['name']))}-copy-{suffix}",
        },
    )
    if not insert_result.first():
        raise HTTPException(status_code=404, detail="Product not found.")
    await session.execute(
        text(
            """
            INSERT INTO product_variants (
                id, product_id, sku, color_name, color_code, storage, ram, configuration,
                specs, image_url, price, sale_price, stock_quantity, is_active
            )
            SELECT
                gen_random_uuid(),
                :new_id,
                LEFT(CONCAT(sku, '-COPY-', :suffix), 120),
                color_name,
                color_code,
                storage,
                ram,
                configuration,
                specs,
                image_url,
                price,
                sale_price,
                0,
                is_active
            FROM product_variants
            WHERE product_id = :source_id AND is_active = TRUE
            """
        ),
        {"new_id": new_id, "source_id": product_id, "suffix": suffix},
    )
    await session.execute(
        text(
            """
            INSERT INTO product_bundles (product_id, bundled_product_id)
            SELECT :new_id, bundled_product_id
            FROM product_bundles
            WHERE product_id = :source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"new_id": new_id, "source_id": product_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO product_accessories (product_id, accessory_product_id)
            SELECT :new_id, accessory_product_id
            FROM product_accessories
            WHERE product_id = :source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"new_id": new_id, "source_id": product_id},
    )
    await session.commit()
    return {"id": str(new_id)}


@router.post("/products/{product_id}/archive", dependencies=[Depends(require_permission("product:update"))])
async def archive_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE"}, next_status="ARCHIVED")


@router.get("/products/{product_id}/inventory", dependencies=[Depends(require_permission("inventory:read"))])
async def get_product_inventory(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product = (
        await session.execute(
            text(
                """
                SELECT id::text, name, sku, stock_quantity AS stock,
                       stock_quantity AS "stockQuantity",
                       CASE WHEN stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END AS "stockState",
                       sales_config AS "salesConfig"
                FROM products
                WHERE id = :id
                """
            ),
            {"id": product_id},
        )
    ).mappings().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    variants = (
        await session.execute(
            text(
                """
                SELECT id::text, sku, color_name AS "colorName", configuration,
                       stock_quantity AS "stockQuantity",
                       CASE WHEN stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END AS "stockState",
                       is_active AS "isActive"
                FROM product_variants
                WHERE product_id = :product_id
                ORDER BY created_at, sku
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    logs = (
        await session.execute(
            text(
                """
                SELECT id::text, product_id::text AS "productId", variant_id::text AS "variantId",
                       old_quantity AS "oldQuantity", new_quantity AS "newQuantity",
                       delta, transaction_type AS "transactionType",
                       reference_code AS "referenceCode", reason, note,
                       supplier_name AS "supplierName", unit_cost AS "unitCost",
                       location_code AS "locationCode", location_name AS "locationName",
                       created_at AS "createdAt"
                FROM inventory_adjustment_logs
                WHERE product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 20
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    product_data = dict(product)
    sales_config = product_data.get("salesConfig") if isinstance(product_data.get("salesConfig"), dict) else {}
    minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
    product_data.update(
        {
            "minimumStock": minimum_stock,
            "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
            "preferredLocationCode": sales_config.get("preferredLocationCode", "") or "",
            "preferredLocationName": sales_config.get("preferredLocationName", "") or "",
            "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
            "stockAlert": "LOW" if int(product_data.get("stockQuantity") or 0) <= minimum_stock else "OK",
        }
    )
    return {**product_data, "variants": [dict(row) for row in variants], "logs": [dict(row) for row in logs]}


@router.patch("/products/{product_id}/inventory/policy", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_product_inventory_policy(
    product_id: UUID,
    payload: InventoryPolicyPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    row = (
        await session.execute(
            text("SELECT sales_config FROM products WHERE id = :product_id FOR UPDATE"),
            {"product_id": product_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found.")
    sales_config = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
    merged = persisted_sales_config(
        {
            **sales_config,
            "minimumStock": payload.minimumStock,
            "blockSaleWhenOutOfStock": payload.blockSaleWhenOutOfStock,
            "preferredLocationCode": payload.preferredLocationCode or "",
            "preferredLocationName": payload.preferredLocationName or "",
            "cycleCountDays": payload.cycleCountDays or sales_config.get("cycleCountDays") or 30,
        }
    )
    await session.execute(
        text("UPDATE products SET sales_config = CAST(:sales_config AS jsonb), updated_at = NOW() WHERE id = :product_id"),
        {"product_id": product_id, "sales_config": json.dumps(merged)},
    )
    await session.commit()
    return {"ok": True, **merged}


@router.get("/inventory/export", dependencies=[Depends(require_permission("inventory:read"))])
async def export_inventory_snapshot(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text AS "productId",
                p.name AS "productName",
                p.sku AS "productSku",
                p.stock_quantity AS "productStock",
                p.status AS "productStatus",
                p.sales_config AS "salesConfig",
                pv.id::text AS "variantId",
                pv.sku AS "variantSku",
                pv.configuration,
                pv.color_name AS "colorName",
                pv.stock_quantity AS "variantStock"
            FROM products p
            LEFT JOIN product_variants pv ON pv.product_id = p.id
            WHERE :search = ''
               OR LOWER(p.name) LIKE LOWER(:pattern)
               OR LOWER(p.sku) LIKE LOWER(:pattern)
               OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
            ORDER BY p.created_at DESC, pv.created_at, pv.sku
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "productId",
            "productName",
            "productSku",
            "variantId",
            "variantSku",
            "variantConfiguration",
            "variantColor",
            "stockQuantity",
            "minimumStock",
            "stockAlert",
            "productStatus",
            "blockSaleWhenOutOfStock",
            "preferredLocationCode",
            "preferredLocationName",
        ],
    )
    writer.writeheader()
    for row in result.mappings().all():
        sales_config = row.get("salesConfig") if isinstance(row.get("salesConfig"), dict) else {}
        minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
        stock_quantity = int(row.get("variantStock") if row.get("variantId") else row.get("productStock") or 0)
        writer.writerow(
            {
                "productId": row.get("productId"),
                "productName": row.get("productName"),
                "productSku": row.get("productSku"),
                "variantId": row.get("variantId") or "",
                "variantSku": row.get("variantSku") or "",
                "variantConfiguration": row.get("configuration") or "",
                "variantColor": row.get("colorName") or "",
                "stockQuantity": stock_quantity,
                "minimumStock": minimum_stock,
                "stockAlert": "Cần nhập thêm" if stock_quantity <= minimum_stock else "Ổn định",
                "productStatus": row.get("productStatus"),
                "blockSaleWhenOutOfStock": "Có" if sales_config.get("blockSaleWhenOutOfStock", True) else "Không",
                "preferredLocationCode": sales_config.get("preferredLocationCode", "") or "",
                "preferredLocationName": sales_config.get("preferredLocationName", "") or "",
            }
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inventory-export.csv"'},
    )


@router.post("/products/{product_id}/inventory/adjust", dependencies=[Depends(require_permission("inventory:adjust"))])
async def adjust_product_inventory(
    product_id: UUID,
    payload: InventoryAdjustmentPayload,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    idem_key = (idempotency_key or payload.referenceCode or "").strip()
    if idem_key:
        await session.execute(
            text("DELETE FROM product_inventory_idempotency WHERE created_at < NOW() - INTERVAL '30 days'")
        )
        existing = (
            await session.execute(
                text("SELECT response_payload FROM product_inventory_idempotency WHERE idempotency_key = :key"),
                {"key": idem_key},
            )
        ).mappings().first()
        if existing:
            return dict(existing["response_payload"])
    if payload.delta is None and payload.quantity is None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity.")
    if payload.delta is not None and payload.quantity is not None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity, not both.")
    if payload.variantId:
        row = (
            await session.execute(
                text(
                    """
                    SELECT id, stock_quantity
                    FROM product_variants
                    WHERE id = :variant_id AND product_id = :product_id
                    FOR UPDATE
                    """
                ),
                {"variant_id": payload.variantId, "product_id": product_id},
            )
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Variant not found.")
        old_quantity = int(row["stock_quantity"] or 0)
        new_quantity = payload.quantity if payload.quantity is not None else old_quantity + int(payload.delta or 0)
        if new_quantity < 0:
            raise HTTPException(status_code=400, detail="Inventory quantity cannot be negative.")
        await session.execute(
            text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
            {"id": payload.variantId, "quantity": new_quantity},
        )
    else:
        row = (
            await session.execute(
                text("SELECT id, stock_quantity FROM products WHERE id = :product_id FOR UPDATE"),
                {"product_id": product_id},
            )
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found.")
        old_quantity = int(row["stock_quantity"] or 0)
        new_quantity = payload.quantity if payload.quantity is not None else old_quantity + int(payload.delta or 0)
        if new_quantity < 0:
            raise HTTPException(status_code=400, detail="Inventory quantity cannot be negative.")
        await session.execute(
            text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
            {"id": product_id, "quantity": new_quantity},
        )
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs (
                id, product_id, variant_id, old_quantity, new_quantity, delta, transaction_type, reference_code, reason, note,
                supplier_name, unit_cost, location_code, location_name
            )
            VALUES (
                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta, :transaction_type, :reference_code, :reason, :note,
                :supplier_name, :unit_cost, :location_code, :location_name
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": payload.variantId,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": new_quantity - old_quantity,
            "transaction_type": payload.transactionType,
            "reference_code": payload.referenceCode,
            "reason": payload.reason,
            "note": payload.note,
            "supplier_name": payload.supplierName,
            "unit_cost": payload.unitCost,
            "location_code": payload.locationCode,
            "location_name": payload.locationName,
        },
    )
    response_payload = {"ok": True, "oldQuantity": old_quantity, "newQuantity": new_quantity}
    if idem_key:
        await session.execute(
            text(
                """
                INSERT INTO product_inventory_idempotency (idempotency_key, product_id, response_payload)
                VALUES (:key, :product_id, CAST(:response_payload AS jsonb))
                ON CONFLICT DO NOTHING
                """
            ),
            {"key": idem_key, "product_id": product_id, "response_payload": json.dumps(response_payload)},
        )
    await sync_parent_price_from_variants(session, product_id)
    await session.commit()
    return response_payload


@router.patch("/products/{product_id}/variants/{variant_id}/inventory", dependencies=[Depends(require_permission("inventory:adjust"))])
async def set_variant_inventory(product_id: UUID, variant_id: UUID, payload: VariantInventoryPayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await adjust_product_inventory(
        product_id,
        InventoryAdjustmentPayload(
            variantId=variant_id,
            quantity=payload.quantity,
            transactionType=payload.transactionType,
            referenceCode=payload.referenceCode,
            reason=payload.reason,
            note=payload.note,
        ),
        idempotency_key=payload.referenceCode,
        session=session,
    )


@router.delete("/products/{product_id}", dependencies=[Depends(require_permission("product:delete"))])
async def deactivate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product_category_row = (
        await session.execute(
            text("SELECT category_id, subcategory_id FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not product_category_row:
        raise HTTPException(status_code=404, detail="Product not found.")
    await ensure_categories_not_migrating(session, [product_category_row["category_id"], product_category_row["subcategory_id"]])
    usage = (
        await session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM order_items WHERE product_id = :id) AS order_count,
                    (SELECT COUNT(*) FROM product_reviews WHERE product_id = :id) AS review_count
                """
            ),
            {"id": product_id},
        )
    ).mappings().one()
    if usage["order_count"] == 0 and usage["review_count"] == 0:
        result = await session.execute(text("UPDATE products SET status = 'ARCHIVED', updated_at = NOW() WHERE id = :id"), {"id": product_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found.")
        await session.commit()
        return {"ok": True, "action": "archived"}

    await session.execute(text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"), {"id": product_id})
    await session.commit()
    return {"ok": True, "action": "deactivated"}


@router.get("/vouchers", dependencies=[Depends(require_permission("voucher:read"))])
async def list_admin_vouchers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                code,
                discount_type AS "discountType",
                discount_value AS "discountAmount",
                min_order_value AS "minOrderValue",
                max_discount AS "maxDiscount",
                usage_limit AS "usageLimit",
                used_count AS "usedCount",
                total_budget_cap AS "totalBudgetCap",
                total_discount_used AS "totalDiscountUsed",
                per_user_limit AS "perUserLimit",
                per_device_limit AS "perDeviceLimit",
                per_ip_limit AS "perIpLimit",
                campaign_type AS "campaignType",
                audience_type AS "audienceType",
                eligible_tiers AS "eligibleTiers",
                eligible_user_registered_after AS "eligibleUserRegisteredAfter",
                assigned_user_id::text AS "assignedUserId",
                include_product_ids AS "includeProductIds",
                exclude_product_ids AS "excludeProductIds",
                include_category_ids AS "includeCategoryIds",
                exclude_category_ids AS "excludeCategoryIds",
                first_order_only AS "firstOrderOnly",
                hidden_code AS "hiddenCode",
                abandoned_cart_only AS "abandonedCartOnly",
                validity_days_after_claim AS "validityDaysAfterClaim",
                stackable,
                refund_policy AS "refundPolicy",
                starts_at AS "startsAt",
                ends_at AS "endsAt",
                internal_note AS "internalNote",
                status
            FROM vouchers
            ORDER BY created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/vouchers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("voucher:create"))])
async def create_voucher(
    payload: VoucherPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    voucher_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO vouchers (
                id, code, discount_type, discount_value, min_order_value, max_discount,
                usage_limit, total_budget_cap, per_user_limit, per_device_limit, per_ip_limit,
                campaign_type, audience_type, eligible_tiers, eligible_user_registered_after,
                assigned_user_id, include_product_ids, exclude_product_ids, include_category_ids,
                exclude_category_ids, first_order_only, hidden_code, abandoned_cart_only,
                validity_days_after_claim, stackable, refund_policy, starts_at, ends_at, internal_note, status
            )
            VALUES (
                :id, :code, :discount_type, :discount_value, :min_order_value, :max_discount,
                :usage_limit, :total_budget_cap, :per_user_limit, :per_device_limit, :per_ip_limit,
                :campaign_type, :audience_type, CAST(:eligible_tiers AS jsonb), :eligible_user_registered_after,
                :assigned_user_id, CAST(:include_product_ids AS jsonb), CAST(:exclude_product_ids AS jsonb), CAST(:include_category_ids AS jsonb),
                CAST(:exclude_category_ids AS jsonb), :first_order_only, :hidden_code, :abandoned_cart_only,
                :validity_days_after_claim, :stackable, :refund_policy, :starts_at, :ends_at, :internal_note, :status
            )
            """
        ),
        {
            "id": voucher_id,
            "code": payload.code.strip().upper(),
            "discount_type": payload.discountType if payload.discountType in {"FIXED", "PERCENT"} else "FIXED",
            "discount_value": payload.discountAmount,
            "min_order_value": payload.minOrderValue,
            "max_discount": payload.maxDiscount,
            "usage_limit": payload.usageLimit,
            "total_budget_cap": payload.totalBudgetCap,
            "per_user_limit": payload.perUserLimit,
            "per_device_limit": payload.perDeviceLimit,
            "per_ip_limit": payload.perIpLimit,
            "campaign_type": payload.campaignType,
            "audience_type": payload.audienceType,
            "eligible_tiers": json.dumps(payload.eligibleTiers),
            "eligible_user_registered_after": payload.eligibleUserRegisteredAfter,
            "assigned_user_id": payload.assignedUserId,
            "include_product_ids": json.dumps(payload.includeProductIds),
            "exclude_product_ids": json.dumps(payload.excludeProductIds),
            "include_category_ids": json.dumps(payload.includeCategoryIds),
            "exclude_category_ids": json.dumps(payload.excludeCategoryIds),
            "first_order_only": payload.firstOrderOnly,
            "hidden_code": payload.hiddenCode,
            "abandoned_cart_only": payload.abandonedCartOnly,
            "validity_days_after_claim": payload.validityDaysAfterClaim,
            "stackable": payload.stackable,
            "refund_policy": payload.refundPolicy,
            "starts_at": payload.startsAt,
            "ends_at": payload.endsAt,
            "internal_note": payload.internalNote,
            "status": payload.status if payload.status in {"ACTIVE", "INACTIVE", "EXPIRED"} else "ACTIVE",
        },
    )
    await session.commit()
    return {"id": str(voucher_id)}


@router.patch("/vouchers/{voucher_id}", dependencies=[Depends(require_permission("voucher:update"))])
async def update_voucher(
    voucher_id: UUID,
    payload: VoucherPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        text(
            """
            UPDATE vouchers
            SET code = :code,
                discount_type = :discount_type,
                discount_value = :discount_value,
                min_order_value = :min_order_value,
                max_discount = :max_discount,
                usage_limit = :usage_limit,
                total_budget_cap = :total_budget_cap,
                per_user_limit = :per_user_limit,
                per_device_limit = :per_device_limit,
                per_ip_limit = :per_ip_limit,
                campaign_type = :campaign_type,
                audience_type = :audience_type,
                eligible_tiers = CAST(:eligible_tiers AS jsonb),
                eligible_user_registered_after = :eligible_user_registered_after,
                assigned_user_id = :assigned_user_id,
                include_product_ids = CAST(:include_product_ids AS jsonb),
                exclude_product_ids = CAST(:exclude_product_ids AS jsonb),
                include_category_ids = CAST(:include_category_ids AS jsonb),
                exclude_category_ids = CAST(:exclude_category_ids AS jsonb),
                first_order_only = :first_order_only,
                hidden_code = :hidden_code,
                abandoned_cart_only = :abandoned_cart_only,
                validity_days_after_claim = :validity_days_after_claim,
                stackable = :stackable,
                refund_policy = :refund_policy,
                starts_at = :starts_at,
                ends_at = :ends_at,
                internal_note = :internal_note,
                status = :status,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": voucher_id,
            "code": payload.code.strip().upper(),
            "discount_type": payload.discountType if payload.discountType in {"FIXED", "PERCENT"} else "FIXED",
            "discount_value": payload.discountAmount,
            "min_order_value": payload.minOrderValue,
            "max_discount": payload.maxDiscount,
            "usage_limit": payload.usageLimit,
            "total_budget_cap": payload.totalBudgetCap,
            "per_user_limit": payload.perUserLimit,
            "per_device_limit": payload.perDeviceLimit,
            "per_ip_limit": payload.perIpLimit,
            "campaign_type": payload.campaignType,
            "audience_type": payload.audienceType,
            "eligible_tiers": json.dumps(payload.eligibleTiers),
            "eligible_user_registered_after": payload.eligibleUserRegisteredAfter,
            "assigned_user_id": payload.assignedUserId,
            "include_product_ids": json.dumps(payload.includeProductIds),
            "exclude_product_ids": json.dumps(payload.excludeProductIds),
            "include_category_ids": json.dumps(payload.includeCategoryIds),
            "exclude_category_ids": json.dumps(payload.excludeCategoryIds),
            "first_order_only": payload.firstOrderOnly,
            "hidden_code": payload.hiddenCode,
            "abandoned_cart_only": payload.abandonedCartOnly,
            "validity_days_after_claim": payload.validityDaysAfterClaim,
            "stackable": payload.stackable,
            "refund_policy": payload.refundPolicy,
            "starts_at": payload.startsAt,
            "ends_at": payload.endsAt,
            "internal_note": payload.internalNote,
            "status": payload.status if payload.status in {"ACTIVE", "INACTIVE", "EXPIRED"} else "ACTIVE",
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Voucher not found.")
    await session.commit()
    return {"ok": True}


@router.delete("/vouchers/{voucher_id}", dependencies=[Depends(require_permission("voucher:delete"))])
async def deactivate_voucher(
    voucher_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await session.execute(text("UPDATE vouchers SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"), {"id": voucher_id})
    await session.commit()
    return {"ok": True}


@router.get("/policies", dependencies=[Depends(require_permission("policy:read"))])
async def list_policies(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                code,
                title,
                summary,
                content,
                is_active AS "isActive",
                status,
                scheduled_at AS "scheduledAt",
                published_at AS "publishedAt",
                seo_title AS "seoTitle",
                seo_description AS "seoDescription",
                seo_keywords AS "seoKeywords",
                scope_type AS "scopeType",
                COALESCE(product_ids, '[]'::jsonb) AS "productIds",
                COALESCE(category_ids, '[]'::jsonb) AS "categoryIds",
                version,
                updated_at AS "updatedAt"
            FROM policies
            ORDER BY updated_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/policies", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("policy:create"))])
async def create_policy(
    payload: PolicyPayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    policy_id = uuid4()
    scheduled_at = parse_optional_datetime(payload.scheduledAt)
    published_at = parse_optional_datetime(payload.publishedAt)
    if scheduled_at and scheduled_at < datetime.now(timezone.utc) and payload.isActive:
        raise HTTPException(status_code=422, detail="scheduledAt must not be in the past.")
    effective_status = normalize_policy_status(payload.status, is_active=payload.isActive, scheduled_at=scheduled_at)
    if effective_status == "PUBLISHED" and not published_at:
        published_at = datetime.now(timezone.utc)
    await session.execute(
        text(
            """
            INSERT INTO policies (
                id, code, title, summary, content, is_active, status, scheduled_at, published_at,
                seo_title, seo_description, seo_keywords, scope_type, product_ids, category_ids, version
            )
            VALUES (
                :id, :code, :title, :summary, :content, :is_active, :status, :scheduled_at, :published_at,
                :seo_title, :seo_description, :seo_keywords, :scope_type,
                CAST(:product_ids AS jsonb), CAST(:category_ids AS jsonb), 1
            )
            """
        ),
        {
            "id": policy_id,
            "code": payload.code.strip().lower(),
            "title": payload.title,
            "summary": payload.summary.strip(),
            "content": payload.content,
            "is_active": payload.isActive,
            "status": effective_status,
            "scheduled_at": scheduled_at,
            "published_at": published_at,
            "seo_title": payload.seoTitle.strip(),
            "seo_description": payload.seoDescription.strip(),
            "seo_keywords": payload.seoKeywords.strip(),
            "scope_type": (payload.scopeType or "GLOBAL").strip().upper(),
            "product_ids": json.dumps(normalize_policy_scope_ids(payload.productIds), ensure_ascii=False),
            "category_ids": json.dumps(normalize_policy_scope_ids(payload.categoryIds), ensure_ascii=False),
        },
    )
    await create_policy_version_snapshot(session, policy_id=policy_id, version_number=1, action="CREATED", actor_id=actor_id)
    await audit_admin_event(session, actor_id=actor_id, event_type="policy_created", resource="policy", metadata={"policyId": str(policy_id), "code": payload.code.strip().lower(), "status": effective_status})
    await session.commit()
    return {"id": str(policy_id)}


@router.patch("/policies/{policy_id}", dependencies=[Depends(require_permission("policy:update"))])
async def update_policy(
    policy_id: UUID,
    payload: PolicyPayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    current = (
        await session.execute(
            text("SELECT version FROM policies WHERE id = :id"),
            {"id": policy_id},
        )
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Policy not found.")
    if payload.version is not None and int(current["version"] or 0) != payload.version:
        raise HTTPException(status_code=409, detail="Policy version mismatch. Reload before saving.")
    scheduled_at = parse_optional_datetime(payload.scheduledAt)
    published_at = parse_optional_datetime(payload.publishedAt)
    if scheduled_at and scheduled_at < datetime.now(timezone.utc) and payload.isActive:
        raise HTTPException(status_code=422, detail="scheduledAt must not be in the past.")
    effective_status = normalize_policy_status(payload.status, is_active=payload.isActive, scheduled_at=scheduled_at)
    if effective_status == "PUBLISHED" and not published_at:
        published_at = datetime.now(timezone.utc)
    result = await session.execute(
        text(
            """
            UPDATE policies
            SET code = :code,
                title = :title,
                summary = :summary,
                content = :content,
                is_active = :is_active,
                status = :status,
                scheduled_at = :scheduled_at,
                published_at = :published_at,
                seo_title = :seo_title,
                seo_description = :seo_description,
                seo_keywords = :seo_keywords,
                scope_type = :scope_type,
                product_ids = CAST(:product_ids AS jsonb),
                category_ids = CAST(:category_ids AS jsonb),
                version = version + 1,
                updated_at = NOW()
            WHERE id = :id AND (:expected_version IS NULL OR version = :expected_version)
            """
        ),
        {
            "id": policy_id,
            "code": payload.code.strip().lower(),
            "title": payload.title,
            "summary": payload.summary.strip(),
            "content": payload.content,
            "is_active": payload.isActive,
            "status": effective_status,
            "scheduled_at": scheduled_at,
            "published_at": published_at,
            "seo_title": payload.seoTitle.strip(),
            "seo_description": payload.seoDescription.strip(),
            "seo_keywords": payload.seoKeywords.strip(),
            "scope_type": (payload.scopeType or "GLOBAL").strip().upper(),
            "product_ids": json.dumps(normalize_policy_scope_ids(payload.productIds), ensure_ascii=False),
            "category_ids": json.dumps(normalize_policy_scope_ids(payload.categoryIds), ensure_ascii=False),
            "expected_version": payload.version,
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=409, detail="Policy version mismatch. Reload before saving.")
    next_version = int(current["version"] or 0) + 1
    await create_policy_version_snapshot(session, policy_id=policy_id, version_number=next_version, action="UPDATED", actor_id=actor_id)
    await audit_admin_event(session, actor_id=actor_id, event_type="policy_updated", resource="policy", metadata={"policyId": str(policy_id), "status": effective_status, "version": next_version})
    await session.commit()
    return {"ok": True}


@router.get("/policies/{policy_id}/history", dependencies=[Depends(require_permission("policy:read"))])
async def list_policy_history(
    policy_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pv.id::text,
                pv.version_number AS "versionNumber",
                pv.action,
                pv.actor_id::text AS "actorId",
                pv.snapshot,
                pv.created_at AS "createdAt"
            FROM policy_versions pv
            WHERE pv.policy_id = :policy_id
            ORDER BY pv.version_number DESC, pv.created_at DESC
            """
        ),
        {"policy_id": policy_id},
    )
    return [dict(row._mapping) for row in result]


@router.delete("/policies/{policy_id}", dependencies=[Depends(require_permission("policy:delete"))])
async def deactivate_policy(
    policy_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    current = (
        await session.execute(
            text("SELECT version FROM policies WHERE id = :id"),
            {"id": policy_id},
        )
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Policy not found.")
    result = await session.execute(
        text(
            """
            UPDATE policies
            SET is_active = FALSE, status = 'ARCHIVED', version = version + 1, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": policy_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Policy not found.")
    next_version = int(current["version"] or 0) + 1
    await create_policy_version_snapshot(session, policy_id=policy_id, version_number=next_version, action="ARCHIVED", actor_id=actor_id)
    await audit_admin_event(session, actor_id=actor_id, event_type="policy_archived", resource="policy", metadata={"policyId": str(policy_id), "version": next_version})
    await session.commit()
    return {"ok": True}


@router.get("/customers", dependencies=[Depends(require_permission("customer:read"))])
async def list_admin_customers(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    offset = (page - 1) * limit
    search_value = (search or "").strip().lower()
    params: dict[str, object] = {"limit": limit, "offset": offset, "search": f"%{search_value}%"}
    where_clause = """
        WHERE u.status != 'DELETED'
          AND (
            :search = '%%'
            OR LOWER(COALESCE(u.full_name, '')) LIKE :search
            OR LOWER(COALESCE(u.email, '')) LIKE :search
            OR LOWER(COALESCE(r.code, '')) LIKE :search
            OR LOWER(COALESCE(u.loyalty_tier, '')) LIKE :search
            OR LOWER(COALESCE(u.status, '')) LIKE :search
          )
    """
    total = await session.scalar(
        text(
            f"""
            SELECT COUNT(*)
            FROM users u
            JOIN roles r ON r.id = u.role_id
            {where_clause}
            """
        ),
        params,
    )
    result = await session.execute(
        text(
            f"""
            SELECT
                u.id::text,
                u.email,
                u.full_name AS "fullName",
                u.phone,
                u.status,
                r.code AS role,
                u.loyalty_tier AS tier,
                u.loyalty_points_balance AS points,
                COUNT(o.id) AS "orderCount",
                COALESCE(SUM(o.total_amount), 0) AS "totalSpent",
                u.created_at AS "createdAt"
            FROM users u
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN orders o ON o.user_id = u.id
            {where_clause}
            GROUP BY u.id, r.code
            ORDER BY u.created_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        params,
    )
    return {
        "items": [dict(row._mapping) for row in result],
        "page": page,
        "limit": limit,
        "total": int(total or 0),
    }


@router.get("/customers/{user_id}", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_detail(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    customer = (
        await session.execute(
            text(
                """
                SELECT
                    u.id::text,
                    u.email,
                    u.full_name AS "fullName",
                    u.phone,
                    u.status,
                    r.code AS role,
                    u.loyalty_tier AS tier,
                    u.loyalty_points_balance AS points,
                    u.loyalty_wallet_status AS "walletStatus",
                    COUNT(o.id) AS "orderCount",
                    COALESCE(SUM(o.total_amount), 0) AS "totalSpent",
                    COALESCE(SUM(o.loyalty_points_earned), 0) AS "totalPointsEarned",
                    COALESCE(SUM(o.loyalty_points_used), 0) AS "totalPointsUsed",
                    u.created_at AS "createdAt",
                    u.updated_at AS "updatedAt"
                FROM users u
                JOIN roles r ON r.id = u.role_id
                LEFT JOIN orders o ON o.user_id = u.id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                GROUP BY u.id, r.code
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if not customer:
        raise HTTPException(status_code=404, detail="User not found.")

    tags = (
        await session.execute(
            text("SELECT tag FROM customer_tags WHERE user_id = :user_id ORDER BY tag"),
            {"user_id": user_id},
        )
    ).scalars().all()
    notes = (
        await session.execute(
            text(
                """
                SELECT COUNT(*) AS count, MAX(created_at) AS "lastCreatedAt"
                FROM customer_notes
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    voucher_count = await session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM user_vouchers
            WHERE user_id = :user_id AND status IN ('AVAILABLE', 'RESERVED', 'USED')
            """
        ),
        {"user_id": user_id},
    )
    return {
        **dict(customer),
        "tags": [str(tag) for tag in tags],
        "noteCount": int(notes["count"] or 0) if notes else 0,
        "lastNoteAt": notes["lastCreatedAt"] if notes else None,
        "voucherCount": int(voucher_count or 0),
    }


@router.get("/customers/{user_id}/overview", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_overview(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await get_admin_customer_detail(user_id, session)


@router.get("/customers/{user_id}/orders", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_orders(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                o.id::text,
                o.order_code AS "orderCode",
                o.status,
                o.payment_method AS "paymentMethod",
                o.payment_status AS "paymentStatus",
                o.total_amount AS "totalAmount",
                o.loyalty_points_earned AS "pointsEarned",
                o.loyalty_points_used AS "pointsUsed",
                o.created_at AS "createdAt",
                o.updated_at AS "updatedAt"
            FROM orders o
            WHERE o.user_id = :user_id
            ORDER BY o.created_at DESC
            LIMIT 100
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/customers/{user_id}/loyalty-history", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_loyalty_history(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                lt.id::text,
                lt.order_id::text AS "orderId",
                lt.type,
                lt.points,
                lt.balance_before AS "balanceBefore",
                lt.balance_after AS "balanceAfter",
                lt.reason,
                lt.metadata,
                lt.created_at AS "createdAt"
            FROM loyalty_transactions lt
            WHERE lt.user_id = :user_id
            ORDER BY lt.created_at DESC
            LIMIT 200
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/customers/{user_id}/notes", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_notes(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                n.id::text,
                n.user_id::text AS "userId",
                n.author_id::text AS "authorId",
                author.full_name AS "authorName",
                n.content,
                n.created_at AS "createdAt",
                n.updated_at AS "updatedAt"
            FROM customer_notes n
            LEFT JOIN users author ON author.id = n.author_id
            WHERE n.user_id = :user_id
            ORDER BY n.created_at DESC
            LIMIT 100
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/customers/{user_id}/audit-logs", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_audit_logs(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                user_id::text AS "userId",
                event_type AS "eventType",
                metadata,
                created_at AS "createdAt"
            FROM security_audit_logs
            WHERE metadata->>'targetUserId' = :user_id
               OR metadata->>'userId' = :user_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"user_id": str(user_id)},
    )
    return [dict(row._mapping) for row in result]


@router.put("/customers/{user_id}/tags", dependencies=[Depends(require_permission("customer:update"))])
async def update_admin_customer_tags(
    user_id: UUID,
    payload: CustomerTagsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    tags = normalize_customer_tags(payload.tags)
    exists = await session.scalar(text("SELECT 1 FROM users WHERE id = :user_id AND status != 'DELETED'"), {"user_id": user_id})
    if not exists:
        raise HTTPException(status_code=404, detail="User not found.")
    await session.execute(text("DELETE FROM customer_tags WHERE user_id = :user_id"), {"user_id": user_id})
    if tags:
        await session.execute(
            text(
                """
                INSERT INTO customer_tags (user_id, tag)
                SELECT :user_id, tag
                FROM unnest(CAST(:tags AS text[])) AS tag
                """
            ),
            {"user_id": user_id, "tags": tags},
        )
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_tags_updated",
        resource="customer",
        target_user_id=user_id,
        metadata={"tags": tags},
    )
    await session.commit()
    return {"ok": True, "tags": tags}


@router.put("/customers/tags/bulk", dependencies=[Depends(require_permission("customer:update"))])
async def bulk_update_admin_customer_tags(
    payload: CustomerBulkTagsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    tags = normalize_customer_tags(payload.tags)
    user_ids = list(dict.fromkeys(payload.userIds))
    await session.execute(
        text("DELETE FROM customer_tags WHERE user_id IN :user_ids").bindparams(bindparam("user_ids", expanding=True)),
        {"user_ids": user_ids},
    )
    if tags:
        for user_id in user_ids:
            await session.execute(
                text(
                    """
                    INSERT INTO customer_tags (user_id, tag)
                    SELECT :user_id, tag
                    FROM unnest(CAST(:tags AS text[])) AS tag
                    """
                ),
                {"user_id": user_id, "tags": tags},
            )
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_tags_bulk_updated",
        resource="customer_bulk_tags",
        metadata={"userIds": [str(user_id) for user_id in user_ids], "tags": tags, "affectedUsers": len(user_ids)},
    )
    await session.commit()
    return {"ok": True, "affectedUsers": len(user_ids), "tags": tags}


@router.post("/customers/{user_id}/notes", dependencies=[Depends(require_permission("customer:update"))])
async def create_admin_customer_note(
    user_id: UUID,
    payload: CustomerNotePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    exists = await session.scalar(text("SELECT 1 FROM users WHERE id = :user_id AND status != 'DELETED'"), {"user_id": user_id})
    if not exists:
        raise HTTPException(status_code=404, detail="User not found.")
    note = (
        await session.execute(
            text(
                """
                INSERT INTO customer_notes (user_id, author_id, content)
                VALUES (:user_id, :author_id, :content)
                RETURNING id::text, created_at AS "createdAt"
                """
            ),
            {"user_id": user_id, "author_id": current_user_id, "content": payload.content.strip()},
        )
    ).mappings().one()
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_note_created",
        resource="customer",
        target_user_id=user_id,
        metadata={"noteId": note["id"]},
    )
    await session.commit()
    return {"ok": True, **dict(note)}


@router.post("/customers/{user_id}/loyalty-adjustments", dependencies=[Depends(require_permission("customer:loyalty_adjust"))])
async def create_admin_customer_loyalty_adjustment(
    user_id: UUID,
    payload: CustomerLoyaltyAdjustmentPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    if payload.delta == 0:
        raise HTTPException(status_code=400, detail="Delta must not be 0.")
    await ensure_manual_loyalty_limit(session, actor_id=current_user_id, requested_delta=payload.delta)
    user = (
        await session.execute(
            text(
                """
                SELECT loyalty_points_balance, loyalty_wallet_status
                FROM users
                WHERE id = :user_id AND status != 'DELETED'
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user["loyalty_wallet_status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail="Loyalty wallet is not active.")
    balance_before = int(user["loyalty_points_balance"] or 0)
    balance_after = balance_before + payload.delta
    if balance_after < 0:
        raise HTTPException(status_code=400, detail="Insufficient loyalty points for this adjustment.")
    await session.execute(
        text("UPDATE users SET loyalty_points_balance = :balance_after, updated_at = NOW() WHERE id = :user_id"),
        {"user_id": user_id, "balance_after": balance_after},
    )
    await session.execute(
        text(
            """
            INSERT INTO loyalty_transactions (user_id, type, points, balance_before, balance_after, reason, metadata)
            VALUES (
                :user_id,
                'ADJUST',
                :points,
                :balance_before,
                :balance_after,
                :reason,
                CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "user_id": user_id,
            "points": abs(payload.delta),
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reason": payload.reason.strip(),
            "metadata": json.dumps(
                {
                    "delta": payload.delta,
                    "adjustedBy": str(current_user_id),
                    "source": "admin_manual_adjustment",
                },
                ensure_ascii=False,
            ),
        },
    )
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_loyalty_adjusted",
        resource="customer",
        target_user_id=user_id,
        metadata={"delta": payload.delta, "balanceBefore": balance_before, "balanceAfter": balance_after},
    )
    await session.commit()
    return {"ok": True, "balanceBefore": balance_before, "balanceAfter": balance_after}


@router.post("/customers/{user_id}/vouchers", dependencies=[Depends(require_permission("customer:issue_voucher"))])
async def issue_admin_customer_voucher(
    user_id: UUID,
    payload: CustomerVoucherIssuePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user = (
        await session.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE id = :user_id AND status != 'DELETED'
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    voucher = (
        await session.execute(
            text(
                """
                SELECT id, starts_at, ends_at, validity_days_after_claim
                FROM vouchers
                WHERE id = :voucher_id AND status = 'ACTIVE'
                FOR UPDATE
                """
            ),
            {"voucher_id": payload.voucherId},
        )
    ).mappings().first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found or inactive.")
    claimed = (
        await session.execute(
            text(
                """
                INSERT INTO user_vouchers (id, user_id, voucher_id, status, expires_at)
                VALUES (
                    gen_random_uuid(),
                    :user_id,
                    :voucher_id,
                    'AVAILABLE',
                    :expires_at
                )
                ON CONFLICT (user_id, voucher_id) WHERE status IN ('AVAILABLE', 'RESERVED', 'USED') DO NOTHING
                RETURNING id::text, voucher_id::text AS "voucherId", expires_at AS "expiresAt"
                """
            ),
            {
                "user_id": user_id,
                "voucher_id": payload.voucherId,
                "expires_at": voucher["ends_at"] or (
                    datetime.now(timezone.utc) + timedelta(days=int(voucher["validity_days_after_claim"] or 0))
                    if int(voucher["validity_days_after_claim"] or 0) > 0
                    else None
                ),
            },
        )
    ).mappings().first()
    if not claimed:
        raise HTTPException(status_code=409, detail="Customer already owns this voucher.")
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_voucher_issued",
        resource="customer",
        target_user_id=user_id,
        metadata={"voucherId": str(payload.voucherId), "note": payload.note},
    )
    await session.commit()
    return {"ok": True, **dict(claimed)}


@router.patch("/users/status/bulk", dependencies=[Depends(require_permission("sys:manage_users"))])
async def bulk_update_user_status(
    payload: CustomerBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user_ids = list(dict.fromkeys(payload.userIds))
    result = await session.execute(
        text(
            """
            UPDATE users
            SET status = :status, updated_at = NOW()
            WHERE id IN :user_ids AND status != 'DELETED'
            """
        ).bindparams(bindparam("user_ids", expanding=True)),
        {"status": payload.status, "user_ids": user_ids},
    )
    await revoke_users(session, user_ids, "bulk_status_changed")
    await clear_permission_cache(redis, user_ids)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_user_status_bulk_updated",
        resource="customer_access_bulk",
        metadata={"userIds": [str(user_id) for user_id in user_ids], "status": payload.status, "affectedUsers": result.rowcount},
    )
    await session.commit()
    return {"ok": True, "affectedUsers": result.rowcount}


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_permission("sys:manage_users"))])
async def update_user_role(
    user_id: UUID,
    payload: UserRolePayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    before = (
        await session.execute(
            text(
                """
                SELECT r.code AS role, u.status
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if before is None:
        raise HTTPException(status_code=404, detail="User not found.")
    role_id = (
        await session.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": payload.role})
    ).scalar_one_or_none()
    if role_id is None:
        raise HTTPException(status_code=404, detail="Role not found.")

    result = await session.execute(
        text(
            """
            UPDATE users
            SET role_id = :role_id, status = :status, updated_at = NOW()
            WHERE id = :user_id AND status != 'DELETED'
            """
        ),
        {"user_id": user_id, "role_id": role_id, "status": payload.status},
    )
    await revoke_users(session, [user_id], "role_changed")
    await clear_permission_cache(redis, [user_id])
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_user_access_updated",
        resource="customer_access",
        target_user_id=user_id,
        metadata={
            "before": dict(before),
            "after": {"role": payload.role, "status": payload.status},
        },
    )
    await session.commit()
    return {"ok": True}


@router.get("/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def list_permissions(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, module, description
            FROM permissions
            ORDER BY module, code
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/roles", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def list_roles(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, name
            FROM roles
            WHERE code IN ('CUSTOMER', 'STAFF_ADMIN', 'SUPER_ADMIN')
            ORDER BY CASE code WHEN 'SUPER_ADMIN' THEN 1 WHEN 'STAFF_ADMIN' THEN 2 ELSE 3 END
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def get_role_permissions(role_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    role = (
        await session.execute(text("SELECT id::text, code, name FROM roles WHERE id = :id"), {"id": role_id})
    ).mappings().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")
    result = await session.execute(
        text(
            """
            SELECT p.code
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = :role_id
            ORDER BY p.code
            """
        ),
        {"role_id": role_id},
    )
    return {**dict(role), "permissionCodes": [str(code) for code in result.scalars().all()]}


@router.put("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def update_role_permissions(
    role_id: UUID,
    payload: RolePermissionsPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    role = (
        await session.execute(text("SELECT code FROM roles WHERE id = :id"), {"id": role_id})
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    previous_permission_codes = (
        await session.execute(
            text(
                """
                SELECT p.code
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = :role_id
                ORDER BY p.code
                """
            ),
            {"role_id": role_id},
        )
    ).scalars().all()
    if role == "SUPER_ADMIN":
        permission_codes = (
            await session.execute(text("SELECT code FROM permissions ORDER BY code"))
        ).scalars().all()
    else:
        permission_codes = sorted(set(payload.permissionCodes))
        unknown = (
            await session.execute(
                text("SELECT code FROM permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
                {"codes": permission_codes or ["__none__"]},
            )
        ).scalars().all()
        if set(unknown) != set(permission_codes):
            raise HTTPException(status_code=400, detail="One or more permissions are invalid.")

    await session.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": role_id})
    if permission_codes:
        await session.execute(
            text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :role_id, id
                FROM permissions
                WHERE code IN :codes
                ON CONFLICT DO NOTHING
                """
            ).bindparams(bindparam("codes", expanding=True)),
            {"role_id": role_id, "codes": list(permission_codes)},
        )
    users = (
        await session.execute(text("SELECT id FROM users WHERE role_id = :role_id"), {"role_id": role_id})
    ).scalars().all()
    user_ids = list(users)
    await revoke_users(session, user_ids, "permissions_changed")
    await clear_permission_cache(redis, user_ids)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_role_permissions_updated",
        resource="role_permissions",
        metadata={
            "roleId": str(role_id),
            "roleCode": role,
            "before": list(previous_permission_codes),
            "after": list(permission_codes),
            "affectedUsers": len(user_ids),
        },
    )
    await session.commit()
    return {"ok": True, "permissionCodes": list(permission_codes)}


@router.get("/audit-logs", dependencies=[Depends(require_permission("audit:read"))])
async def list_audit_logs(
    event_type: str | None = None,
    actor_id: UUID | None = None,
    resource: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    limit = max(1, min(limit, 500))
    filters = ["event_type LIKE 'admin_%'"]
    params: dict[str, object] = {"limit": limit}
    if event_type:
        filters.append("event_type = :event_type")
        params["event_type"] = event_type
    if actor_id:
        filters.append("user_id = :actor_id")
        params["actor_id"] = actor_id
    if resource:
        filters.append("metadata->>'resource' = :resource")
        params["resource"] = resource
    if from_date:
        filters.append("created_at >= CAST(:from_date AS timestamptz)")
        params["from_date"] = from_date
    if to_date:
        filters.append("created_at <= CAST(:to_date AS timestamptz)")
        params["to_date"] = to_date
    result = await session.execute(
        text(
            f"""
            SELECT id::text, user_id::text AS "userId", event_type AS "eventType",
                   email, ip_address AS "ipAddress", user_agent AS "userAgent",
                   metadata, created_at AS "createdAt"
            FROM security_audit_logs
            WHERE {' AND '.join(filters)}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        params,
    )
    return [dict(row._mapping) for row in result]


@router.get("/reviews", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_reviews(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pr.id::text,
                pr.product_id::text AS "productId",
                p.name AS "productName",
                pr.user_id::text AS "userId",
                pr.user_name AS "userName",
                pr.rating,
                pr.comment,
                pr.media_urls AS "mediaUrls",
                pr.status,
                pr.moderation_note AS "moderationNote",
                pr.shop_reply AS "shopReply",
                pr.shop_replied_at AS "shopRepliedAt",
                pr.flagged_reason AS "flaggedReason",
                pr.flagged_at AS "flaggedAt",
                pr.is_spam AS "isSpam",
                pr.spam_reason AS "spamReason",
                pr.review_window_expires_at AS "reviewWindowExpiresAt",
                pr.edited_at AS "editedAt",
                CASE
                    WHEN o.status = 'REFUNDED' THEN 'DA_HOAN_TIEN'
                    WHEN o.status = 'RETURNED' THEN 'DA_TRA_HANG'
                    ELSE NULL
                END AS "orderOutcome",
                pr.created_at AS "createdAt"
            FROM product_reviews pr
            JOIN products p ON p.id = pr.product_id
            LEFT JOIN orders o ON o.id = pr.order_id
            ORDER BY pr.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/reviews/summary", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_review_summary(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text AS "productId",
                p.name AS "productName",
                COUNT(pr.id) AS "totalReviews",
                COALESCE(p.review_count, 0) AS "publishedReviews",
                COUNT(*) FILTER (WHERE pr.status = 'PENDING') AS "pendingReviews",
                COUNT(*) FILTER (WHERE pr.flagged_reason IS NOT NULL) AS "flaggedReviews",
                p.rating AS "averageRating"
            FROM products p
            JOIN product_reviews pr ON pr.product_id = p.id
            GROUP BY p.id, p.name, p.rating, p.review_count
            ORDER BY "averageRating" DESC NULLS LAST, "totalReviews" DESC, p.name
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.patch("/reviews/{review_id}", dependencies=[Depends(require_permission("review:update"))])
async def update_review_status(review_id: UUID, payload: ReviewStatusPayload, session: AsyncSession = Depends(get_session)) -> dict:
    product_id = await session.scalar(text("SELECT product_id FROM product_reviews WHERE id = :id"), {"id": review_id})
    if not product_id:
        raise HTTPException(status_code=404, detail="Review not found.")

    updates: list[str] = []
    params: dict[str, object] = {"id": review_id}

    if payload.status is not None:
        updates.append("status = :status")
        params["status"] = payload.status
    if payload.moderationNote is not None:
        updates.append("moderation_note = :moderation_note")
        params["moderation_note"] = sanitize_review_text(payload.moderationNote).strip() or None
    if payload.shopReply is not None:
        updates.append("shop_reply = :shop_reply")
        updates.append("shop_replied_at = CASE WHEN :shop_reply IS NULL THEN NULL ELSE NOW() END")
        params["shop_reply"] = sanitize_review_text(payload.shopReply).strip() or None
    if payload.flaggedReason is not None:
        updates.append("flagged_reason = :flagged_reason")
        updates.append("flagged_at = CASE WHEN :flagged_reason IS NULL THEN NULL ELSE NOW() END")
        params["flagged_reason"] = sanitize_review_text(payload.flaggedReason).strip() or None
    if payload.isSpam is not None:
        updates.append("is_spam = :is_spam")
        params["is_spam"] = payload.isSpam
    if payload.spamReason is not None:
        updates.append("spam_reason = :spam_reason")
        params["spam_reason"] = sanitize_review_text(payload.spamReason).strip() or None

    if not updates:
        raise HTTPException(status_code=400, detail="No review fields supplied for update.")

    updates.append("updated_at = NOW()")
    result = await session.execute(
        text(f"UPDATE product_reviews SET {', '.join(updates)} WHERE id = :id"),
        params,
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Review not found.")
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True}


@router.delete("/reviews/{review_id}", dependencies=[Depends(require_permission("review:delete"))])
async def delete_review(review_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product_id = await session.scalar(text("SELECT product_id FROM product_reviews WHERE id = :id"), {"id": review_id})
    if not product_id:
        raise HTTPException(status_code=404, detail="Review not found.")
    result = await session.execute(text("DELETE FROM product_reviews WHERE id = :id"), {"id": review_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Review not found.")
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True}


def normalize_content_type(value: str | None) -> str:
    candidate = (value or "VIDEO").strip().upper()
    return candidate if candidate in {"VIDEO", "BANNER", "MARKETING_PAGE"} else "VIDEO"


def normalize_content_status(value: str | None, *, scheduled_at: datetime | None, published_at: datetime | None, is_active: bool) -> str:
    candidate = (value or "").strip().upper()
    allowed = {"DRAFT", "SCHEDULED", "PUBLISHED", "ARCHIVED"}
    if candidate not in allowed:
        if not is_active:
            return "ARCHIVED"
        if scheduled_at and scheduled_at > datetime.now(timezone.utc):
            return "SCHEDULED"
        if published_at or is_active:
            return "PUBLISHED"
        return "DRAFT"
    return candidate


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_policy_status(status_value: str | None, *, is_active: bool, scheduled_at: datetime | None) -> str:
    candidate = (status_value or "DRAFT").strip().upper()
    if candidate not in {"DRAFT", "SCHEDULED", "PUBLISHED", "ARCHIVED"}:
        candidate = "DRAFT"
    if candidate == "ARCHIVED":
        return "ARCHIVED"
    if scheduled_at and scheduled_at > datetime.now(timezone.utc):
        return "SCHEDULED"
    if candidate == "PUBLISHED" and is_active:
        return "PUBLISHED"
    return candidate


def normalize_policy_scope_ids(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized[:100]


async def create_policy_version_snapshot(
    session: AsyncSession,
    *,
    policy_id: UUID,
    version_number: int,
    action: str,
    actor_id: UUID | None,
) -> None:
    snapshot_result = await session.execute(
        text(
            """
            SELECT jsonb_build_object(
                'id', id::text,
                'code', code,
                'title', title,
                'summary', summary,
                'content', content,
                'isActive', is_active,
                'status', status,
                'scheduledAt', scheduled_at,
                'publishedAt', published_at,
                'seoTitle', seo_title,
                'seoDescription', seo_description,
                'seoKeywords', seo_keywords,
                'scopeType', scope_type,
                'productIds', COALESCE(product_ids, '[]'::jsonb),
                'categoryIds', COALESCE(category_ids, '[]'::jsonb),
                'updatedAt', updated_at
            )
            FROM policies
            WHERE id = :id
            """
        ),
        {"id": policy_id},
    )
    snapshot = snapshot_result.scalar_one_or_none()
    if snapshot is None:
        return
    await session.execute(
        text(
            """
            INSERT INTO policy_versions (id, policy_id, version_number, action, snapshot, actor_id)
            VALUES (:id, :policy_id, :version_number, :action, CAST(:snapshot AS jsonb), :actor_id)
            """
        ),
        {
            "id": uuid4(),
            "policy_id": policy_id,
            "version_number": version_number,
            "action": action,
            "snapshot": json.dumps(snapshot, ensure_ascii=False, default=str),
            "actor_id": actor_id,
        },
    )


def normalize_content_comments(comments: list[ContentCommentPayload]) -> list[dict]:
    normalized: list[dict] = []
    for item in comments:
        normalized.append(
            {
                "id": item.id or uuid4().hex[:12],
                "userName": item.userName.strip(),
                "content": sanitize_review_text(item.content).strip(),
                "parentId": item.parentId,
                "isHidden": bool(item.isHidden),
            }
        )
    return normalized


def validate_content_payload(payload: ContentPayload) -> dict:
    content_type = normalize_content_type(payload.contentType)
    ensure_not_data_url(payload.videoUrl, "videoUrl")
    ensure_not_data_url(payload.thumbnailUrl, "thumbnailUrl")
    ensure_not_data_url(payload.bannerImageUrl, "bannerImageUrl")
    ensure_not_data_url(payload.ctaUrl, "ctaUrl")
    scheduled_at = parse_optional_datetime(payload.scheduledAt)
    published_at = parse_optional_datetime(payload.publishedAt)
    now_utc = datetime.now(timezone.utc)
    if content_type == "VIDEO" and not payload.videoUrl:
        raise HTTPException(status_code=422, detail="Video content requires videoUrl.")
    if content_type == "BANNER" and not (payload.bannerImageUrl or payload.thumbnailUrl):
        raise HTTPException(status_code=422, detail="Banner content requires bannerImageUrl or thumbnailUrl.")
    if payload.videoUrl and not any(str(payload.videoUrl).lower().endswith(ext) for ext in (".mp4", ".webm")):
        raise HTTPException(status_code=422, detail="videoUrl must use mp4 or webm.")
    if scheduled_at and scheduled_at < now_utc + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="scheduledAt must be at least 5 minutes in the future.")
    if scheduled_at and published_at and published_at < scheduled_at:
        raise HTTPException(status_code=422, detail="publishedAt must not be earlier than scheduledAt.")
    status_value = normalize_content_status(payload.status, scheduled_at=scheduled_at, published_at=published_at, is_active=payload.isActive)
    comments = normalize_content_comments(payload.comments)
    return {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "content_type": content_type,
        "status": status_value,
        "video_url": payload.videoUrl,
        "thumbnail_url": payload.thumbnailUrl,
        "banner_image_url": payload.bannerImageUrl,
        "content_body": payload.contentBody.strip(),
        "cta_label": payload.ctaLabel.strip() if payload.ctaLabel else None,
        "cta_url": payload.ctaUrl,
        "product_ids": [item for item in payload.productIds if item],
        "category_ids": [item for item in payload.categoryIds if item],
        "comments": comments,
        "like_count": payload.likeCount,
        "view_count": payload.viewCount,
        "sort_order": payload.sortOrder,
        "scheduled_at": scheduled_at,
        "published_at": published_at,
        "is_active": payload.isActive,
        "version": payload.version,
    }


def content_storefront_cache_key(page: int, limit: int) -> str:
    return f"storefront:content:videos:page:{page}:limit:{limit}"


async def invalidate_content_storefront_cache(redis: Redis, max_pages: int = 12, page_sizes: tuple[int, ...] = (12, 24, 48)) -> None:
    tracked_key = "storefront:content:videos:keys"
    tracked = await redis.smembers(tracked_key)
    if tracked:
        await redis.delete(*list(tracked))
    await redis.delete(tracked_key)


async def replace_content_product_relations(session: AsyncSession, content_id: UUID, product_ids: list[str]) -> None:
    await session.execute(text("DELETE FROM content_product_relations WHERE content_id = :content_id"), {"content_id": content_id})
    for product_id in product_ids:
        await session.execute(
            text(
                """
                INSERT INTO content_product_relations (content_id, product_id)
                VALUES (:content_id, :product_id)
                ON CONFLICT (content_id, product_id) DO NOTHING
                """
            ),
            {"content_id": content_id, "product_id": product_id},
        )


async def replace_content_category_relations(session: AsyncSession, content_id: UUID, category_ids: list[str]) -> None:
    await session.execute(text("DELETE FROM content_category_relations WHERE content_id = :content_id"), {"content_id": content_id})
    for category_id in category_ids:
        await session.execute(
            text(
                """
                INSERT INTO content_category_relations (content_id, category_id)
                VALUES (:content_id, :category_id)
                ON CONFLICT (content_id, category_id) DO NOTHING
                """
            ),
            {"content_id": content_id, "category_id": category_id},
        )


async def replace_content_comments(session: AsyncSession, content_id: UUID, comments: list[dict], actor_id: UUID) -> None:
    await session.execute(text("DELETE FROM content_comments WHERE content_id = :content_id"), {"content_id": content_id})
    for item in comments:
        comment_id = item.get("id")
        try:
            persisted_id = UUID(str(comment_id))
        except Exception:
            persisted_id = uuid4()
        parent_id = item.get("parentId")
        try:
            parent_uuid = UUID(str(parent_id)) if parent_id else None
        except Exception:
            parent_uuid = None
        await session.execute(
            text(
                """
                INSERT INTO content_comments (
                    id, content_id, user_name, body, parent_id, is_hidden, created_by, updated_by
                )
                VALUES (
                    :id, :content_id, :user_name, :body, :parent_id, :is_hidden, :created_by, :updated_by
                )
                """
            ),
            {
                "id": persisted_id,
                "content_id": content_id,
                "user_name": item["userName"],
                "body": item["content"],
                "parent_id": parent_uuid,
                "is_hidden": item["isHidden"],
                "created_by": actor_id,
                "updated_by": actor_id,
            },
        )


@router.get("/content", dependencies=[Depends(require_permission("content:read"))])
async def list_admin_content(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                v.id::text,
                v.title,
                v.description,
                v.content_type AS "contentType",
                v.status,
                v.video_url AS "videoUrl",
                v.thumbnail_url AS "thumbnailUrl",
                v.banner_image_url AS "bannerImageUrl",
                v.content_body AS "contentBody",
                LEFT(COALESCE(v.content_body, ''), 320) AS "contentBodyPreview",
                v.cta_label AS "ctaLabel",
                v.cta_url AS "ctaUrl",
                v.like_count AS "likeCount",
                v.view_count AS "viewCount",
                v.sort_order AS "sortOrder",
                v.scheduled_at AS "scheduledAt",
                v.published_at AS "publishedAt",
                v.is_active AS "isActive",
                v.created_by::text AS "createdBy",
                v.updated_by::text AS "updatedBy",
                v.deleted_at AS "deletedAt",
                v.version,
                v.created_at AS "createdAt",
                v.updated_at AS "updatedAt",
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', p.id::text, 'name', p.name))
                        FROM content_product_relations cpr
                        JOIN products p ON p.id = cpr.product_id
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS products,
                COALESCE(
                    (
                        SELECT json_agg(cpr.product_id::text)
                        FROM content_product_relations cpr
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS "productIds",
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', c.id::text, 'name', c.name))
                        FROM content_category_relations ccr
                        JOIN categories c ON c.id = ccr.category_id
                        WHERE ccr.content_id = v.id
                    ),
                    '[]'::json
                ) AS categories,
                COALESCE(
                    (
                        SELECT json_agg(ccr.category_id::text)
                        FROM content_category_relations ccr
                        WHERE ccr.content_id = v.id
                    ),
                    '[]'::json
                ) AS "categoryIds",
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'id', cc.id::text,
                                'userName', cc.user_name,
                                'content', cc.body,
                                'parentId', cc.parent_id::text,
                                'isHidden', cc.is_hidden,
                                'createdAt', cc.created_at
                            )
                            ORDER BY cc.created_at ASC
                        )
                        FROM content_comments cc
                        WHERE cc.content_id = v.id
                          AND cc.deleted_at IS NULL
                    ),
                    '[]'::json
                ) AS comments,
                (
                    SELECT COUNT(*)
                    FROM content_comments cc
                    WHERE cc.content_id = v.id
                      AND cc.deleted_at IS NULL
                ) AS "commentCount"
            FROM videos v
            WHERE v.deleted_at IS NULL
            ORDER BY v.sort_order DESC, COALESCE(v.scheduled_at, v.created_at) DESC, v.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/content", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:create"))])
async def create_content(
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    data = validate_content_payload(payload)
    content_id = uuid4()
    async with session.begin():
        await session.execute(
            text(
                """
                INSERT INTO videos (
                    id, title, description, content_type, status, video_url, thumbnail_url, banner_image_url,
                    content_body, cta_label, cta_url,
                    like_count, view_count, sort_order, scheduled_at, published_at,
                    is_active, version, created_by, updated_by, created_at, updated_at
                )
                VALUES (
                    :id, :title, :description, :content_type, :status, :video_url, :thumbnail_url, :banner_image_url,
                    :content_body, :cta_label, :cta_url,
                    :like_count, :view_count, :sort_order, :scheduled_at, :published_at,
                    :is_active, 1, :created_by, :updated_by, NOW(), NOW()
                )
                """
            ),
            {"id": content_id, **data, "created_by": actor_id, "updated_by": actor_id},
        )
        await replace_content_product_relations(session, content_id, data["product_ids"])
        await replace_content_category_relations(session, content_id, data["category_ids"])
        await replace_content_comments(session, content_id, data["comments"], actor_id)
        await audit_admin_event(session, actor_id=actor_id, event_type="content_created", resource="content", metadata={"contentId": str(content_id), "contentType": data["content_type"], "status": data["status"]})
    await invalidate_content_storefront_cache(redis)
    return {"id": str(content_id)}


@router.patch("/content/{content_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_content(
    content_id: UUID,
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    data = validate_content_payload(payload)
    expected_version = data.get("version")
    if expected_version is None:
        raise HTTPException(status_code=409, detail="Missing content version. Reload before saving.")
    async with session.begin():
        result = await session.execute(
            text(
                """
                UPDATE videos
                SET
                    title = :title,
                    description = :description,
                    content_type = :content_type,
                    status = :status,
                    video_url = :video_url,
                    thumbnail_url = :thumbnail_url,
                    banner_image_url = :banner_image_url,
                    content_body = :content_body,
                    cta_label = :cta_label,
                    cta_url = :cta_url,
                    like_count = :like_count,
                    view_count = :view_count,
                    sort_order = :sort_order,
                    scheduled_at = :scheduled_at,
                    published_at = :published_at,
                    is_active = :is_active,
                    version = version + 1,
                    updated_by = :updated_by,
                    updated_at = NOW()
                WHERE id = :id
                  AND deleted_at IS NULL
                  AND version = :expected_version
                """
            ),
            {"id": content_id, **data, "updated_by": actor_id, "expected_version": expected_version},
        )
        if result.rowcount == 0:
            exists = await session.scalar(text("SELECT COUNT(*) FROM videos WHERE id = :id AND deleted_at IS NULL"), {"id": content_id})
            if exists:
                raise HTTPException(status_code=409, detail="Content was updated by another admin. Reload before saving.")
            raise HTTPException(status_code=404, detail="Content not found.")
        await replace_content_product_relations(session, content_id, data["product_ids"])
        await replace_content_category_relations(session, content_id, data["category_ids"])
        await replace_content_comments(session, content_id, data["comments"], actor_id)
        await audit_admin_event(session, actor_id=actor_id, event_type="content_updated", resource="content", metadata={"contentId": str(content_id), "contentType": data["content_type"], "status": data["status"]})
    await invalidate_content_storefront_cache(redis)
    return {"ok": True}


@router.delete("/content/{content_id}", dependencies=[Depends(require_permission("content:delete"))])
async def delete_content(
    content_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    async with session.begin():
        result = await session.execute(
            text(
                """
                UPDATE videos
                SET deleted_at = NOW(), is_active = FALSE, status = 'ARCHIVED', version = version + 1, updated_by = :actor_id, updated_at = NOW()
                WHERE id = :id
                  AND deleted_at IS NULL
                """
            ),
            {"id": content_id, "actor_id": actor_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Content not found.")
        await audit_admin_event(session, actor_id=actor_id, event_type="content_deleted", resource="content", metadata={"contentId": str(content_id), "mode": "soft_delete"})
    await invalidate_content_storefront_cache(redis)
    return {"ok": True}
