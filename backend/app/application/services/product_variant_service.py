from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import ProductVariantPayload
from app.application.services.product_helper_service import (
    normalized_option_key,
    sync_parent_price_if_variants_exist,
)
from app.infrastructure.database.repositories import product_variant_repo


COLOR_CODE_FALLBACK = {
    "Ã„â€˜en": "#000000", "black": "#000000",
    "trÃ¡ÂºÂ¯ng": "#FFFFFF", "white": "#FFFFFF",
    "Ã„â€˜Ã¡Â»Â": "#FF0000", "red": "#FF0000",
    "xanh lÃƒÂ¡": "#00FF00", "green": "#00FF00",
    "xanh dÃ†Â°Ã†Â¡ng": "#0000FF", "blue": "#0000FF",
    "vÃƒÂ ng": "#FFFF00", "yellow": "#FFFF00",
    "cam": "#FFA500", "orange": "#FFA500",
    "hÃ¡Â»â€œng": "#FFC0CB", "pink": "#FFC0CB",
    "xÃƒÂ¡m": "#808080", "gray": "#808080", "grey": "#808080",
    "tÃƒÂ­m": "#800080", "purple": "#800080",
    "bÃ¡ÂºÂ¡c": "#C0C0C0", "silver": "#C0C0C0",
    "vÃƒÂ ng hÃ¡Â»â€œng": "#B76E79", "rose gold": "#B76E79",
}


def validate_variant_options(options: list[dict], variants_payload: list[ProductVariantPayload]) -> None:
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
                    detail=f"ThuÃ¡Â»â„¢c tÃƒÂ­nh '{k}' cÃ¡Â»Â§a biÃ¡ÂºÂ¿n thÃ¡Â»Æ’ khÃƒÂ´ng nÃ¡ÂºÂ±m trong cÃƒÂ¡c lÃ¡Â»Â±a chÃ¡Â»Ân cÃ¡Â»Â§a sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m.",
                )
            if normalized_option_key(v) not in options_dict[normalized_key]:
                raise HTTPException(
                    status_code=400,
                    detail=f"GiÃƒÂ¡ trÃ¡Â»â€¹ '{v}' cÃ¡Â»Â§a thuÃ¡Â»â„¢c tÃƒÂ­nh '{k}' khÃƒÂ´ng hÃ¡Â»Â£p lÃ¡Â»â€¡.",
                )
        if options:
            for opt in options:
                opt_name = opt.get("name", "")
                if normalized_option_key(opt_name) not in normalized_var_attrs:
                    raise HTTPException(
                        status_code=400,
                        detail=f"BiÃ¡ÂºÂ¿n thÃ¡Â»Æ’ thiÃ¡ÂºÂ¿u thuÃ¡Â»â„¢c tÃƒÂ­nh '{opt_name}' yÃƒÂªu cÃ¡ÂºÂ§u bÃ¡Â»Å¸i sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m.",
                    )


def validate_default_variant_count(variants_payload: list[ProductVariantPayload]) -> None:
    default_count = sum(1 for variant in variants_payload if variant.isDefault)
    if variants_payload and default_count != 1:
        raise HTTPException(
            status_code=400,
            detail="MÃ¡Â»â€”i sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m chÃ¡Â»â€° Ã„â€˜Ã†Â°Ã¡Â»Â£c cÃƒÂ³ mÃ¡Â»â„¢t biÃ¡ÂºÂ¿n thÃ¡Â»Æ’ mÃ¡ÂºÂ·c Ã„â€˜Ã¡Â»â€¹nh.",
            headers={"x-error-code": "MULTIPLE_DEFAULT_VARIANTS"},
        )


def resolve_variant_values(variant: ProductVariantPayload, *, is_revision: bool) -> dict:
    color_val = None
    storage_val = None
    ram_val = None
    config_val = None

    var_attrs = variant.attributes or {}
    for key, value in var_attrs.items():
        key_lower = key.lower()
        if key_lower in {"color", "mÃƒÂ u", "mÃƒÂ u sÃ¡ÂºÂ¯c"}:
            color_val = str(value)
        elif key_lower in {"storage", "dung lÃ†Â°Ã¡Â»Â£ng", "bÃ¡Â»â„¢ nhÃ¡Â»â€º"}:
            storage_val = str(value)
        elif key_lower in {"ram", "bÃ¡Â»â„¢ nhÃ¡Â»â€º trong"}:
            ram_val = str(value)
        elif key_lower in {"configuration", "cÃ¡ÂºÂ¥u hÃƒÂ¬nh", "phiÃƒÂªn bÃ¡ÂºÂ£n"}:
            config_val = str(value)

    normalized_attrs = {normalized_option_key(key): str(value) for key, value in var_attrs.items()}
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

    color_code = COLOR_CODE_FALLBACK.get(color_val.lower(), "#CCCCCC") if color_val else None
    db_price = variant.price
    db_sale_price = variant.salePrice if variant.salePrice is not None and variant.salePrice > 0 else None
    db_compare_at_price = None
    if variant.compareAtPrice is not None and variant.compareAtPrice > 0:
        db_price = variant.compareAtPrice
        db_sale_price = db_sale_price if db_sale_price is not None else variant.price
        db_compare_at_price = variant.compareAtPrice

    specs = dict(variant.specs or {})
    if not specs:
        specs = dict(var_attrs)

    return {
        "sku": variant.sku.strip() if variant.sku else None,
        "color_name": color_val or variant.colorName,
        "color_code": color_code or variant.colorCode,
        "storage": storage_val or variant.storage,
        "ram": ram_val or variant.ram,
        "configuration": config_val or variant.configuration,
        "specs": product_variant_repo.json_param(specs),
        "image_url": variant.imageUrl,
        "images": product_variant_repo.json_param(variant.images or []),
        "price": db_price,
        "sale_price": db_sale_price,
        "compare_at_price": db_compare_at_price,
        "stock_quantity": variant.stockQuantity,
        "is_active": variant.isActive,
        "is_default": variant.isDefault,
        "status": "revision_draft" if is_revision else variant.status,
        "attributes": product_variant_repo.json_param(var_attrs),
    }


async def validate_unique_variant_skus(
    session: AsyncSession,
    *,
    product_id: UUID,
    parent_product_id: UUID | None,
    variants_payload: list[ProductVariantPayload],
) -> None:
    sku_list = [variant.sku.strip() for variant in variants_payload if variant.sku]
    if len(sku_list) != len(set(sku_list)):
        raise HTTPException(status_code=400, detail="TrÃƒÂ¹ng lÃ¡ÂºÂ·p SKU trong danh sÃƒÂ¡ch biÃ¡ÂºÂ¿n thÃ¡Â»Æ’ gÃ¡Â»Â­i lÃƒÂªn.")

    for variant in variants_payload:
        if not variant.sku:
            continue
        existing = await product_variant_repo.find_active_variant_by_sku(
            session,
            sku=variant.sku.strip(),
            product_id=product_id,
            parent_product_id=parent_product_id,
            exclude_variant_id=variant.id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"SKU '{variant.sku}' Ã„â€˜ÃƒÂ£ Ã„â€˜Ã†Â°Ã¡Â»Â£c sÃ¡Â»Â­ dÃ¡Â»Â¥ng bÃ¡Â»Å¸i mÃ¡Â»â„¢t biÃ¡ÂºÂ¿n thÃ¡Â»Æ’ khÃƒÂ¡c Ã„â€˜ang hoÃ¡ÂºÂ¡t Ã„â€˜Ã¡Â»â„¢ng.",
            )


async def upsert_product_variants(
    session: AsyncSession,
    product_id: UUID,
    variants_payload: list[ProductVariantPayload],
    product_name: str,
    default_price: float = 0,
    default_sale_price: float | None = None,
    default_stock: int = 0,
) -> None:
    del product_name, default_price, default_sale_price, default_stock
    product_row = await product_variant_repo.get_product_variant_context(session, product_id)
    if not product_row:
        raise HTTPException(status_code=404, detail="KhÃƒÂ´ng tÃƒÂ¬m thÃ¡ÂºÂ¥y sÃ¡ÂºÂ£n phÃ¡ÂºÂ©m.")

    options = product_row["options"] or []
    product_status = product_row.get("status")
    parent_product_id = product_row.get("parent_product_id")
    is_revision = product_status == "REVISION_DRAFT"

    await validate_unique_variant_skus(
        session,
        product_id=product_id,
        parent_product_id=parent_product_id,
        variants_payload=variants_payload,
    )
    validate_variant_options(options, variants_payload)
    validate_default_variant_count(variants_payload)

    db_variants = await product_variant_repo.list_active_variant_ids(session, product_id)
    payload_ids = {variant.id for variant in variants_payload if variant.id}
    to_delete_ids = [variant_id for variant_id in db_variants if variant_id not in payload_ids]
    default_sku_for_parent = None

    for variant in variants_payload:
        values = resolve_variant_values(variant, is_revision=is_revision)
        if not values["sku"]:
            values["sku"] = f"SKU-{uuid4().hex[:10].upper()}"
        if variant.isDefault:
            default_sku_for_parent = values["sku"]

        if variant.id and variant.id in db_variants:
            await product_variant_repo.update_variant(session, variant_id=variant.id, values=values)
        else:
            new_variant_id = variant.id if variant.id and variant.id in db_variants else uuid4()
            if values["sku"].startswith("SKU-") and not variant.sku:
                values["sku"] = f"SKU-{new_variant_id.hex[:10].upper()}"
            values["parent_variant_id"] = variant.id if variant.id and variant.id not in db_variants else None
            await product_variant_repo.insert_variant(
                session,
                variant_id=new_variant_id,
                product_id=product_id,
                values=values,
            )

    await product_variant_repo.soft_delete_variants(session, to_delete_ids)

    if default_sku_for_parent and not is_revision:
        await product_variant_repo.update_product_sku(session, product_id=product_id, sku=default_sku_for_parent)


async def delete_product_variant(
    product_id: UUID,
    variant_id: UUID,
    session: AsyncSession,
) -> dict:
    variant = await product_variant_repo.get_variant_for_delete(
        session,
        product_id=product_id,
        variant_id=variant_id,
    )
    if not variant:
        raise HTTPException(status_code=404, detail="KhÃƒÂ´ng tÃƒÂ¬m thÃ¡ÂºÂ¥y biÃ¡ÂºÂ¿n thÃ¡Â»Æ’.")

    await product_variant_repo.soft_delete_variant(session, variant_id)

    if variant["is_default"]:
        next_variant = await product_variant_repo.get_next_default_variant(session, product_id)
        if next_variant:
            await product_variant_repo.mark_variant_default(session, next_variant["id"])
            await product_variant_repo.update_product_sku_with_timestamp(
                session,
                sku=next_variant["sku"],
                product_id=product_id,
            )

    await sync_parent_price_if_variants_exist(session, product_id)
    await session.commit()
    return {"ok": True}
