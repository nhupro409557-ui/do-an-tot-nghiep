import json
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.admin import *
from app.shared.admin_utils import (
    category_branch_cache_key,
    category_is_active,
    category_path_label,
    category_root_id_from_path,
    category_workflow_status,
    ensure_not_data_url,
    slugify,
)
from app.api.v1.routers.admin_customers import (
    enqueue_category_cache_refresh,
    process_category_migration_job,
)
from app.infrastructure.database.repositories import category_repo


# Router decorators were moved to app.api.v1.routers.admin_categories.
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
        raise HTTPException(status_code=422, detail="Danh m?c kh?ng th? l? cha c?a ch?nh n?.")
    if await category_repo.category_descendant_contains(session, category_id=category_id, parent_id=parent_id):
        raise HTTPException(status_code=422, detail="Kh?ng th? ch?n danh m?c con l?m danh m?c cha v? s? t?o v?ng l?p.")

async def ensure_category_depth(session: AsyncSession, category_id: UUID | None, parent_id: UUID | None, max_depth: int = 5) -> None:
    parent_depth = 0
    if parent_id:
        parent_depth = await category_repo.get_category_path_depth(session, parent_id)
        if parent_depth == 0:
            raise HTTPException(status_code=422, detail="Parent category not found.")
    subtree_depth = await category_repo.get_category_subtree_depth(session, category_id) if category_id else 1
    if parent_depth + subtree_depth > max_depth:
        raise HTTPException(status_code=422, detail=f"Category tree cannot exceed {max_depth} levels.")

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
    product_ids = await category_repo.list_visible_product_ids_in_category_branch(session, category_id)
    if not product_ids:
        return 0
    await category_repo.hide_products_by_category(session, product_ids)
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



async def list_admin_categories(session: AsyncSession) -> list[dict]:
    return await category_repo.list_admin_categories(session)

async def check_category_slug(payload: CategorySlugCheckPayload, session: AsyncSession) -> dict:
    if await category_repo.category_slug_exists(session, slug=slugify(payload.slug), exclude_id=payload.excludeId):
        raise HTTPException(status_code=409, detail="Slug danh m?c ?? t?n t?i.")
    return {"available": True}

async def create_category(
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    category_id = uuid4()
    slug = slugify(payload.slug) if payload.slug else f"{slugify(payload.name)}-{category_id.hex[:5]}"
    code = payload.code or slug
    category_status = payload.status
    is_active = category_is_active(category_status, payload.isActive)
    filter_config = category_filter_config(payload.specFields, payload.filterConfig)
    duplicate = await category_repo.find_category_slug_or_code_duplicate(session, slug=slug, code=code)
    if duplicate:
        if duplicate["slug_match"]:
            raise HTTPException(status_code=409, detail="Slug danh mục đã tồn tại.")
        raise HTTPException(status_code=409, detail="Mã danh mục đã tồn tại.")
    await ensure_categories_not_migrating(session, [payload.parentId])
    await ensure_category_depth(session, None, payload.parentId)
    await ensure_spec_inheritance_safe(session, None, payload.parentId, payload.specFields)
    ensure_not_data_url(payload.iconUrl, "iconUrl")
    ensure_not_data_url(payload.bannerUrl, "bannerUrl")
    await category_repo.insert_category(
        session,
        category_id=category_id,
        parent_id=payload.parentId,
        code=code,
        slug=slug,
        name=payload.name,
        icon=payload.icon,
        icon_url=payload.iconUrl,
        banner_url=payload.bannerUrl,
        spec_fields=payload.specFields,
        filter_config=filter_config,
        inventory_policy=payload.inventoryPolicy,
        warranty_policy=payload.warrantyPolicy,
        sort_order=payload.order,
        status=category_status,
        workflow_status=category_workflow_status(category_status),
        is_active=is_active,
        path_label=category_path_label(category_id),
    )
    await audit_category_event(session, category_id, "CATEGORY_CREATED", new_value={"name": payload.name, "slug": slug, "status": category_status}, actor_id=actor_id)
    await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_CREATED")
    await session.commit()
    affected_root_ids = [category_id] if payload.parentId is None else await find_root_ids_for_categories(session, [payload.parentId])
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
    return {"id": str(category_id)}


async def reorder_categories(
    payload: CategoryReorderPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    ids = [item.id for item in payload.items]
    await ensure_categories_not_migrating(session, ids)
    rows = await category_repo.list_category_parent_rows(session, ids)
    if len(rows) != len(set(ids)):
        raise HTTPException(status_code=404, detail="Một hoặc nhiều danh mục không tồn tại.")
    parent_by_id = {row["id"]: row["parent_id"] for row in rows}
    for item in payload.items:
        if parent_by_id[item.id] != item.parentId:
            raise HTTPException(status_code=422, detail="Chỉ được sắp xếp danh mục trong cùng một cấp.")
    parent_keys = {str(item.parentId or "root") for item in payload.items}
    if len(parent_keys) != 1:
        raise HTTPException(status_code=422, detail="Chỉ được sắp xếp một nhóm danh mục trong mỗi lần thao tác.")
    await category_repo.lock_category_reorder_group(session, f"category-reorder:{next(iter(parent_keys))}")
    for item in payload.items:
        await category_repo.update_category_sort_order(session, category_id=item.id, sort_order=item.order)
        await audit_category_event(session, item.id, "CATEGORY_REORDERED", new_value={"order": item.order, "parentId": str(item.parentId) if item.parentId else None}, actor_id=actor_id)
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=await find_root_ids_for_categories(session, ids))
    return {"ok": True}


async def bulk_update_categories(
    payload: CategoryBulkPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    updated = 0
    impacted_ids: list[UUID] = []
    if payload.items:
        ids = [item.id for item in payload.items]
        impacted_ids.extend(ids)
        await ensure_categories_not_migrating(session, ids)
        rows = await category_repo.list_category_parent_rows(session, ids)
        if len(rows) != len(set(ids)):
            raise HTTPException(status_code=404, detail="Một hoặc nhiều danh mục không tồn tại.")
        parent_by_id = {row["id"]: row["parent_id"] for row in rows}
        for item in payload.items:
            if parent_by_id[item.id] != item.parentId:
                raise HTTPException(status_code=422, detail="Chỉ được cập nhật thứ tự trong cùng một cấp.")
        for item in payload.items:
            updated += await category_repo.update_category_sort_order(session, category_id=item.id, sort_order=item.order, require_not_deleted=True)
            await audit_category_event(session, item.id, "CATEGORY_BULK_REORDERED", new_value={"order": item.order}, actor_id=actor_id)
    if payload.status and payload.ids:
        impacted_ids.extend(payload.ids)
        await ensure_categories_not_migrating(session, payload.ids)
        is_active = category_is_active(payload.status, True)
        updated += await category_repo.bulk_update_category_status(
            session,
            ids=payload.ids,
            status=payload.status,
            workflow_status=category_workflow_status(payload.status),
            is_active=is_active,
        )
        for category_id in payload.ids:
            if not is_active:
                await deactivate_products_in_category_branch(session, category_id)
                await category_repo.hide_active_child_categories(session, category_id)
            else:
                await category_repo.restore_hidden_children(session, category_id)
                await category_repo.restore_products_hidden_by_category(session, category_id)
            await audit_category_event(session, category_id, "CATEGORY_BULK_STATUS_CHANGED", new_value={"status": payload.status}, actor_id=actor_id)
            await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_BULK_STATUS_CHANGED")
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=await find_root_ids_for_categories(session, impacted_ids))
    return {"updated": updated}


async def update_category(
    category_id: UUID,
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    slug = slugify(payload.slug) if payload.slug else f"{slugify(payload.name)}-{str(category_id)[:5]}"
    code = payload.code or slug
    category_status = payload.status
    is_active = category_is_active(category_status, payload.isActive)
    spec_fields = payload.specFields
    filter_config = category_filter_config(spec_fields, payload.filterConfig)
    existing = await category_repo.get_category_for_update(session, category_id)
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
    duplicate = await category_repo.find_category_slug_or_code_duplicate(session, slug=slug, code=code, exclude_id=category_id)
    if duplicate:
        if duplicate["slug_match"]:
            raise HTTPException(status_code=409, detail="Slug danh mục đã tồn tại.")
        raise HTTPException(status_code=409, detail="Mã danh mục đã tồn tại.")
    ensure_not_data_url(payload.iconUrl, "iconUrl")
    ensure_not_data_url(payload.bannerUrl, "bannerUrl")
    if await category_repo.update_category(
        session,
        category_id=category_id,
        parent_id=payload.parentId,
        code=code,
        slug=slug,
        name=payload.name,
        icon=payload.icon,
        icon_url=payload.iconUrl,
        banner_url=payload.bannerUrl,
        spec_fields=spec_fields,
        filter_config=filter_config,
        inventory_policy=payload.inventoryPolicy,
        warranty_policy=payload.warrantyPolicy,
        sort_order=payload.order,
        status=category_status,
        workflow_status=category_workflow_status(category_status),
        is_active=is_active,
        spec_version_delta=1 if changed_spec_types else 0,
        path_label=category_path_label(category_id),
    ) == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
    if existing["parent_id"] != payload.parentId and existing["path"]:
        await category_repo.update_moved_category_children_paths(session, category_id=category_id, old_path=existing["path"])
    if existing["is_active"] and not is_active:
        await deactivate_products_in_category_branch(session, category_id)
        await category_repo.hide_active_child_categories(session, category_id)
    elif not existing["is_active"] and is_active:
        await category_repo.restore_hidden_children(session, category_id)
        await category_repo.restore_products_hidden_by_category(session, category_id)
    await record_category_redirect(session, category_id, existing["slug"], slug)
    if existing["slug"] != slug:
        await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_SLUG_CHANGED")
    if existing["parent_id"] != payload.parentId and int(existing["product_count"] or 0) > 0:
        job_id = uuid4()
        await category_repo.insert_category_migration_job(
            session,
            job_id=job_id,
            category_id=category_id,
            old_parent_id=existing["parent_id"],
            new_parent_id=payload.parentId,
            total_products=int(existing["product_count"] or 0),
        )
        await category_repo.mark_category_workflow_migrating(session, category_id)
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


async def restore_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    affected_root_ids = await find_root_ids_for_categories(session, [category_id])
    if await category_repo.restore_category(session, category_id) == 0:
        raise HTTPException(status_code=404, detail="Category not found.")
    await category_repo.restore_hidden_children(session, category_id)
    await category_repo.restore_products_hidden_by_category(session, category_id)
    await audit_category_event(session, category_id, "CATEGORY_RESTORED", new_value={"status": "ACTIVE"}, actor_id=actor_id)
    await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_RESTORED")
    await session.commit()
    enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
    return {"ok": True}


async def deactivate_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    affected_root_ids = await find_root_ids_for_categories(session, [category_id])
    await ensure_categories_not_migrating(session, [category_id])
    delete_blockers = await category_repo.get_category_delete_blockers(session, category_id)
    if not delete_blockers.get("exists"):
        raise HTTPException(status_code=404, detail="Category not found.")
    if delete_blockers.get("can_hard_delete"):
        if await category_repo.hard_delete_category(session, category_id) == 0:
            raise HTTPException(status_code=404, detail="Category not found.")
        await enqueue_sitemap_refresh(session, "category", category_id, "CATEGORY_HARD_DELETED")
        await session.commit()
        enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids, removed_root_ids=affected_root_ids)
        return {"ok": True, "action": "hard_deleted", "affectedProducts": 0}

    raise HTTPException(
        status_code=409,
        detail="Không thể xóa danh mục đang có dữ liệu liên quan. Hãy ẩn danh mục nếu cần ngừng hiển thị.",
    )


async def list_category_audit_logs(category_id: UUID, session: AsyncSession) -> list[dict]:
    return await category_repo.list_category_audit_logs(session, category_id)

async def list_category_migration_jobs(category_id: UUID, session: AsyncSession) -> list[dict]:
    await recover_stale_category_migrations(session)
    await session.commit()
    return await category_repo.list_category_migration_jobs(session, category_id)

async def category_operational_metrics(session: AsyncSession, redis: Redis) -> dict:
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
    job_metrics = await category_repo.get_category_migration_job_metrics(
        session,
        stale_after_minutes=CATEGORY_MIGRATION_STALE_MINUTES,
    )
    business_metrics = await category_repo.get_category_business_metrics(session)
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
