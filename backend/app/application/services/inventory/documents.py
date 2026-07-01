from .common import *
from app.infrastructure.database.repositories import store_info_repo


def _store_info_payload(info) -> dict | None:
    if info is None:
        return None
    return {
        "name": info.name,
        "description": info.description,
        "address": info.address,
        "hotline": info.hotline,
    }


async def list_inventory_receipts(
    session: AsyncSession,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    if date_from:
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Từ ngày không hợp lệ.") from exc
    if date_to:
        try:
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Đến ngày không hợp lệ.") from exc
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="Từ ngày không được lớn hơn đến ngày.")
    rows = await inventory_repo.list_inventory_receipts(
        session,
        search.strip(),
        date_from.strip(),
        date_to.strip(),
    )
    normalized_status = status.strip().upper()
    if normalized_status:
        rows = [row for row in rows if str(row.get("status") or "COMPLETED").upper() == normalized_status]
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": rows[start:start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


async def get_inventory_receipt_report(session: AsyncSession) -> dict:
    return await inventory_repo.get_inventory_receipt_report(session)


async def export_inventory_receipt_document(session: AsyncSession, reference_code: str, export_format: str) -> Response:
    reference_code = reference_code.strip()
    export_format = export_format.strip().lower()
    if export_format not in {"pdf", "docx"}:
        raise HTTPException(status_code=400, detail="Định dạng xuất phiếu không hợp lệ.")
    receipts = await inventory_repo.list_inventory_receipts(session, reference_code)
    receipt = next((item for item in receipts if str(item.get("referenceCode") or "") == reference_code), None)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    store_info = _store_info_payload(await store_info_repo.get_store_info(session))
    if export_format == "pdf":
        content, filename = document_export_service.render_inventory_receipt_pdf(receipt, store_info)
        media_type = "application/pdf"
    else:
        content, filename = document_export_service.render_inventory_receipt_docx(receipt, store_info)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def list_inventory_stock_counts(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_stock_counts(session, search.strip())


async def list_inventory_adjustments(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_adjustments(session, search.strip())


async def create_inventory_stock_count(
    session: AsyncSession,
    payload: InventoryStockCountPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    if existing_receipt or existing_count:
        raise HTTPException(status_code=409, detail="Mã phiếu kiểm kê đã tồn tại.")
    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or "MAIN").strip() or "MAIN",
        name=(payload.locationName or "Kho chính").strip() or "Kho chính",
    )
    document_id = uuid4()
    await inventory_repo.insert_inventory_stock_count_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        reason=(payload.reason or "KIEM_KE_DINH_KY").strip() or "KIEM_KE_DINH_KY",
        note=payload.note,
        location_id=location["id"],
        created_by=current_user_id,
    )
    seen_keys: set[tuple[str, str]] = set()
    total_abs_variance = 0
    for index, line in enumerate(payload.lines, start=1):
        key = (str(line.productId), str(line.variantId or ""))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng trong phiếu kiểm kê.")
        seen_keys.add(key)
        product_id = line.productId
        variant_id = line.variantId
        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để kiểm kê.")
        expected_quantity = int(line.expectedQuantity)
        counted_quantity = int(line.countedQuantity)
        total_abs_variance += abs(counted_quantity - expected_quantity)
        await inventory_repo.insert_inventory_stock_count_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            expected_quantity=expected_quantity,
            counted_quantity=counted_quantity,
            note=line.note,
        )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(payload.lines),
        "absoluteVarianceQuantity": total_abs_variance,
    }


async def update_inventory_stock_count_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryStockCountStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu kiểm kê không hợp lệ.")
    document = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu kiểm kê.")
    if document["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ phiếu kiểm kê nháp mới được duyệt hoặc hủy.")

    lines = await inventory_repo.list_inventory_stock_count_lines(session, document["id"])
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    if target_status == "APPROVED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            counted_quantity = int(line["countedQuantity"] or 0)
            expected_quantity = int(line["expectedQuantity"] or 0)
            variance = counted_quantity - expected_quantity
            if variant_id:
                current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
            else:
                current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
            if not current_row:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: sản phẩm/biến thể không còn tồn tại.")
            old_quantity = int(current_row["stock_quantity"] or 0)
            if counted_quantity < 0:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số đếm không được âm.")
            if variant_id:
                await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=counted_quantity)
            else:
                await inventory_repo.update_product_stock(session, product_id=product_id, quantity=counted_quantity)
            await inventory_repo.set_inventory_level_counted_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                counted_quantity=counted_quantity,
            )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=old_quantity,
                new_quantity=counted_quantity,
                delta=counted_quantity - old_quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason=document.get("reason") or "KIEM_KE",
                note=line.get("note") or payload.note or f"Kiểm kê kho: lệch {variance}",
                supplier_name=None,
                unit_cost=None,
                location_code=document.get("locationCode") or "MAIN",
                location_name=document.get("locationName") or "Kho chính",
            )
            if variant_id:
                touched_products.add(product_id)
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "expectedQuantity": expected_quantity,
                    "countedQuantity": counted_quantity,
                    "oldQuantity": old_quantity,
                    "varianceQuantity": variance,
                }
            )
        for product_id in touched_products:
            await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=document["id"],
        status=target_status,
        note=payload.note,
        actor_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": target_status, "postedLineCount": len(posted_lines), "lines": posted_lines}


async def create_inventory_adjustment_request(
    session: AsyncSession,
    payload: InventoryAdjustmentRequestPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    existing_adjustment = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    if existing_receipt or existing_count or existing_adjustment:
        raise HTTPException(status_code=409, detail="Mã phiếu điều chỉnh tồn đã tồn tại.")
    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or "MAIN").strip() or "MAIN",
        name=(payload.locationName or "Kho chính").strip() or "Kho chính",
    )
    document_id = uuid4()
    await inventory_repo.insert_inventory_adjustment_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        reason=(payload.reason or "DIEU_CHINH_THU_CONG").strip() or "DIEU_CHINH_THU_CONG",
        note=payload.note,
        location_id=location["id"],
        created_by=current_user_id,
    )
    seen_keys: set[tuple[str, str]] = set()
    total_abs_variance = 0
    for index, line in enumerate(payload.lines, start=1):
        key = (str(line.productId), str(line.variantId or ""))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng trong phiếu điều chỉnh.")
        seen_keys.add(key)
        reason = line.reason.strip()
        if not reason:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: phải nhập lý do điều chỉnh.")
        product_id = line.productId
        variant_id = line.variantId
        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để điều chỉnh.")
        actual_current = int(current_row["stock_quantity"] or 0)
        current_quantity = int(line.currentQuantity)
        new_quantity = int(line.newQuantity)
        if current_quantity != actual_current:
            raise HTTPException(status_code=409, detail=f"Dòng {index}: tồn hệ thống đã thay đổi từ {current_quantity} sang {actual_current}, vui lòng tải lại trước khi tạo phiếu.")
        total_abs_variance += abs(new_quantity - current_quantity)
        await inventory_repo.insert_inventory_adjustment_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            current_quantity=current_quantity,
            new_quantity=new_quantity,
            reason=reason,
            note=line.note,
        )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(payload.lines),
        "absoluteVarianceQuantity": total_abs_variance,
    }


async def update_inventory_adjustment_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryAdjustmentRequestStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu điều chỉnh tồn không hợp lệ.")
    document = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu điều chỉnh tồn.")
    if document["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ phiếu điều chỉnh nháp mới được duyệt hoặc hủy.")

    lines = await inventory_repo.list_inventory_adjustment_lines(session, document["id"])
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    if target_status == "APPROVED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            requested_current = int(line["currentQuantity"] or 0)
            new_quantity = int(line["newQuantity"] or 0)
            if variant_id:
                current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
            else:
                current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
            if not current_row:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: sản phẩm/biến thể không còn tồn tại.")
            old_quantity = int(current_row["stock_quantity"] or 0)
            if old_quantity != requested_current:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: tồn hệ thống đã thay đổi từ {requested_current} sang {old_quantity}, không thể duyệt tự động.")
            if variant_id:
                await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_quantity)
            else:
                await inventory_repo.update_product_stock(session, product_id=product_id, quantity=new_quantity)
            await inventory_repo.set_inventory_level_counted_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                counted_quantity=new_quantity,
            )
            reason = str(line.get("reason") or document.get("reason") or "DIEU_CHINH_THU_CONG")
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                delta=new_quantity - old_quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason=reason,
                note=line.get("note") or payload.note,
                supplier_name=None,
                unit_cost=None,
                location_code=document.get("locationCode") or "MAIN",
                location_name=document.get("locationName") or "Kho chính",
            )
            if variant_id:
                touched_products.add(product_id)
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "oldQuantity": old_quantity,
                    "newQuantity": new_quantity,
                    "varianceQuantity": new_quantity - old_quantity,
                }
            )
        for product_id in touched_products:
            await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=document["id"],
        status=target_status,
        note=payload.note,
        actor_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": target_status, "postedLineCount": len(posted_lines), "lines": posted_lines}


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
    secondary_imeis = _clean_imeis(getattr(payload, "secondaryImeis", []))
    serial_numbers = _clean_serial_numbers(payload.serialNumbers)
    if payload.transactionType == "RECEIPT" and delta > 0:
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        if _policy_tracks_imei(policy_row):
            if len(imeis) != delta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm cần quản lý IMEI. Vui lòng nhập đúng {delta} IMEI.",
                )
            if secondary_imeis:
                _validate_imei_format(secondary_imeis)
                if len(secondary_imeis) != len(imeis):
                    raise HTTPException(status_code=400, detail="Số IMEI2 phải bằng số IMEI1 nếu có nhập IMEI2.")
            all_imeis = imeis + secondary_imeis
            if len(set(all_imeis)) != len(all_imeis):
                raise HTTPException(status_code=400, detail="Danh sách IMEI có mã bị trùng.")
            existing_imeis = await inventory_repo.list_existing_imeis(session, all_imeis)
            if existing_imeis:
                raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {', '.join(existing_imeis[:5])}")
            for imei in all_imeis:
                await inventory_repo.insert_product_imei(
                    session,
                    product_id=product_id,
                    variant_id=actual_variant_id,
                    imei=imei,
                    source_reference=payload.referenceCode,
                )
        elif imeis or secondary_imeis:
            raise HTTPException(status_code=400, detail="Sản phẩm không bật quản lý IMEI nên không được nhập IMEI.")
        if _policy_tracks_serial_number(policy_row):
            if len(serial_numbers) != delta:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm cần quản lý serial number. Vui lòng nhập đúng {delta} serial number.",
                )
            _validate_serial_number_format(serial_numbers)
            if len(set(serial_numbers)) != len(serial_numbers):
                raise HTTPException(status_code=400, detail="Danh sách serial number có mã bị trùng.")
            existing_serial_numbers = await inventory_repo.list_existing_serial_numbers(session, serial_numbers, product_id=product_id)
            if existing_serial_numbers:
                raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {', '.join(existing_serial_numbers[:5])}")
            for serial_number in serial_numbers:
                await inventory_repo.insert_product_serial_number(
                    session,
                    product_id=product_id,
                    variant_id=actual_variant_id,
                    serial_number=serial_number,
                    source_reference=payload.referenceCode,
                )
        elif serial_numbers:
            raise HTTPException(status_code=400, detail="Sản phẩm không bật quản lý serial number nên không được nhập serial number.")
        if _policy_tracks_imei(policy_row) and _policy_tracks_serial_number(policy_row):
            if len(imeis) != len(serial_numbers):
                raise HTTPException(status_code=400, detail="Số IMEI và serial number phải khớp nhau theo từng máy.")
            if secondary_imeis and len(secondary_imeis) != len(imeis):
                raise HTTPException(status_code=400, detail="Số IMEI2 phải bằng số IMEI1 nếu có nhập IMEI2.")
            for index, (imei, serial_number) in enumerate(zip(imeis, serial_numbers, strict=True)):
                await inventory_repo.upsert_product_identifier_pair(
                    session,
                    product_id=product_id,
                    variant_id=actual_variant_id,
                    imei1=imei,
                    imei2=secondary_imeis[index] if secondary_imeis else None,
                    serial_number=serial_number,
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
