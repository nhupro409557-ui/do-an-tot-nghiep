import csv
import io
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.category_service import audit_product_event, ensure_categories_not_migrating
from app.application.services import attached_service
from app.api.schemas.admin import *
from app.shared.admin_utils import (
    display_status,
    ensure_not_data_url,
    generate_variant_sku,
    normalize_status,
    slugify,
    split_relation_tokens,
    stock_state,
)
from app.application.services.product_helper_service import (
    persisted_sales_config,
    sync_parent_price_from_variants,
    sync_parent_price_if_variants_exist,
    normalized_option_key,
    normalize_product_options,
    extract_product_metadata,
    validate_optimized_media,
    resolve_catalog_labels,
    validate_product_specifications,
)
from app.application.services.product_variant_service import upsert_product_variants
from app.infrastructure.database.session import AsyncSessionFactory
from sqlalchemy import text
from app.infrastructure.database.repositories import product_repo, media_repo, used_product_repo
from app.shared.exceptions import BusinessException
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024


def _payload_has_selected_variant_specs(payload: ProductPayload) -> bool:
    raw_keys = (payload.specifications or {}).get("_variantSpecKeys") or (payload.specifications or {}).get("variantSpecKeys") or []
    if isinstance(raw_keys, str):
        raw_keys = [raw_keys]
    selected_keys = [key for key in raw_keys if normalized_option_key(key)]
    return bool(payload.variants and selected_keys)


async def resolve_product_refs(session: AsyncSession, product_id: UUID) -> None:
    pass


async def sync_product_relations(session: AsyncSession, product_id: UUID, sales_config: dict) -> None:
    await product_repo.delete_product_accessories(session, product_id)
    for offer in sales_config.get("accessoryOffers", []) or []:
        if not isinstance(offer, dict):
            continue
        try:
            acc_id = UUID(str(offer.get("productId") or ""))
        except ValueError:
            raise BusinessException(
                400,
                "ACCESSORY_PRODUCT_INVALID",
                f"Mã sản phẩm mua kèm không đúng định dạng: {offer.get('productId')}.",
            )
        if acc_id == product_id:
            raise BusinessException(
                400,
                "ACCESSORY_PRODUCT_INVALID",
                "Sản phẩm không thể tự chọn làm sản phẩm mua kèm của chính nó.",
            )
        acc_exists = await session.execute(
            text("SELECT 1 FROM products WHERE id = :id AND status = 'ACTIVE' AND deleted_at IS NULL"),
            {"id": acc_id}
        )
        if not acc_exists.scalar():
            raise BusinessException(
                400,
                "ACCESSORY_PRODUCT_INVALID",
                f"Sản phẩm mua kèm {acc_id} không tồn tại hoặc không ở trạng thái hoạt động.",
            )
        await product_repo.insert_product_accessory(session, product_id=product_id, accessory_id=acc_id)

    await product_repo.delete_product_attached_services(session, product_id)
    used_service_groups = set()
    for item in sales_config.get("attachedServices", []) or []:
        if not isinstance(item, dict):
            continue
        try:
            service_id = UUID(str(item.get("serviceId") or ""))
        except ValueError:
            raise BusinessException(
                400,
                "ATTACHED_SERVICE_INVALID",
                f"Mã dịch vụ đi kèm không đúng định dạng: {item.get('serviceId')}.",
            )
        service_row = await product_repo.get_active_attached_service_group(session, service_id)
        if not service_row:
            raise BusinessException(
                400,
                "ATTACHED_SERVICE_INVALID",
                f"Dịch vụ đi kèm {service_id} không tồn tại hoặc đã ngừng hoạt động.",
            )
        group_key = f"{service_row['service_type']}:{service_row['attribute_group'] or service_id}"
        if service_row["attribute_group"] and group_key in used_service_groups:
            continue
        used_service_groups.add(group_key)
        await product_repo.upsert_product_attached_service(session, product_id=product_id, service_id=service_id)


async def list_admin_products(
    page: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=80),
    search: str = Query(default="", max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    categoryId: UUID | None = None,
    brandId: UUID | None = None,
    session: AsyncSession | None = None,
) -> list[dict] | dict:
    rows, total = await product_repo.list_admin_product_rows(
        session,
        page=page,
        limit=limit,
        cursor=cursor,
        search=search,
        status_filter=status_filter,
        category_id=categoryId,
        brand_id=brandId,
    )
    if rows:
        product_ids = [UUID(item["id"]) for item in rows]
        bundle_rows = await product_repo.list_product_bundle_rows(session, product_ids)
        accessory_rows = await product_repo.list_product_accessory_rows(session, product_ids)
        service_rows = await product_repo.list_product_attached_service_rows(session, product_ids)
        service_lookup: dict[str, list[dict]] = {}
        for service in service_rows:
            service_lookup.setdefault(service["product_id"], []).append(
                {
                    "serviceId": service["service_id"],
                    "code": service["code"],
                    "name": service["name"],
                    "serviceType": service["service_type"],
                    "attributeGroup": service["attribute_group"],
                    "durationMonths": service["duration_months"],
                    "priceMode": service["price_mode"],
                    "fixedPrice": service["fixed_price"],
                    "percentValue": service["percent_value"],
                    "baseAmount": service["base_amount"],
                    "overridePrice": service["override_price"],
                    "metadata": service["metadata"] if isinstance(service["metadata"], dict) else {},
                }
            )
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
                    "price": item.get("price"),
                    "discountPrice": item.get("discountPrice"),
                    "salePrice": item.get("salePrice"),
                    "stock_quantity": item.get("stock_quantity"),
                    "status": item.get("status"),
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
                original_price = float(accessory_meta.get("price") or 0)
                normal_discount_price = float(
                    accessory_meta.get("salePrice")
                    or accessory_meta.get("discountPrice")
                    or original_price
                    or 0
                )
                configured_price = float(offer.get("price") or 0)
                discount_type = str(offer.get("discountType") or "").upper()
                discount_value = float(offer.get("discountValue") or 0)
                if configured_price > 0:
                    offer_price = configured_price
                elif discount_type == "PERCENT":
                    offer_price = max(0, round(normal_discount_price * (1 - discount_value / 100)))
                elif discount_type in {"FIXED", "AMOUNT", "FIXED_AMOUNT"}:
                    offer_price = max(0, round(normal_discount_price - discount_value))
                else:
                    offer_price = round(normal_discount_price)
                stock_quantity = int(accessory_meta.get("stock_quantity") or 0)
                accessory_offers.append(
                    {
                        **offer,
                        "productId": product_id,
                        "productName": accessory_meta.get("name", ""),
                        "productSku": accessory_meta.get("sku", ""),
                        "imageUrl": accessory_meta.get("imageUrl", ""),
                        "price": offer_price,
                        "salePrice": normal_discount_price,
                        "discountPrice": normal_discount_price,
                        "originalPrice": original_price,
                        "normalDiscountPrice": normal_discount_price,
                        "stockQuantity": stock_quantity,
                        "isSellable": accessory_meta.get("status") == "ACTIVE" and stock_quantity > 0,
                    }
                )
            item["salesConfig"] = {
                **sales_config,
                "bundleRefs": bundles.get(item["id"], []),
                "accessoryRefs": accessories.get(item["id"], []),
                "accessoryOffers": accessory_offers,
                "attachedServices": service_lookup.get(item["id"], sales_config.get("attachedServices", [])),
            }
    if cursor:
        paged = rows
        return {"items": paged, "nextCursor": paged[-1]["id"] if len(paged) == limit else None, "limit": limit}
    if page is None:
        return rows
    return {"items": rows, "totalRecords": total or 0, "totalPages": ((total or 0) + limit - 1) // limit, "page": page, "limit": limit}


async def suggest_admin_products(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
    excludeId: UUID | None = None,
    categoryId: UUID | None = None,
    brandId: UUID | None = None,
    session: AsyncSession | None = None,
) -> list[dict]:
    return await product_repo.suggest_admin_products(
        session,
        search=search,
        limit=limit,
        exclude_id=excludeId,
        category_id=categoryId,
        brand_id=brandId,
    )

async def list_attached_services(session: AsyncSession | None = None) -> list[dict]:
    return await attached_service.list_attached_services(session)


async def create_attached_service(payload: AttachedServicePayload, session: AsyncSession | None = None) -> dict:
    return await attached_service.create_attached_service(session, payload)


async def update_attached_service(service_id: UUID, payload: AttachedServicePayload, session: AsyncSession | None = None) -> dict:
    return await attached_service.update_attached_service(session, service_id, payload)


async def deactivate_attached_service(service_id: UUID, session: AsyncSession | None = None) -> dict:
    return await attached_service.deactivate_attached_service(session, service_id)


async def process_product_import_job(job_id: UUID, csv_text: str) -> None:
    async with AsyncSessionFactory() as session:
        try:
            rows = list(csv.DictReader(csv_text.splitlines()))
            await product_repo.mark_product_import_processing(session, job_id=job_id, total=len(rows))
            await session.commit()
            imported = 0
            failed = 0
            for row in rows:
                try:
                    async with session.begin_nested():
                        product_id = uuid4()
                        name = (row.get("name") or "").strip()
                        if not name:
                            raise ValueError("Tên sản phẩm không được trống")
                        specs, seo_metadata, sales_config = extract_product_metadata({
                            "_seoTitle": row.get("seoTitle") or "",
                            "_seoDescription": row.get("seoDescription") or "",
                            "_seoSlug": row.get("seoSlug") or "",
                        })
                        category_val = (row.get("category") or "ACCESSORY").strip()
                        brand_val = (row.get("brand") or "Khac").strip()
                        cat_res = await session.execute(
                            text("SELECT id FROM categories WHERE (LOWER(name) = LOWER(:name) OR LOWER(slug) = LOWER(:name)) AND is_deleted IS NOT TRUE LIMIT 1"),
                            {"name": category_val}
                        )
                        category_id = cat_res.scalar()
                        brand_res = await session.execute(
                            text("SELECT id FROM brands WHERE (LOWER(name) = LOWER(:name) OR LOWER(slug) = LOWER(:name)) AND is_active = TRUE LIMIT 1"),
                            {"name": brand_val}
                        )
                        brand_id = brand_res.scalar()

                        await product_repo.insert_imported_product(
                            session,
                            product_id=product_id,
                            sku=f"SKU-{product_id.hex[:10].upper()}",
                            name=name,
                            slug=f"{slugify(name)}-{product_id.hex[:6]}",
                            category=category_val,
                            brand=brand_val,
                            category_id=category_id,
                            brand_id=brand_id,
                            description=row.get("description") or "",
                            seo_metadata=seo_metadata,
                            sales_config=persisted_sales_config(sales_config),
                            price=float(row.get("price") or 0),
                            sale_price=float(row["discountPrice"]) if row.get("discountPrice") else None,
                            image_url=row.get("imageUrl") or None,
                            status=normalize_status(row.get("status") or "DRAFT"),
                        )
                    imported += 1
                except Exception:
                    failed += 1
                try:
                    await product_repo.update_product_import_progress(session, job_id=job_id, imported=imported, failed=failed)
                    await session.commit()
                except Exception:
                    await session.rollback()
            await product_repo.mark_product_import_completed(session, job_id)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            await product_repo.mark_product_import_failed(session, job_id=job_id, error=str(exc))
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
    try:
        revision_id = uuid4()
        clean_options = normalize_product_options(payload.options)
        await product_repo.insert_product_record(
            session,
            product_id=revision_id,
            parent_product_id=product_id,
            sku=f"REV-{revision_id.hex[:10].upper()}",
            name=payload.name,
            slug=f"{slugify(payload.name)}-revision-{revision_id.hex[:6]}",
            category=category,
            brand=brand,
            category_id=payload.categoryId,
            subcategory_id=payload.subcategoryId,
            brand_id=payload.brandId,
            description=payload.description or "",
            specifications=clean_specs,
            seo_metadata=seo_metadata,
            sales_config=persisted_sales_config(sales_config),
            price=payload.price,
            sale_price=payload.discountPrice,
            stock_quantity=0,
            image_url=payload.imageUrl,
            images=payload.images,
            video_url=payload.videoUrl,
            status="REVISION_DRAFT",
            is_featured=payload.isFeatured,
            is_flash_sale=payload.isFlashSale,
            options=clean_options,
        )
        await upsert_product_variants(session, revision_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
        await sync_parent_price_if_variants_exist(session, revision_id)
        await sync_product_relations(session, revision_id, sales_config)
        await session.commit()
        return {"ok": True, "revisionId": str(revision_id), "status": "REVISION_DRAFT"}
    except Exception as exc:
        await session.rollback()
        raise exc


async def import_products(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession | None = None,
) -> dict:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ nhập sản phẩm từ tệp CSV.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Tệp CSV quá lớn.")
    job_id = uuid4()
    await product_repo.create_product_import_job(session, job_id=job_id, source_filename=file.filename)
    await session.commit()
    background_tasks.add_task(process_product_import_job, job_id, content.decode("utf-8-sig"))
    return {"jobId": str(job_id), "status": "PENDING"}

async def list_product_import_jobs(session: AsyncSession | None = None) -> list[dict]:
    return await product_repo.list_product_import_jobs(session)

async def process_product_export_job(job_id: UUID, filters: dict) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await product_repo.mark_product_export_processing(session, job_id)
            rows = await product_repo.list_products_for_export(session, filters)
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "sku", "name", "brand", "category", "price", "discountPrice", "stock", "status", "seoTitle", "seoDescription", "seoSlug"])
            writer.writeheader()
            for row in rows:
                seo = row.get("seo_metadata") if isinstance(row.get("seo_metadata"), dict) else {}
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
                })
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            export_path = export_dir / f"products-{job_id}.csv"
            export_path.write_text(output.getvalue(), encoding="utf-8-sig")
            download_url = f"/exports/{export_path.name}"
            await product_repo.mark_product_export_completed(
                session,
                job_id=job_id,
                total=len(rows),
                file_path=str(export_path),
                download_url=download_url,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            await session.commit()
        except Exception as exc:
            await product_repo.mark_product_export_failed(session, job_id=job_id, error=str(exc))
            await session.commit()
async def export_products(
    background_tasks: BackgroundTasks,
    filters: dict | None = None,
    session: AsyncSession | None = None,
) -> dict:
    job_id = uuid4()
    export_filters = filters or {}
    await product_repo.create_product_export_job(session, job_id=job_id, filters=export_filters)
    await session.commit()
    background_tasks.add_task(process_product_export_job, job_id, export_filters)
    return {"jobId": str(job_id), "status": "PENDING"}

async def list_product_export_jobs(session: AsyncSession | None = None) -> list[dict]:
    return await product_repo.list_product_export_jobs(session)

async def product_catalog_kpis(session: AsyncSession | None = None) -> dict:
    return await product_repo.get_product_catalog_kpis(session)

async def list_product_audit_logs(product_id: UUID, session: AsyncSession | None = None) -> list[dict]:
    return await product_repo.list_product_audit_logs(session, product_id)



async def create_product(payload: ProductPayload, session: AsyncSession | None = None) -> dict:
    try:
        if len(payload.variants) < 2 and not _payload_has_selected_variant_specs(payload):
            payload.variants = []
            payload.options = []
        product_id = uuid4()
        clean_options = normalize_product_options(payload.options)
        validate_optimized_media(payload)
        ensure_not_data_url(payload.imageUrl, "imageUrl")
        ensure_not_data_url(payload.videoUrl, "videoUrl")
        for image in payload.images:
            ensure_not_data_url(image, "images")
            
        variant_media_urls = []
        for variant in payload.variants:
            if variant.imageUrl:
                ensure_not_data_url(variant.imageUrl, "variants.imageUrl")
                variant_media_urls.append(variant.imageUrl)
            if variant.images:
                for img in variant.images:
                    ensure_not_data_url(img, "variants.images")
                    variant_media_urls.append(img)
            
        await media_repo.assert_all_product_media_claimed(
            session,
            urls=[payload.imageUrl, *payload.images, payload.videoUrl] + variant_media_urls,
            entity_id=product_id,
        )
        
        await ensure_categories_not_migrating(session, [payload.categoryId, payload.subcategoryId])
        category, brand = await resolve_catalog_labels(session, payload)
        clean_specs, seo_metadata, sales_config = extract_product_metadata(payload.specifications)
        await validate_product_specifications(session, payload.categoryId, payload.subcategoryId, clean_specs, payload.variants)
        await product_repo.insert_product_record(
            session,
            product_id=product_id,
            sku=f"SKU-{product_id.hex[:10].upper()}",
            name=payload.name,
            slug=f"{slugify(payload.name)}-{product_id.hex[:6]}",
            category=category,
            brand=brand,
            category_id=payload.categoryId,
            subcategory_id=payload.subcategoryId,
            brand_id=payload.brandId,
            description=payload.description or "",
            specifications=clean_specs,
            seo_metadata=seo_metadata,
            sales_config=persisted_sales_config(sales_config),
            price=payload.price,
            sale_price=payload.discountPrice,
            stock_quantity=0,
            image_url=payload.imageUrl,
            images=payload.images,
            video_url=payload.videoUrl,
            status="DRAFT",
            is_featured=payload.isFeatured,
            is_flash_sale=payload.isFlashSale,
            options=clean_options,
        )
        await upsert_product_variants(session, product_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
        await sync_parent_price_if_variants_exist(session, product_id)
        await sync_product_relations(session, product_id, sales_config)
        
        # claim_media_assets already associated them at the beginning
        
        await audit_product_event(session, product_id, "PRODUCT_CREATED", new_value={"name": payload.name, "status": normalize_status(payload.status)})
        await session.commit()
        return {"id": str(product_id)}
    except Exception as exc:
        await session.rollback()
        raise exc


async def update_product(product_id: UUID, payload: ProductPayload, session: AsyncSession | None = None) -> dict:
    try:
        if len(payload.variants) < 2 and not _payload_has_selected_variant_specs(payload):
            payload.variants = []
            payload.options = []
        clean_options = normalize_product_options(payload.options)
        validate_optimized_media(payload)
        ensure_not_data_url(payload.imageUrl, "imageUrl")
        ensure_not_data_url(payload.videoUrl, "videoUrl")
        for image in payload.images:
            ensure_not_data_url(image, "images")
            
        variant_media_urls = []
        for variant in payload.variants:
            if variant.imageUrl:
                ensure_not_data_url(variant.imageUrl, "variants.imageUrl")
                variant_media_urls.append(variant.imageUrl)
            if variant.images:
                for img in variant.images:
                    ensure_not_data_url(img, "variants.images")
                    variant_media_urls.append(img)
            
        await media_repo.assert_all_product_media_claimed(
            session,
            urls=[payload.imageUrl, *payload.images, payload.videoUrl] + variant_media_urls,
            entity_id=product_id,
        )
        
        await ensure_categories_not_migrating(session, [payload.categoryId, payload.subcategoryId])
        category, brand = await resolve_catalog_labels(session, payload)
        clean_specs, seo_metadata, sales_config = extract_product_metadata(payload.specifications)
        await validate_product_specifications(session, payload.categoryId, payload.subcategoryId, clean_specs, payload.variants)
        current = await product_repo.get_product_current_for_update(session, product_id)
        if not current:
            raise BusinessException(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
        await ensure_categories_not_migrating(session, [current["category_id"], current["subcategory_id"], payload.categoryId, payload.subcategoryId])
        
        if payload.version is not None and int(current["version"] or 0) != payload.version:
            raise BusinessException(
                409,
                "PRODUCT_VERSION_CONFLICT",
                "Sản phẩm đã được cập nhật bởi người khác. Vui lòng tải lại.",
            )
        if payload.updatedAt and payload.version is None:
            if str(current["updated_at"].isoformat())[:19] != str(payload.updatedAt)[:19]:
                raise BusinessException(
                    409,
                    "PRODUCT_VERSION_CONFLICT",
                    "Sản phẩm đã được cập nhật bởi người khác. Vui lòng tải lại.",
                )
                
        if current["status"] == "MERGED":
            raise BusinessException(400, "INVALID_PRODUCT_STATE", "Bản chỉnh sửa này đã được áp dụng vào sản phẩm gốc, không thể sửa hoặc khôi phục lại.")
        if current["status"] == "ARCHIVED" and normalize_status(payload.status) == "ACTIVE":
            raise BusinessException(400, "INVALID_PRODUCT_STATE", "Sản phẩm đã lưu trữ không thể khôi phục trực tiếp. Vui lòng tạo bản nháp mới nếu cần bán lại.")
        
        if normalize_status(payload.status) == "ACTIVE":
            blocker = await product_repo.product_visibility_blocker(
                session,
                product_id=product_id,
                category_id=payload.categoryId,
                subcategory_id=payload.subcategoryId,
                brand_id=payload.brandId,
            )
            if blocker:
                raise BusinessException(400, "PRODUCT_VISIBILITY_BLOCKED", blocker)
                
        if current["status"] == "ACTIVE":
            return await create_product_revision(session, product_id, payload, clean_specs, seo_metadata, sales_config, category, brand)
            
        next_record_status = current["status"] if current["status"] in {"DRAFT", "REVISION_DRAFT", "PENDING"} else normalize_status(payload.status)
        expected_version = payload.version if payload.version is not None else int(current["version"] or 0)
        
        updated_count = await product_repo.update_product_record(
            session,
            product_id=product_id,
            expected_version=expected_version,
            name=payload.name,
            category=category,
            brand=brand,
            category_id=payload.categoryId,
            subcategory_id=payload.subcategoryId,
            brand_id=payload.brandId,
            description=payload.description or "",
            specifications=clean_specs,
            seo_metadata=seo_metadata,
            sales_config=persisted_sales_config(sales_config),
            price=payload.price,
            sale_price=payload.discountPrice,
            stock_quantity=int(current["stock_quantity"] or 0),
            image_url=payload.imageUrl,
            images=payload.images,
            video_url=payload.videoUrl,
            options=clean_options,
            status=next_record_status,
            is_featured=payload.isFeatured,
            is_flash_sale=payload.isFlashSale,
        )
        if updated_count == 0:
            still_exists = await session.scalar(text("SELECT EXISTS(SELECT 1 FROM products WHERE id = :id)"), {"id": product_id})
            if still_exists:
                raise BusinessException(
                    409,
                    "PRODUCT_VERSION_CONFLICT",
                    "Sản phẩm đã được cập nhật bởi người khác. Vui lòng tải lại.",
                )
            else:
                raise BusinessException(404, "PRODUCT_NOT_FOUND", "Không tìm thấy sản phẩm.")
                
        await upsert_product_variants(session, product_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
        await sync_parent_price_if_variants_exist(session, product_id)
        if normalize_status(payload.status) in {"INACTIVE", "ARCHIVED"}:
            await product_repo.deactivate_product_variants(session, product_id)
            await used_product_repo.hide_listings_by_product(session, product_id)
        await sync_product_relations(session, product_id, sales_config)
        
        # claim_media_assets already associated them at the beginning
        
        await audit_product_event(
            session,
            product_id,
            "PRODUCT_UPDATED",
            old_value={"name": current["name"], "price": str(current["price"]), "salePrice": str(current["sale_price"])},
            new_value={"name": payload.name, "price": payload.price, "salePrice": payload.discountPrice, "status": normalize_status(payload.status)},
        )
        await session.commit()
        return {"ok": True}
    except Exception as exc:
        await session.rollback()
        raise exc


async def duplicate_product(product_id: UUID, session: AsyncSession | None = None) -> dict:
    try:
        source = await product_repo.get_product_source_for_duplicate(session, product_id)
        if not source:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")

        new_id = uuid4()
        suffix = new_id.hex[:6]
        inserted = await product_repo.duplicate_product_record(
            session,
            new_id=new_id,
            source_id=product_id,
            sku=f"SKU-{new_id.hex[:10].upper()}",
            slug=f"{slugify(str(source['name']))}-copy-{suffix}",
        )
        if not inserted:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")

        await product_repo.duplicate_product_variants(session, new_id=new_id, source_id=product_id, suffix=suffix)
        await product_repo.duplicate_product_bundles(session, new_id=new_id, source_id=product_id)
        await product_repo.duplicate_product_accessories(session, new_id=new_id, source_id=product_id)
        await product_repo.duplicate_product_attached_services(session, new_id=new_id, source_id=product_id)
        await session.commit()
        return {"id": str(new_id)}
    except Exception as exc:
        await session.rollback()
        raise exc
