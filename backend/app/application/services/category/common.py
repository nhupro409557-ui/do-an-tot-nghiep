import json
import re
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import *
from app.shared.admin_utils import (
    category_branch_cache_key,
    category_is_active,
    category_path_label,
    category_root_id_from_path,
    category_workflow_status,
    ensure_not_data_url,
    slugify,
)
from app.api.routers.admin_customers import (
    enqueue_category_cache_refresh,
    process_category_migration_job,
)
from app.infrastructure.database.repositories import category_repo


# Router decorators were moved to app.api.routers.admin_categories.
CATEGORY_CACHE_ROOT_ORDER_KEY = "catalog:categories:roots:active"
CATEGORY_CACHE_ROOT_ORDER_STALE_KEY = "catalog:categories:roots:stale"
CATEGORY_MIGRATION_STALE_MINUTES = 30
IMEI_PATTERN = re.compile(r"^[0-9]{15}$")
SERIAL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{2,119}$")

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


def identifier_policy_changes(old_policy: dict | None, new_policy: dict | None) -> list[str]:
    old_policy = old_policy or {}
    new_policy = new_policy or {}
    changes: list[str] = []
    if not bool(old_policy.get("trackImei")) and bool(new_policy.get("trackImei")):
        changes.append("IMEI")
    if not bool(old_policy.get("trackSerialNumber")) and bool(new_policy.get("trackSerialNumber")):
        changes.append("SERIAL")
    return changes


def normalize_identifier_inventory_policy(policy: dict | None) -> dict:
    normalized = dict(policy or {})
    track_imei = bool(normalized.get("trackImei"))
    track_serial_number = bool(normalized.get("trackSerialNumber"))
    if track_imei:
        track_serial_number = True
    if not track_serial_number:
        track_imei = False
    normalized["trackImei"] = track_imei
    normalized["trackSerialNumber"] = track_serial_number
    return normalized


def identifier_preview_summary(identifier_type: str, lines: list[dict]) -> dict:
    relevant = [line for line in lines if int(line["requiredIdentifierCount"]) > 0]
    return {
        "identifierType": identifier_type,
        "affectedProducts": len({line["productId"] for line in relevant}),
        "affectedVariants": len(relevant),
        "physicalStock": sum(int(line["physicalStock"]) for line in relevant),
        "existingIdentifiers": sum(int(line["existingIdentifierCount"]) for line in relevant),
        "requiredIdentifiers": sum(int(line["requiredIdentifierCount"]) for line in relevant),
        "lines": relevant,
    }


async def ensure_no_category_cycle(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None) -> None:
    if not category_id or not parent_id:
        return
    if category_id == parent_id:
        raise HTTPException(status_code=422, detail="Danh mục không thể là cha của chính nó.")
    if await category_repo.category_descendant_contains(session, category_id=category_id, parent_id=parent_id):
        raise HTTPException(status_code=422, detail="Không thể chọn danh mục con làm danh mục cha vì sẽ tạo vòng lặp.")

async def ensure_category_depth(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None, max_depth: int = 5) -> None:
    parent_depth = 0
    if parent_id:
        parent_depth = await category_repo.get_category_path_depth(session, parent_id)
        if parent_depth == 0:
            raise HTTPException(status_code=422, detail="Không tìm thấy danh mục cha.")
    subtree_depth = await category_repo.get_category_subtree_depth(session, category_id) if category_id else 1
    if parent_depth + subtree_depth > max_depth:
        raise HTTPException(status_code=422, detail=f"Cây danh mục không được vượt quá {max_depth} cấp.")

async def ensure_spec_inheritance_safe(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None, own_fields: list[dict]) -> None:
    own_keys = spec_keys(own_fields)
    if not parent_id or not own_keys:
        return
    inherited_keys: set[str] = set()
    for fields in await category_repo.list_ancestor_spec_fields(session, parent_id=parent_id, category_id=category_id):
        inherited_keys.update(spec_keys(fields))
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
    return await category_repo.count_products_using_spec_keys(session, category_id=category_id, keys=keys)

async def ensure_categories_not_migrating(session: AsyncSession, category_ids: list[UUID | None]) -> None:
    await recover_stale_category_migrations(session)
    ids = [item for item in category_ids if item]
    if not ids:
        return
    row = await category_repo.find_running_migration_for_category_branch(session, ids)
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
    stale_rows = await category_repo.list_stale_category_migration_jobs(session, stale_after_minutes=stale_after_minutes)
    if not stale_rows:
        return []
    released_ids: list[str] = []
    for row in stale_rows:
        await category_repo.mark_category_migration_failed(session, row["id"])
        await category_repo.unlock_category_workflow_status(session, row["category_id"])
        released_ids.append(str(row["id"]))
    return released_ids

async def find_root_ids_for_categories(session: AsyncSession, category_ids: list[UUID | None]) -> list[UUID]:
    ids = [item for item in category_ids if item]
    if not ids:
        return []
    rows = await category_repo.list_root_ids_for_categories(session, ids)
    root_ids: list[UUID] = []
    for row in rows:
        root_id = category_root_id_from_path(row["path"])
        if root_id and root_id not in root_ids:
            root_ids.append(root_id)
    return root_ids

async def list_visible_root_category_ids(session: AsyncSession) -> list[UUID]:
    return await category_repo.list_visible_root_category_ids(session)

async def fetch_visible_category_branch(session: AsyncSession, root_id: UUID) -> dict | None:
    return await category_repo.fetch_visible_category_branch(session, root_id)


async def rebuild_category_branch_cache(
    session: AsyncSession,
    redis: Redis,
    affected_root_ids: list[UUID] | None = None,
    removed_root_ids: list[UUID] | None = None,
) -> None:
    visible_root_ids = await list_visible_root_category_ids(session)
    await redis.set(
        CATEGORY_CACHE_ROOT_ORDER_KEY,
        json.dumps([str(root_id) for root_id in visible_root_ids], ensure_ascii=False),
        ex=30 * 60,
    )
    await redis.set(
        CATEGORY_CACHE_ROOT_ORDER_STALE_KEY,
        json.dumps([str(root_id) for root_id in visible_root_ids], ensure_ascii=False),
        ex=24 * 60 * 60,
    )

    target_root_ids = visible_root_ids if affected_root_ids is None else [root_id for root_id in visible_root_ids if root_id in affected_root_ids]
    for root_id in target_root_ids:
        branch = await fetch_visible_category_branch(session, root_id)
        if branch is None:
            await redis.delete(category_branch_cache_key(root_id), category_branch_cache_key(root_id, stale=True))
            continue
        payload = json.dumps(branch, ensure_ascii=False, default=str)
        await redis.set(category_branch_cache_key(root_id), payload, ex=30 * 60)
        await redis.set(category_branch_cache_key(root_id, stale=True), payload, ex=24 * 60 * 60)

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
            await redis.set(category_branch_cache_key(root_id), cached, ex=30 * 60)
            await redis.set(category_branch_cache_key(root_id, stale=True), cached, ex=24 * 60 * 60)
        branches.append(json.loads(cached))
    await redis.set("catalog:categories:tree:active", "catalog:categories:tree:branch-cache")
    await redis.set("catalog:categories:tree:stale", json.dumps(branches, ensure_ascii=False, default=str), ex=24 * 60 * 60)


async def deactivate_products_in_category_branch(session: AsyncSession, category_id: UUID) -> int:
    # Khi một nhánh danh mục bị ẩn/xóa mềm, toàn bộ sản phẩm trong nhánh được chuyển
    # sang INACTIVE để storefront không giữ trạng thái "active nhưng không còn taxonomy".
    product_ids = await category_repo.list_visible_product_ids_in_category_branch(session, category_id)
    if not product_ids:
        return 0
    await category_repo.hide_products_by_category(session, product_ids)
    from app.infrastructure.database.repositories import used_product_repo
    await used_product_repo.hide_listings_by_products(session, product_ids)
    return len(product_ids)


async def enqueue_sitemap_refresh(session: AsyncSession, entity_type: str, entity_id: UUID | None, reason: str) -> None:
    await category_repo.enqueue_sitemap_refresh(session, entity_type, entity_id, reason)


async def audit_product_event(
    session: AsyncSession,
    product_id: UUID,
    action: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor_id: UUID | None = None,
) -> None:
    await category_repo.audit_product_event(session, product_id, action, old_value, new_value, actor_id)


async def audit_category_event(
    session: AsyncSession,
    category_id: UUID,
    action_type: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
    actor_id: UUID | None = None,
) -> None:
    await category_repo.audit_category_event(session, category_id, action_type, old_value, new_value, actor_id)


async def record_category_redirect(session: AsyncSession, category_id: UUID, old_slug: str | None, new_slug: str | None) -> None:
    if not old_slug or not new_slug or old_slug == new_slug:
        return
    source_path = f"/category/{old_slug}"
    target_path = f"/category/{new_slug}"
    if await category_repo.category_redirect_loop_exists(session, source_path=source_path, target_path=target_path):
        raise HTTPException(status_code=409, detail="Category redirect loop detected.")
    await category_repo.update_upstream_category_redirects(session, category_id=category_id, source_path=source_path, target_path=target_path)
    await category_repo.delete_category_redirect_by_source(session, target_path)
    await category_repo.upsert_category_redirect(session, category_id=category_id, source_path=source_path, target_path=target_path)

__all__ = [name for name in globals() if not name.startswith("__")]
