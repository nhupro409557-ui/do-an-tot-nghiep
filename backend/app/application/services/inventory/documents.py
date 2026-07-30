from .common import *
from .common import validate_identifier_pairs
from app.infrastructure.database.repositories import store_info_repo

TRANSFER_IDENTIFIER_STATUS_BY_PURPOSE = {
    "STORAGE": "IN_STOCK",
    "VIRTUAL": "IN_STOCK",
    "DAMAGED": "DEFECTIVE_RETURNED",
    "WARRANTY": "IN_WARRANTY",
    "QC": "INSPECTION_PENDING",
    "RETURN": "RETURNED",
}
SELLABLE_LOCATION_PURPOSES = {"STORAGE", "VIRTUAL"}
DISPOSAL_TYPES = {"SCRAP", "LIQUIDATED", "OUT_OF_SYSTEM"}


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


async def list_inventory_transfers(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_transfers(session, search.strip())


async def list_inventory_internal_holds(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_internal_holds(session, search.strip())


async def list_inventory_disposals(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_disposals(session, search.strip())


async def list_inventory_cost_adjustments(session: AsyncSession, search: str = "") -> list[dict]:
    return await inventory_repo.list_inventory_cost_adjustments(session, search.strip())


async def _prepare_stock_count_identifiers(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    imeis: list[str],
    serial_numbers: list[str],
    submitted_counted_quantity: int,
    line_index: int,
) -> tuple[int, dict]:
    policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
    tracks_imei = _policy_tracks_imei(policy_row)
    tracks_serial_number = _policy_tracks_serial_number(policy_row)
    cleaned_imeis = _clean_imeis(imeis)
    cleaned_serial_numbers = _clean_serial_numbers(serial_numbers)

    if len(set(cleaned_imeis)) != len(cleaned_imeis):
        raise HTTPException(status_code=400, detail=f"Dòng {line_index}: danh sách IMEI quét bị trùng.")
    if len(set(cleaned_serial_numbers)) != len(cleaned_serial_numbers):
        raise HTTPException(status_code=400, detail=f"Dòng {line_index}: danh sách serial quét bị trùng.")
    if tracks_imei:
        _validate_imei_format(cleaned_imeis)
    elif cleaned_imeis:
        raise HTTPException(status_code=400, detail=f"Dòng {line_index}: sản phẩm không quản lý IMEI.")
    if tracks_serial_number:
        _validate_serial_number_format(cleaned_serial_numbers)
    elif cleaned_serial_numbers:
        raise HTTPException(status_code=400, detail=f"Dòng {line_index}: sản phẩm không quản lý serial.")
    if tracks_imei and tracks_serial_number:
        if not cleaned_imeis or not cleaned_serial_numbers:
            raise HTTPException(status_code=400, detail=f"Dòng {line_index}: cần chọn đủ thiết bị gồm IMEI và serial.")
        await validate_identifier_pairs(
            session,
            product_id=product_id,
            variant_id=variant_id,
            imeis=cleaned_imeis,
            serial_numbers=cleaned_serial_numbers,
            line_index=line_index,
        )

    system_imeis = (
        await inventory_repo.list_stock_count_imeis(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location_id,
        )
        if tracks_imei
        else []
    )
    system_serial_numbers = (
        await inventory_repo.list_stock_count_serial_numbers(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location_id,
        )
        if tracks_serial_number
        else []
    )
    counted_quantity = submitted_counted_quantity
    if tracks_imei and tracks_serial_number:
        counted_quantity = len(cleaned_serial_numbers)
    elif tracks_imei:
        counted_quantity = len(cleaned_imeis)
    elif tracks_serial_number:
        counted_quantity = len(cleaned_serial_numbers)
    else:
        if counted_quantity < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {line_index}: Số lượng thực tế đếm được không thể nhỏ hơn 0."
            )

    system_imei_set = set(system_imeis)
    scanned_imei_set = set(cleaned_imeis)
    system_serial_set = set(system_serial_numbers)
    scanned_serial_set = set(cleaned_serial_numbers)
    return counted_quantity, {
        "tracksImei": tracks_imei,
        "tracksSerialNumber": tracks_serial_number,
        "imeis": cleaned_imeis,
        "serialNumbers": cleaned_serial_numbers,
        "missingImeis": sorted(system_imei_set - scanned_imei_set),
        "unexpectedImeis": sorted(scanned_imei_set - system_imei_set),
        "missingSerialNumbers": sorted(system_serial_set - scanned_serial_set),
        "unexpectedSerialNumbers": sorted(scanned_serial_set - system_serial_set),
    }


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
    location_code = (payload.locationCode or "").strip()
    if not location_code:
        raise HTTPException(status_code=400, detail="Phiếu kiểm kê phải chọn một kệ cụ thể.")
    location = await inventory_repo.get_inventory_location_by_code(session, location_code)
    if not location:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy kệ {location_code}.")
    if str(location.get("status") or "ACTIVE").upper() != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Kệ {location_code} đang bị khóa, không thể kiểm kê.")
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
        stock_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
        )
        expected_quantity = int(stock_level["onHandQuantity"] or 0) if stock_level else 0
        counted_quantity, identifier_metadata = await _prepare_stock_count_identifiers(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            imeis=line.imeis,
            serial_numbers=line.serialNumbers,
            submitted_counted_quantity=int(line.countedQuantity),
            line_index=index,
        )
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
            metadata=identifier_metadata,
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
            stock_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
            )
            current_level_quantity = int(stock_level["onHandQuantity"] or 0) if stock_level else 0
            reserved_quantity = int(stock_level["reservedQuantity"] or 0) if stock_level else 0
            if current_level_quantity != expected_quantity:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Dòng {index}: tồn tại kệ đã thay đổi từ {expected_quantity} thành "
                        f"{current_level_quantity} sau khi lập phiếu. Vui lòng kiểm kê lại."
                    ),
                )
            if counted_quantity < reserved_quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: thực đếm {counted_quantity} nhỏ hơn số đang giữ {reserved_quantity} tại kệ.",
                )
            verified_counted_quantity, current_identifier_metadata = await _prepare_stock_count_identifiers(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                imeis=line.get("imeis") or [],
                serial_numbers=line.get("serialNumbers") or [],
                submitted_counted_quantity=counted_quantity,
                line_index=index,
            )
            if verified_counted_quantity != counted_quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: số lượng mã quét đã thay đổi, vui lòng lập lại phiếu kiểm kê.",
                )
            identifier_mismatches = [
                *(current_identifier_metadata["missingImeis"]),
                *(current_identifier_metadata["unexpectedImeis"]),
                *(current_identifier_metadata["missingSerialNumbers"]),
                *(current_identifier_metadata["unexpectedSerialNumbers"]),
            ]
            if identifier_mismatches:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Dòng {index}: danh sách mã quét chưa khớp mã hệ thống tại kệ. "
                        "Hãy xử lý mã thiếu/thừa trước khi duyệt kiểm kê."
                    ),
                )
            if variant_id:
                current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
            else:
                current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
            if not current_row:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: sản phẩm/biến thể không còn tồn tại.")
            old_quantity = int(current_row["stock_quantity"] or 0)
            new_quantity = old_quantity + variance
            if new_quantity < 0:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: chênh lệch kiểm kê làm tổng tồn bị âm.")
            if variant_id:
                await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_quantity)
            else:
                await inventory_repo.update_product_stock(session, product_id=product_id, quantity=new_quantity)
            await inventory_repo.set_inventory_level_counted_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                counted_quantity=counted_quantity,
            )
            if variance < 0:
                try:
                    await inventory_repo.consume_inventory_lots_fifo(
                        session,
                        document_id=document["id"],
                        reference_code=reference_code,
                        product_id=product_id,
                        variant_id=variant_id,
                        location_id=document["target_location_id"],
                        quantity=abs(variance),
                        movement_note=f"Kiểm kê kho lệch thiếu {variance}.",
                    )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dòng {index}: không đủ dữ liệu lô FIFO để ghi sổ. {exc}",
                    ) from exc
            elif variance > 0:
                avg_cost = stock_level.get("averageUnitCost") if stock_level else None
                await inventory_repo.create_inventory_lot_for_reconciliation(
                    session,
                    document_id=document["id"],
                    reference_code=reference_code,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=document["target_location_id"],
                    quantity=variance,
                    unit_cost=avg_cost,
                    note=f"Tự động tạo lô do chênh lệch thừa khi kiểm kê lệch thừa {variance}.",
                )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                delta=variance,
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
                    "newQuantity": new_quantity,
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
        policy_row = await inventory_repo.get_product_inventory_policy(session, line.productId)
        if _policy_tracks_imei(policy_row) or _policy_tracks_serial_number(policy_row):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: sản phẩm quản lý IMEI/serial không được phép sử dụng phiếu điều chỉnh tồn kho. Vui lòng dùng phiếu kiểm kê."
            )
        if not reason:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: phải nhập lý do điều chỉnh.")
        product_id = line.productId
        variant_id = line.variantId
        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail="Product not found")
        stock_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
        )
        actual_current = int(stock_level["onHandQuantity"] or 0) if stock_level else 0
        current_quantity = int(line.currentQuantity)
        new_quantity = int(line.newQuantity)
        if new_quantity < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: Số lượng điều chỉnh mới không được nhỏ hơn 0."
            )
        if current_quantity != actual_current:
            raise HTTPException(
                status_code=409,
                detail=f"Dòng {index}: tồn tại kệ đã thay đổi từ {current_quantity} sang {actual_current}, vui lòng tải lại trước khi tạo phiếu."
            )
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
            stock_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
            )
            old_location_quantity = int(stock_level["onHandQuantity"] or 0) if stock_level else 0
            if old_location_quantity != requested_current:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: tồn tại kệ đã thay đổi từ {requested_current} sang {old_location_quantity}, không thể duyệt."
                )
            variance = new_quantity - old_location_quantity
            old_quantity = int(current_row["stock_quantity"] or 0)
            new_total_qty = old_quantity + variance
            if new_total_qty < 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: chênh lệch điều chỉnh làm tổng tồn bị âm."
                )
            if variant_id:
                await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_total_qty)
            else:
                await inventory_repo.update_product_stock(session, product_id=product_id, quantity=new_total_qty)
            await inventory_repo.set_inventory_level_counted_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=document["target_location_id"],
                counted_quantity=new_quantity,
            )
            if variance < 0:
                try:
                    await inventory_repo.consume_inventory_lots_fifo(
                        session,
                        document_id=document["id"],
                        reference_code=reference_code,
                        product_id=product_id,
                        variant_id=variant_id,
                        location_id=document["target_location_id"],
                        quantity=abs(variance),
                        movement_note=f"Điều chỉnh kho lệch thiếu {variance}.",
                    )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dòng {index}: không đủ dữ liệu lô FIFO để ghi sổ. {exc}",
                    ) from exc
            elif variance > 0:
                avg_cost = stock_level.get("averageUnitCost") if stock_level else None
                await inventory_repo.create_inventory_lot_for_reconciliation(
                    session,
                    document_id=document["id"],
                    reference_code=reference_code,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=document["target_location_id"],
                    quantity=variance,
                    unit_cost=avg_cost or 0,
                    movement_note=f"Điều chỉnh kho lệch thừa {variance}.",
                )
            new_quantity = new_total_qty
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


async def create_inventory_transfer_request(
    session: AsyncSession,
    payload: InventoryTransferPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    existing_adjustment = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    existing_transfer = await inventory_repo.get_inventory_transfer_for_update(session, reference_code)
    if existing_receipt or existing_count or existing_adjustment or existing_transfer:
        raise HTTPException(status_code=409, detail="Mã phiếu chuyển kệ đã tồn tại.")

    document_id = uuid4()
    await inventory_repo.insert_inventory_transfer_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        reason=(payload.reason or "CHUYEN_KE").strip() or "CHUYEN_KE",
        note=payload.note,
        created_by=current_user_id,
    )

    seen_keys: set[tuple[str, str, str, str]] = set()
    total_quantity = 0
    requested_volume_by_location: dict[str, float] = {}
    assigned_skus_by_location: dict[str, set[str]] = {}
    for index, line in enumerate(payload.lines, start=1):
        product_id = line.productId
        variant_id = line.variantId
        quantity = int(line.quantity)
        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: Số lượng chuyển kệ phải lớn hơn 0."
            )
        if line.fromLocationId == line.toLocationId:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: kệ nguồn và kệ đích phải khác nhau.")
        key = (str(product_id), str(variant_id or ""), str(line.fromLocationId), str(line.toLocationId))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể và cặp kệ bị trùng trong phiếu chuyển.")
        seen_keys.add(key)

        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để chuyển kệ.")

        from_location = await _get_active_inventory_location(session, line.fromLocationId, f"Dòng {index}: kệ nguồn")
        to_location = await _get_active_inventory_location(session, line.toLocationId, f"Dòng {index}: kệ đích")
        target_identifier_status = TRANSFER_IDENTIFIER_STATUS_BY_PURPOSE.get(
            str(to_location.get("purpose") or "STORAGE").upper()
        )
        if not target_identifier_status:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: mục đích kệ đích không hỗ trợ điều chuyển trạng thái.")
        if line.targetIdentifierStatus and line.targetIdentifierStatus != target_identifier_status:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: trạng thái mã đích không phù hợp với mục đích kệ {to_location.get('code')}.",
            )
        stock_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=line.fromLocationId,
        )
        available_quantity = 0
        if stock_level:
            available_quantity = int(stock_level["onHandQuantity"] or 0) - int(stock_level["reservedQuantity"] or 0)
        if available_quantity < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Dòng {index}: kệ {from_location.get('code')} không đủ tồn khả dụng để chuyển. Cần {quantity}, khả dụng {max(available_quantity, 0)}.",
            )

        imeis = _clean_imeis(line.imeis)
        serial_numbers = _clean_serial_numbers(line.serialNumbers)
        pair_ids = list(dict.fromkeys(line.identifierPairIds))
        if pair_ids:
            pair_rows = (
                await session.execute(
                    text(
                        """
                        SELECT
                            pair.id, pair.imei1, pair.imei2, pair.serial_number,
                            imei1.location_id AS imei1_location_id,
                            imei1.status AS imei1_status,
                            imei2.location_id AS imei2_location_id,
                            imei2.status AS imei2_status,
                            serial.location_id AS serial_location_id,
                            serial.status AS serial_status
                        FROM product_identifier_pairs pair
                        JOIN product_imeis imei1
                          ON imei1.product_id = pair.product_id AND imei1.imei = pair.imei1
                        LEFT JOIN product_imeis imei2
                          ON imei2.product_id = pair.product_id AND imei2.imei = pair.imei2
                        JOIN product_serial_numbers serial
                          ON serial.product_id = pair.product_id AND serial.serial_number = pair.serial_number
                        WHERE pair.id = ANY(:pair_ids)
                          AND pair.product_id = :product_id
                          AND pair.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                        FOR UPDATE OF pair
                        """
                    ),
                    {"pair_ids": pair_ids, "product_id": product_id, "variant_id": variant_id},
                )
            ).mappings().all()
            if len(pair_rows) != len(pair_ids):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: Có thiết bị ghép cặp không thuộc sản phẩm/biến thể đã chọn.")
            if len(pair_rows) != quantity:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: Số thiết bị ghép cặp phải bằng số lượng chuyển.")
            for pair in pair_rows:
                expected_location = str(line.fromLocationId)
                locations = [pair["imei1_location_id"], pair["serial_location_id"]]
                if pair["imei2"]:
                    locations.append(pair["imei2_location_id"])
                if any(str(value or "") != expected_location for value in locations):
                    raise HTTPException(status_code=409, detail=f"Dòng {index}: IMEI và serial của một thiết bị đang khác kệ; cần đối soát trước khi chuyển.")
                statuses = [pair["imei1_status"], pair["serial_status"]]
                if pair["imei2"]:
                    statuses.append(pair["imei2_status"])
                if len(set(statuses)) != 1:
                    raise HTTPException(status_code=409, detail=f"Dòng {index}: IMEI và serial của một thiết bị đang khác trạng thái; cần đối soát trước khi chuyển.")
            imeis = [code for pair in pair_rows for code in (pair["imei1"], pair["imei2"]) if code]
            serial_numbers = [pair["serial_number"] for pair in pair_rows]
        if len(set(imeis)) != len(imeis):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách IMEI bị trùng.")
        if len(set(serial_numbers)) != len(serial_numbers):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách serial bị trùng.")
        _validate_imei_format(imeis)
        _validate_serial_number_format(serial_numbers)

        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        if _policy_tracks_imei(policy_row) and not pair_ids and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm quản lý IMEI nên số IMEI phải bằng số lượng chuyển.")
        if _policy_tracks_serial_number(policy_row) and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm quản lý serial nên số serial phải bằng số lượng chuyển.")

        await validate_identifier_pairs(
            session,
            product_id=product_id,
            variant_id=variant_id,
            imeis=imeis,
            serial_numbers=serial_numbers,
            line_index=index,
        )

        await _ensure_location_has_receipt_capacity(
            session,
            location_id=to_location["id"],
            line_index=index,
            quantity=quantity,
            policy_row=policy_row,
            requested_volume_by_location=requested_volume_by_location,
            product_id=product_id,
            variant_id=variant_id,
            assigned_skus_by_location=assigned_skus_by_location,
        )
        await inventory_repo.insert_inventory_transfer_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            from_location_id=from_location["id"],
            to_location_id=to_location["id"],
            quantity=quantity,
            imeis=imeis,
            serial_numbers=serial_numbers,
            target_identifier_status=target_identifier_status,
            note=line.note,
        )
        total_quantity += quantity

    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(payload.lines),
        "totalQuantity": total_quantity,
    }


async def update_inventory_transfer_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryTransferStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "COMPLETED", "CANCELLED", "REVERSED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu chuyển kệ không hợp lệ.")
    document = await inventory_repo.get_inventory_transfer_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu chuyển kệ.")
    allowed_transitions = {
        "DRAFT": {"APPROVED", "CANCELLED"},
        "APPROVED": {"COMPLETED", "CANCELLED"},
        "COMPLETED": {"REVERSED"},
    }
    current_status = str(document["status"])
    if target_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Không thể chuyển phiếu chuyển kệ từ {current_status} sang {target_status}.",
        )

    if target_status == "REVERSED":
        return await reverse_completed_transfer(session, reference_code, current_user_id)

    lines = await inventory_repo.list_inventory_transfer_lines(session, document["id"])
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    if target_status in {"APPROVED", "COMPLETED"}:
        requested_volume_by_location: dict[str, float] = {}
        assigned_skus_by_location: dict[str, set[str]] = {}
        for index, line in enumerate(lines, start=1):
            prod_id = line["productId"]
            var_id = line["variantId"]
            to_loc_id = line["toLocationId"]
            qty = int(line["quantity"] or 0)
            policy_row = await inventory_repo.get_product_inventory_policy(session, prod_id)
            await _ensure_location_has_receipt_capacity(
                session,
                location_id=to_loc_id,
                line_index=index,
                quantity=qty,
                policy_row=policy_row,
                requested_volume_by_location=requested_volume_by_location,
                product_id=prod_id,
                variant_id=var_id,
                assigned_skus_by_location=assigned_skus_by_location,
            )

    # --- Khóa tồn khi APPROVED: tăng reserved_quantity + lock IMEI/Serial ---
    if target_status == "APPROVED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            from_location_id = line["fromLocationId"]
            quantity = int(line["quantity"] or 0)
            adjusted = await inventory_repo.adjust_inventory_level_reserved_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=from_location_id,
                delta=quantity,
            )
            if not adjusted:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: kệ nguồn {line.get('fromLocationCode')} "
                           f"không đủ tồn khả dụng để giữ {quantity} đơn vị cho phiếu chuyển.",
                )
            imeis = [str(i).strip() for i in (line.get("imeis") or []) if str(i).strip()]
            serial_numbers = [str(s).strip().upper() for s in (line.get("serialNumbers") or []) if str(s).strip()]
            if imeis or serial_numbers:
                locked_imeis, locked_serials = await inventory_repo.lock_identifiers_for_hold(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=from_location_id,
                    imeis=imeis,
                    serial_numbers=serial_numbers,
                )
                policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
                if _policy_tracks_imei(policy_row) and len(locked_imeis) != len(imeis):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dòng {index}: Một hoặc nhiều IMEI không sẵn IN_STOCK tại kệ nguồn để khóa giữ.",
                    )
                if _policy_tracks_serial_number(policy_row) and len(locked_serials) != len(serial_numbers):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dòng {index}: Một hoặc nhiều Serial không sẵn IN_STOCK tại kệ nguồn để khóa giữ.",
                    )

    # --- Giải phóng reserved khi HỦY từ APPROVED ---
    if target_status == "CANCELLED" and current_status == "APPROVED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            from_location_id = line["fromLocationId"]
            quantity = int(line["quantity"] or 0)
            await inventory_repo.adjust_inventory_level_reserved_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=from_location_id,
                delta=-quantity,
            )
            imeis = [str(i).strip() for i in (line.get("imeis") or []) if str(i).strip()]
            serial_numbers = [str(s).strip().upper() for s in (line.get("serialNumbers") or []) if str(s).strip()]
            if imeis or serial_numbers:
                await inventory_repo.unlock_identifiers_for_hold(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=from_location_id,
                    imeis=imeis,
                    serial_numbers=serial_numbers,
                )

    if target_status == "COMPLETED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            from_location_id = line["fromLocationId"]
            to_location_id = line["toLocationId"]
            quantity = int(line["quantity"] or 0)
            target_identifier_status = str(
                line.get("targetIdentifierStatus")
                or TRANSFER_IDENTIFIER_STATUS_BY_PURPOSE.get(str(line.get("toLocationPurpose") or "STORAGE").upper())
                or "IN_STOCK"
            )
            if not to_location_id:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: phiếu thiếu kệ đích.")
            stock_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=from_location_id,
            )
            available_quantity = 0
            if stock_level:
                available_quantity = int(stock_level["onHandQuantity"] or 0) - int(stock_level["reservedQuantity"] or 0)
            if available_quantity < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: kệ {line.get('fromLocationCode')} không đủ tồn khả dụng để hoàn tất chuyển. Cần {quantity}, khả dụng {max(available_quantity, 0)}.",
                )

            from_loc_purpose = str(line.get("fromLocationPurpose") or "").upper()
            to_loc_purpose = str(line.get("toLocationPurpose") or "").upper()
            imeis = [str(item).strip() for item in (line.get("imeis") or []) if str(item).strip()]
            serial_numbers = [str(item).strip().upper() for item in (line.get("serialNumbers") or []) if str(item).strip()]
            if to_loc_purpose in {"STORAGE", "VIRTUAL"} and from_loc_purpose in {"QC", "DAMAGED", "RETURN", "WARRANTY"}:
                # Kiểm tra QC cho hàng thường (không có IMEI/Serial) qua inventory_lots
                if not imeis and not serial_numbers:
                    lot_res = await session.execute(
                        text("""
                            SELECT DISTINCT il.source_reference
                            FROM inventory_lots il
                            WHERE il.product_id = :product_id
                              AND il.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                              AND il.location_id = :from_location_id
                              AND il.remaining_quantity > 0
                              AND il.status = 'ACTIVE'
                              AND il.source_reference IS NOT NULL
                        """),
                        {
                            "product_id": product_id,
                            "variant_id": variant_id,
                            "from_location_id": from_location_id,
                        },
                    )
                    for lot_row in lot_res.mappings():
                        source_ref = lot_row["source_reference"]
                        receipt_res = await session.execute(
                            text("SELECT COALESCE(metadata->>'qualityStatus', 'PENDING') as qs FROM inventory_documents WHERE document_no = :ref AND document_type = 'INBOUND'"),
                            {"ref": source_ref},
                        )
                        r_row = receipt_res.mappings().first()
                        if r_row and r_row["qs"] != "PASSED":
                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"Dòng {index}: Không thể chuyển hàng về STORAGE/VIRTUAL "
                                    f"khi lô hàng từ phiếu nhập {source_ref} chưa đạt QC "
                                    f"(Trạng thái hiện tại: {r_row['qs']})."
                                ),
                            )
                if imeis:
                    res = await session.execute(
                        text("""
                            SELECT imei, source_reference
                            FROM product_imeis
                            WHERE imei = ANY(:imeis)
                        """),
                        {"imeis": imeis}
                    )
                    for row in res.mappings():
                        source_ref = row["source_reference"]
                        if source_ref:
                            receipt_res = await session.execute(
                                text("SELECT COALESCE(metadata->>'qualityStatus', 'PENDING') as qs FROM inventory_documents WHERE document_no = :ref AND document_type = 'INBOUND'"),
                                {"ref": source_ref}
                            )
                            r_row = receipt_res.mappings().first()
                            if r_row and r_row["qs"] != "PASSED":
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Không thể chuyển IMEI {row['imei']} về STORAGE/VIRTUAL khi phiếu nhập {source_ref} chưa đạt QC (Trạng thái hiện tại: {r_row['qs']})."
                                )
                if serial_numbers:
                    res = await session.execute(
                        text("""
                            SELECT serial_number, source_reference
                            FROM product_serial_numbers
                            WHERE product_id = :product_id AND serial_number = ANY(:serials)
                        """),
                        {"product_id": product_id, "serials": serial_numbers}
                    )
                    for row in res.mappings():
                        source_ref = row["source_reference"]
                        if source_ref:
                            receipt_res = await session.execute(
                                text("SELECT COALESCE(metadata->>'qualityStatus', 'PENDING') as qs FROM inventory_documents WHERE document_no = :ref AND document_type = 'INBOUND'"),
                                {"ref": source_ref}
                            )
                            r_row = receipt_res.mappings().first()
                            if r_row and r_row["qs"] != "PASSED":
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Không thể chuyển Serial {row['serial_number']} về STORAGE/VIRTUAL khi phiếu nhập {source_ref} chưa đạt QC (Trạng thái hiện tại: {r_row['qs']})."
                                )

            # --- Giải phóng reserved đã khóa lúc APPROVED trước khi chuyển thực tế ---
            await inventory_repo.adjust_inventory_level_reserved_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=from_location_id,
                delta=-quantity,
            )
            if imeis or serial_numbers:
                await inventory_repo.unlock_identifiers_for_hold(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=from_location_id,
                    imeis=imeis,
                    serial_numbers=serial_numbers,
                )

            moved_imeis = await inventory_repo.move_product_imeis_location(
                session,
                product_id=product_id,
                variant_id=variant_id,
                from_location_id=from_location_id,
                to_location_id=to_location_id,
                imeis=imeis,
                target_status=target_identifier_status,
            )
            missing_imeis = sorted(set(imeis) - set(moved_imeis))
            if missing_imeis:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: IMEI không còn ở kệ nguồn hoặc không ở trạng thái còn hàng: {', '.join(missing_imeis[:5])}.",
                )
            moved_serial_numbers = await inventory_repo.move_product_serial_numbers_location(
                session,
                product_id=product_id,
                variant_id=variant_id,
                from_location_id=from_location_id,
                to_location_id=to_location_id,
                serial_numbers=serial_numbers,
                target_status=target_identifier_status,
            )
            missing_serial_numbers = sorted(set(serial_numbers) - set(moved_serial_numbers))
            if missing_serial_numbers:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: serial không còn ở kệ nguồn hoặc không ở trạng thái còn hàng: {', '.join(missing_serial_numbers[:5])}.",
                )

            try:
                moved_lots = await inventory_repo.transfer_inventory_lots_fifo(
                    session,
                    document_id=document["id"],
                    reference_code=reference_code,
                    product_id=product_id,
                    variant_id=variant_id,
                    from_location_id=from_location_id,
                    to_location_id=to_location_id,
                    quantity=quantity,
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: {exc}") from exc

            source_old_quantity = int(stock_level["onHandQuantity"] or 0)
            target_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=to_location_id,
            )
            target_old_quantity = int(target_level["onHandQuantity"] or 0) if target_level else 0
            try:
                await inventory_repo.transfer_inventory_level_quantity(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                    from_location_id=from_location_id,
                    to_location_id=to_location_id,
                    quantity=quantity,
                    average_unit_cost=stock_level.get("averageUnitCost"),
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            source_sellable = str(line.get("fromLocationPurpose") or "STORAGE").upper() in SELLABLE_LOCATION_PURPOSES
            target_sellable = str(line.get("toLocationPurpose") or "STORAGE").upper() in SELLABLE_LOCATION_PURPOSES
            if source_sellable != target_sellable:
                inventory_row = (
                    await inventory_repo.get_variant_inventory_for_update(
                        session,
                        product_id=product_id,
                        variant_id=variant_id,
                    )
                    if variant_id
                    else await inventory_repo.get_product_stock_for_update(session, product_id)
                )
                if not inventory_row:
                    raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy tồn bán được của sản phẩm.")
                sellable_delta = quantity if target_sellable else -quantity
                new_sellable_quantity = int(inventory_row["stock_quantity"] or 0) + sellable_delta
                if new_sellable_quantity < 0:
                    raise HTTPException(status_code=409, detail=f"Dòng {index}: tồn bán được không đủ để chuyển trạng thái.")
                if variant_id:
                    await inventory_repo.update_variant_stock(
                        session,
                        variant_id=variant_id,
                        quantity=new_sellable_quantity,
                    )
                    touched_products.add(product_id)
                else:
                    await inventory_repo.update_product_stock(
                        session,
                        product_id=product_id,
                        quantity=new_sellable_quantity,
                    )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=source_old_quantity,
                new_quantity=source_old_quantity - quantity,
                delta=-quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason="TRANSFER_OUT",
                note=line.get("note") or payload.note or "Chuyển hàng ra khỏi kệ.",
                supplier_name=None,
                unit_cost=None,
                location_code=line.get("fromLocationCode"),
                location_name=line.get("fromLocationName"),
            )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=target_old_quantity,
                new_quantity=target_old_quantity + quantity,
                delta=quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason="TRANSFER_IN",
                note=line.get("note") or payload.note or "Chuyển hàng vào kệ.",
                supplier_name=None,
                unit_cost=None,
                location_code=line.get("toLocationCode"),
                location_name=line.get("toLocationName"),
            )
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "fromLocationId": str(from_location_id),
                    "toLocationId": str(to_location_id),
                    "quantity": quantity,
                    "imeis": moved_imeis,
                    "serialNumbers": moved_serial_numbers,
                    "targetIdentifierStatus": target_identifier_status,
                    "movedLots": moved_lots,
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


async def reverse_completed_transfer(
    session: AsyncSession,
    reference_code: str,
    actor_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    transfer = await inventory_repo.get_inventory_transfer_for_update(session, reference_code)
    if not transfer or transfer["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail="Chỉ đảo phiếu chuyển kệ đã hoàn tất.")

    lines = await inventory_repo.list_inventory_transfer_lines(session, transfer["id"])
    touched_products: set[UUID] = set()

    for line in lines:
        product_id = line["productId"]
        variant_id = line["variantId"]
        from_location_id = line["fromLocationId"]
        to_location_id = line["toLocationId"]
        quantity = int(line["quantity"])

        # 1. Reverse IMEI/serial numbers back to the original location and status
        imeis = [str(item).strip() for item in (line.get("imeis") or []) if str(item).strip()]
        serial_numbers = [str(item).strip().upper() for item in (line.get("serialNumbers") or []) if str(item).strip()]

        original_status = TRANSFER_IDENTIFIER_STATUS_BY_PURPOSE.get(
            str(line.get("fromLocationPurpose") or "STORAGE").upper(), "IN_STOCK"
        )

        if imeis:
            moved_imeis = await inventory_repo.move_product_imeis_location(
                session,
                product_id=product_id,
                variant_id=variant_id,
                from_location_id=to_location_id,
                to_location_id=from_location_id,
                imeis=imeis,
                target_status=original_status,
            )
            missing_imeis = sorted(set(imeis) - set(moved_imeis))
            if missing_imeis:
                raise HTTPException(
                    status_code=409,
                    detail=f"Không thể đảo vì một số IMEI đã bị di chuyển hoặc thay đổi trạng thái: {', '.join(missing_imeis[:5])}."
                )

        if serial_numbers:
            moved_serials = await inventory_repo.move_product_serial_numbers_location(
                session,
                product_id=product_id,
                variant_id=variant_id,
                from_location_id=to_location_id,
                to_location_id=from_location_id,
                serial_numbers=serial_numbers,
                target_status=original_status,
            )
            missing_serials = sorted(set(serial_numbers) - set(moved_serials))
            if missing_serials:
                raise HTTPException(
                    status_code=409,
                    detail=f"Không thể đảo vì một số Serial đã bị di chuyển hoặc thay đổi trạng thái: {', '.join(missing_serials[:5])}."
                )

        # 2. Reverse FIFO lots:
        # We query the destination lots created for this transfer reference.
        # We decrease their remaining_quantity at the destination shelf (toLocationId)
        # And increase remaining_quantity of their original source lots at fromLocationId.
        target_lots_res = await session.execute(
            text(
                """
                SELECT id, remaining_quantity, initial_quantity, metadata->>'transferredFromLotId' AS parent_lot_id
                FROM inventory_lots
                WHERE metadata->>'transferReference' = :reference_code
                  AND product_id = :product_id
                  AND variant_id IS NOT DISTINCT FROM :variant_id
                """
            ),
            {"reference_code": reference_code, "product_id": product_id, "variant_id": variant_id}
        )
        target_lots = target_lots_res.mappings().all()
        for t_lot in target_lots:
            parent_lot_id = t_lot["parent_lot_id"]
            qty_to_reverse = int(t_lot["initial_quantity"] or 0)

            # Deduct from target lot (the one at toLocationId)
            await session.execute(
                text(
                    """
                    UPDATE inventory_lots
                    SET remaining_quantity = GREATEST(remaining_quantity - :qty, 0),
                        status = CASE WHEN GREATEST(remaining_quantity - :qty, 0) = 0 THEN 'DEPLETED' ELSE status END,
                        updated_at = NOW()
                    WHERE id = :lot_id
                    """
                ),
                {"lot_id": t_lot["id"], "qty": qty_to_reverse}
            )

            # Add back to parent/source lot (the one at fromLocationId)
            if parent_lot_id:
                await session.execute(
                    text(
                        """
                        UPDATE inventory_lots
                        SET remaining_quantity = remaining_quantity + :qty,
                            status = 'ACTIVE',
                            updated_at = NOW()
                        WHERE id = :lot_id
                        """
                    ),
                    {"lot_id": UUID(parent_lot_id), "qty": qty_to_reverse}
                )

            # Log movements in inventory_lot_movements
            for lot_id, movement_qty, note in (
                (t_lot["id"], qty_to_reverse, "Hoàn đảo lô (xóa lô chuyển kệ)."),
                (UUID(parent_lot_id) if parent_lot_id else None, qty_to_reverse, "Nhận lại lô từ đảo chuyển kệ.")
            ):
                if lot_id:
                    await session.execute(
                        text(
                            """
                            INSERT INTO inventory_lot_movements (
                                id, lot_id, movement_type, quantity,
                                reference_code, inventory_document_id, note
                            )
                            VALUES (
                                :id, :lot_id, 'ADJUSTMENT', :quantity,
                                :reference_code, :document_id, :note
                            )
                            """
                        ),
                        {
                            "id": uuid4(),
                            "lot_id": lot_id,
                            "quantity": movement_qty,
                            "reference_code": reference_code,
                            "document_id": transfer["id"],
                            "note": note,
                        }
                    )

        # 3. Get old quantities before the physical inventory level transfer
        from_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=to_location_id,
        )
        from_old_qty = int(from_level["onHandQuantity"] or 0) if from_level else 0

        to_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=from_location_id,
        )
        to_old_qty = int(to_level["onHandQuantity"] or 0) if to_level else 0

        # 4. Reverse the inventory level quantity
        try:
            await inventory_repo.transfer_inventory_level_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                from_location_id=to_location_id,
                to_location_id=from_location_id,
                quantity=quantity,
                average_unit_cost=None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        # 5. Reverse the sellable variant/product stock_quantity if purposes changed
        source_sellable = str(line.get("fromLocationPurpose") or "STORAGE").upper() in SELLABLE_LOCATION_PURPOSES
        target_sellable = str(line.get("toLocationPurpose") or "STORAGE").upper() in SELLABLE_LOCATION_PURPOSES
        if source_sellable != target_sellable:
            inventory_row = (
                await inventory_repo.get_variant_inventory_for_update(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                )
                if variant_id
                else await inventory_repo.get_product_stock_for_update(session, product_id)
            )
            if not inventory_row:
                raise HTTPException(status_code=404, detail="Không tìm thấy tồn bán được của sản phẩm.")
            reversal_sellable_delta = quantity if source_sellable else -quantity
            new_sellable_quantity = int(inventory_row["stock_quantity"] or 0) + reversal_sellable_delta
            if new_sellable_quantity < 0:
                raise HTTPException(status_code=409, detail="Tồn bán được không đủ để đảo chuyển trạng thái.")
            if variant_id:
                await inventory_repo.update_variant_stock(
                    session,
                    variant_id=variant_id,
                    quantity=new_sellable_quantity,
                )
                touched_products.add(product_id)
            else:
                await inventory_repo.update_product_stock(
                    session,
                    product_id=product_id,
                    quantity=new_sellable_quantity,
                )

        # 6. Insert new reverse inventory adjustment logs
        await inventory_repo.insert_inventory_adjustment_log(
            session,
            log_id=uuid4(),
            product_id=product_id,
            variant_id=variant_id,
            old_quantity=from_old_qty,
            new_quantity=from_old_qty - quantity,
            delta=-quantity,
            transaction_type="ADJUSTMENT",
            reference_code=reference_code,
            reason="REVERSE_TRANSFER_OUT",
            note=f"Đảo chuyển kệ: Xuất khỏi kệ đích {line.get('toLocationCode')}",
            supplier_name=None,
            unit_cost=None,
            location_code=line.get("toLocationCode"),
            location_name=line.get("toLocationName"),
        )
        await inventory_repo.insert_inventory_adjustment_log(
            session,
            log_id=uuid4(),
            product_id=product_id,
            variant_id=variant_id,
            old_quantity=to_old_qty,
            new_quantity=to_old_qty + quantity,
            delta=quantity,
            transaction_type="ADJUSTMENT",
            reference_code=reference_code,
            reason="REVERSE_TRANSFER_IN",
            note=f"Đảo chuyển kệ: Nhập lại vào kệ nguồn {line.get('fromLocationCode')}",
            supplier_name=None,
            unit_cost=None,
            location_code=line.get("fromLocationCode"),
            location_name=line.get("fromLocationName"),
        )

    for product_id in touched_products:
        await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=transfer["id"],
        status="REVERSED",
        note="Đảo phiếu điều chuyển kệ",
        actor_id=actor_id,
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": "REVERSED"}


async def create_inventory_internal_hold(
    session: AsyncSession,
    payload: InventoryInternalHoldPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    existing_adjustment = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    existing_transfer = await inventory_repo.get_inventory_transfer_for_update(session, reference_code)
    existing_hold = await inventory_repo.get_inventory_internal_hold_for_update(session, reference_code)
    if existing_receipt or existing_count or existing_adjustment or existing_transfer or existing_hold:
        raise HTTPException(status_code=409, detail="Mã phiếu khóa/mở khóa tồn đã tồn tại.")

    hold_type = payload.holdType.strip().upper()
    reason = payload.reason.strip()
    if hold_type not in {"QC_HOLD", "CLAIM_HOLD", "INTERNAL_HOLD"}:
        raise HTTPException(status_code=400, detail="Loại giữ nội bộ không hợp lệ.")
    if not reason:
        raise HTTPException(status_code=400, detail="Phiếu giữ nội bộ phải có lý do.")

    document_id = uuid4()
    await inventory_repo.insert_inventory_internal_hold_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        hold_type=hold_type,
        reason=reason,
        note=payload.note,
        created_by=current_user_id,
    )
    seen_keys: set[tuple[str, str, str]] = set()
    total_quantity = 0
    for index, line in enumerate(payload.lines, start=1):
        product_id = line.productId
        variant_id = line.variantId
        location = await _get_active_inventory_location(session, line.locationId, f"Dòng {index}: kệ giữ")
        key = (str(product_id), str(variant_id or ""), str(location["id"]))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể và kệ bị trùng trong phiếu giữ.")
        seen_keys.add(key)
        if variant_id:
            current_row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        else:
            current_row = await inventory_repo.get_product_stock_for_update(session, product_id)
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để giữ.")
        stock_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
        )
        on_hand_quantity = int(stock_level["onHandQuantity"] or 0) if stock_level else 0
        reserved_quantity = int(stock_level["reservedQuantity"] or 0) if stock_level else 0
        available_quantity = max(on_hand_quantity - reserved_quantity, 0)
        quantity = int(line.quantity)
        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: Số lượng giữ kho phải lớn hơn 0."
            )
        if available_quantity < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Dòng {index}: kệ {location.get('code')} không đủ tồn khả dụng để lập phiếu giữ. Cần {quantity}, khả dụng {available_quantity}.",
            )

        imeis = _clean_imeis(line.imeis or [])
        serial_numbers = _clean_serial_numbers(line.serialNumbers or [])
        if len(set(imeis)) != len(imeis):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách IMEI bị trùng.")
        if len(set(serial_numbers)) != len(serial_numbers):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách serial bị trùng.")
        _validate_imei_format(imeis)
        _validate_serial_number_format(serial_numbers)

        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        if _policy_tracks_imei(policy_row) and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm quản lý IMEI nên số IMEI phải bằng số lượng giữ.")

        if _policy_tracks_serial_number(policy_row) and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm quản lý serial nên số serial phải bằng số lượng giữ.")

        await validate_identifier_pairs(
            session,
            product_id=product_id,
            variant_id=variant_id,
            imeis=imeis,
            serial_numbers=serial_numbers,
            line_index=index,
        )

        if _policy_tracks_imei(policy_row):
            imei_statuses = await inventory_repo.list_imei_statuses_by_location(session, product_id, variant_id, location["id"], imeis)
            if len(imei_statuses) != len(imeis):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: Một hoặc nhiều IMEI không có sẵn tại kệ để giữ.")
        if _policy_tracks_serial_number(policy_row):
            serial_statuses = await inventory_repo.list_serial_statuses_by_location(session, product_id, variant_id, location["id"], serial_numbers)
            if len(serial_statuses) != len(serial_numbers):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: Một hoặc nhiều số serial không có sẵn tại kệ để giữ.")

        await inventory_repo.insert_inventory_internal_hold_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            quantity=quantity,
            hold_type=hold_type,
            reason=reason,
            note=line.note,
            imeis=imeis,
            serial_numbers=serial_numbers,
        )
        total_quantity += quantity

    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "holdType": hold_type,
        "lineCount": len(payload.lines),
        "totalQuantity": total_quantity,
    }


async def update_inventory_internal_hold_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryInternalHoldStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "COMPLETED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu giữ nội bộ không hợp lệ.")
    document = await inventory_repo.get_inventory_internal_hold_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu giữ nội bộ.")
    current_status = str(document["status"])
    allowed_transitions = {
        "DRAFT": {"APPROVED", "CANCELLED"},
        "APPROVED": {"COMPLETED"},
    }
    if target_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Không thể chuyển phiếu giữ nội bộ từ {current_status} sang {target_status}.",
        )

    lines = await inventory_repo.list_inventory_internal_hold_lines(session, document["id"])
    posted_lines: list[dict] = []
    if target_status in {"APPROVED", "COMPLETED"}:
        delta_sign = 1 if target_status == "APPROVED" else -1
        action_label = "khóa" if target_status == "APPROVED" else "mở khóa"
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            location_id = line["locationId"]
            quantity = int(line["quantity"] or 0)
            stock_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
            )
            on_hand_quantity = int(stock_level["onHandQuantity"] or 0) if stock_level else 0
            reserved_quantity = int(stock_level["reservedQuantity"] or 0) if stock_level else 0
            if target_status == "APPROVED" and max(on_hand_quantity - reserved_quantity, 0) < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: kệ {line.get('locationCode')} không đủ tồn khả dụng để duyệt giữ. Cần {quantity}, khả dụng {max(on_hand_quantity - reserved_quantity, 0)}.",
                )
            if target_status == "COMPLETED" and reserved_quantity < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: số đang giữ tại kệ {line.get('locationCode')} nhỏ hơn số cần mở khóa.",
                )
            adjusted = await inventory_repo.adjust_inventory_level_reserved_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
                delta=delta_sign * quantity,
            )
            if not adjusted:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: không thể {action_label} tồn tại kệ {line.get('locationCode')}.",
                )

            imeis = line.get("imeis") or []
            serial_numbers = line.get("serialNumbers") or []

            if target_status == "APPROVED":
                locked_imeis, locked_serials = await inventory_repo.lock_identifiers_for_hold(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=location_id,
                    imeis=imeis,
                    serial_numbers=serial_numbers,
                )
                policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
                tracks_imei = _policy_tracks_imei(policy_row)
                tracks_serial = _policy_tracks_serial_number(policy_row)
                if tracks_imei and len(locked_imeis) != len(imeis):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dòng {index}: Một hoặc nhiều IMEI không còn sẵn ở trạng thái IN_STOCK tại kệ để khóa giữ.",
                    )
                if tracks_serial and len(locked_serials) != len(serial_numbers):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dòng {index}: Một hoặc nhiều serial không còn sẵn ở trạng thái IN_STOCK tại kệ để khóa giữ.",
                    )
            elif target_status == "COMPLETED":
                await inventory_repo.unlock_identifiers_for_hold(
                    session,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=location_id,
                    imeis=imeis,
                    serial_numbers=serial_numbers,
                )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=on_hand_quantity,
                new_quantity=on_hand_quantity,
                delta=0,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason=line.get("holdType") or document.get("holdType") or "INTERNAL_HOLD",
                note=line.get("note") or payload.note or f"{action_label.capitalize()} tồn nội bộ.",
                supplier_name=None,
                unit_cost=None,
                location_code=line.get("locationCode"),
                location_name=line.get("locationName"),
            )
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "locationId": str(location_id),
                    "quantity": quantity,
                    "reservedQuantity": int(adjusted["reservedQuantity"] or 0),
                }
            )

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=document["id"],
        status=target_status,
        note=payload.note,
        actor_id=current_user_id,
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": target_status,
        "holdType": document.get("holdType"),
        "postedLineCount": len(posted_lines),
        "lines": posted_lines,
    }
async def create_inventory_cost_adjustment(
    session: AsyncSession,
    payload: InventoryCostAdjustmentPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    existing_adjustment = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    existing_transfer = await inventory_repo.get_inventory_transfer_for_update(session, reference_code)
    existing_hold = await inventory_repo.get_inventory_internal_hold_for_update(session, reference_code)
    existing_disposal = await inventory_repo.get_inventory_disposal_for_update(session, reference_code)
    existing_cost = await inventory_repo.get_inventory_cost_adjustment_for_update(session, reference_code)
    if existing_receipt or existing_count or existing_adjustment or existing_transfer or existing_hold or existing_disposal or existing_cost:
        raise HTTPException(status_code=409, detail="Mã phiếu điều chỉnh giá vốn đã tồn tại.")

    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Phiếu điều chỉnh giá vốn phải có lý do.")
    document_id = uuid4()
    await inventory_repo.insert_inventory_cost_adjustment_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        reason=reason,
        note=payload.note,
        created_by=current_user_id,
    )
    seen_lines = set()
    for index, line in enumerate(payload.lines, start=1):
        line_key = (str(line.productId), str(line.variantId or ""), str(line.locationId))
        if line_key in seen_lines:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể và kệ bị trùng trong phiếu điều chỉnh.")
        seen_lines.add(line_key)
        location = await inventory_repo.get_inventory_location_by_id(session, line.locationId)
        if not location or location.get("status") != "ACTIVE":
            raise HTTPException(status_code=400, detail=f"Dòng {index}: kệ điều chỉnh không hợp lệ.")
        stock_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=line.productId,
            variant_id=line.variantId,
            location_id=line.locationId,
        )
        if not stock_level or int(stock_level.get("onHandQuantity") or 0) <= 0:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: không có tồn tại kệ để điều chỉnh giá vốn.")
        if not await inventory_repo.get_product_inventory_policy(session, line.productId):
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm.")
        new_avg_cost = float(line.newAverageUnitCost or 0)
        if new_avg_cost <= 0:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: Giá vốn mới phải lớn hơn 0.")
        current_lots = await inventory_repo.list_active_lots_for_cost_adjustment(
            session,
            product_id=line.productId,
            variant_id=line.variantId,
            location_id=line.locationId,
        )
        lot_map = {str(lot["id"]): lot for lot in current_lots}
        lot_costs: list[dict] = []
        seen_lots = set()
        for lot_item in line.lotCosts:
            lot_id = str(lot_item.lotId)
            if lot_id in seen_lots:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: lô bị trùng trong danh sách điều chỉnh giá vốn.")
            seen_lots.add(lot_id)
            lot_id = str(lot_item.lotId)
            if lot_id not in lot_map:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: lô điều chỉnh không thuộc tồn tại kệ này.")
            lot = lot_map[lot_id]
            new_u_cost = float(lot_item.newUnitCost or 0)
            if new_u_cost <= 0:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: Giá vốn lô hàng mới phải lớn hơn 0.")
            lot_costs.append(
                {
                    "lotId": lot_id,
                    "lotCode": lot.get("lotCode"),
                    "remainingQuantity": int(lot.get("remainingQuantity") or 0),
                    "oldUnitCost": float(lot.get("unitCost") or 0),
                    "newUnitCost": new_u_cost,
                }
            )
        if not lot_costs:
            lot_costs = [
                {
                    "lotId": str(lot["id"]),
                    "lotCode": lot.get("lotCode"),
                    "remainingQuantity": int(lot.get("remainingQuantity") or 0),
                    "oldUnitCost": float(lot.get("unitCost") or 0),
                    "newUnitCost": float(line.newAverageUnitCost or 0),
                }
                for lot in current_lots
            ]
        await inventory_repo.insert_inventory_cost_adjustment_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=line.productId,
            variant_id=line.variantId,
            location_id=line.locationId,
            on_hand_quantity=int(stock_level.get("onHandQuantity") or 0),
            old_average_unit_cost=float(stock_level.get("averageUnitCost") or 0),
            new_average_unit_cost=float(line.newAverageUnitCost or 0),
            lot_costs=lot_costs,
            note=line.note,
        )
    await session.commit()
    rows = await inventory_repo.list_inventory_cost_adjustments(session, reference_code)
    return rows[0] if rows else {"referenceCode": reference_code, "status": "DRAFT"}


async def update_inventory_cost_adjustment_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryCostAdjustmentStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "COMPLETED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu điều chỉnh giá vốn không hợp lệ.")
    document = await inventory_repo.get_inventory_cost_adjustment_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu điều chỉnh giá vốn.")
    current_status = str(document["status"])
    allowed_transitions = {"DRAFT": {"APPROVED", "CANCELLED"}, "APPROVED": {"COMPLETED", "CANCELLED"}}
    if target_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(status_code=400, detail=f"Không thể chuyển phiếu điều chỉnh giá vốn từ {current_status} sang {target_status}.")

    lines = await inventory_repo.list_inventory_cost_adjustment_lines(session, document["id"])
    posted_lines: list[dict] = []
    if target_status == "COMPLETED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            location_id = line["locationId"]
            stock_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
            )
            if not stock_level:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: không còn tồn tại kệ để điều chỉnh giá vốn.")
            on_hand_quantity = int(stock_level.get("onHandQuantity") or 0)
            if on_hand_quantity != int(line.get("onHandQuantity") or 0):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: tồn tại kệ đã thay đổi, cần lập lại phiếu giá vốn.")
            new_average_cost = float(line.get("newAverageUnitCost") or 0)
            if new_average_cost <= 0:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: Giá vốn mới phải lớn hơn 0.")
            updated_level = await inventory_repo.update_inventory_level_average_unit_cost(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
                new_average_unit_cost=new_average_cost,
            )
            if not updated_level:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: không cập nhật được giá vốn kệ.")
            current_lots = await inventory_repo.list_active_lots_for_cost_adjustment(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
            )
            lot_map = {str(lot["id"]): lot for lot in current_lots}
            applied_lots: list[dict] = []
            for lot_item in line.get("lotCosts") or []:
                lot_id = str(lot_item.get("lotId") or "")
                if lot_id not in lot_map:
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: lô điều chỉnh không còn tồn tại tại kệ.")
                old_lot = lot_map[lot_id]
                new_unit_cost = float(lot_item.get("newUnitCost") or 0)
                if new_unit_cost <= 0:
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: Giá vốn lô hàng mới phải lớn hơn 0.")
                updated_lot = await inventory_repo.update_inventory_lot_unit_cost(
                    session,
                    lot_id=UUID(lot_id),
                    new_unit_cost=new_unit_cost,
                )
                applied_lots.append(
                    {
                        "lotId": lot_id,
                        "lotCode": old_lot.get("lotCode"),
                        "remainingQuantity": int(old_lot.get("remainingQuantity") or 0),
                        "oldUnitCost": float(old_lot.get("unitCost") or 0),
                        "newUnitCost": float(updated_lot.get("unitCost") or new_unit_cost) if updated_lot else new_unit_cost,
                    }
                )
            await inventory_repo.update_inventory_cost_adjustment_line_applied_lots(
                session,
                line_id=line["id"],
                applied_lots=applied_lots,
            )
            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=on_hand_quantity,
                new_quantity=on_hand_quantity,
                delta=0,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason="COST_ADJUSTMENT",
                note=payload.note or line.get("note") or document.get("reason"),
                supplier_name=None,
                unit_cost=new_average_cost,
                location_code=stock_level.get("locationCode"),
                location_name=stock_level.get("locationName"),
            )
            posted_lines.append({**line, "newAverageUnitCost": new_average_cost, "appliedLots": applied_lots})

    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=document["id"],
        status=target_status,
        note=payload.note,
        actor_id=current_user_id,
    )
    await session.commit()
    rows = await inventory_repo.list_inventory_cost_adjustments(session, reference_code)
    result = rows[0] if rows else {**document, "status": target_status}
    return {**result, "postedLineCount": len(posted_lines), "postedLines": posted_lines}


async def create_inventory_disposal(
    session: AsyncSession,
    payload: InventoryDisposalPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    existing_count = await inventory_repo.get_inventory_stock_count_for_update(session, reference_code)
    existing_adjustment = await inventory_repo.get_inventory_adjustment_for_update(session, reference_code)
    existing_transfer = await inventory_repo.get_inventory_transfer_for_update(session, reference_code)
    existing_hold = await inventory_repo.get_inventory_internal_hold_for_update(session, reference_code)
    existing_disposal = await inventory_repo.get_inventory_disposal_for_update(session, reference_code)
    if existing_receipt or existing_count or existing_adjustment or existing_transfer or existing_hold or existing_disposal:
        raise HTTPException(status_code=409, detail="Mã phiếu xử lý tồn đã tồn tại.")

    disposition_type = payload.dispositionType.strip().upper()
    if disposition_type not in DISPOSAL_TYPES:
        raise HTTPException(status_code=400, detail="Loại xử lý tồn không hợp lệ.")
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Phiếu xử lý tồn phải có lý do.")

    document_id = uuid4()
    await inventory_repo.insert_inventory_disposal_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        disposition_type=disposition_type,
        reason=reason,
        note=payload.note,
        partner_name=(payload.partnerName or "").strip() or None,
        recovery_value=payload.recoveryValue,
        created_by=current_user_id,
    )
    seen_keys: set[tuple[str, str, str]] = set()
    total_quantity = 0
    for index, line in enumerate(payload.lines, start=1):
        product_id = line.productId
        variant_id = line.variantId
        location = await _get_active_inventory_location(session, line.locationId, f"Dòng {index}: kệ xử lý")
        key = (str(product_id), str(variant_id or ""), str(location["id"]))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể và kệ bị trùng trong phiếu xử lý.")
        seen_keys.add(key)
        current_row = (
            await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
            if variant_id
            else await inventory_repo.get_product_stock_for_update(session, product_id)
        )
        if not current_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm/biến thể để xử lý.")
        stock_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
        )
        available_quantity = 0
        if stock_level:
            available_quantity = int(stock_level["onHandQuantity"] or 0) - int(stock_level["reservedQuantity"] or 0)
        quantity = int(line.quantity)
        if quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: Số lượng thanh lý phải lớn hơn 0."
            )
        if available_quantity < quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Dòng {index}: kệ {location.get('code')} không đủ tồn khả dụng để xử lý. Cần {quantity}, khả dụng {max(available_quantity, 0)}.",
            )

        imeis = _clean_imeis(line.imeis)
        serial_numbers = _clean_serial_numbers(line.serialNumbers)
        if len(set(imeis)) != len(imeis):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách IMEI bị trùng.")
        if len(set(serial_numbers)) != len(serial_numbers):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách serial bị trùng.")
        _validate_imei_format(imeis)
        _validate_serial_number_format(serial_numbers)
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        tracks_imei = _policy_tracks_imei(policy_row)
        tracks_serial = _policy_tracks_serial_number(policy_row)
        if tracks_imei and not tracks_serial and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm quản lý IMEI nên số IMEI phải bằng số lượng xử lý.")
        if tracks_serial and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm quản lý serial nên số serial phải bằng số lượng xử lý.")
        await validate_identifier_pairs(
            session,
            product_id=product_id,
            variant_id=variant_id,
            imeis=imeis,
            serial_numbers=serial_numbers,
            line_index=index,
        )
        await inventory_repo.insert_inventory_disposal_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=location["id"],
            quantity=quantity,
            disposition_type=disposition_type,
            reason=reason,
            imeis=imeis,
            serial_numbers=serial_numbers,
            note=line.note,
        )
        total_quantity += quantity

    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "dispositionType": disposition_type,
        "lineCount": len(payload.lines),
        "totalQuantity": total_quantity,
    }


async def update_inventory_disposal_status(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryDisposalStatusPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    target_status = payload.status.upper()
    if target_status not in {"APPROVED", "COMPLETED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phiếu xử lý tồn không hợp lệ.")
    document = await inventory_repo.get_inventory_disposal_for_update(session, reference_code)
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xử lý tồn.")
    current_status = str(document["status"])
    allowed_transitions = {
        "DRAFT": {"APPROVED", "CANCELLED"},
        "APPROVED": {"COMPLETED", "CANCELLED"},
    }
    if target_status not in allowed_transitions.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Không thể chuyển phiếu xử lý tồn từ {current_status} sang {target_status}.",
        )

    lines = await inventory_repo.list_inventory_disposal_lines(session, document["id"])
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    if target_status == "COMPLETED":
        for index, line in enumerate(lines, start=1):
            product_id = line["productId"]
            variant_id = line["variantId"]
            location_id = line["locationId"]
            quantity = int(line["quantity"] or 0)
            disposition_type = str(line.get("dispositionType") or document.get("dispositionType") or "").upper()
            if disposition_type not in DISPOSAL_TYPES:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: loại xử lý tồn không hợp lệ.")
            stock_level = await inventory_repo.get_inventory_level_for_transfer(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
            )
            available_quantity = 0
            if stock_level:
                available_quantity = int(stock_level["onHandQuantity"] or 0) - int(stock_level["reservedQuantity"] or 0)
            if available_quantity < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: kệ {line.get('locationCode')} không đủ tồn khả dụng để hoàn tất xử lý. Cần {quantity}, khả dụng {max(available_quantity, 0)}.",
                )
            imeis = [str(item).strip() for item in (line.get("imeis") or []) if str(item).strip()]
            serial_numbers = [str(item).strip().upper() for item in (line.get("serialNumbers") or []) if str(item).strip()]
            moved_imeis = await inventory_repo.dispose_product_imeis(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
                imeis=imeis,
                target_status=disposition_type,
            )
            missing_imeis = sorted(set(imeis) - set(moved_imeis))
            if missing_imeis:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: IMEI không còn ở kệ hoặc không ở trạng thái có thể xử lý: {', '.join(missing_imeis[:5])}.",
                )
            moved_serial_numbers = await inventory_repo.dispose_product_serial_numbers(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
                serial_numbers=serial_numbers,
                target_status=disposition_type,
            )
            missing_serial_numbers = sorted(set(serial_numbers) - set(moved_serial_numbers))
            if missing_serial_numbers:
                raise HTTPException(
                    status_code=409,
                    detail=f"Dòng {index}: serial không còn ở kệ hoặc không ở trạng thái có thể xử lý: {', '.join(missing_serial_numbers[:5])}.",
                )
            try:
                consumed_lots = await inventory_repo.consume_inventory_lots_fifo(
                    session,
                    document_id=document["id"],
                    reference_code=reference_code,
                    product_id=product_id,
                    variant_id=variant_id,
                    location_id=location_id,
                    quantity=quantity,
                    movement_note=f"Xử lý tồn cuối: {disposition_type}.",
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: {exc}") from exc

            source_old_quantity = int(stock_level["onHandQuantity"] or 0)
            adjusted_level = await inventory_repo.decrement_inventory_level_quantity(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=location_id,
                quantity=quantity,
            )
            if not adjusted_level:
                raise HTTPException(status_code=409, detail=f"Dòng {index}: không thể giảm tồn tại kệ {line.get('locationCode')}.")

            source_sellable = str(line.get("locationPurpose") or "STORAGE").upper() in SELLABLE_LOCATION_PURPOSES
            new_sellable_quantity = None
            if source_sellable:
                inventory_row = (
                    await inventory_repo.get_variant_inventory_for_update(
                        session,
                        product_id=product_id,
                        variant_id=variant_id,
                    )
                    if variant_id
                    else await inventory_repo.get_product_stock_for_update(session, product_id)
                )
                if not inventory_row:
                    raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy tồn bán được của sản phẩm.")
                new_sellable_quantity = int(inventory_row["stock_quantity"] or 0) - quantity
                if new_sellable_quantity < 0:
                    raise HTTPException(status_code=409, detail=f"Dòng {index}: tồn bán được không đủ để xử lý.")
                if variant_id:
                    await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_sellable_quantity)
                    touched_products.add(product_id)
                else:
                    await inventory_repo.update_product_stock(session, product_id=product_id, quantity=new_sellable_quantity)

            await inventory_repo.insert_inventory_adjustment_log(
                session,
                log_id=uuid4(),
                product_id=product_id,
                variant_id=variant_id,
                old_quantity=source_old_quantity,
                new_quantity=source_old_quantity - quantity,
                delta=-quantity,
                transaction_type="ADJUSTMENT",
                reference_code=reference_code,
                reason=disposition_type,
                note=line.get("note") or payload.note or f"Xử lý tồn cuối: {disposition_type}.",
                supplier_name=document.get("partnerName"),
                unit_cost=stock_level.get("averageUnitCost") if stock_level else None,
                location_code=line.get("locationCode"),
                location_name=line.get("locationName"),
            )
            posted_lines.append(
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id) if variant_id else None,
                    "locationId": str(location_id),
                    "quantity": quantity,
                    "dispositionType": disposition_type,
                    "imeis": moved_imeis,
                    "serialNumbers": moved_serial_numbers,
                    "consumedLots": consumed_lots,
                    "sellableQuantity": new_sellable_quantity,
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
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": target_status,
        "dispositionType": document.get("dispositionType"),
        "postedLineCount": len(posted_lines),
        "lines": posted_lines,
    }


async def adjust_product_inventory(
    session: AsyncSession,
    product_id: UUID,
    payload: InventoryAdjustmentPayload,
    idempotency_key: str | None = None,
) -> dict:
    raise HTTPException(
        status_code=400,
        detail="Kh\u00f4ng \u0111\u01b0\u1ee3c ph\u00e9p \u0111i\u1ec1u ch\u1ec9nh t\u1ed3n kho tr\u1ef1c ti\u1ebfp. Vui l\u00f2ng s\u1eed d\u1ee5ng phi\u1ebfu ki\u1ec3m k\u00ea ho\u1eb7c phi\u1ebfu \u0111i\u1ec1u ch\u1ec9nh kho chu\u1ea9n."
    )
    pass

    row = await inventory_repo.get_variant_inventory_for_update(
        session,
        product_id=product_id,
        variant_id=actual_variant_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy biến thể sản phẩm.")

    old_quantity = int(row["stock_quantity"] or 0)
    new_quantity = payload.quantity if payload.quantity is not None else old_quantity + int(payload.delta or 0)
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Số lượng tồn kho không được âm.")
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


async def list_products_due_for_cycle_count(
    session: AsyncSession,
    *,
    due_only: bool = False,
    search: str = "",
) -> list[dict]:
    return await inventory_repo.list_products_due_for_cycle_count(
        session,
        due_only=due_only,
        search=search,
    )
