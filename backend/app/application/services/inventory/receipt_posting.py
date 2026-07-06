from .common import *
from app.application.services import account_payable_service

async def _post_inventory_receipt(
    session: AsyncSession,
    document_id: UUID,
    reference_code: str,
    receipt_reason_code: str | None,
    supplier_name: str | None,
    note: str | None,
    location_id: UUID | None,
    location_code: str | None,
    location_name: str | None,
) -> list[dict]:
    document_lines = await inventory_repo.list_inventory_receipt_lines(session, document_id)
    posted_lines: list[dict] = []
    touched_products: set[UUID] = set()
    requested_volume_by_location: dict[str, float] = {}
    assigned_skus_by_location: dict[str, set[str]] = {}

    for index, line in enumerate(document_lines, start=1):
        product_id = line["productId"]
        actual_variant_id = line["variantId"]
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line.get("receivedQuantity") or 0)
        if quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số lượng thực nhận phải lớn hơn 0 trước khi hoàn tất.")
        row = await inventory_repo.get_variant_inventory_for_update(
            session,
            product_id=product_id,
            variant_id=actual_variant_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy biến thể hợp lệ.")

        imeis = _clean_imeis(line.get("imeis") or [])
        secondary_imeis = _clean_imeis(line.get("secondaryImeis") or [])
        all_imeis = imeis + secondary_imeis
        serial_numbers = _clean_serial_numbers(line.get("serialNumbers") or [])
        if tracks_imei and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI phải khớp số lượng thực nhận trước khi hoàn tất.")
        if secondary_imeis and len(secondary_imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI2 phải khớp số lượng thực nhận trước khi hoàn tất.")
        if tracks_serial_number and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: số serial number phải khớp số lượng thực nhận trước khi hoàn tất.")

        imei_statuses = await inventory_repo.list_imei_statuses(session, all_imeis)
        if tracks_imei and (
            len(imei_statuses) != len(all_imeis)
            or any(
                str(item.get("status")) != "PENDING_INBOUND"
                or str(item.get("source_reference")) != reference_code
                for item in imei_statuses
            )
        ):
            raise HTTPException(status_code=409, detail=f"Dòng {index}: IMEI/IMEI2 chưa được giữ chỗ hợp lệ cho phiếu nhập này.")
        serial_statuses = await inventory_repo.list_product_serial_number_statuses(
            session,
            product_id=product_id,
            serial_numbers=serial_numbers,
        )
        if tracks_serial_number and (
            len(serial_statuses) != len(serial_numbers)
            or any(
                str(item.get("status")) != "PENDING_INBOUND"
                or str(item.get("source_reference")) != reference_code
                for item in serial_statuses
            )
        ):
            raise HTTPException(status_code=409, detail=f"Dòng {index}: serial number chưa được giữ chỗ hợp lệ cho phiếu nhập này.")

        line_location_id = line.get("locationId") or location_id
        line_location = None
        if line_location_id:
            line_location = await _get_active_inventory_location(session, line_location_id, f"Dòng {index}: kệ hàng")
            policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
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
            await inventory_repo.post_inventory_level_receipt(
                session,
                product_id=product_id,
                variant_id=actual_variant_id,
                location_id=line_location_id,
                quantity=quantity,
                unit_cost=line.get("unitCost"),
            )
            await inventory_repo.create_inventory_lot_for_receipt(
                session,
                document_id=document_id,
                reference_code=reference_code,
                product_id=product_id,
                variant_id=actual_variant_id,
                location_id=line_location_id,
                quantity=quantity,
                unit_cost=line.get("unitCost"),
            )
            await inventory_repo.assign_identifier_locations_for_receipt_line(
                session,
                product_id=product_id,
                location_id=line_location_id,
                imeis=all_imeis,
                serial_numbers=serial_numbers,
            )
        old_quantity = int(row["stock_quantity"] or 0)
        sellable_receipt = _location_is_sellable(line_location)
        new_quantity = old_quantity + quantity if sellable_receipt else old_quantity
        if sellable_receipt:
            await inventory_repo.update_variant_stock(session, variant_id=actual_variant_id, quantity=new_quantity)
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
            reason=receipt_reason_code or "NK_MUA",
            note=line.get("note") or note,
            supplier_name=supplier_name,
            unit_cost=line.get("unitCost"),
            location_code=line.get("storageLocationCode") or location_code or "MAIN",
            location_name=line.get("storageLocationName") or location_name or "Kho chính",
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
                "secondaryImeiCount": len(secondary_imeis),
                "tracksImei": tracks_imei,
                "serialNumberCount": len(serial_numbers),
                "tracksSerialNumber": tracks_serial_number,
            }
        )

    for product_id in touched_products:
        await sync_parent_price_from_variants(session, product_id)

    await inventory_repo.activate_pending_inbound_identifiers(session, reference_code)
    return posted_lines


async def _receipt_imei_summary(session: AsyncSession, document_id: UUID) -> dict:
    lines = await inventory_repo.list_inventory_receipt_lines(session, document_id)
    tracked_lines = [line for line in lines if bool(line.get("tracksImei")) or bool(line.get("tracksSerialNumber"))]
    planned = sum(int(line.get("quantity") or 0) for line in tracked_lines)
    received = sum(int(line.get("receivedQuantity") or 0) for line in tracked_lines)
    has_shortage = any(int(line.get("receivedQuantity") or 0) < int(line.get("quantity") or 0) for line in lines)
    all_complete = all(int(line.get("receivedQuantity") or 0) == int(line.get("quantity") or 0) for line in tracked_lines)
    return {
        "lines": lines,
        "trackedLines": tracked_lines,
        "trackedLineCount": len(tracked_lines),
        "plannedIdentifierQuantity": planned,
        "receivedIdentifierQuantity": received,
        "hasShortage": has_shortage,
        "allImeiComplete": all_complete,
    }


async def submit_inventory_receipt_imeis(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptImeiPayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt["status"] != "PROCESSING_IMEI":
        raise HTTPException(status_code=400, detail="Chỉ phiếu ở trạng thái xử lý IMEI mới được xác nhận danh sách IMEI.")

    lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    if not lines:
        raise HTTPException(status_code=400, detail="Phiếu nhập này không có dòng sản phẩm.")

    payload_by_line = {str(item.lineId): _clean_imeis(item.imeis) for item in payload.lines}
    payload_secondary_imeis_by_line = {str(item.lineId): _clean_imeis(getattr(item, "secondaryImeis", [])) for item in payload.lines}
    payload_serials_by_line = {str(item.lineId): _clean_serial_numbers(item.serialNumbers) for item in payload.lines}
    accepted_shortages_by_line = {str(item.lineId): bool(item.acceptShortage) for item in payload.lines}
    shortage_reasons_by_line = {str(item.lineId): (item.shortageReason or "").strip() for item in payload.lines}
    seen_imeis: set[str] = set()
    seen_serial_numbers_by_product: dict[UUID, set[str]] = {}
    has_shortage = False
    shortage_reasons: list[str] = []
    total_planned = 0
    total_received = 0

    for index, line in enumerate(lines, start=1):
        line_id = str(line["id"])
        planned_quantity = int(line.get("quantity") or 0)
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        is_tracked = tracks_imei or tracks_serial_number

        if is_tracked:
            imeis = payload_by_line.get(line_id, [])
            secondary_imeis = payload_secondary_imeis_by_line.get(line_id, [])
            serial_numbers = payload_serials_by_line.get(line_id, [])
            if tracks_imei:
                _validate_imei_format(imeis)
                if secondary_imeis:
                    _validate_imei_format(secondary_imeis)
            elif imeis:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không bật quản lý IMEI.")
            if secondary_imeis and not tracks_imei:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không bật quản lý IMEI2.")
            if tracks_serial_number:
                _validate_serial_number_format(serial_numbers)
            elif serial_numbers:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: sản phẩm không bật quản lý serial number.")
            if len(imeis) > planned_quantity:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI vượt quá số lượng dự kiến.")
            if len(secondary_imeis) > planned_quantity:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI2 vượt quá số lượng dự kiến.")
            if secondary_imeis and len(secondary_imeis) != len(imeis):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI2 phải bằng số IMEI1 nếu có nhập IMEI2.")
            if len(serial_numbers) > planned_quantity:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số serial number vượt quá số lượng dự kiến.")
            if tracks_imei and tracks_serial_number and len(imeis) != len(serial_numbers):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số IMEI và serial number phải khớp nhau theo từng máy.")
            line_imeis_for_duplicate_check = imeis + secondary_imeis
            duplicate_in_line = len(set(line_imeis_for_duplicate_check)) != len(line_imeis_for_duplicate_check)
            duplicate_in_receipt = any(imei in seen_imeis for imei in line_imeis_for_duplicate_check)
            if duplicate_in_line or duplicate_in_receipt:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách IMEI có mã bị trùng.")
            product_serials = seen_serial_numbers_by_product.setdefault(line["productId"], set())
            duplicate_serial_in_line = len(set(serial_numbers)) != len(serial_numbers)
            duplicate_serial_in_receipt = any(serial_number in product_serials for serial_number in serial_numbers)
            if duplicate_serial_in_line or duplicate_serial_in_receipt:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: danh sách serial number có mã bị trùng trong cùng sản phẩm.")
            seen_imeis.update(line_imeis_for_duplicate_check)
            product_serials.update(serial_numbers)
            line_received_counts = []
            if tracks_imei:
                line_received_counts.append(len(imeis))
            if tracks_serial_number:
                line_received_counts.append(len(serial_numbers))
            received_quantity = min(line_received_counts) if line_received_counts else planned_quantity
        else:
            item_payload = next((item for item in payload.lines if str(item.lineId) == line_id), None)
            if item_payload and item_payload.receivedQuantity is not None:
                received_quantity = item_payload.receivedQuantity
            else:
                received_quantity = planned_quantity
            if received_quantity < 0:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: số lượng thực nhận không thể âm.")

        if received_quantity < planned_quantity:
            has_shortage = True
            if not accepted_shortages_by_line.get(line_id):
                raise HTTPException(status_code=400, detail=f"Dòng {index}: phải xác nhận nhập thiếu trước khi gửi danh sách thiếu.")
            shortage_reason = shortage_reasons_by_line.get(line_id) or (payload.shortageReason or "").strip()
            if not shortage_reason:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: thiếu hàng phải nhập lý do thiếu.")
            shortage_reasons.append(shortage_reason)
        total_planned += planned_quantity
        total_received += received_quantity

    await inventory_repo.release_pending_inbound_identifiers(session, reference_code)

    existing_imeis = await inventory_repo.list_existing_imeis(session, list(seen_imeis))
    if existing_imeis:
        raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {', '.join(existing_imeis[:5])}")
    for product_id, serial_numbers in seen_serial_numbers_by_product.items():
        existing_serial_numbers = await inventory_repo.list_existing_serial_numbers(session, list(serial_numbers), product_id=product_id)
        if existing_serial_numbers:
            raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {', '.join(existing_serial_numbers[:5])}")

    for line in lines:
        line_id = str(line["id"])
        planned_quantity = int(line.get("quantity") or 0)
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        is_tracked = tracks_imei or tracks_serial_number

        if is_tracked:
            imeis = payload_by_line.get(line_id, [])
            secondary_imeis = payload_secondary_imeis_by_line.get(line_id, [])
            serial_numbers = payload_serials_by_line.get(line_id, [])
            line_received_counts = []
            if tracks_imei:
                line_received_counts.append(len(imeis))
            if tracks_serial_number:
                line_received_counts.append(len(serial_numbers))
            received_quantity = min(line_received_counts) if line_received_counts else planned_quantity
            line_shortage_reason = shortage_reasons_by_line.get(line_id) or (payload.shortageReason or "").strip()
            await inventory_repo.update_inventory_receipt_line_imeis(
                session,
                line_id=line["id"],
                imeis=imeis,
                secondary_imeis=secondary_imeis,
                serial_numbers=serial_numbers,
                received_quantity=received_quantity,
                shortage_reason=line_shortage_reason if received_quantity < planned_quantity else None,
            )
            for imei in imeis + secondary_imeis:
                await inventory_repo.insert_pending_product_imei(
                    session,
                    product_id=line["productId"],
                    variant_id=line["variantId"],
                    imei=imei,
                    source_reference=reference_code,
                )
            for serial_number in serial_numbers:
                await inventory_repo.insert_pending_product_serial_number(
                    session,
                    product_id=line["productId"],
                    variant_id=line["variantId"],
                    serial_number=serial_number,
                    source_reference=reference_code,
                )
            if tracks_imei and tracks_serial_number:
                for index, (imei, serial_number) in enumerate(zip(imeis, serial_numbers, strict=True)):
                    await inventory_repo.upsert_product_identifier_pair(
                        session,
                        product_id=line["productId"],
                        variant_id=line["variantId"],
                        imei1=imei,
                        imei2=secondary_imeis[index] if secondary_imeis else None,
                        serial_number=serial_number,
                        source_reference=reference_code,
                    )
        else:
            item_payload = next((item for item in payload.lines if str(item.lineId) == line_id), None)
            if item_payload and item_payload.receivedQuantity is not None:
                received_quantity = item_payload.receivedQuantity
            else:
                received_quantity = planned_quantity
            line_shortage_reason = shortage_reasons_by_line.get(line_id) or (payload.shortageReason or "").strip()
            await inventory_repo.update_inventory_receipt_line_imeis(
                session,
                line_id=line["id"],
                imeis=[],
                secondary_imeis=[],
                serial_numbers=[],
                received_quantity=received_quantity,
                shortage_reason=line_shortage_reason if received_quantity < planned_quantity else None,
            )

    pending_imei_statuses = await inventory_repo.list_imei_statuses(session, list(seen_imeis))
    if len(pending_imei_statuses) != len(seen_imeis) or any(
        str(item.get("status")) != "PENDING_INBOUND" or str(item.get("source_reference")) != reference_code
        for item in pending_imei_statuses
    ):
        raise HTTPException(status_code=409, detail="Không thể giữ chỗ một số IMEI cho phiếu nhập này. Vui lòng kiểm tra mã trùng.")
    for product_id, serial_numbers in seen_serial_numbers_by_product.items():
        pending_serial_statuses = await inventory_repo.list_product_serial_number_statuses(
            session,
            product_id=product_id,
            serial_numbers=list(serial_numbers),
        )
        if len(pending_serial_statuses) != len(serial_numbers) or any(
            str(item.get("status")) != "PENDING_INBOUND" or str(item.get("source_reference")) != reference_code
            for item in pending_serial_statuses
        ):
            raise HTTPException(status_code=409, detail="Không thể giữ chỗ một số serial number cho phiếu nhập này. Vui lòng kiểm tra mã trùng.")

    next_status = "PENDING_SHORTAGE_APPROVAL" if has_shortage else "PENDING_APPROVAL"
    document_shortage_note = "; ".join(dict.fromkeys(shortage_reasons)) if has_shortage else None
    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=receipt["id"],
        status=next_status,
        note=document_shortage_note,
        actor_id=current_user_id,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="identifiers_submitted",
        reference_code=reference_code,
        metadata={
            "fromStatus": receipt["status"],
            "toStatus": next_status,
            "plannedIdentifierQuantity": total_planned,
            "receivedIdentifierQuantity": total_received,
            "hasShortage": has_shortage,
            "shortageReasons": list(dict.fromkeys(shortage_reasons)),
        },
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "status": next_status,
        "plannedIdentifierQuantity": total_planned,
        "receivedIdentifierQuantity": total_received,
        "hasShortage": has_shortage,
    }


async def update_inventory_receipt_status(
    session: AsyncSession,
    reference_code: str,
    status_payload,
    current_user_id: UUID | None = None,
    current_role_code: str | None = None,
) -> dict:
    target_status = status_payload.status
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    current_status = receipt["status"]
    allowed = RECEIPT_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(status_code=400, detail=f"Không thể chuyển phiếu nhập từ {current_status} sang {target_status}.")
    note = status_payload.cancelReason if target_status == "CANCELLED" else None
    summary = await _receipt_imei_summary(session, receipt["id"])

    if target_status in {"APPROVED", "COMPLETED", "CANCELLED"}:
        _ensure_super_admin_inventory_action(
            current_role_code,
            {
                "APPROVED": "duyệt phiếu nhập kho",
                "COMPLETED": "hoàn tất nhập kho và cập nhật tồn",
                "CANCELLED": "hủy phiếu nhập kho",
            }[target_status],
        )
    if target_status == "CANCELLED":
        await inventory_repo.release_pending_inbound_identifiers(session, reference_code)
    if target_status == "PROCESSING_IMEI" and len(summary["lines"]) == 0:
        raise HTTPException(status_code=400, detail="Phiếu nhập này không có dòng sản phẩm.")
    if target_status == "APPROVED":
        _ensure_receipt_approval_allowed(receipt, current_user_id)
        if summary["trackedLineCount"] > 0 and current_status == "DRAFT":
            raise HTTPException(status_code=400, detail="Phiếu có sản phẩm cần IMEI/serial number phải qua bước xử lý mã định danh trước khi duyệt.")
        if current_status == "PROCESSING_IMEI" and not summary["allImeiComplete"]:
            raise HTTPException(status_code=400, detail="Phiếu chưa đủ IMEI/serial number. Vui lòng bổ sung hoặc chốt thiếu để chờ duyệt.")
        if current_status == "PENDING_APPROVAL" and not summary["allImeiComplete"]:
            raise HTTPException(status_code=400, detail="Phiếu chưa đủ IMEI/serial number, không thể duyệt.")

    posted_lines: list[dict] = []
    if target_status == "COMPLETED":
        if receipt.get("posted_at"):
            raise HTTPException(status_code=409, detail="Phiếu nhập kho này đã được hoàn tất trước đó.")
        quarantine = bool(receipt.get("quarantine"))
        if str(receipt.get("qualityStatus") or "PENDING").upper() != "PASSED" and not quarantine:
            raise HTTPException(status_code=400, detail="Phiếu nhập phải có kết quả kiểm tra chất lượng Đạt hoặc được bật cách ly trước khi hoàn tất.")
        if quarantine:
            for index, line in enumerate(summary["lines"], start=1):
                line_location_id = line.get("locationId") or receipt.get("target_location_id")
                if not line_location_id:
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: phiếu cách ly phải có kệ nhận hàng.")
                line_location = await _get_active_inventory_location(session, line_location_id, f"Dòng {index}: kệ cách ly")
                _ensure_receipt_quarantine_location(line_location, index)
        posted_lines = await _post_inventory_receipt(
            session,
            receipt["id"],
            receipt["document_no"],
            receipt.get("reason"),
            receipt.get("supplier_name"),
            receipt.get("note"),
            receipt.get("target_location_id"),
            receipt.get("locationCode"),
            receipt.get("locationName"),
        )
    await inventory_repo.update_inventory_receipt_status(
        session,
        document_id=receipt["id"],
        status=target_status,
        note=note,
        actor_id=current_user_id,
    )
    payable_result = None
    if target_status == "COMPLETED":
        payable_result = await account_payable_service.ensure_payable_for_completed_receipt(
            session,
            document_id=receipt["id"],
            actor_id=current_user_id,
        )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="status_changed",
        reference_code=reference_code,
        metadata={
            "fromStatus": current_status,
            "toStatus": target_status,
            "postedLineCount": len(posted_lines),
            "cancelReason": note,
            "payable": payable_result,
        },
    )
    await session.commit()
    return {"ok": True, "referenceCode": reference_code, "status": target_status, "postedLineCount": len(posted_lines)}


async def reverse_inventory_receipt(
    session: AsyncSession,
    reference_code: str,
    payload: InventoryReceiptReversePayload,
    current_user_id: UUID | None = None,
) -> dict:
    reference_code = reference_code.strip()
    receipt = await inventory_repo.get_inventory_receipt_for_update(session, reference_code)
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu nhập kho.")
    if receipt["status"] != "COMPLETED" or not receipt.get("posted_at"):
        raise HTTPException(status_code=400, detail="Chỉ có thể đảo phiếu nhập đã hoàn tất.")
    if await inventory_repo.inventory_receipt_has_reversal(session, receipt["id"]):
        raise HTTPException(status_code=409, detail="Phiếu nhập này đã có chứng từ đảo.")

    document_lines = await inventory_repo.list_inventory_receipt_lines(session, receipt["id"])
    reversal_code = f"REV-{reference_code[:48]}-{datetime.utcnow().strftime('%H%M%S')}"
    touched_products: set[UUID] = set()
    reversed_lines: list[dict] = []

    for index, line in enumerate(document_lines, start=1):
        product_id = line["productId"]
        variant_id = line["variantId"]
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line.get("receivedQuantity") or 0)
        if quantity <= 0:
            continue

        row = await inventory_repo.get_variant_inventory_for_update(session, product_id=product_id, variant_id=variant_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy biến thể hợp lệ để đảo phiếu.")
        line_location_id = line.get("locationId") or receipt.get("target_location_id")
        line_location = None
        if line_location_id:
            line_location = await inventory_repo.get_inventory_location_by_id(session, line_location_id)
            if not line_location:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: không tìm thấy kệ nhận hàng của phiếu nhập.")
        sellable_reversal = _location_is_sellable(line_location)
        old_quantity = int(row["stock_quantity"] or 0)
        if sellable_reversal and old_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: tồn kho hiện tại không đủ để đảo phiếu nhập.")

        imeis = _clean_imeis(line.get("imeis") or [])
        secondary_imeis = _clean_imeis(line.get("secondaryImeis") or [])
        all_imeis = imeis + secondary_imeis
        serial_numbers = _clean_serial_numbers(line.get("serialNumbers") or [])
        if tracks_imei and len(imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: dữ liệu IMEI của phiếu không khớp số lượng thực nhận, không thể đảo tự động.")
        if secondary_imeis and len(secondary_imeis) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: dữ liệu IMEI2 của phiếu không khớp số lượng thực nhận, không thể đảo tự động.")
        if tracks_serial_number and len(serial_numbers) != quantity:
            raise HTTPException(status_code=400, detail=f"Dòng {index}: dữ liệu serial number của phiếu không khớp số lượng thực nhận, không thể đảo tự động.")

        reversible_identifier_statuses = {"IN_STOCK", "INSPECTION_PENDING", "RETURNED", "IN_WARRANTY", "DEFECTIVE_RETURNED"}
        imei_statuses = await inventory_repo.list_imei_statuses(session, all_imeis)
        if len(imei_statuses) != len(all_imeis) or any(
            str(item["status"]) not in reversible_identifier_statuses
            or str(item.get("source_reference")) != reference_code
            or (line_location_id is not None and item.get("location_id") != line_location_id)
            for item in imei_statuses
        ):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: chỉ có thể đảo IMEI/IMEI2 còn ở đúng kệ nhận của phiếu nhập.")
        serial_statuses = await inventory_repo.list_product_serial_number_statuses(
            session,
            product_id=product_id,
            serial_numbers=serial_numbers,
        )
        if len(serial_statuses) != len(serial_numbers) or any(
            str(item["status"]) not in reversible_identifier_statuses
            or str(item.get("source_reference")) != reference_code
            or (line_location_id is not None and item.get("location_id") != line_location_id)
            for item in serial_statuses
        ):
            raise HTTPException(status_code=400, detail=f"Dòng {index}: chỉ có thể đảo serial number còn ở đúng kệ nhận của phiếu nhập.")
        new_quantity = old_quantity - quantity if sellable_reversal else old_quantity
        if sellable_reversal:
            await inventory_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_quantity)
        if line_location_id:
            await inventory_repo.post_inventory_level_reversal(
                session,
                product_id=product_id,
                variant_id=variant_id,
                location_id=line_location_id,
                quantity=quantity,
            )
            try:
                await inventory_repo.reverse_inventory_lots_for_receipt(
                    session,
                    document_id=receipt["id"],
                    location_id=line_location_id,
                    product_id=product_id,
                    variant_id=variant_id,
                    quantity=quantity,
                    reversal_reference=reversal_code,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Dòng {index}: {exc}") from exc
        await inventory_repo.mark_imeis_reversed(session, all_imeis)
        await inventory_repo.mark_serial_numbers_reversed(session, serial_numbers, product_id=product_id)
        await inventory_repo.insert_inventory_adjustment_log(
            session,
            log_id=uuid4(),
            product_id=product_id,
            variant_id=variant_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            delta=-quantity,
            transaction_type="REVERSAL",
            reference_code=reversal_code,
            reason=payload.reason,
            note=payload.note or f"Đảo phiếu nhập {reference_code}",
            supplier_name=receipt.get("supplier_name"),
            unit_cost=line.get("unitCost"),
            location_code=line.get("storageLocationCode") or receipt.get("locationCode") or "MAIN",
            location_name=line.get("storageLocationName") or receipt.get("locationName") or "Kho chính",
        )
        touched_products.add(product_id)
        reversed_lines.append(
            {
                "productId": str(product_id),
                "variantId": str(variant_id),
                "oldQuantity": old_quantity,
                "newQuantity": new_quantity,
                "quantity": quantity,
                "imeiCount": len(imeis),
                "secondaryImeiCount": len(secondary_imeis),
                "serialNumberCount": len(serial_numbers),
            }
        )

    if not reversed_lines:
        raise HTTPException(status_code=400, detail="Phiếu nhập không có dòng thực nhận để đảo.")

    reversal_document_id = uuid4()
    await inventory_repo.insert_inventory_reversal_document(
        session,
        document_id=reversal_document_id,
        reference_code=reversal_code,
        original_document_id=receipt["id"],
        reason=payload.reason,
        note=payload.note,
        location_id=receipt.get("target_location_id"),
        created_by=current_user_id,
    )
    for line in document_lines:
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line.get("receivedQuantity") or 0)
        if quantity <= 0:
            continue
        await inventory_repo.insert_inventory_receipt_line(
            session,
            line_id=uuid4(),
            document_id=reversal_document_id,
            product_id=line["productId"],
            variant_id=line["variantId"],
            location_id=line.get("locationId") or receipt.get("target_location_id"),
            quantity=quantity,
            unit_cost=line.get("unitCost"),
            note=payload.note or f"Đảo dòng phiếu nhập {reference_code}",
            imeis=_clean_imeis(line.get("imeis") or []),
            secondary_imeis=_clean_imeis(line.get("secondaryImeis") or []),
            tracks_imei=tracks_imei,
            serial_numbers=_clean_serial_numbers(line.get("serialNumbers") or []),
            tracks_serial_number=tracks_serial_number,
            storage_location_code=line.get("storageLocationCode"),
            storage_location_name=line.get("storageLocationName"),
        )
        await sync_parent_price_from_variants(session, line["productId"])
    await inventory_repo.mark_inventory_receipt_reversed(
        session,
        document_id=receipt["id"],
        actor_id=current_user_id,
        note=payload.note,
    )
    await inventory_repo.insert_inventory_receipt_audit_log(
        session,
        actor_id=current_user_id,
        action="reversed",
        reference_code=reference_code,
        metadata={
            "fromStatus": receipt["status"],
            "toStatus": "REVERSED",
            "reversalReferenceCode": reversal_code,
            "reason": payload.reason,
            "reversedLineCount": len(reversed_lines),
        },
    )
    await account_payable_service.cancel_payable_for_reversed_receipt(
        session,
        source_document_id=receipt["id"],
        actor_id=current_user_id,
        note=payload.note or f"Đảo phiếu nhập {reference_code}",
    )
    await session.commit()
    return {
        "ok": True,
        "referenceCode": reference_code,
        "reversalReferenceCode": reversal_code,
        "status": "REVERSED",
        "reversedLineCount": len(reversed_lines),
        "lines": reversed_lines,
    }
