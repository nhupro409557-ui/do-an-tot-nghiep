from .common import *

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
            return existing

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
        existing_line_ids = {UUID(str(l["id"])) for l in existing_lines}
        for l_payload in payload.lines:
            if l_payload.lineId not in existing_line_ids:
                raise HTTPException(status_code=400, detail=f"Dòng ID {l_payload.lineId} không thuộc phiếu nhập này.")
            await inventory_repo.update_inventory_receipt_line_quality(
                session,
                line_id=l_payload.lineId,
                passed_quantity=l_payload.passedQuantity,
                failed_quantity=l_payload.failedQuantity,
                notes=l_payload.notes,
                action_type=l_payload.actionType,
                images=l_payload.images,
                checked_by=current_user_id,
            )
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
) -> None:
    seen_keys: set[tuple[str, str]] = set()
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
        key = (str(product_id), str(actual_variant_id))
        if key in seen_keys:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm/biến thể bị trùng trong phiếu nhập.")
        seen_keys.add(key)

        quantity = int(line.quantity)
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        tracks_imei = _policy_tracks_imei(policy_row)
        tracks_serial_number = _policy_tracks_serial_number(policy_row)
        line_location = await _resolve_receipt_line_location(session, line, location_id, index)
        if quarantine:
            _ensure_receipt_quarantine_location(line_location, index)
        line_location_id = line_location["id"]
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
            unit_cost=line.unitCost,
            note=line.note,
            imeis=[],
            tracks_imei=tracks_imei,
            serial_numbers=[],
            tracks_serial_number=tracks_serial_number,
            storage_location_code=storage_location_code or None,
            storage_location_name=storage_location_name or None,
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
            }
        )
