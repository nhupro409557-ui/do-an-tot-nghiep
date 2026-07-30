from .common import *
from app.infrastructure.database.repositories import purchase_order_repo

async def create_inventory_receipt(
    session: AsyncSession,
    payload: InventoryReceiptPayload,
    idempotency_key: str | None = None,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = payload.referenceCode.strip()
    idem_key = (idempotency_key or reference_code).strip()
    if idem_key:
        await inventory_repo.delete_old_inventory_idempotency(session)
        existing = await inventory_repo.get_inventory_idempotency_response(session, idem_key)
        if existing:
            existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
            if existing_receipt:
                return existing
            await inventory_repo.delete_inventory_idempotency_response(session, idem_key)

    requested_status = payload.status if payload.status in RECEIPT_STATUSES else "DRAFT"
    if requested_status != "DRAFT":
        raise HTTPException(status_code=400, detail="Phiếu nhập mới phải bắt đầu ở trạng thái Nháp.")
    receipt_reason_code = str(payload.receiptReasonCode or "NK_MUA").strip().upper()
    if receipt_reason_code not in INVENTORY_RECEIPT_REASONS:
        raise HTTPException(status_code=400, detail="Lý do nhập kho không hợp lệ.")
    if receipt_reason_code == "NK_KHAC" and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="Nhập khác phải ghi rõ lý do trong ghi chú chung.")
    existing_receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if existing_receipt:
        raise HTTPException(status_code=409, detail="Mã phiếu nhập đã tồn tại.")

    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or "MAIN").strip() or "MAIN",
        name=(payload.locationName or "Kho chính").strip() or "Kho chính",
    )
    receipt_metadata = _receipt_metadata_from_payload(payload)
    document_id = uuid4()
    await inventory_repo.insert_inventory_receipt_document(
        session,
        document_id=document_id,
        reference_code=reference_code,
        status=requested_status,
        reason=receipt_reason_code,
        supplier_name=payload.supplierName,
        note=payload.note,
        location_id=location["id"],
        created_by=current_user_id,
        metadata=receipt_metadata,
    )

    prepared_lines: list[dict] = []
    await _validate_and_store_receipt_lines(
        session,
        document_id,
        location["id"],
        payload.lines,
        prepared_lines,
        quarantine=bool(receipt_metadata.get("quarantine")),
        purchase_order_id=payload.purchaseOrderId,
        supplier_id=payload.supplierId,
        discount_amount=float(payload.discountAmount or 0),
        shipping_fee=float(payload.shippingFee or 0),
    )

    response_payload = {
        "ok": True,
        "referenceCode": reference_code,
        "status": requested_status,
        "lineCount": len(prepared_lines),
        "postedLineCount": 0,
        "lines": prepared_lines,
    }
    if idem_key:
        await inventory_repo.insert_inventory_idempotency_response(
            session,
            key=idem_key,
            product_id=payload.lines[0].productId,
            response_payload=response_payload,
        )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="created",
        reference_code=reference_code,
        metadata={
            "status": requested_status,
            "reason": receipt_reason_code,
            "metadata": receipt_metadata,
            "lineCount": len(prepared_lines),
            "lines": prepared_lines,
        },
    )
    await session.commit()
    return response_payload


async def update_inventory_receipt(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptPayload,
    current_user_id: UUID | None = None,
    current_role_code: str | None = None,
) -> dict:
    reference_code = reference_code.strip()
    payload_reference_code = payload.referenceCode.strip()
    if payload_reference_code and payload_reference_code != reference_code:
        raise HTTPException(status_code=400, detail="Không được đổi mã phiếu nhập khi chỉnh sửa.")

    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt.get("posted_at") or receipt["status"] not in RECEIPT_EDITABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Chỉ có thể chỉnh sửa phiếu nhập chưa hoàn tất quy trình.")
    if receipt["status"] in {"PENDING_APPROVAL", "PENDING_SHORTAGE_APPROVAL", "APPROVED"}:
        _ensure_super_admin_inventory_action(current_role_code, "trả phiếu nhập đã gửi duyệt về nháp để chỉnh sửa")
    previous_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    await inventory_repo.release_pending_inbound_identifiers(session, reference_code)

    receipt_reason_code = str(payload.receiptReasonCode or receipt.get("reason") or "NK_MUA").strip().upper()
    if receipt_reason_code not in INVENTORY_RECEIPT_REASONS:
        raise HTTPException(status_code=400, detail="Lý do nhập kho không hợp lệ.")
    if receipt_reason_code == "NK_KHAC" and not (payload.note or "").strip():
        raise HTTPException(status_code=400, detail="Nhập khác phải ghi rõ lý do trong ghi chú chung.")

    location = await inventory_repo.ensure_inventory_location(
        session,
        code=(payload.locationCode or receipt.get("locationCode") or "MAIN").strip() or "MAIN",
        name=(payload.locationName or receipt.get("locationName") or "Kho chính").strip() or "Kho chính",
    )
    receipt_metadata = _receipt_metadata_from_payload(payload)
    await inventory_repo.update_inventory_receipt_document(
        session,
        document_id=receipt["id"],
        reason=receipt_reason_code,
        supplier_name=payload.supplierName,
        note=payload.note,
        location_id=location["id"],
        metadata=receipt_metadata,
    )
    await inventory_repo.delete_inventory_receipt_lines(session, receipt["id"])

    prepared_lines: list[dict] = []
    await _validate_and_store_receipt_lines(
        session,
        receipt["id"],
        location["id"],
        payload.lines,
        prepared_lines,
        quarantine=bool(receipt_metadata.get("quarantine")),
        purchase_order_id=payload.purchaseOrderId,
        supplier_id=payload.supplierId,
        discount_amount=float(payload.discountAmount or 0),
        shipping_fee=float(payload.shippingFee or 0),
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="updated",
        reference_code=reference_code,
        metadata={
            "fromStatus": receipt["status"],
            "toStatus": "DRAFT",
            "reason": receipt_reason_code,
            "metadata": receipt_metadata,
            "previousLines": [
                {
                    "lineId": str(line["id"]),
                    "productId": str(line["productId"]),
                    "variantId": str(line["variantId"]) if line.get("variantId") else None,
                    "quantity": int(line.get("quantity") or 0),
                    "receivedQuantity": int(line.get("receivedQuantity") or 0),
                    "tracksImei": bool(line.get("tracksImei")),
                    "tracksSerialNumber": bool(line.get("tracksSerialNumber")),
                }
                for line in previous_lines
            ],
            "newLines": prepared_lines,
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": "DRAFT",
        "lineCount": len(prepared_lines),
        "postedLineCount": 0,
        "lines": prepared_lines,
    }


async def update_inventory_receipt_quality(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptQualityPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt.get("posted_at") or receipt["status"] in {"COMPLETED", "REVERSED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Không thể cập nhật QC cho phiếu nhập đã kết thúc.")
    quality_status = str(payload.qualityStatus or "PENDING").strip().upper()
    if quality_status not in QUALITY_STATUS_LABELS:
        raise HTTPException(status_code=400, detail="Trạng thái kiểm tra chất lượng không hợp lệ.")
    await inventory_repo.update_inventory_receipt_quality(
        session,
        document_id=receipt["id"],
        quality_status=quality_status,
        quality_note=(payload.qualityNote or "").strip() or None,
        quarantine=bool(payload.quarantine),
        quarantine_location=(payload.quarantineLocation or "").strip() or None,
    )
    if payload.lines:
        existing_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
        existing_by_id = {UUID(str(l["id"])): l for l in existing_lines}
        payload_line_ids = [item.lineId for item in payload.lines]
        if len(set(payload_line_ids)) != len(payload_line_ids):
            raise HTTPException(status_code=400, detail="Danh sách QC có dòng bị trùng.")
        if quality_status in {"PASSED", "FAILED"} and set(payload_line_ids) != set(existing_by_id):
            raise HTTPException(status_code=400, detail="Phải kiểm tra QC đầy đủ tất cả dòng trước khi kết luận.")
        total_failed_quantity = 0
        for l_payload in payload.lines:
            existing_line = existing_by_id.get(l_payload.lineId)
            if not existing_line:
                raise HTTPException(status_code=400, detail=f"Dòng ID {l_payload.lineId} không thuộc phiếu nhập này.")
            received_quantity = int(existing_line.get("receivedQuantity") or 0)
            if received_quantity <= 0:
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: chưa có số lượng thực nhận để kiểm tra QC.")
            if l_payload.passedQuantity + l_payload.failedQuantity != received_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {l_payload.lineId}: số lượng đạt và lỗi phải bằng số lượng thực nhận ({received_quantity}).",
                )
            if l_payload.failedQuantity > 0 and l_payload.actionType in {None, "NONE"}:
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: hàng lỗi phải có hướng xử lý.")
            if l_payload.failedQuantity > 0 and not l_payload.failedLocationId:
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: hàng lỗi phải có kệ cách ly.")
            failed_imeis = _clean_imeis(l_payload.failedImeis)
            failed_serials = _clean_serial_numbers(l_payload.failedSerialNumbers)
            total_failed_quantity += l_payload.failedQuantity
            if existing_line.get("tracksImei") and len(failed_imeis) != l_payload.failedQuantity:
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: số IMEI lỗi phải bằng số lượng lỗi.")
            if existing_line.get("tracksSerialNumber") and len(failed_serials) != l_payload.failedQuantity:
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: số serial lỗi phải bằng số lượng lỗi.")
            if any(value not in (existing_line.get("imeis") or []) for value in failed_imeis):
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: IMEI lỗi không thuộc dòng phiếu.")
            if any(value not in (existing_line.get("serialNumbers") or []) for value in failed_serials):
                raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: serial lỗi không thuộc dòng phiếu.")
            if l_payload.failedLocationId:
                failed_location = await _get_active_inventory_location(session, l_payload.failedLocationId, "Kệ cách ly")
                _ensure_receipt_quarantine_location(failed_location, 1)
            quality_images = []
            for image in l_payload.images:
                if isinstance(image, str):
                    url = image.strip()
                    caption = None
                else:
                    url = str(image.get("url") or "").strip()
                    caption = str(image.get("caption") or "").strip() or None
                if not url:
                    raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: ảnh QC thiếu đường dẫn.")
                if len(url) > 1000:
                    raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: đường dẫn ảnh QC quá dài.")
                if caption and len(caption) > 200:
                    raise HTTPException(status_code=400, detail=f"Dòng {l_payload.lineId}: chú thích ảnh QC tối đa 200 ký tự.")
                quality_images.append({"url": url, "caption": caption})
            await inventory_repo.update_inventory_receipt_line_quality(
                session,
                line_id=l_payload.lineId,
                passed_quantity=l_payload.passedQuantity,
                failed_quantity=l_payload.failedQuantity,
                notes=l_payload.notes,
                action_type=l_payload.actionType,
                images=quality_images,
                checked_by=current_user_id,
                failed_location_id=l_payload.failedLocationId,
                failed_imeis=failed_imeis,
                failed_serial_numbers=failed_serials,
            )
        if quality_status == "PASSED" and total_failed_quantity > 0:
            raise HTTPException(status_code=400, detail="Không thể kết luận QC đạt khi vẫn có hàng lỗi.")
        if quality_status == "FAILED" and total_failed_quantity == 0:
            raise HTTPException(status_code=400, detail="Không thể kết luận QC không đạt khi không có hàng lỗi.")
    elif quality_status in {"PASSED", "FAILED"}:
        raise HTTPException(status_code=400, detail="Phải kiểm tra QC chi tiết tất cả dòng trước khi kết luận.")
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="quality_updated",
        reference_code=reference_code,
        metadata={
            "fromQualityStatus": receipt.get("qualityStatus"),
            "toQualityStatus": quality_status,
            "qualityNote": (payload.qualityNote or "").strip() or None,
            "quarantine": bool(payload.quarantine),
            "quarantineLocation": (payload.quarantineLocation or "").strip() or None,
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "qualityStatus": quality_status,
        "quarantine": bool(payload.quarantine),
    }


async def update_inventory_receipt_attachments(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptAttachmentsPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt["status"] in {"CANCELLED", "REVERSED"}:
        raise HTTPException(status_code=400, detail="Không thể bổ sung chứng từ cho phiếu nhập đã hủy hoặc đã đảo.")

    previous_attachments = receipt.get("metadata", {}).get("attachments") or []
    attachments = _receipt_attachments_from_payload(payload)
    await inventory_repo.update_inventory_receipt_attachments(
        session,
        document_id=receipt["id"],
        attachments=attachments,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="attachments_submitted",
        reference_code=reference_code,
        metadata={
            "fromAttachments": previous_attachments,
            "pendingAttachments": attachments,
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "attachments": previous_attachments,
        "pendingAttachments": attachments,
        "attachmentApprovalStatus": "PENDING",
    }


async def decide_inventory_receipt_attachments(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptAttachmentDecisionPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    metadata = receipt.get("metadata", {}) or {}
    pending_attachments = metadata.get("pendingAttachments") or []
    if not pending_attachments:
        raise HTTPException(status_code=400, detail="Phiếu nhập không có chứng từ đang chờ duyệt.")

    approve = bool(payload.approve)
    note = (payload.note or "").strip() or None
    current_attachments = metadata.get("attachments") or []
    await inventory_repo.decide_inventory_receipt_attachments(
        session,
        document_id=receipt["id"],
        attachments=pending_attachments,
        approve=approve,
        note=note,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="attachments_approved" if approve else "attachments_rejected",
        reference_code=reference_code,
        metadata={
            "fromAttachments": current_attachments,
            "pendingAttachments": pending_attachments,
            "toAttachments": pending_attachments if approve else current_attachments,
            "note": note,
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "attachments": pending_attachments if approve else current_attachments,
        "pendingAttachments": [],
        "attachmentApprovalStatus": "APPROVED" if approve else "REJECTED",
        "attachmentApprovalNote": note,
    }


async def delete_inventory_receipt(
    session: AsyncSession,
    reference_code: str,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt.get("posted_at") or receipt["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ có thể xóa phiếu nhập còn ở trạng thái nháp.")

    previous_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    await inventory_repo.delete_inventory_receipt_lines(session, receipt["id"])
    await inventory_repo.delete_inventory_receipt_document(session, receipt["id"])
    await inventory_repo.delete_inventory_idempotency_response(session, reference_code)
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="deleted",
        reference_code=reference_code,
        metadata={
            "status": receipt["status"],
            "lineCount": len(previous_lines),
            "lines": [
                {
                    "lineId": str(line["id"]),
                    "productId": str(line["productId"]),
                    "variantId": str(line["variantId"]) if line.get("variantId") else None,
                    "quantity": int(line.get("quantity") or 0),
                }
                for line in previous_lines
            ],
        },
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "deleted": True}


async def _validate_and_store_receipt_lines(
    session: AsyncSession,
    document_id: UUID,
    location_id: UUID,
    lines: list,
    prepared_lines: list[dict],
    *,
    quarantine: bool = False,
    purchase_order_id: UUID | None = None,
    supplier_id: UUID | None = None,
    discount_amount: float = 0,
    shipping_fee: float = 0,
) -> None:
    gross_total = sum(int(line.quantity) * float(line.unitCost or 0) for line in lines)
    if discount_amount > gross_total:
        raise HTTPException(status_code=400, detail="Chiết khấu phiếu nhập không được lớn hơn tiền hàng.")
    if gross_total <= 0 and (discount_amount > 0 or shipping_fee > 0):
        raise HTTPException(status_code=400, detail="Không thể phân bổ chiết khấu hoặc phí nhập khi tiền hàng bằng 0.")
    purchase_order = None
    purchase_lines: dict[str, dict] = {}
    if purchase_order_id:
        purchase_order = await purchase_order_repo.get_purchase_order(session, purchase_order_id, for_update=True)
        if not purchase_order:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn mua hàng được liên kết.")
        if purchase_order["status"] not in {"APPROVED", "PARTIALLY_RECEIVED"}:
            raise HTTPException(status_code=400, detail="Chỉ được nhập kho từ đơn mua đã duyệt và còn hàng chưa nhận.")
        if supplier_id and str(purchase_order["supplierId"]) != str(supplier_id):
            raise HTTPException(status_code=400, detail="Nhà cung cấp trên phiếu nhập không khớp đơn mua hàng.")
        purchase_lines = {str(item["id"]): item for item in purchase_order["lines"]}
    seen_keys: set[tuple[str, str, str]] = set()
    purchase_received_by_line: dict[str, int] = {}
    requested_volume_by_location: dict[str, float] = {}
    assigned_skus_by_location: dict[str, set[str]] = {}
    for index, line in enumerate(lines, start=1):
        product_id = line.productId
        actual_variant_id = line.variantId
        product_gate = await inventory_repo.get_product_receipt_eligibility_for_update(session, product_id)
        if not product_gate:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy sản phẩm để nhập kho.")
        product_label = f"{product_gate.get('name') or 'Sản phẩm'} ({product_gate.get('sku') or product_id})"
        product_status = str(product_gate.get("status") or "").upper()
        if product_gate.get("deleted_at") is not None:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: {product_label} đã bị xóa, không được nhập kho.")
        if product_status != "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: {product_label} đang ở trạng thái {product_status or 'không xác định'}, không được nhập kho.",
            )
        if product_gate.get("hidden_by_category") or product_gate.get("hidden_by_brand"):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index}: {product_label} đang bị ẩn theo danh mục hoặc thương hiệu, không được nhập kho.",
            )
        if product_gate.get("has_pending_revision"):
            raise HTTPException(
                status_code=409,
                detail=f"Dòng {index}: {product_label} đang có bản chỉnh sửa chờ duyệt. Vui lòng duyệt hoặc hủy bản chỉnh sửa trước khi nhập kho.",
            )
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
        purchase_line = None
        if purchase_order:
            if not line.purchaseOrderLineId:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: phải chọn dòng đơn mua hàng tương ứng.")
            purchase_line = purchase_lines.get(str(line.purchaseOrderLineId))
            if not purchase_line:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: dòng đơn mua không thuộc đơn đã chọn.")
            if str(purchase_line["productId"]) != str(product_id) or str(purchase_line.get("variantId") or "") != str(actual_variant_id or ""):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể không khớp dòng đơn mua.")
            purchase_line_key = str(line.purchaseOrderLineId)
            accumulated_quantity = purchase_received_by_line.get(purchase_line_key, 0) + quantity
            if accumulated_quantity > int(purchase_line["remainingQuantity"] or 0):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số lượng nhập vượt số còn lại của đơn mua.")
            purchase_received_by_line[purchase_line_key] = accumulated_quantity
            if abs(float(line.unitCost or 0) - float(purchase_line["unitCost"] or 0)) > 0.01:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: đơn giá nhập không khớp đơn mua hàng.")
        quoted_unit_cost = float(line.unitCost or 0)
        allocated_adjustment = 0.0
        line_gross = quantity * quoted_unit_cost
        if gross_total > 0:
            allocated_adjustment = (shipping_fee - discount_amount) * (line_gross / gross_total)
        effective_unit_cost = quoted_unit_cost + (allocated_adjustment / quantity)
        if effective_unit_cost < 0:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: giá vốn sau phân bổ không hợp lệ.")
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        tracks_imei = _policy_tracks_imei(policy_row)
        tracks_serial_number = _policy_tracks_serial_number(policy_row)
        line_location = await _resolve_receipt_line_location(session, line, location_id, index)
        if quarantine:
            _ensure_receipt_quarantine_location(line_location, index)
        line_location_id = line_location["id"]
        key = (str(product_id), str(actual_variant_id), str(line_location_id))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể đã được phân bổ vào kệ này.")
        seen_keys.add(key)
        storage_location_code = str(line_location.get("code") or line.storageLocationCode or "").strip()
        storage_location_name = str(line_location.get("name") or line.storageLocationName or "").strip()
        await _ensure_location_has_receipt_capacity(
            session,
            location_id=line_location_id,
            line_index=index,
            quantity=quantity,
            policy_row=policy_row,
            requested_volume_by_location=requested_volume_by_location,
            product_id=product_id,
            variant_id=actual_variant_id,
            assigned_skus_by_location=assigned_skus_by_location,
        )

        await inventory_repo.insert_inventory_receipt_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=actual_variant_id,
            location_id=line_location_id,
            quantity=quantity,
            unit_cost=effective_unit_cost,
            note=line.note,
            reason=line.reason,
            imeis=[],
            tracks_imei=tracks_imei,
            serial_numbers=[],
            tracks_serial_number=tracks_serial_number,
            storage_location_code=storage_location_code or None,
            storage_location_name=storage_location_name or None,
            purchase_order_line_id=line.purchaseOrderLineId,
            quoted_unit_cost=quoted_unit_cost,
        )
        prepared_lines.append(
            {
                "productId": str(product_id),
                "variantId": str(actual_variant_id),
                "quantity": quantity,
                "imeiCount": 0,
                "tracksImei": tracks_imei,
                "serialNumberCount": 0,
                "tracksSerialNumber": tracks_serial_number,
                "warehouseLocationId": str(line_location_id),
                "storageLocationCode": storage_location_code or None,
                "storageLocationName": storage_location_name or None,
                "purchaseOrderLineId": str(line.purchaseOrderLineId) if line.purchaseOrderLineId else None,
                "quotedUnitCost": quoted_unit_cost,
                "effectiveUnitCost": effective_unit_cost,
            }
        )
