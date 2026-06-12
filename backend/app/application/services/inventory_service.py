import csv
import io
from uuid import UUID, uuid4

from fastapi import HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.product_helper_service import persisted_sales_config, sync_parent_price_from_variants
from app.api.schemas.admin import InventoryAdjustmentPayload, InventoryReceiptPayload, InventorySettingsPayload, VariantInventoryPayload
from app.infrastructure.database.repositories import inventory_repo


def _policy_tracks_imei(policy_row: dict | None) -> bool:
    if not policy_row:
        return False
    child_policy = policy_row.get("child_policy") if isinstance(policy_row.get("child_policy"), dict) else {}
    parent_policy = policy_row.get("parent_policy") if isinstance(policy_row.get("parent_policy"), dict) else {}
    if child_policy and not child_policy.get("inheritImeiPolicy", True):
        return bool(child_policy.get("trackImei"))
    return bool(parent_policy.get("trackImei"))


def _clean_imeis(raw_imeis: list[str]) -> list[str]:
    return [str(item).strip() for item in raw_imeis if str(item).strip()]


async def get_product_inventory(session: AsyncSession, product_id: UUID) -> dict:
    product_data = await inventory_repo.get_product_inventory_summary(session, product_id)
    if not product_data:
        raise HTTPException(status_code=404, detail="Product not found.")
    variants = await inventory_repo.list_product_inventory_variants(session, product_id)
    logs = await inventory_repo.list_inventory_adjustment_logs(session, product_id)
    sales_config = product_data.get("salesConfig") if isinstance(product_data.get("salesConfig"), dict) else {}
    minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
    product_data.update(
        {
            "minimumStock": minimum_stock,
            "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
            "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
            "stockAlert": "LOW" if int(product_data.get("stockQuantity") or 0) <= minimum_stock else "OK",
        }
    )
    return {**product_data, "variants": variants, "logs": logs}

async def update_product_inventory_settings(
    session: AsyncSession,
    product_id: UUID,
    payload: InventorySettingsPayload,
) -> dict:
    row = await inventory_repo.get_product_sales_config_for_update(session, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found.")
    sales_config = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
    merged = persisted_sales_config(
        {
            **sales_config,
            "minimumStock": payload.minimumStock,
            "blockSaleWhenOutOfStock": payload.blockSaleWhenOutOfStock,
            "cycleCountDays": payload.cycleCountDays or sales_config.get("cycleCountDays") or 30,
        }
    )
    await inventory_repo.update_product_sales_config(session, product_id=product_id, sales_config=merged)
    await session.commit()
    return {"ok": True, **merged}

async def export_inventory_snapshot(session: AsyncSession, search: str = "") -> Response:
    rows = await inventory_repo.list_inventory_snapshot_rows(session, search)
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
        ],
    )
    writer.writeheader()
    for row in rows:
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
            }
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inventory-export.csv"'},
    )


async def list_inventory_receipts(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_receipts(session, search.strip())


async def adjust_product_inventory(
    session: AsyncSession,
    product_id: UUID,
    payload: InventoryAdjustmentPayload,
    idempotency_key: str | None = None,
) -> dict:
    idem_key = (idempotency_key or payload.referenceCode or "").strip()
    if idem_key:
        await inventory_repo.delete_old_inventory_idempotency(session)
        existing = await inventory_repo.get_inventory_idempotency_response(session, idem_key)
        if existing:
            return existing
    if payload.delta is None and payload.quantity is None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity.")
    if payload.delta is not None and payload.quantity is not None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity, not both.")
    
    actual_variant_id = payload.variantId
    if not actual_variant_id:
        active_variants = await inventory_repo.list_product_variant_ids(session, product_id)
        if len(active_variants) == 1:
            actual_variant_id = active_variants[0]["id"]
        elif len(active_variants) > 1:
            raise HTTPException(
                status_code=400,
                detail="Sản phẩm có nhiều biến thể. Vui lòng chọn biến thể cụ thể để điều chỉnh tồn kho."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Sản phẩm không có biến thể hoạt động nào."
            )

    row = await inventory_repo.get_variant_inventory_for_update(
        session,
        product_id=product_id,
        variant_id=actual_variant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Variant not found.")
    
    old_quantity = int(row["stock_quantity"] or 0)
    new_quantity = payload.quantity if payload.quantity is not None else old_quantity + int(payload.delta or 0)
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Inventory quantity cannot be negative.")
    await inventory_repo.update_variant_stock(session, variant_id=actual_variant_id, quantity=new_quantity)
    item_sku = row["sku"]

    delta = int(payload.delta or 0) if payload.delta is not None else (new_quantity - old_quantity)

    imeis = _clean_imeis(payload.imeis)
    if payload.transactionType == "RECEIPT" and delta > 0:
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        if _policy_tracks_imei(policy_row):
            if len(imeis) != delta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm cần quản lý IMEI. Vui lòng nhập đúng {delta} IMEI.",
                )
            if len(set(imeis)) != len(imeis):
                raise HTTPException(status_code=400, detail="Danh sách IMEI có mã bị trùng.")
            existing_imeis = await inventory_repo.list_existing_imeis(session, imeis)
            if existing_imeis:
                raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {', '.join(existing_imeis[:5])}")
            for imei in imeis:
                await inventory_repo.insert_product_imei(
                    session,
                    product_id=product_id,
                    variant_id=actual_variant_id,
                    imei=imei,
                    source_reference=payload.referenceCode,
                )
    await inventory_repo.insert_inventory_adjustment_log(
        session,
        log_id=uuid4(),
        product_id=product_id,
        variant_id=actual_variant_id,
        old_quantity=old_quantity,
        new_quantity=new_quantity,
        delta=delta,
        transaction_type=payload.transactionType,
        reference_code=payload.referenceCode,
        reason=payload.reason,
        note=payload.note,
        supplier_name=payload.supplierName,
        unit_cost=payload.unitCost,
        location_code=payload.locationCode,
        location_name=payload.locationName,
    )
    response_payload = {"ok": True, "oldQuantity": old_quantity, "newQuantity": new_quantity}
    if idem_key:
        await inventory_repo.insert_inventory_idempotency_response(
            session,
            key=idem_key,
            product_id=product_id,
            response_payload=response_payload,
        )
    await sync_parent_price_from_variants(session, product_id)
    await session.commit()
    return response_payload


async def create_inventory_receipt(
    session: AsyncSession,
    payload: InventoryReceiptPayload,
    idempotency_key: str | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    idem_key = (idempotency_key or reference_code).strip()
    if idem_key:
        await inventory_repo.delete_old_inventory_idempotency(session)
        existing = await inventory_repo.get_inventory_idempotency_response(session, idem_key)
        if existing:
            return existing

    seen_imeis: set[str] = set()
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()

    for index, line in enumerate(payload.lines, start=1):
        product_id = line.productId
        actual_variant_id = line.variantId
        if not actual_variant_id:
            active_variants = await inventory_repo.list_product_variant_ids(session, product_id)
            if len(active_variants) == 1:
                actual_variant_id = active_variants[0]["id"]
            elif len(active_variants) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {index}: sản phẩm có nhiều biến thể. Vui lòng chọn biến thể cần nhập kho.",
                )
            else:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không có biến thể hoạt động.")

        row = await inventory_repo.get_variant_inventory_for_update(
            session,
            product_id=product_id,
            variant_id=actual_variant_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy biến thể hợp lệ.")

        quantity = int(line.quantity)
        old_quantity = int(row["stock_quantity"] or 0)
        new_quantity = old_quantity + quantity
        imeis = _clean_imeis(line.imeis)
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        tracks_imei = _policy_tracks_imei(policy_row)

        if tracks_imei:
            if len(imeis) != quantity:
                product_name = policy_row.get("name") if policy_row else "sản phẩm"
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {index}: {product_name} cần đúng {quantity} IMEI.",
                )
            duplicate_in_line = len(set(imeis)) != len(imeis)
            duplicate_in_receipt = any(imei in seen_imeis for imei in imeis)
            if duplicate_in_line or duplicate_in_receipt:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách IMEI có mã bị trùng.")
            seen_imeis.update(imeis)
            existing_imeis = await inventory_repo.list_existing_imeis(session, imeis)
            if existing_imeis:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: IMEI đã tồn tại: {', '.join(existing_imeis[:5])}")
        elif imeis:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: sản phẩm này không bật quản lý IMEI, không cần nhập IMEI.",
            )

        await inventory_repo.update_variant_stock(session, variant_id=actual_variant_id, quantity=new_quantity)
        for imei in imeis:
            await inventory_repo.insert_product_imei(
                session,
                product_id=product_id,
                variant_id=actual_variant_id,
                imei=imei,
                source_reference=reference_code,
            )
        await inventory_repo.insert_inventory_adjustment_log(
            session,
            log_id=uuid4(),
            product_id=product_id,
            variant_id=actual_variant_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            delta=quantity,
            transaction_type="RECEIPT",
            reference_code=reference_code,
            reason=line.reason or "Nhập kho",
            note=line.note or payload.note,
            supplier_name=payload.supplierName,
            unit_cost=line.unitCost,
            location_code=payload.locationCode,
            location_name=payload.locationName,
        )
        touched_products.add(product_id)
        posted_lines.append(
            {
                "productId": str(product_id),
                "variantId": str(actual_variant_id),
                "oldQuantity": old_quantity,
                "newQuantity": new_quantity,
                "quantity": quantity,
                "imeiCount": len(imeis),
                "tracksImei": tracks_imei,
            }
        )

    for product_id in touched_products:
        await sync_parent_price_from_variants(session, product_id)

    response_payload = {"ok": True, "referenceCode": reference_code, "lineCount": len(posted_lines), "lines": posted_lines}
    if idem_key and posted_lines:
        await inventory_repo.insert_inventory_idempotency_response(
            session,
            key=idem_key,
            product_id=payload.lines[0].productId,
            response_payload=response_payload,
        )
    await session.commit()
    return response_payload


async def set_variant_inventory(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID,
    payload: VariantInventoryPayload,
) -> dict:
    return await adjust_product_inventory(
        session,
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
    )
