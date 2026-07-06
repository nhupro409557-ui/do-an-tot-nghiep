from .common import *
from .common import _same_actor

async def list_inventory_identifiers(session: AsyncSession, product_id: UUID, variant_id: UUID | None = None) -> dict:
    imeis = await inventory_repo.list_product_imeis_for_inventory(session, product_id, variant_id)
    serial_numbers = await inventory_repo.list_product_serial_numbers_for_inventory(session, product_id, variant_id)
    edit_requests = await inventory_repo.list_identifier_edit_requests(
        session,
        product_id=product_id,
        variant_id=variant_id,
        limit=100,
    )
    return {
        "productId": str(product_id),
        "variantId": str(variant_id) if variant_id else None,
        "imeis": imeis,
        "serialNumbers": serial_numbers,
        "editRequests": edit_requests,
    }


async def list_inventory_issue_suggestions(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
    quantity: int = 1,
) -> list[dict]:
    requested_quantity = max(1, min(int(quantity or 1), 500))
    level_rows = await inventory_repo.list_level_issue_candidates(session, product_id=product_id, variant_id=variant_id)
    remaining = requested_quantity
    suggestions: list[dict] = []
    for row in level_rows:
        available = int(row.get("availableQuantity") or 0)
        if available <= 0 or remaining <= 0:
            continue
        suggested = min(available, remaining)
        suggestions.append(
            {
                "warehouseLocationId": row.get("locationId"),
                "locationCode": row.get("locationCode"),
                "locationName": row.get("locationName"),
                "availableQuantity": available,
                "suggestedQuantity": suggested,
                "oldestReceivedAt": row.get("oldestReceivedAt") or row.get("updatedAt"),
                "identifiers": [],
                "mode": "LOCATION",
            }
        )
        remaining -= suggested
    return suggestions


async def list_inventory_putaway_suggestions(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
    quantity: int = 1,
    reason_code: str = "NK_MUA",
) -> list[dict]:
    requested_quantity = max(1, min(int(quantity or 1), 500))
    policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
    unit_volume = _effective_package_volume_cm3(policy_row)
    required_volume = requested_quantity * unit_volume

    # Xác định purpose dựa trên reason_code
    reason_upper = (reason_code or "").upper()
    if "TRA" in reason_upper or "RETURN" in reason_upper:
        preferred_purpose = "RETURN"
    elif "BH" in reason_upper or "WARRANTY" in reason_upper:
        preferred_purpose = "WARRANTY"
    elif "ERROR" in reason_upper or "ERR" in reason_upper or "DAMAGED" in reason_upper:
        preferred_purpose = "DAMAGED"
    else:
        preferred_purpose = "STORAGE"

    # Lấy danh sách toàn bộ kệ đang hoạt động
    locations = await inventory_repo.list_inventory_locations(
        session,
        include_inactive=False,
    )

    # Lấy danh sách location_id đang chứa SKU này
    containing_locations = await inventory_repo.list_locations_containing_sku(
        session,
        product_id,
        variant_id,
    )
    containing_set = set(containing_locations)

    suggestions = []
    for loc in locations:
        if loc.get("status") != "ACTIVE":
            continue

        usable_vol = loc.get("usableVolumeCm3")
        available_vol = loc.get("availableVolumeCm3")

        if usable_vol is None or available_vol is None:
            # Fallback cho kệ ảo hoặc kệ chưa cấu hình kích thước
            available_vol = 999999999.0
            usable_vol = 999999999.0

        if available_vol < required_volume:
            continue  # Không đủ chỗ chứa

        loc_id_str = str(loc.get("id") or "")
        sku_count = int(loc.get("skuCount") or 0)
        allow_mixed = bool(loc.get("allowMixedSku"))

        # Phân nhóm độ ưu tiên:
        # 1. Kệ đang chứa cùng SKU (SAME_SKU)
        # 2. Kệ trống hoàn toàn (EMPTY_LOCATION)
        # 3. Kệ chứa SKU khác nhưng cho phép trộn (MIXED_SKU)
        is_same_sku = loc_id_str in containing_set

        if is_same_sku:
            priority = 1
            match_reason = "Kệ đang chứa cùng dòng sản phẩm"
        elif sku_count == 0:
            priority = 2
            match_reason = "Kệ trống hoàn toàn"
        elif allow_mixed:
            priority = 3
            match_reason = "Kệ trống và cho phép chứa nhiều loại sản phẩm"
        else:
            continue  # Kệ không cho phép trộn SKU và đang chứa SKU khác

        # Điểm ưu tiên bổ sung theo purpose
        purpose_score = 0
        loc_purpose = loc.get("purpose") or "STORAGE"
        if loc_purpose == preferred_purpose:
            purpose_score = 2
        elif preferred_purpose in ("RETURN", "WARRANTY") and loc_purpose == "QC":
            purpose_score = 1
        elif preferred_purpose == "STORAGE" and loc_purpose == "STORAGE":
            purpose_score = 2
        elif loc_purpose == "STORAGE":
            purpose_score = 0
        else:
            purpose_score = -1

        # Tính tỷ lệ đầy sau khi nhập
        current_used = float(loc.get("usedVolumeCm3") or 0)
        used_after = current_used + required_volume
        fill_ratio_after = used_after / usable_vol if usable_vol > 0 else 0.0
        fill_ratio_current = float(loc.get("fillRatio") or 0)

        suggestions.append({
            "warehouseLocationId": loc.get("id"),
            "locationCode": loc.get("code"),
            "locationName": loc.get("name"),
            "availableVolumeCm3": available_vol,
            "fillRatio": fill_ratio_current,
            "fillRatioAfterImport": fill_ratio_after,
            "matchReason": match_reason,
            "priority": priority,
            "purposeScore": purpose_score,
            "sortOrder": int(loc.get("sortOrder") or 0),
        })

    # Sắp xếp các gợi ý:
    # 1. Theo purposeScore giảm dần (đúng mục đích sử dụng trước)
    # 2. Theo priority tăng dần (cùng SKU -> kệ trống -> kệ trộn)
    # 3. Theo fillRatioAfterImport tăng dần (ưu tiên kệ rộng rãi hơn sau khi nhập)
    # 4. Theo sortOrder tăng dần (vị trí tối ưu đường đi)
    suggestions.sort(key=lambda x: (-x["purposeScore"], x["priority"], x["fillRatioAfterImport"], x["sortOrder"]))

    # Chuẩn hoá response để trả về đúng schema
    formatted_suggestions = []
    for s in suggestions[:5]:  # Trả về tối đa 5 gợi ý
        formatted_suggestions.append({
            "warehouseLocationId": s["warehouseLocationId"],
            "locationCode": s["locationCode"],
            "locationName": s["locationName"],
            "availableVolumeCm3": s["availableVolumeCm3"] if s["availableVolumeCm3"] < 999999999.0 else None,
            "fillRatio": s["fillRatio"] if s["fillRatio"] < 100.0 else None,
            "fillRatioAfterImport": s["fillRatioAfterImport"] if s["fillRatioAfterImport"] < 100.0 else None,
            "matchReason": s["matchReason"],
            "priority": s["priority"],
        })

    return formatted_suggestions


async def list_inventory_identifier_edit_requests(session: AsyncSession, status_filter: str = "PENDING") -> list[dict]:
    status_filter = status_filter.strip().upper()
    status = status_filter if status_filter in {"PENDING", "APPROVED", "CANCELLED"} else None
    return await inventory_repo.list_identifier_edit_requests(session, status=status, limit=200)


async def list_inventory_identifier_location_requests(session: AsyncSession, status_filter: str = "PENDING") -> list[dict]:
    status_filter = status_filter.strip().upper()
    status = status_filter if status_filter in {"PENDING", "APPROVED", "CANCELLED"} else None
    return await inventory_repo.list_identifier_location_requests(session, status=status, limit=200)


async def create_inventory_identifier_edit_request(
    session: AsyncSession,
    payload: InventoryIdentifierEditRequestPayload,
    current_user_id: UUID | None = None,
) -> dict:
    identifier_type = payload.identifierType.upper()
    new_value = payload.newValue.strip()
    reason = payload.reason.strip()
    if len(reason) < 5:
        raise HTTPException(status_code=400, detail="Lý do chỉnh sửa mã định danh phải có ít nhất 5 ký tự.")
    if identifier_type == "IMEI":
        _validate_imei_format([new_value])
    else:
        cleaned_serial_numbers = _clean_serial_numbers([new_value])
        if not cleaned_serial_numbers:
            raise HTTPException(status_code=400, detail="Serial number mới không được để trống.")
        new_value = cleaned_serial_numbers[0]
        _validate_serial_number_format([new_value])

    identifier = await inventory_repo.get_identifier_for_edit(session, identifier_type, payload.identifierId)
    if not identifier:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã định danh cần chỉnh sửa.")
    current_value = str(identifier["current_value"])
    if current_value == new_value:
        raise HTTPException(status_code=400, detail="Mã mới phải khác mã hiện tại.")
    if await inventory_repo.has_pending_identifier_edit_request(session, identifier_type, payload.identifierId):
        raise HTTPException(status_code=409, detail="Mã này đang có yêu cầu chỉnh sửa chờ duyệt.")

    if identifier_type == "IMEI":
        existing = await inventory_repo.list_existing_imeis(session, [new_value])
        if existing:
            raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {new_value}")
    else:
        existing = await inventory_repo.list_existing_serial_numbers(session, [new_value], product_id=identifier["product_id"])
        if existing:
            raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {new_value}")

    request_id = uuid4()
    await inventory_repo.insert_identifier_edit_request(
        session,
        request_id=request_id,
        identifier_type=identifier_type,
        identifier_id=payload.identifierId,
        product_id=identifier["product_id"],
        variant_id=identifier.get("variant_id"),
        current_value=current_value,
        new_value=new_value,
        reason=reason,
        requested_by=current_user_id,
    )
    await session.commit()
    return {
        "ok": True,
        "requestId": str(request_id),
        "status": "PENDING",
        "identifierType": identifier_type,
        "currentValue": current_value,
        "newValue": new_value,
    }


async def decide_inventory_identifier_edit_request(
    session: AsyncSession,
    request_id: UUID,
    payload: InventoryIdentifierEditDecisionPayload,
    current_user_id: UUID | None = None,
) -> dict:
    request = await inventory_repo.get_identifier_edit_request_for_update(session, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu chỉnh sửa mã định danh.")
    if request["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Yêu cầu chỉnh sửa này đã được xử lý.")

    decision = payload.decision.upper()
    if decision == "APPROVED":
        if _same_actor(request.get("requested_by"), current_user_id):
            raise HTTPException(status_code=403, detail="Người tạo yêu cầu sửa mã định danh không được tự duyệt.")
        identifier_type = str(request["identifier_type"])
        new_value = str(request["new_value"])
        identifier = await inventory_repo.get_identifier_for_edit(session, identifier_type, request["identifier_id"])
        if not identifier:
            raise HTTPException(status_code=404, detail="Mã định danh gốc không còn tồn tại.")
        if str(identifier["current_value"]) != str(request["current_value"]):
            raise HTTPException(status_code=409, detail="Mã định danh đã thay đổi sau khi tạo yêu cầu, không thể duyệt tự động.")
        if identifier_type == "IMEI":
            existing = await inventory_repo.list_existing_imeis(session, [new_value])
            if existing:
                raise HTTPException(status_code=409, detail=f"IMEI đã tồn tại: {new_value}")
        else:
            existing = await inventory_repo.list_existing_serial_numbers(session, [new_value], product_id=identifier["product_id"])
            if existing:
                raise HTTPException(status_code=409, detail=f"Serial number đã tồn tại trong cùng sản phẩm: {new_value}")
        await inventory_repo.update_identifier_value(session, identifier_type, request["identifier_id"], new_value)

    await inventory_repo.update_identifier_edit_request_status(
        session,
        request_id=request_id,
        status=decision,
        decided_by=current_user_id,
        decision_note=payload.note,
    )
    await session.commit()
    return {"ok": True, "requestId": str(request_id), "status": decision}


async def create_inventory_identifier_location_request(
    session: AsyncSession,
    payload: InventoryIdentifierLocationRequestPayload,
    current_user_id: UUID | None = None,
) -> dict:
    identifier_type = payload.identifierType.upper()
    identifier_value = (payload.identifierValue or "").strip()
    if identifier_type == "IMEI" and identifier_value:
        _validate_imei_format([identifier_value])
    elif identifier_type == "SERIAL" and identifier_value:
        cleaned_serial_numbers = _clean_serial_numbers([identifier_value])
        identifier_value = cleaned_serial_numbers[0] if cleaned_serial_numbers else ""
        _validate_serial_number_format([identifier_value])

    identifier = (
        await inventory_repo.get_identifier_for_edit(session, identifier_type, payload.identifierId)
        if payload.identifierId
        else await inventory_repo.get_identifier_by_value(session, identifier_type, identifier_value)
    )
    if not identifier:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã định danh cần gán vị trí.")
    if UUID(str(identifier["product_id"])) != payload.productId:
        raise HTTPException(status_code=400, detail="Mã định danh không thuộc sản phẩm đã chọn.")
    identifier_variant_id = identifier.get("variant_id")
    if str(identifier_variant_id or "") != str(payload.variantId or ""):
        raise HTTPException(status_code=400, detail="Mã định danh không thuộc biến thể đã chọn.")
    if str(identifier.get("status") or "").upper() != "IN_STOCK":
        raise HTTPException(status_code=409, detail="Chỉ mã đang còn trong kho mới được gán lại vị trí.")
    if identifier_value and str(identifier["current_value"]) != identifier_value:
        raise HTTPException(status_code=409, detail="Giá trị mã định danh không khớp dữ liệu hiện tại.")
    if identifier.get("location_id") == payload.newLocationId:
        raise HTTPException(status_code=400, detail="Mã định danh đã nằm tại kệ đích.")
    if await inventory_repo.has_pending_identifier_location_request(session, identifier_type, identifier["id"]):
        raise HTTPException(status_code=409, detail="Mã này đang có yêu cầu đổi vị trí chờ duyệt.")
    identifier_pair = await inventory_repo.get_identifier_pair_by_value(
        session,
        product_id=payload.productId,
        variant_id=payload.variantId,
        identifier_type=identifier_type,
        identifier_value=str(identifier["current_value"]),
    )
    if identifier_pair and await inventory_repo.has_pending_identifier_pair_location_request(session, identifier_pair["id"]):
        raise HTTPException(status_code=409, detail="Thiết bị này đang có yêu cầu đổi vị trí chờ duyệt cho một mã ghép cặp.")

    target_location = await inventory_repo.get_inventory_location_by_id(session, payload.newLocationId)
    if not target_location:
        raise HTTPException(status_code=404, detail="Không tìm thấy kệ đích.")
    if str(target_location.get("status") or "ACTIVE").upper() != "ACTIVE":
        raise HTTPException(status_code=400, detail="Kệ đích đang bị khóa.")
    target_level = await inventory_repo.get_inventory_level_for_transfer(
        session,
        product_id=payload.productId,
        variant_id=payload.variantId,
        location_id=payload.newLocationId,
    )
    if not target_level or int(target_level.get("onHandQuantity") or 0) <= 0:
        raise HTTPException(
            status_code=409,
            detail="Kệ đích chưa có tồn của sản phẩm/biến thể này. Hãy điều chỉnh hoặc chuyển tồn trước khi gán mã.",
        )

    request_id = uuid4()
    await inventory_repo.insert_identifier_location_request(
        session,
        request_id=request_id,
        identifier_type=identifier_type,
        identifier_id=identifier["id"],
        identifier_value=str(identifier["current_value"]),
        product_id=payload.productId,
        variant_id=payload.variantId,
        identifier_pair_id=identifier_pair["id"] if identifier_pair else None,
        current_location_id=identifier.get("location_id"),
        new_location_id=payload.newLocationId,
        reason=payload.reason.strip(),
        requested_by=current_user_id,
    )
    await session.commit()
    return {
        "ok": True,
        "requestId": str(request_id),
        "status": "PENDING",
        "identifierType": identifier_type,
        "identifierValue": str(identifier["current_value"]),
        "newLocationId": str(payload.newLocationId),
    }


async def decide_inventory_identifier_location_request(
    session: AsyncSession,
    request_id: UUID,
    payload: InventoryIdentifierEditDecisionPayload,
    current_user_id: UUID | None = None,
) -> dict:
    request = await inventory_repo.get_identifier_location_request_for_update(session, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu gán vị trí mã định danh.")
    if request["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Yêu cầu gán vị trí này đã được xử lý.")

    decision = payload.decision.upper()
    if decision == "APPROVED":
        if _same_actor(request.get("requested_by"), current_user_id):
            raise HTTPException(status_code=403, detail="Người tạo yêu cầu gán vị trí không được tự duyệt.")
        identifier_type = str(request["identifier_type"])
        identifier = await inventory_repo.get_identifier_for_location_update(
            session,
            identifier_type,
            request["identifier_id"],
        )
        if not identifier:
            raise HTTPException(status_code=404, detail="Mã định danh gốc không còn tồn tại.")
        if str(identifier.get("status") or "").upper() != "IN_STOCK":
            raise HTTPException(status_code=409, detail="Mã định danh không còn ở trạng thái trong kho.")
        if str(identifier["current_value"]) != str(request["identifier_value"]):
            raise HTTPException(status_code=409, detail="Giá trị mã định danh đã thay đổi sau khi tạo yêu cầu.")
        if str(identifier.get("location_id") or "") != str(request.get("current_location_id") or ""):
            raise HTTPException(status_code=409, detail="Vị trí mã định danh đã thay đổi sau khi tạo yêu cầu.")

        target_location = await inventory_repo.get_inventory_location_by_id(session, request["new_location_id"])
        if not target_location or str(target_location.get("status") or "ACTIVE").upper() != "ACTIVE":
            raise HTTPException(status_code=409, detail="Kệ đích không còn hoạt động.")
        target_level = await inventory_repo.get_inventory_level_for_transfer(
            session,
            product_id=request["product_id"],
            variant_id=request["variant_id"],
            location_id=request["new_location_id"],
        )
        if not target_level or int(target_level.get("onHandQuantity") or 0) <= 0:
            raise HTTPException(status_code=409, detail="Kệ đích không còn tồn phù hợp để gán mã.")
        pair_id = request.get("identifier_pair_id")
        if pair_id:
            identifier_pair = await inventory_repo.get_identifier_pair_for_location_update(session, pair_id)
            if not identifier_pair:
                raise HTTPException(status_code=409, detail="Bộ IMEI/serial ghép cặp không còn tồn tại.")
            pair_values = {
                str(identifier_pair["imei1"]),
                str(identifier_pair["serial_number"]),
            }
            if identifier_pair.get("imei2"):
                pair_values.add(str(identifier_pair["imei2"]))
            if str(request["identifier_value"]) not in pair_values:
                raise HTTPException(status_code=409, detail="Mã định danh không còn thuộc bộ mã ghép cặp ban đầu.")
            members = await inventory_repo.list_identifier_pair_members_for_update(
                session,
                product_id=request["product_id"],
                variant_id=request["variant_id"],
                imei1=str(identifier_pair["imei1"]),
                imei2=str(identifier_pair["imei2"]) if identifier_pair.get("imei2") else None,
                serial_number=str(identifier_pair["serial_number"]),
            )
            expected_member_count = 3 if identifier_pair.get("imei2") else 2
            if len(members) != expected_member_count:
                raise HTTPException(status_code=409, detail="Bộ mã ghép cặp đang thiếu IMEI hoặc serial.")
            unavailable_members = [
                str(member["identifier_value"])
                for member in members
                if str(member.get("status") or "").upper() != "IN_STOCK"
            ]
            if unavailable_members:
                raise HTTPException(
                    status_code=409,
                    detail=f"Bộ mã có thành viên không còn trong kho: {', '.join(unavailable_members)}.",
                )
            await inventory_repo.update_identifier_pair_locations(
                session,
                product_id=request["product_id"],
                variant_id=request["variant_id"],
                imei1=str(identifier_pair["imei1"]),
                imei2=str(identifier_pair["imei2"]) if identifier_pair.get("imei2") else None,
                serial_number=str(identifier_pair["serial_number"]),
                location_id=request["new_location_id"],
            )
        else:
            await inventory_repo.update_identifier_location(
                session,
                identifier_type,
                request["identifier_id"],
                request["new_location_id"],
            )

    await inventory_repo.update_identifier_location_request_status(
        session,
        request_id=request_id,
        status=decision,
        decided_by=current_user_id,
        decision_note=payload.note,
    )
    await session.commit()
    return {"ok": True, "requestId": str(request_id), "status": decision}
