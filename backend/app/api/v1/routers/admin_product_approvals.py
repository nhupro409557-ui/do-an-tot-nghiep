import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission, get_current_role_code
from app.api.v1.routers.admin_schemas import ProductBulkActionPayload
from app.api.v1.routers.admin_categories import audit_product_event, ensure_categories_not_migrating
from app.api.v1.routers.admin_product_utils import (
    sync_parent_price_from_variants,
    sync_parent_price_if_variants_exist,
)
from app.infrastructure.database.session import get_session

router = APIRouter()

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
    if not active_revision_rows:
        raise HTTPException(status_code=400, detail="Không thể áp dụng bản chỉnh sửa nếu không có ít nhất một biến thể đang hoạt động.")

    live_by_id = {row["id"]: row for row in live_rows}
    live_by_sku = {str(row["sku"] or "").strip(): row for row in live_rows if str(row["sku"] or "").strip()}
    revision_skus = {str(row["sku"] or "").strip() for row in revision_rows if str(row["sku"] or "").strip()}
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
                        id, product_id, parent_variant_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                        is_active, is_default, status, attributes, created_at, updated_at
                    )
                    VALUES (
                        :id, :parent_id, NULL, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                        CAST(:specs AS jsonb), :image_url, CAST(:images AS jsonb), :price, :sale_price, :compare_at_price, :stock_quantity,
                        :is_active, :is_default, :status, CAST(:attributes AS jsonb), NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": new_variant_id,
                    "parent_id": parent_id,
                    "sku": sku or f"SKU-{new_variant_id.hex[:10].upper()}",
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
                    "stock_quantity": max(0, int(revision["stock_quantity"] or 0)),
                    "is_active": revision["is_active"],
                    "is_default": revision["is_default"],
                    "status": "active" if revision["is_active"] is not False else "inactive",
                    "attributes": json.dumps(revision["attributes"] or {}),
                },
            )

    kept_revision_parent_ids = {row["parent_variant_id"] for row in revision_rows if row["parent_variant_id"]}
    missing_live = [row for row in live_rows if row["id"] not in kept_revision_parent_ids and str(row["sku"] or "").strip() not in revision_skus]
    for live in missing_live:
        history_sql = """
                    SELECT
                        (SELECT COUNT(*) FROM inventory_adjustment_logs WHERE variant_id = :variant_id) AS total
                    """
        if has_order_item_variant_id:
            history_sql = """
                    SELECT
                        (SELECT COUNT(*) FROM order_items WHERE variant_id = :variant_id) +
                        (SELECT COUNT(*) FROM inventory_adjustment_logs WHERE variant_id = :variant_id) AS total
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
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await ensure_categories_not_migrating(session, [row["category_id"], row["subcategory_id"]])
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
    if next_status == "ACTIVE":
        variant_keys = []
        sales_config = row["sales_config"] or {}
        if isinstance(sales_config, dict):
            variant_keys = sales_config.get("variantSpecKeys") or []
        active_variants = [variant for variant in variants if variant["is_active"] is not False]
        if variant_keys and not active_variants:
            raise HTTPException(status_code=400, detail="Sản phẩm cần có ít nhất một biến thể hoạt động trước khi duyệt.")
        if active_variants:
            invalid_variant = next((variant for variant in active_variants if float(variant["sale_price"] or variant["price"] or 0) <= 0), None)
            if invalid_variant:
                raise HTTPException(status_code=400, detail="Mỗi biến thể hoạt động cần có giá hợp lệ trước khi duyệt.")
        elif float(row["sale_price"] or row["price"] or 0) <= 0:
            raise HTTPException(status_code=400, detail="Sản phẩm đơn lẻ cần có giá hợp lệ trước khi duyệt.")
        await sync_parent_price_if_variants_exist(session, product_id)
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
                        options = revision.options,
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
            await sync_parent_price_from_variants(session, parent_id)
            await audit_product_event(session, parent_id, "REVISION_PUBLISHED", old_value={"revisionId": str(product_id)}, new_value={"publishedProductId": str(parent_id), "revisionStatus": "MERGED"})
            await session.execute(text("UPDATE products SET status = 'MERGED', updated_at = NOW() WHERE id = :revision_id"), {"revision_id": product_id})
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
            raise HTTPException(status_code=409, detail="Sản phẩm đang được sử dụng trong combo/phụ kiện bán kèm hoặc chương trình flash sale. Vui lòng kiểm tra lại các liên kết trước khi lưu trữ.")
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
async def approve_product(
    product_id: UUID, 
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    return await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")


@router.post("/products/bulk-approve", dependencies=[Depends(require_permission("product:update"))])
async def bulk_approve_products(
    payload: ProductBulkActionPayload, 
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    ids = payload.ids or payload.productIds or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    for product_id in ids:
        try:
            await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "updated": updated, "skipped": skipped}


@router.post("/products/bulk-action", dependencies=[Depends(require_permission("product:update"))])
async def product_bulk_action(
    payload: ProductBulkActionPayload, 
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
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
                await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            elif payload.action == "ARCHIVE":
                await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE"}, next_status="ARCHIVED")
            elif payload.action == "DELETE":
                result = await session.execute(
                    text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id AND status <> 'ARCHIVED'"),
                    {"id": product_id},
                )
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
                await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :id"), {"id": product_id})
                await session.commit()
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "action": payload.action, "updated": updated, "skipped": skipped}


@router.post("/products/{product_id}/archive", dependencies=[Depends(require_permission("product:update"))])
async def archive_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE", "REVISION_DRAFT"}, next_status="ARCHIVED")


@router.delete("/products/{product_id}", dependencies=[Depends(require_permission("product:delete"))])
async def deactivate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product_category_row = (
        await session.execute(
            text("SELECT category_id, subcategory_id, parent_product_id, status FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not product_category_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    if product_category_row["status"] == "MERGED":
        raise HTTPException(status_code=400, detail="Bản chỉnh sửa này đã được áp dụng vào sản phẩm gốc, không thể xóa hoặc lưu trữ lại.")
    if product_category_row["status"] == "ARCHIVED":
        raise HTTPException(status_code=400, detail="Sản phẩm đã được lưu trữ trước đó.")
    if product_category_row["status"] == "REVISION_DRAFT" and product_category_row["parent_product_id"]:
        await session.execute(text("DELETE FROM product_bundles WHERE product_id = :id"), {"id": product_id})
        await session.execute(text("DELETE FROM product_accessories WHERE product_id = :id"), {"id": product_id})
        await session.execute(text("DELETE FROM product_attached_services WHERE product_id = :id"), {"id": product_id})
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET deleted_at = NOW(),
                    status = 'deleted',
                    is_active = FALSE,
                    is_default = FALSE,
                    updated_at = NOW()
                WHERE product_id = :id AND deleted_at IS NULL
                """
            ),
            {"id": product_id},
        )
        await session.execute(
            text("UPDATE products SET status = 'ARCHIVED', deleted_at = NOW(), updated_at = NOW() WHERE id = :id"),
            {"id": product_id},
        )
        await session.commit()
        return {"ok": True, "action": "revision_discarded"}
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
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
        await session.commit()
        return {"ok": True, "action": "archived"}

    await session.execute(text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"), {"id": product_id})
    await session.commit()
    return {"ok": True, "action": "deactivated"}
