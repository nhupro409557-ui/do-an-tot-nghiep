from .common import *
from app.shared.exceptions import BusinessException


def validate_category_spec_fields(spec_fields: list[dict]) -> None:
    import re
    seen_keys: set[str] = set()
    for field in spec_fields:
        key = field.get("key")
        if not key or not isinstance(key, str) or not key.strip():
            raise BusinessException(400, "INVALID_SPEC_FIELD_KEY", "Mã trường thông số kỹ thuật không được trống.")
        key_stripped = key.strip()
        if not re.match(r"^[a-zA-Z0-9_-]+$", key_stripped):
            raise BusinessException(
                400,
                "INVALID_SPEC_FIELD_KEY",
                f"Mã trường '{key_stripped}' không hợp lệ. Chỉ chấp nhận chữ cái, số, dấu gạch ngang và gạch dưới."
            )
        normalized_key = key_stripped.casefold()
        if normalized_key in seen_keys:
            raise BusinessException(
                409,
                "DUPLICATE_SPEC_FIELD_KEY",
                f"Mã trường thông số '{key_stripped}' bị trùng trong danh mục. Vui lòng giữ mỗi key một lần."
            )
        seen_keys.add(normalized_key)
        field_type = field.get("type")
        if field_type not in {"text", "number", "select", "color"}:
            raise BusinessException(
                400,
                "INVALID_SPEC_FIELD_TYPE",
                f"Kiểu dữ liệu '{field_type}' cho trường '{key_stripped}' không hợp lệ."
            )

async def list_admin_categories(session: AsyncSession) -> list[dict]:
    return await category_repo.list_admin_categories(session)


async def check_category_slug(payload: CategorySlugCheckPayload, session: AsyncSession) -> dict:
    if await category_repo.category_slug_exists(session, slug=slugify(payload.slug), exclude_id=payload.excludeId):
        raise BusinessException(409, "CATEGORY_SLUG_EXISTS", "Slug danh mục đã tồn tại.")
    return {"available": True}


async def create_category(
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    validate_category_spec_fields(payload.specFields)
    try:
        category_id = uuid4()
        slug = slugify(payload.slug) if payload.slug else f"{slugify(payload.name)}-{category_id.hex[:5]}"
        code = payload.code or slug
        category_status = payload.status
        is_active = category_is_active(category_status, payload.isActive)
        filter_config = category_filter_config(payload.specFields, payload.filterConfig)
        duplicate = await category_repo.find_category_slug_or_code_duplicate(session, slug=slug, code=code)
        if duplicate:
            if duplicate["slug_match"]:
                raise BusinessException(409, "CATEGORY_SLUG_EXISTS", "Slug danh mục đã tồn tại.")
            raise BusinessException(409, "CATEGORY_CODE_EXISTS", "Mã danh mục đã tồn tại.")
        await ensure_categories_not_migrating(session, [payload.parentId])
        await ensure_category_depth(session, None, payload.parentId)
        await ensure_spec_inheritance_safe(session, None, payload.parentId, payload.specFields)
        if is_active and payload.parentId:
            parent_status_res = await session.execute(
                text("SELECT is_active, status FROM categories WHERE id = :parent_id AND COALESCE(is_deleted, FALSE) = FALSE"),
                {"parent_id": payload.parentId}
            )
            parent_row = parent_status_res.mappings().first()
            if parent_row and (not parent_row["is_active"] or parent_row["status"] != "ACTIVE"):
                raise BusinessException(
                    400,
                    "INACTIVE_PARENT_CATEGORY",
                    "Không thể kích hoạt danh mục con khi danh mục cha đang tạm ngưng hoạt động."
                )
        ensure_not_data_url(payload.iconUrl, "iconUrl")
        ensure_not_data_url(payload.bannerUrl, "bannerUrl")
        inventory_policy = normalize_identifier_inventory_policy(payload.inventoryPolicy)
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
            inventory_policy=inventory_policy,
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
    except Exception as exc:
        await session.rollback()
        raise exc


async def reorder_categories(
    payload: CategoryReorderPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    try:
        ids = [item.id for item in payload.items]
        await ensure_categories_not_migrating(session, ids)
        rows = await category_repo.list_category_parent_rows(session, ids)
        if len(rows) != len(set(ids)):
            raise BusinessException(404, "CATEGORY_NOT_FOUND", "Một hoặc nhiều danh mục không tồn tại.")
        parent_by_id = {row["id"]: row["parent_id"] for row in rows}
        for item in payload.items:
            if parent_by_id[item.id] != item.parentId:
                raise BusinessException(422, "INVALID_REORDER_OPERATION", "Chỉ được sắp xếp danh mục trong cùng một cấp.")
        parent_keys = {str(item.parentId or "root") for item in payload.items}
        if len(parent_keys) != 1:
            raise BusinessException(422, "INVALID_REORDER_OPERATION", "Chỉ được sắp xếp một nhóm danh mục trong mỗi lần thao tác.")
        
        # pg_advisory_xact_lock locks category reordering group
        await category_repo.lock_category_reorder_group(session, f"category-reorder:{next(iter(parent_keys))}")
        for item in payload.items:
            await category_repo.update_category_sort_order(session, category_id=item.id, sort_order=item.order)
            await audit_category_event(session, item.id, "CATEGORY_REORDERED", new_value={"order": item.order, "parentId": str(item.parentId) if item.parentId else None}, actor_id=actor_id)
        await session.commit()
        enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=await find_root_ids_for_categories(session, ids))
        return {"ok": True}
    except Exception as exc:
        await session.rollback()
        raise exc


async def bulk_update_categories(
    payload: CategoryBulkPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    try:
        updated = 0
        impacted_ids: list[UUID] = []
        if payload.items:
            ids = [item.id for item in payload.items]
            impacted_ids.extend(ids)
            await ensure_categories_not_migrating(session, ids)
            rows = await category_repo.list_category_parent_rows(session, ids)
            if len(rows) != len(set(ids)):
                raise BusinessException(404, "CATEGORY_NOT_FOUND", "Một hoặc nhiều danh mục không tồn tại.")
            parent_by_id = {row["id"]: row["parent_id"] for row in rows}
            for item in payload.items:
                if parent_by_id[item.id] != item.parentId:
                    raise BusinessException(422, "INVALID_REORDER_OPERATION", "Chỉ được cập nhật thứ tự trong cùng một cấp.")
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
    except Exception as exc:
        await session.rollback()
        raise exc


async def update_category(
    category_id: UUID,
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    actor_id: UUID,
) -> dict:
    try:
        slug = slugify(payload.slug) if payload.slug else f"{slugify(payload.name)}-{str(category_id)[:5]}"
        code = payload.code or slug
        category_status = payload.status
        is_active = category_is_active(category_status, payload.isActive)
        spec_fields = payload.specFields
        validate_category_spec_fields(spec_fields)
        filter_config = category_filter_config(spec_fields, payload.filterConfig)
        inventory_policy = normalize_identifier_inventory_policy(payload.inventoryPolicy)
        existing = await category_repo.get_category_for_update(session, category_id)
        if not existing:
            raise BusinessException(404, "CATEGORY_NOT_FOUND", "Không tìm thấy danh mục.")
        if payload.version is not None and int(existing["version"] or 0) != payload.version:
            raise BusinessException(
                409,
                "CATEGORY_VERSION_CONFLICT",
                "Danh mục đã được quản trị viên khác cập nhật. Vui lòng tải lại trước khi lưu.",
            )
        old_root_id = category_root_id_from_path(existing["path"])
        await ensure_categories_not_migrating(session, [category_id, existing["parent_id"], payload.parentId])
        await ensure_no_category_cycle(session, category_id, payload.parentId)
        await ensure_category_depth(session, category_id, payload.parentId)
        await ensure_spec_inheritance_safe(session, category_id, payload.parentId, spec_fields)
        if is_active and payload.parentId:
            parent_status_res = await session.execute(
                text("SELECT is_active, status FROM categories WHERE id = :parent_id AND COALESCE(is_deleted, FALSE) = FALSE"),
                {"parent_id": payload.parentId}
            )
            parent_row = parent_status_res.mappings().first()
            if parent_row and (not parent_row["is_active"] or parent_row["status"] != "ACTIVE"):
                raise BusinessException(
                    400,
                    "INACTIVE_PARENT_CATEGORY",
                    "Không thể kích hoạt danh mục con khi danh mục cha đang tạm ngưng hoạt động."
                )
        policy_previews: list[dict] = []
        for identifier_type in identifier_policy_changes(existing.get("inventoryPolicy"), inventory_policy):
            lines = await category_repo.preview_identifier_policy_change(
                session,
                category_id=category_id,
                identifier_type=identifier_type,
            )
            summary = identifier_preview_summary(identifier_type, lines)
            if summary["requiredIdentifiers"] > 0:
                active = await category_repo.find_active_identifier_policy_migration(
                    session,
                    category_id=category_id,
                    identifier_type=identifier_type,
                )
                if active:
                    raise BusinessException(
                        409,
                        "IDENTIFIER_POLICY_MIGRATION_ACTIVE",
                        f"Đang có tác vụ bổ sung {identifier_type} cho danh mục này.",
                        {"migrationId": str(active["id"])},
                    )
                policy_previews.append(summary)
        if policy_previews:
            raise BusinessException(
                409,
                "IDENTIFIER_POLICY_MIGRATION_REQUIRED",
                "Tồn kho hiện tại chưa đủ mã định danh. Hãy tạo tác vụ bổ sung trước khi bật chính sách.",
                {
                    "categoryId": str(category_id),
                    "targetInventoryPolicy": inventory_policy,
                    "previews": policy_previews,
                },
            )
        changed_spec_types = spec_type_changes(existing["specFields"], spec_fields)
        impacted_spec_products = await count_products_using_spec_keys(session, category_id, [item["key"] for item in changed_spec_types])
        if changed_spec_types and impacted_spec_products > 0 and not payload.allowSpecTypeMigration:
            raise BusinessException(
                409,
                "SPEC_TYPE_CHANGE_REQUIRES_CONFIRMATION",
                f"Thay đổi kiểu thông số sẽ ảnh hưởng {impacted_spec_products} sản phẩm hiện tại.",
                {
                    "impactedProducts": impacted_spec_products,
                    "changes": changed_spec_types,
                },
            )
        duplicate = await category_repo.find_category_slug_or_code_duplicate(session, slug=slug, code=code, exclude_id=category_id)
        if duplicate:
            if duplicate["slug_match"]:
                raise BusinessException(409, "CATEGORY_SLUG_EXISTS", "Slug danh mục đã tồn tại.")
            raise BusinessException(409, "CATEGORY_CODE_EXISTS", "Mã danh mục đã tồn tại.")
        ensure_not_data_url(payload.iconUrl, "iconUrl")
        ensure_not_data_url(payload.bannerUrl, "bannerUrl")
        expected_version = payload.version if payload.version is not None else int(existing["version"] or 1)
        
        # Concurrency: Acquire advisory lock if parent ID changes (moving subtree)
        if existing["parent_id"] != payload.parentId:
            await category_repo.lock_category_reorder_group(session, "category-hierarchy-modification")

        if await category_repo.update_category(
            session,
            category_id=category_id,
            expected_version=expected_version,
            parent_id=payload.parentId,
            code=code,
            slug=slug,
            name=payload.name,
            icon=payload.icon,
            icon_url=payload.iconUrl,
            banner_url=payload.bannerUrl,
            spec_fields=spec_fields,
            filter_config=filter_config,
            inventory_policy=inventory_policy,
            warranty_policy=payload.warrantyPolicy,
            sort_order=payload.order,
            status=category_status,
            workflow_status=category_workflow_status(category_status),
            is_active=is_active,
            spec_version_delta=1 if changed_spec_types else 0,
            path_label=category_path_label(category_id),
        ) == 0:
            still_exists = await session.scalar(text("SELECT EXISTS(SELECT 1 FROM categories WHERE id = :id AND COALESCE(is_deleted, FALSE) = FALSE)"), {"id": category_id})
            if still_exists:
                raise BusinessException(
                    409,
                    "CATEGORY_VERSION_CONFLICT",
                    "Danh mục đã được quản trị viên khác cập nhật. Vui lòng tải lại trước khi lưu.",
                )
            else:
                raise BusinessException(404, "CATEGORY_NOT_FOUND", "Không tìm thấy danh mục.")
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
                "inventoryPolicy": existing.get("inventoryPolicy") or {},
            },
            new_value={
                "name": payload.name,
                "slug": slug,
                "status": category_status,
                "isActive": is_active,
                "specFields": spec_fields,
                "filterConfig": filter_config,
                "inventoryPolicy": inventory_policy,
                "specTypeChanges": changed_spec_types,
            },
            actor_id=actor_id,
        )
        await session.commit()
        new_root_ids = [category_id] if payload.parentId is None else await find_root_ids_for_categories(session, [payload.parentId, category_id])
        affected_root_ids = [root_id for root_id in [old_root_id, *new_root_ids] if root_id]
        enqueue_category_cache_refresh(background_tasks, redis, affected_root_ids=affected_root_ids)
        return {"ok": True}
    except Exception as exc:
        await session.rollback()
        raise exc
