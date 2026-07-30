import json
from uuid import UUID, uuid4
from fastapi import HTTPException

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import ProductBulkActionPayload
from app.infrastructure.database.repositories.category_repo import audit_product_event, find_running_migration_for_category_branch


async def ensure_approval_categories_not_migrating(session: AsyncSession, category_ids: list[UUID | None]) -> None:
    active_ids = [category_id for category_id in category_ids if category_id]
    if not active_ids:
        return
    migration = await find_running_migration_for_category_branch(session, active_ids)
    if migration:
        raise HTTPException(status_code=409, detail="Danh mục của sản phẩm đang trong quá trình di chuyển. Vui lòng thử lại sau.")


async def merge_revision_variants(session: AsyncSession, *, parent_id: UUID, revision_id: UUID) -> None:
    has_order_item_variant_id = (
        await session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'order_items' AND column_name = 'variant_id'
                )
                """
            )
        )
    ).scalar()
    live_rows = (
        await session.execute(
            text(
                """
                SELECT id, sku, is_default
                FROM product_variants
                WHERE product_id = :parent_id AND deleted_at IS NULL
                FOR UPDATE
                """
            ),
            {"parent_id": parent_id},
        )
    ).mappings().all()
    revision_rows = (
        await session.execute(
            text(
                """
                SELECT id, parent_variant_id, sku, color_name, color_code, storage, ram, configuration,
                       specs, image_url, images, price, sale_price, compare_at_price,
                       stock_quantity, is_active, is_default, status, attributes
                FROM product_variants
                WHERE product_id = :revision_id AND deleted_at IS NULL
                ORDER BY created_at ASC
                """
            ),
            {"revision_id": revision_id},
        )
    ).mappings().all()
    active_revision_rows = [row for row in revision_rows if row["is_active"] is not False and str(row["status"]).lower() not in {"deleted", "archived", "inactive"}]
    if revision_rows and not active_revision_rows:
        raise HTTPException(status_code=400, detail="Không thể áp dụng bản chỉnh sửa nếu không có ít nhất một biến thể đang hoạt động.")

    live_by_id = {row["id"]: row for row in live_rows}
    live_by_sku = {str(row["sku"] or "").strip(): row for row in live_rows if str(row["sku"] or "").strip()}
    kept_live_ids: set[UUID] = set()

    for revision in revision_rows:
        sku = str(revision["sku"] or "").strip()
        live = live_by_id.get(revision["parent_variant_id"]) if revision["parent_variant_id"] else None
        live = live or live_by_sku.get(sku)
        if live:
            kept_live_ids.add(live["id"])
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET parent_variant_id = NULL,
                        color_name = :color_name,
                        color_code = :color_code,
                        storage = :storage,
                        ram = :ram,
                        configuration = :configuration,
                        specs = CAST(:specs AS jsonb),
                        image_url = :image_url,
                        images = CAST(:images AS jsonb),
                        price = :price,
                        sale_price = :sale_price,
                        compare_at_price = :compare_at_price,
                        is_active = :is_active,
                        is_default = :is_default,
                        status = :status,
                        attributes = CAST(:attributes AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": live["id"],
                    "color_name": revision["color_name"],
                    "color_code": revision["color_code"],
                    "storage": revision["storage"],
                    "ram": revision["ram"],
                    "configuration": revision["configuration"],
                    "specs": json.dumps(revision["specs"] or {}),
                    "image_url": revision["image_url"],
                    "images": json.dumps(revision["images"] or []),
                    "price": revision["price"],
                    "sale_price": revision["sale_price"],
                    "compare_at_price": revision["compare_at_price"],
                    "is_active": revision["is_active"],
                    "is_default": revision["is_default"],
                    "status": "active" if revision["is_active"] is not False else "inactive",
                    "attributes": json.dumps(revision["attributes"] or {}),
                },
            )
        else:
            new_variant_id = uuid4()
            kept_live_ids.add(new_variant_id)
            await session.execute(
                text(
                    """
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                        is_active, is_default, status, attributes, created_at, updated_at
                    )
                    VALUES (
                        :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                        CAST(:specs AS jsonb), :image_url, CAST(:images AS jsonb), :price, :sale_price, :compare_at_price,
                        0, :is_active, :is_default, :status, CAST(:attributes AS jsonb), NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": new_variant_id,
                    "product_id": parent_id,
                    "sku": revision["sku"],
                    "color_name": revision["color_name"],
                    "color_code": revision["color_code"],
                    "storage": revision["storage"],
                    "ram": revision["ram"],
                    "configuration": revision["configuration"],
                    "specs": json.dumps(revision["specs"] or {}),
                    "image_url": revision["image_url"],
                    "images": json.dumps(revision["images"] or []),
                    "price": revision["price"],
                    "sale_price": revision["sale_price"],
                    "compare_at_price": revision["compare_at_price"],
                    "is_active": revision["is_active"],
                    "is_default": revision["is_default"],
                    "status": "active" if revision["is_active"] is not False else "inactive",
                    "attributes": json.dumps(revision["attributes"] or {}),
                },
            )

    for live in live_rows:
        if live["id"] in kept_live_ids:
            continue
        history_sql = """
            SELECT (
                SELECT COUNT(*) FROM order_items WHERE variant_id = :variant_id
            ) + (
                SELECT COUNT(*) FROM inventory_adjustment_logs WHERE variant_id = :variant_id
            ) AS total
        """
        has_history = (
            await session.execute(
                text(history_sql),
                {"variant_id": live["id"]},
            )
        ).scalar_one()
        next_status = "inactive" if int(has_history or 0) > 0 else "archived"
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET is_active = FALSE,
                    is_default = FALSE,
                    status = :status,
                    deleted_at = CASE WHEN :status = 'archived' THEN NOW() ELSE deleted_at END,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": live["id"], "status": next_status},
        )

    total_count = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM product_variants
                WHERE product_id = :parent_id AND deleted_at IS NULL
                """
            ),
            {"parent_id": parent_id},
        )
    ).scalar_one()

    if int(total_count or 0) > 0:
        default_count = (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM product_variants
                    WHERE product_id = :parent_id AND deleted_at IS NULL AND is_active = TRUE AND is_default = TRUE
                    """
                ),
                {"parent_id": parent_id},
            )
        ).scalar_one()
        if int(default_count or 0) != 1:
            first_active = (
                await session.execute(
                    text(
                        """
                        SELECT id
                        FROM product_variants
                        WHERE product_id = :parent_id AND deleted_at IS NULL AND is_active = TRUE
                        ORDER BY created_at ASC
                        LIMIT 1
                        """
                    ),
                    {"parent_id": parent_id},
                )
            ).scalar()
            if not first_active:
                raise HTTPException(status_code=400, detail="Không thể áp dụng bản chỉnh sửa nếu không có ít nhất một biến thể đang hoạt động.")
            await session.execute(text("UPDATE product_variants SET is_default = FALSE WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(text("UPDATE product_variants SET is_default = TRUE WHERE id = :id"), {"id": first_active})


async def unpublish_product_dependents(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :id"),
        {"id": product_id},
    )
    await session.execute(
        text("""
            UPDATE used_device_listings
            SET status = 'HIDDEN', updated_at = NOW()
            WHERE device_id IN (SELECT id FROM used_devices WHERE product_id = :id)
              AND status = 'PUBLISHED'
        """),
        {"id": product_id},
    )
    await session.execute(
        text("""
            UPDATE used_devices
            SET status = 'READY_FOR_PRICING', updated_at = NOW()
            WHERE product_id = :id AND status = 'READY_FOR_SALE'
        """),
        {"id": product_id},
    )


async def transition_product_status_data(
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
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await ensure_approval_categories_not_migrating(session, [row["category_id"], row["subcategory_id"]])
    current_status = str(row["status"])
    if current_status not in allowed_from:
        raise HTTPException(status_code=400, detail=f"Không thể chuyển đổi trạng thái sản phẩm từ {current_status} sang {next_status}.")
    variants = (
        await session.execute(
            text("SELECT price, sale_price, stock_quantity, is_active FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
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
            field_names = {
                "name": "tên sản phẩm",
                "sku": "mã SKU",
                "category": "danh mục",
                "imageUrl": "ảnh đại diện"
            }
            missing_translated = [field_names.get(f, f) for f in missing]
            raise HTTPException(status_code=400, detail=f"Thiếu các trường thông tin bắt buộc trước khi gửi duyệt: {', '.join(missing_translated)}.")
    final_status = next_status
    if next_status == "ACTIVE":
        variant_keys = []
        sales_config = row["sales_config"] or {}
        final_status = "ACTIVE"
        if isinstance(sales_config, dict):
            variant_keys = sales_config.get("variantSpecKeys") or []
            target_status = str(sales_config.get("targetProductStatus") or "ACTIVE").upper()
            if target_status in {"ACTIVE", "INACTIVE", "DISCONTINUED"}:
                final_status = target_status
        active_variants = [variant for variant in variants if variant["is_active"] is not False]
        if variant_keys and not active_variants:
            raise HTTPException(status_code=400, detail="Sản phẩm cần có ít nhất một biến thể hoạt động trước khi duyệt.")
        if active_variants:
            invalid_variant = next((variant for variant in active_variants if float(variant["sale_price"] or variant["price"] or 0) <= 0), None)
            if invalid_variant:
                raise HTTPException(status_code=400, detail="Mỗi biến thể hoạt động cần có giá hợp lệ trước khi duyệt.")
        elif float(row["sale_price"] or row["price"] or 0) <= 0:
            raise HTTPException(status_code=400, detail="Sản phẩm đơn lẻ cần có giá hợp lệ trước khi duyệt.")
        if row["parent_product_id"]:
            parent_id = row["parent_product_id"]
            parent_snapshot = (
                await session.execute(
                    text(
                        """
                        SELECT jsonb_build_object(
                            'id', id::text,
                            'name', name,
                            'sku', sku,
                            'status', status,
                            'categoryId', category_id::text,
                            'subcategoryId', subcategory_id::text,
                            'brandId', brand_id::text,
                            'price', price::text,
                            'salePrice', sale_price::text,
                            'stockQuantity', stock_quantity,
                            'specifications', specifications,
                            'salesConfig', sales_config,
                            'imageUrl', image_url,
                            'images', images,
                            'videoUrl', video_url,
                            'options', options,
                            'isFeatured', is_featured,
                            'isFlashSale', is_flash_sale,
                            'version', version
                        )
                        FROM products
                        WHERE id = :parent_id
                        """
                    ),
                    {"parent_id": parent_id},
                )
            ).scalar_one()
            revision_snapshot = (
                await session.execute(
                    text(
                        """
                        SELECT jsonb_build_object(
                            'id', id::text,
                            'name', name,
                            'sku', sku,
                            'status', status,
                            'categoryId', category_id::text,
                            'subcategoryId', subcategory_id::text,
                            'brandId', brand_id::text,
                            'price', price::text,
                            'salePrice', sale_price::text,
                            'stockQuantity', stock_quantity,
                            'specifications', specifications,
                            'salesConfig', sales_config,
                            'imageUrl', image_url,
                            'images', images,
                            'videoUrl', video_url,
                            'options', options,
                            'isFeatured', is_featured,
                            'isFlashSale', is_flash_sale,
                            'version', version
                        )
                        FROM products
                        WHERE id = :revision_id
                        """
                    ),
                    {"revision_id": product_id},
                )
            ).scalar_one()
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
                        price = revision.price,
                        sale_price = revision.sale_price,
                        image_url = revision.image_url,
                        images = revision.images,
                        video_url = revision.video_url,
                        options = revision.options,
                        is_featured = revision.is_featured,
                        is_flash_sale = revision.is_flash_sale,
                        status = :final_status,
                        version = parent.version + 1,
                        updated_at = NOW()
                    FROM products revision
                    WHERE parent.id = :parent_id AND revision.id = :revision_id
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id, "final_status": final_status},
            )
            await merge_revision_variants(session, parent_id=parent_id, revision_id=product_id)
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
            await session.execute(text("DELETE FROM product_attached_services WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(
                text(
                    """
                    INSERT INTO product_attached_services (product_id, service_id, override_price)
                    SELECT :parent_id, service_id, override_price
                    FROM product_attached_services
                    WHERE product_id = :revision_id
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await audit_product_event(
                session,
                parent_id,
                "REVISION_PUBLISHED",
                old_value={
                    "productBefore": parent_snapshot,
                    "revisionId": str(product_id),
                },
                new_value={
                    "productAfter": revision_snapshot,
                    "publishedProductId": str(parent_id),
                    "revisionDeleted": True,
                },
            )
            # Reassociate media assets from revision_id to parent_id
            await session.execute(
                text(
                    """
                    UPDATE media_assets
                    SET associated_entity_id = :parent_id
                    WHERE associated_entity_id = :revision_id
                      AND associated_entity_type = 'PRODUCT'
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            # Release media assets of other revisions being deleted
            await session.execute(
                text(
                    """
                    UPDATE media_assets
                    SET associated_entity_id = NULL, associated_entity_type = NULL
                    WHERE associated_entity_type = 'PRODUCT'
                      AND associated_entity_id IN (
                          SELECT id FROM products
                          WHERE parent_product_id = :parent_id AND id <> :revision_id
                      )
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            # Delete relations of other revisions being deleted
            await session.execute(
                text(
                    """
                    DELETE FROM product_bundles
                    WHERE product_id IN (
                        SELECT id FROM products
                        WHERE parent_product_id = :parent_id AND id <> :revision_id
                    )
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            await session.execute(
                text(
                    """
                    DELETE FROM product_accessories
                    WHERE product_id IN (
                        SELECT id FROM products
                        WHERE parent_product_id = :parent_id AND id <> :revision_id
                    )
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            await session.execute(
                text(
                    """
                    DELETE FROM product_attached_services
                    WHERE product_id IN (
                        SELECT id FROM products
                        WHERE parent_product_id = :parent_id AND id <> :revision_id
                    )
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            # Delete other draft/pending revisions of the parent product to avoid old drafts overriding the active product later
            await session.execute(
                text(
                    """
                    DELETE FROM product_variants
                    WHERE product_id IN (
                        SELECT id FROM products
                        WHERE parent_product_id = :parent_id AND id <> :revision_id
                    )
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            await session.execute(
                text(
                    """
                    DELETE FROM products
                    WHERE parent_product_id = :parent_id AND id <> :revision_id
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id}
            )
            await session.execute(text("DELETE FROM products WHERE id = :revision_id"), {"revision_id": product_id})
            return {"ok": True, "status": final_status, "publishedProductId": str(parent_id)}
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
            raise HTTPException(status_code=409, detail="Sản phẩm đang được sử dụng trong combo/phụ kiện bán kèm hoặc chương trình flash sale. Vui lòng kiểm tra lại các liên kết trước khi lưu trữ.")
    status_to_apply = final_status if next_status == "ACTIVE" else next_status
    await session.execute(
        text("UPDATE products SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "status": status_to_apply},
    )
    if status_to_apply in ("INACTIVE", "ARCHIVED"):
        await unpublish_product_dependents(session, product_id)
    await audit_product_event(session, product_id, "PRODUCT_STATUS_CHANGED", old_value={"status": current_status}, new_value={"status": status_to_apply, "approvalAction": next_status})
    return {"ok": True, "status": status_to_apply}


async def submit_product_data(product_id: UUID, session: AsyncSession) -> dict:
    return await transition_product_status_data(session, product_id, allowed_from={"DRAFT", "REVISION_DRAFT"}, next_status="PENDING")


async def approve_product_data(
    product_id: UUID, 
    session: AsyncSession,
    role_code: str,
) -> dict:
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    return await transition_product_status_data(session, product_id, allowed_from=allowed, next_status="ACTIVE")


async def reactivate_product_data(product_id: UUID, session: AsyncSession) -> dict:
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
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await ensure_approval_categories_not_migrating(session, [row["category_id"], row["subcategory_id"]])
    current_status = str(row["status"])
    if current_status not in {"INACTIVE", "DISCONTINUED", "ARCHIVED"}:
        raise HTTPException(status_code=400, detail="Chỉ sản phẩm đang tạm ẩn, ngừng kinh doanh hoặc lưu trữ mới được bật lại.")

    variants = (
        await session.execute(
            text(
                """
                SELECT price, sale_price, stock_quantity, deleted_at, status
                FROM product_variants
                WHERE product_id = :product_id
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    restorable_variants = [
        variant for variant in variants
        if variant["deleted_at"] is None and str(variant["status"] or "").lower() not in {"deleted", "archived"}
    ]

    variant_keys = []
    sales_config = row["sales_config"] or {}
    if isinstance(sales_config, dict):
        variant_keys = sales_config.get("variantSpecKeys") or []
    if variant_keys and not restorable_variants:
        raise HTTPException(status_code=400, detail="Sản phẩm cần có ít nhất một biến thể còn hợp lệ trước khi bật lại.")
    if restorable_variants:
        invalid_variant = next((variant for variant in restorable_variants if float(variant["sale_price"] or variant["price"] or 0) <= 0), None)
        if invalid_variant:
            raise HTTPException(status_code=400, detail="Mỗi biến thể hoạt động cần có giá hợp lệ trước khi bật lại.")
    elif float(row["sale_price"] or row["price"] or 0) <= 0:
        raise HTTPException(status_code=400, detail="Sản phẩm đơn lẻ cần có giá hợp lệ trước khi bật lại.")

    await session.execute(
        text("UPDATE products SET status = 'ACTIVE', updated_at = NOW() WHERE id = :id"),
        {"id": product_id},
    )
    await session.execute(
        text(
            """
            UPDATE product_variants
            SET is_active = TRUE,
                status = 'active',
                updated_at = NOW()
            WHERE product_id = :product_id
              AND deleted_at IS NULL
              AND LOWER(COALESCE(status, 'active')) NOT IN ('deleted', 'archived')
            """
        ),
        {"product_id": product_id},
    )
    await audit_product_event(session, product_id, "PRODUCT_STATUS_CHANGED", old_value={"status": current_status}, new_value={"status": "ACTIVE"})
    return {"ok": True, "status": "ACTIVE"}


async def bulk_approve_products_data(
    payload: ProductBulkActionPayload, 
    session: AsyncSession,
    role_code: str,
) -> dict:
    ids = payload.ids or payload.productIds or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    for product_id in ids:
        try:
            await transition_product_status_data(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "updated": updated, "skipped": skipped}


async def product_bulk_action_data(
    payload: ProductBulkActionPayload, 
    session: AsyncSession,
    role_code: str,
) -> dict:
    ids = payload.productIds or payload.ids or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    for product_id in ids:
        try:
            if payload.action == "APPROVE":
                await transition_product_status_data(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            elif payload.action == "ARCHIVE":
                await transition_product_status_data(session, product_id, allowed_from={"DRAFT", "INACTIVE"}, next_status="ARCHIVED")
            elif payload.action == "DELETE":
                result = await session.execute(
                    text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id AND status <> 'ARCHIVED'"),
                    {"id": product_id},
                )
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
                await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :id"), {"id": product_id})
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "action": payload.action, "updated": updated, "skipped": skipped}


async def hide_product_data(product_id: UUID, session: AsyncSession) -> dict:
    product_category_row = (
        await session.execute(
            text("SELECT category_id, subcategory_id, status FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not product_category_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    if product_category_row["status"] == "MERGED":
        raise HTTPException(status_code=400, detail="Bản chỉnh sửa đã áp dụng không thể ẩn.")
    if product_category_row["status"] == "ARCHIVED":
        raise HTTPException(status_code=400, detail="Sản phẩm đã lưu trữ không thể ẩn.")
    await ensure_approval_categories_not_migrating(session, [product_category_row["category_id"], product_category_row["subcategory_id"]])
    result = await session.execute(
        text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id AND status <> 'INACTIVE'"),
        {"id": product_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="Sản phẩm đã ở trạng thái ẩn.")
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :id"),
        {"id": product_id},
    )
    await session.execute(
        text(
            """
            UPDATE used_device_listings
            SET status = 'HIDDEN', updated_at = NOW()
            WHERE device_id IN (
                SELECT id FROM used_devices WHERE product_id = :product_id
            ) AND status = 'PUBLISHED'
            """
        ),
        {"product_id": product_id}
    )
    await session.execute(
        text(
            """
            UPDATE used_devices
            SET status = 'READY_FOR_PRICING', updated_at = NOW()
            WHERE product_id = :product_id AND status = 'READY_FOR_SALE'
            """
        ),
        {"product_id": product_id}
    )
    await audit_product_event(session, product_id, "PRODUCT_STATUS_CHANGED", old_value={"status": product_category_row["status"]}, new_value={"status": "INACTIVE"})
    return {"ok": True, "action": "hidden"}


async def archive_product_data(product_id: UUID, session: AsyncSession) -> dict:
    return await transition_product_status_data(session, product_id, allowed_from={"DRAFT", "INACTIVE", "REVISION_DRAFT"}, next_status="ARCHIVED")


async def deactivate_product_data(product_id: UUID, session: AsyncSession) -> dict:
    product_category_row = (
        await session.execute(
            text("SELECT category_id, subcategory_id, status FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not product_category_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    if product_category_row["status"] == "MERGED":
        raise HTTPException(status_code=400, detail="Bản chỉnh sửa này đã được áp dụng vào sản phẩm gốc, không thể xóa hoặc lưu trữ lại.")

    await ensure_approval_categories_not_migrating(session, [product_category_row["category_id"], product_category_row["subcategory_id"]])
    usage = (
        await session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM order_items WHERE product_id = :id) AS order_count,
                    (SELECT COUNT(*) FROM product_reviews WHERE product_id = :id) AS review_count,
                    (SELECT COUNT(*) FROM used_device_intake_requests WHERE product_id = :id) AS used_intake_count,
                    (SELECT COUNT(*) FROM used_devices WHERE product_id = :id) AS used_device_count,
                    (
                        SELECT COUNT(*)
                        FROM inventory_adjustment_logs
                        WHERE product_id = :id
                          AND transaction_type = 'RECEIPT'
                          AND delta > 0
                    ) AS receipt_count,
                    (
                        SELECT COUNT(*)
                        FROM inventory_transactions it
                        LEFT JOIN inventory_documents doc ON doc.id = it.document_id
                        WHERE (it.product_id = :id OR it.variant_id IN (SELECT id FROM product_variants WHERE product_id = :id))
                          AND it.movement_type = 'IN'
                          AND it.quantity > 0
                          AND (doc.document_type = 'INBOUND' OR doc.document_type IS NULL)
                    ) AS inbound_transaction_count
                """
            ),
            {"id": product_id},
        )
    ).mappings().one()

    if usage["order_count"] > 0 or usage["review_count"] > 0 or usage["used_intake_count"] > 0 or usage["used_device_count"] > 0:
        await session.execute(text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"), {"id": product_id})
        await unpublish_product_dependents(session, product_id)
        return {"ok": True, "action": "deactivated"}

    if usage["receipt_count"] > 0 or usage["inbound_transaction_count"] > 0:
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa sản phẩm đã có dữ liệu nhập kho thật. Hãy ẩn sản phẩm nếu cần ngừng bán.",
        )

    # Clean up empty inventory levels for product and its variants to avoid FK constraint errors on deletion
    await session.execute(
        text(
            """
            DELETE FROM inventory_levels
            WHERE (on_hand_quantity = 0 AND reserved_quantity = 0)
              AND (
                  variant_id IN (SELECT id FROM product_variants WHERE product_id = :id)
                  OR (product_id = :id AND variant_id IS NULL)
              )
            """
        ),
        {"id": product_id}
    )

    await session.execute(text("DELETE FROM product_bundles WHERE product_id = :id OR bundled_product_id = :id"), {"id": product_id})
    await session.execute(text("DELETE FROM product_accessories WHERE product_id = :id OR accessory_product_id = :id"), {"id": product_id})
    await session.execute(text("DELETE FROM product_attached_services WHERE product_id = :id"), {"id": product_id})
    await session.execute(
        text("UPDATE media_assets SET associated_entity_id = NULL, associated_entity_type = NULL WHERE associated_entity_id = :id"),
        {"id": product_id}
    )
    result = await session.execute(text("DELETE FROM products WHERE id = :id"), {"id": product_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    return {"ok": True, "action": "deleted"}
