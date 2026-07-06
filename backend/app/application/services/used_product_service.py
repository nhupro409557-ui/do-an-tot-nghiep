from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin.used_product import (
    UsedDeviceInspectionPayload,
    UsedDeviceIntakePayload,
    UsedDeviceListingPayload,
    UsedDeviceListingStatusPayload,
    UsedDeviceStatusPayload,
)
from app.infrastructure.database.repositories import used_product_repo
from app.shared.admin_utils import slugify


INTAKE_TRANSITIONS = {
    "SUBMITTED": {"RECEIVED", "CANCELLED"},
    "RECEIVED": {"INSPECTING", "REJECTED"},
    "REPAIR_REQUIRED": {"INSPECTING", "REJECTED"},
    "APPRAISED": {"ACCEPTED", "REJECTED"},
}


async def create_intake(
    session: AsyncSession,
    *,
    payload: UsedDeviceIntakePayload,
    actor_id: UUID,
) -> dict:
    if not await used_product_repo.product_variant_exists(
        session,
        product_id=payload.productId,
        variant_id=payload.variantId,
    ):
        raise HTTPException(status_code=400, detail="Sản phẩm hoặc biến thể gốc không hợp lệ.")
    if await used_product_repo.active_imei_exists(session, payload.imei):
        raise HTTPException(status_code=409, detail="IMEI đã có hồ sơ hàng cũ đang hoạt động.")

    intake_id = uuid4()
    request_code = await used_product_repo.next_request_code(session)
    try:
        await used_product_repo.insert_intake(
            session,
            intake_id=intake_id,
            request_code=request_code,
            payload=payload,
            actor_id=actor_id,
        )
        await used_product_repo.insert_event(
            session,
            intake_id=intake_id,
            event_type="INTAKE_CREATED",
            old_status=None,
            new_status="SUBMITTED",
            actor_id=actor_id,
            note=payload.note,
            metadata={"sourceType": payload.sourceType},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="IMEI hoặc mã hồ sơ hàng cũ đã tồn tại.") from exc
    return {"id": str(intake_id), "requestCode": request_code, "status": "SUBMITTED"}


async def list_intakes(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
    page: int,
    limit: int,
) -> dict:
    return await used_product_repo.list_intakes(
        session,
        status_value=status_value,
        search=search,
        page=page,
        limit=limit,
    )


async def update_intake_status(
    session: AsyncSession,
    *,
    intake_id: UUID,
    payload: UsedDeviceStatusPayload,
    actor_id: UUID,
) -> dict:
    intake = await used_product_repo.get_intake_for_update(session, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tiếp nhận hàng cũ.")
    current_status = str(intake["status"])
    target_status = payload.status
    if target_status not in INTAKE_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển hồ sơ từ {current_status} sang {target_status}.",
        )

    device_id = None
    if target_status == "ACCEPTED":
        appraisal = await used_product_repo.latest_appraisal(session, intake_id)
        if not appraisal:
            raise HTTPException(status_code=409, detail="Hồ sơ chưa có kết quả thẩm định hợp lệ.")
        if not appraisal["condition_grade"] or appraisal["condition_score"] is None:
            raise HTTPException(status_code=409, detail="Kết quả thẩm định thiếu hạng hoặc điểm tình trạng.")
        if appraisal["proposed_sale_price"] is None:
            raise HTTPException(status_code=409, detail="Kết quả thẩm định chưa có giá bán đề xuất.")
        try:
            device_id = await used_product_repo.create_device_from_intake(
                session,
                intake=intake,
                appraisal=appraisal,
                actor_id=actor_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    await used_product_repo.update_intake_status(
        session,
        intake_id=intake_id,
        status_value=target_status,
        actor_id=actor_id,
    )
    await used_product_repo.insert_event(
        session,
        intake_id=intake_id,
        device_id=device_id,
        event_type="INTAKE_STATUS_CHANGED",
        old_status=current_status,
        new_status=target_status,
        actor_id=actor_id,
        note=payload.note,
    )
    await session.commit()
    return {
        "id": str(intake_id),
        "status": target_status,
        "deviceId": str(device_id) if device_id else None,
    }


async def inspect_intake(
    session: AsyncSession,
    *,
    intake_id: UUID,
    payload: UsedDeviceInspectionPayload,
    actor_id: UUID,
) -> dict:
    intake = await used_product_repo.get_intake_for_update(session, intake_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ tiếp nhận hàng cũ.")
    if intake["status"] not in {"RECEIVED", "INSPECTING"}:
        raise HTTPException(status_code=409, detail="Hồ sơ chưa ở trạng thái có thể thẩm định.")
    if payload.outcome == "APPRAISED":
        if payload.conditionGrade is None or payload.conditionScore is None:
            raise HTTPException(status_code=400, detail="Thẩm định đạt phải có hạng và điểm tình trạng.")
        if payload.proposedAcquisitionPrice is None or payload.proposedSalePrice is None:
            raise HTTPException(status_code=400, detail="Thẩm định đạt phải có giá thu mua và giá bán đề xuất.")
    inspection_id = uuid4()
    await used_product_repo.insert_inspection(
        session,
        inspection_id=inspection_id,
        intake_id=intake_id,
        actor_id=actor_id,
        payload=payload,
    )
    await used_product_repo.update_intake_status(
        session,
        intake_id=intake_id,
        status_value=payload.outcome,
        actor_id=actor_id,
    )
    await used_product_repo.insert_event(
        session,
        intake_id=intake_id,
        event_type="INTAKE_INSPECTED",
        old_status=str(intake["status"]),
        new_status=payload.outcome,
        actor_id=actor_id,
        note=payload.note,
        metadata={
            "conditionGrade": payload.conditionGrade,
            "conditionScore": payload.conditionScore,
            "batteryHealth": payload.batteryHealth,
        },
    )
    await session.commit()
    return {"id": str(inspection_id), "status": payload.outcome}


async def list_devices(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
) -> list[dict]:
    return await used_product_repo.list_devices(
        session,
        status_value=status_value,
        search=search,
    )


async def list_source_products(session: AsyncSession, search: str) -> list[dict]:
    return await used_product_repo.list_source_products(session, search)


async def list_device_history(session: AsyncSession, device_id: UUID) -> dict:
    history = await used_product_repo.list_device_history(session, device_id)
    if not history:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị cũ.")
    return history


DEVICE_STATUS_TRANSITIONS = {
    "RETURNED_QC": {"READY_FOR_PRICING", "REPAIRING", "RETIRED"},
    "REPAIRING": {"RETURNED_QC", "RETIRED"},
}


async def reinspect_device(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload: UsedDeviceInspectionPayload,
    actor_id: UUID,
) -> dict:
    device = await used_product_repo.get_device_for_listing(session, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị cũ.")
    current_status = str(device["status"])
    if current_status != "RETURNED_QC":
        raise HTTPException(status_code=409, detail="Chỉ thiết bị hoàn về chờ QC mới có thể thẩm định lại.")
    if payload.outcome == "APPRAISED":
        if not payload.conditionGrade or payload.conditionScore is None:
            raise HTTPException(status_code=400, detail="QC đạt phải có hạng và điểm tình trạng.")
        if payload.proposedSalePrice is None or payload.proposedSalePrice <= 0:
            raise HTTPException(status_code=400, detail="QC đạt phải có giá bán hàng cũ mới.")
    if payload.outcome == "REPAIR_REQUIRED" and payload.repairCostEstimate <= 0:
        raise HTTPException(status_code=400, detail="Thiết bị cần sửa chữa phải có chi phí sửa dự kiến.")

    target_status = await used_product_repo.apply_device_reinspection(
        session,
        inspection_id=uuid4(),
        device=device,
        payload=payload,
        actor_id=actor_id,
    )
    await used_product_repo.insert_event(
        session,
        intake_id=device["intake_request_id"],
        device_id=device_id,
        event_type="DEVICE_REINSPECTED",
        old_status=current_status,
        new_status=target_status,
        actor_id=actor_id,
        note=payload.note,
        metadata={
            "outcome": payload.outcome,
            "conditionGrade": payload.conditionGrade,
            "conditionScore": payload.conditionScore,
            "batteryHealth": payload.batteryHealth,
            "proposedSalePrice": float(payload.proposedSalePrice) if payload.proposedSalePrice is not None else None,
            "resetListingToDraft": target_status == "READY_FOR_PRICING",
        },
    )
    await session.commit()
    return {"id": str(device_id), "status": target_status}


async def update_device_status(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload,
    actor_id: UUID,
) -> dict:
    device = await used_product_repo.get_device_for_listing(session, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị cũ.")
    current_status = str(device["status"])
    target_status = payload.status
    if target_status not in DEVICE_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển thiết bị từ {current_status} sang {target_status}.",
        )
    await used_product_repo.update_device_status(
        session,
        device_id=device_id,
        status_value=target_status,
    )
    await used_product_repo.insert_event(
        session,
        intake_id=device["intake_request_id"],
        device_id=device_id,
        event_type="DEVICE_STATUS_CHANGED",
        old_status=current_status,
        new_status=target_status,
        actor_id=actor_id,
        note=payload.note,
        metadata={"resetListingToDraft": target_status == "READY_FOR_PRICING"},
    )
    await session.commit()
    return {"id": str(device_id), "status": target_status}


async def save_listing(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload: UsedDeviceListingPayload,
    actor_id: UUID,
) -> dict:
    device = await used_product_repo.get_device_for_listing(session, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị cũ.")
    if device["status"] in {"RESERVED", "SOLD", "RETURNED_QC", "RETIRED"}:
        raise HTTPException(status_code=409, detail="Thiết bị không thể tạo hoặc sửa bài đăng ở trạng thái hiện tại.")
    snapshot = device["original_snapshot"] or {}
    new_reference_price = Decimal(str(snapshot.get("newReferencePrice") or 0))
    sale_price = Decimal(str(device["approved_sale_price"] or 0))
    if sale_price <= 0:
        raise HTTPException(status_code=409, detail="Thiết bị chưa có giá bán hàng cũ hợp lệ.")
    if new_reference_price > 0 and sale_price >= new_reference_price and not payload.priceComparisonNote:
        raise HTTPException(
            status_code=400,
            detail="Giá hàng cũ không thấp hơn giá máy mới; phải ghi rõ lý do so sánh giá.",
        )
    listing_id = uuid4()
    listing_slug = f"{slugify(payload.title)}-{str(device['device_code']).lower()}"
    try:
        saved_id = await used_product_repo.upsert_listing(
            session,
            listing_id=listing_id,
            device_id=device_id,
            slug=listing_slug,
            payload=payload,
            actor_id=actor_id,
        )
        await used_product_repo.insert_event(
            session,
            intake_id=device["intake_request_id"],
            device_id=device_id,
            event_type="LISTING_SAVED",
            old_status=str(device["status"]),
            new_status="LISTING_DRAFT",
            actor_id=actor_id,
            metadata={"listingId": str(saved_id), "imageCount": len(payload.images)},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Slug bài đăng hàng cũ đã tồn tại.") from exc
    return {"id": str(saved_id), "slug": listing_slug, "status": "DRAFT"}


LISTING_TRANSITIONS = {
    "DRAFT": {"PENDING_APPROVAL"},
    "HIDDEN": {"PENDING_APPROVAL"},
    "PENDING_APPROVAL": {"DRAFT", "PUBLISHED"},
    "PUBLISHED": {"HIDDEN"},
}


async def update_listing_status(
    session: AsyncSession,
    *,
    listing_id: UUID,
    payload: UsedDeviceListingStatusPayload,
    actor_id: UUID,
) -> dict:
    listing = await used_product_repo.get_listing_for_update(session, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài đăng hàng cũ.")
    current_status = str(listing["status"])
    target_status = payload.status
    if target_status not in LISTING_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Không thể chuyển bài đăng từ {current_status} sang {target_status}.",
        )
    device_status = {
        "DRAFT": "LISTING_DRAFT",
        "PENDING_APPROVAL": "LISTING_REVIEW",
        "PUBLISHED": "READY_FOR_SALE",
        "HIDDEN": "READY_FOR_PRICING",
    }[target_status]
    await used_product_repo.update_listing_status(
        session,
        listing_id=listing_id,
        device_id=listing["device_id"],
        status_value=target_status,
        device_status=device_status,
        actor_id=actor_id,
    )
    await used_product_repo.insert_event(
        session,
        device_id=listing["device_id"],
        event_type="LISTING_STATUS_CHANGED",
        old_status=current_status,
        new_status=target_status,
        actor_id=actor_id,
        note=payload.note,
        metadata={"listingId": str(listing_id)},
    )
    await session.commit()
    return {"id": str(listing_id), "status": target_status}


async def list_admin_listings(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
) -> list[dict]:
    return await used_product_repo.list_admin_listings(
        session,
        status_value=status_value,
        search=search,
    )


async def list_public_listings(
    session: AsyncSession,
    *,
    search: str,
    grade: str,
    min_price: Decimal | None,
    max_price: Decimal | None,
    sort: str,
    page: int,
    limit: int,
) -> dict:
    if grade and grade.upper() not in {"A", "B", "C"}:
        raise HTTPException(status_code=400, detail="Hạng thiết bị không hợp lệ.")
    return await used_product_repo.list_published_devices(
        session,
        search=search,
        grade=grade,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        limit=limit,
    )


async def get_public_listing(session: AsyncSession, slug: str) -> dict:
    listing = await used_product_repo.get_published_device(session, slug)
    if not listing:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị cũ đang bán.")
    imei = str(listing.get("imei") or "")
    listing["maskedImei"] = f"{imei[:4]}•••••••{imei[-4:]}" if len(imei) >= 8 else "Đã xác minh"
    listing.pop("imei", None)
    return listing
