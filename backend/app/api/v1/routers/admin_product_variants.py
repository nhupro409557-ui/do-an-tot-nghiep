import json
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.routers.admin_schemas import ProductVariantPayload
from app.api.v1.routers.admin_product_utils import (
    normalized_option_key,
    normalize_product_options,
    sync_parent_price_if_variants_exist,
)
from app.infrastructure.database.session import get_session

router = APIRouter()

COLOR_CODE_FALLBACK = {
    "đen": "#000000", "black": "#000000",
    "trắng": "#FFFFFF", "white": "#FFFFFF",
    "đỏ": "#FF0000", "red": "#FF0000",
    "xanh lá": "#00FF00", "green": "#00FF00",
    "xanh dương": "#0000FF", "blue": "#0000FF",
    "vàng": "#FFFF00", "yellow": "#FFFF00",
    "cam": "#FFA500", "orange": "#FFA500",
    "hồng": "#FFC0CB", "pink": "#FFC0CB",
    "xám": "#808080", "gray": "#808080", "grey": "#808080",
    "tím": "#800080", "purple": "#800080",
    "bạc": "#C0C0C0", "silver": "#C0C0C0",
    "vàng hồng": "#B76E79", "rose gold": "#B76E79"
}

async def upsert_product_variants(
    session: AsyncSession,
    product_id: UUID,
    variants_payload: list[ProductVariantPayload],
    product_name: str,
    default_price: float = 0,
    default_sale_price: float | None = None,
    default_stock: int = 0,
) -> None:
    # 1. Fetch product options to validate attributes
    product_row = (
        await session.execute(
            text("SELECT options, sku, status, parent_product_id FROM products WHERE id = :product_id"),
            {"product_id": product_id}
        )
    ).mappings().first()
    if not product_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    options = product_row["options"] or []
    product_status = product_row.get("status")
    parent_product_id = product_row.get("parent_product_id")
    is_revision = (product_status == "REVISION_DRAFT")
    
    # Validate SKU duplicate in payload
    sku_list = [v.sku.strip() for v in variants_payload if v.sku]
    if len(sku_list) != len(set(sku_list)):
        raise HTTPException(status_code=400, detail="Trùng lặp SKU trong danh sách biến thể gửi lên.")

    # Validate options matching attributes
    options_dict = {
        normalized_option_key(opt["name"]): [normalized_option_key(v) for v in opt["values"]]
        for opt in options
        if "name" in opt and "values" in opt
    }
    for var in variants_payload:
        var_attrs = var.attributes or {}
        normalized_var_attrs = {normalized_option_key(k): v for k, v in var_attrs.items()}
        for k, v in var_attrs.items():
            normalized_key = normalized_option_key(k)
            if normalized_key not in options_dict:
                raise HTTPException(
                    status_code=400,
                    detail=f"Thuộc tính '{k}' của biến thể không nằm trong các lựa chọn của sản phẩm."
                )
            if normalized_option_key(v) not in options_dict[normalized_key]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Giá trị '{v}' của thuộc tính '{k}' không hợp lệ."
                )
        if options:
            for opt in options:
                opt_name = opt.get("name", "")
                if normalized_option_key(opt_name) not in normalized_var_attrs:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Biến thể thiếu thuộc tính '{opt_name}' yêu cầu bởi sản phẩm."
                    )

    # Validate default variant constraints only when variants are present.
    default_count = sum(1 for v in variants_payload if v.isDefault)
    if variants_payload and default_count != 1:
        raise HTTPException(
            status_code=400,
            detail="Mỗi sản phẩm chỉ được có một biến thể mặc định.",
            headers={"x-error-code": "MULTIPLE_DEFAULT_VARIANTS"}
        )

    # Validate unique active SKUs in DB
    for var in variants_payload:
        if not var.sku:
            continue
        sku_query = """
            SELECT pv.id FROM product_variants pv
            WHERE pv.sku = :sku 
              AND pv.deleted_at IS NULL 
              AND pv.status <> 'revision_draft'
              AND pv.product_id <> :product_id
              AND (CAST(:parent_product_id AS UUID) IS NULL OR pv.product_id <> CAST(:parent_product_id AS UUID))
              AND (CAST(:id AS UUID) IS NULL OR pv.id <> CAST(:id AS UUID))
        """
        existing = (
            await session.execute(
                text(sku_query),
                {
                    "sku": var.sku.strip(),
                    "id": var.id,
                    "product_id": product_id,
                    "parent_product_id": parent_product_id,
                }
            )
        ).scalar()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"SKU '{var.sku}' đã được sử dụng bởi một biến thể khác đang hoạt động."
            )

    db_variants = (
        await session.execute(
            text("SELECT id FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
            {"product_id": product_id}
        )
    ).scalars().all()
    
    payload_ids = {var.id for var in variants_payload if var.id}
    to_delete_ids = [vid for vid in db_variants if vid not in payload_ids]
    
    default_sku_for_parent = None

    for var in variants_payload:
        color_val = None
        storage_val = None
        ram_val = None
        config_val = None
        
        var_attrs = var.attributes or {}
        for k, v in var_attrs.items():
            k_lower = k.lower()
            if k_lower in {"color", "màu", "màu sắc"}:
                color_val = str(v)
            elif k_lower in {"storage", "dung lượng", "bộ nhớ"}:
                storage_val = str(v)
            elif k_lower in {"ram", "bộ nhớ trong"}:
                ram_val = str(v)
            elif k_lower in {"configuration", "cấu hình", "phiên bản"}:
                config_val = str(v)
                
        normalized_attrs = {normalized_option_key(k): str(v) for k, v in var_attrs.items()}
        if not color_val:
            color_val = normalized_attrs.get("color") or normalized_attrs.get("mau") or normalized_attrs.get("mau sac")
        if not storage_val:
            storage_val = (
                normalized_attrs.get("storage")
                or normalized_attrs.get("dung luong")
                or normalized_attrs.get("bo nho")
                or normalized_attrs.get("bo nho trong")
                or normalized_attrs.get("rom")
            )
        if not ram_val:
            ram_val = normalized_attrs.get("ram") or normalized_attrs.get("bo nho ram")
        if not config_val:
            config_val = normalized_attrs.get("configuration") or normalized_attrs.get("cau hinh") or normalized_attrs.get("phien ban")

        color_code = None
        if color_val:
            color_code = COLOR_CODE_FALLBACK.get(color_val.lower(), "#CCCCCC")

        db_price = var.price
        db_sale_price = var.salePrice if var.salePrice is not None and var.salePrice > 0 else None
        db_compare_at_price = None
        if var.compareAtPrice is not None and var.compareAtPrice > 0:
            db_price = var.compareAtPrice
            db_sale_price = db_sale_price if db_sale_price is not None else var.price
            db_compare_at_price = var.compareAtPrice

        if var.isDefault:
            default_sku_for_parent = var.sku

        specs = dict(var.specs or {})
        if not specs:
            specs = dict(var_attrs)

        if var.id and var.id in db_variants:
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET sku = :sku,
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
                        stock_quantity = :stock_quantity,
                        is_active = :is_active,
                        is_default = :is_default,
                        status = :status,
                        attributes = CAST(:attributes AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": var.id,
                    "sku": var.sku.strip() if var.sku else f"SKU-{uuid4().hex[:10].upper()}",
                    "color_name": color_val or var.colorName,
                    "color_code": color_code or var.colorCode,
                    "storage": storage_val or var.storage,
                    "ram": ram_val or var.ram,
                    "configuration": config_val or var.configuration,
                    "specs": json.dumps(specs),
                    "image_url": var.imageUrl,
                    "images": json.dumps(var.images or []),
                    "price": db_price,
                    "sale_price": db_sale_price,
                    "compare_at_price": db_compare_at_price,
                    "stock_quantity": var.stockQuantity,
                    "is_active": var.isActive,
                    "is_default": var.isDefault,
                    "status": "revision_draft" if is_revision else var.status,
                    "attributes": json.dumps(var_attrs)
                }
            )
        else:
            new_var_id = var.id if var.id and var.id in db_variants else uuid4()
            await session.execute(
                text(
                    """
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                        is_active, is_default, status, attributes, parent_variant_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                        CAST(:specs AS jsonb), :image_url, CAST(:images AS jsonb), :price, :sale_price, :compare_at_price, :stock_quantity,
                        :is_active, :is_default, :status, CAST(:attributes AS jsonb), :parent_variant_id, NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": new_var_id,
                    "product_id": product_id,
                    "sku": var.sku.strip() if var.sku else f"SKU-{new_var_id.hex[:10].upper()}",
                    "color_name": color_val or var.colorName,
                    "color_code": color_code or var.colorCode,
                    "storage": storage_val or var.storage,
                    "ram": ram_val or var.ram,
                    "configuration": config_val or var.configuration,
                    "specs": json.dumps(specs),
                    "image_url": var.imageUrl,
                    "images": json.dumps(var.images or []),
                    "price": db_price,
                    "sale_price": db_sale_price,
                    "compare_at_price": db_compare_at_price,
                    "stock_quantity": var.stockQuantity,
                    "is_active": var.isActive,
                    "is_default": var.isDefault,
                    "status": "revision_draft" if is_revision else var.status,
                    "attributes": json.dumps(var_attrs),
                    "parent_variant_id": var.id if var.id and var.id not in db_variants else None,
                }
            )

    if to_delete_ids:
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET deleted_at = NOW(),
                    status = 'deleted',
                    is_active = FALSE
                WHERE id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": to_delete_ids}
        )

    if default_sku_for_parent and not is_revision:
        await session.execute(
            text("UPDATE products SET sku = :sku WHERE id = :product_id"),
            {"sku": default_sku_for_parent, "product_id": product_id}
        )


@router.delete("/products/{product_id}/variants/{variant_id}", dependencies=[Depends(require_permission("product:delete"))])
async def delete_product_variant(
    product_id: UUID,
    variant_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    variant = (
        await session.execute(
            text(
                """
                SELECT id, is_default, sku
                FROM product_variants
                WHERE id = :variant_id AND product_id = :product_id AND deleted_at IS NULL
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Không tìm thấy biến thể.")

    await session.execute(
        text(
            """
            UPDATE product_variants
            SET deleted_at = NOW(),
                status = 'deleted',
                is_active = FALSE,
                is_default = FALSE,
                updated_at = NOW()
            WHERE id = :variant_id
            """
        ),
        {"variant_id": variant_id},
    )

    if variant["is_default"]:
        next_variant = (
            await session.execute(
                text(
                    """
                    SELECT id, sku
                    FROM product_variants
                    WHERE product_id = :product_id AND deleted_at IS NULL
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ),
                {"product_id": product_id},
            )
        ).mappings().first()
        if next_variant:
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET is_default = TRUE,
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": next_variant["id"]},
            )
            await session.execute(
                text(
                    """
                    UPDATE products
                    SET sku = :sku,
                        updated_at = NOW()
                    WHERE id = :product_id
                    """
                ),
                {"sku": next_variant["sku"], "product_id": product_id},
            )

    await sync_parent_price_if_variants_exist(session, product_id)
    await session.commit()
    return {"ok": True}
