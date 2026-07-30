from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from app.shared.exceptions import BusinessException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin.used_product import (
    UsedDeviceInspectionPayload,
    UsedDeviceIntakePayload,
    UsedDeviceListingPayload,
    UsedDeviceListingStatusPayload,
    UsedDevicePricePayload,
    UsedDeviceStatusPayload,
)
from app.api.schemas.used_product import UserBuybackRequestPayload
from app.infrastructure.database.repositories import used_product_repo, media_repo
from sqlalchemy import text
from app.shared.admin_utils import slugify


INTAKE_TRANSITIONS = {
    "SUBMITTED": {"RECEIVED", "CANCELLED"},
    "RECEIVED": {"INSPECTING", "REJECTED"},
    "REPAIR_REQUIRED": {"INSPECTING", "REJECTED"},
    "APPRAISED": {"ACCEPTED", "REJECTED"},
}

REQUIRED_APPRAISAL_CHECKS = {
    "imeiVerified": "IMEI trên máy phải khớp với hồ sơ tiếp nhận",
    "accountUnlocked": "thiết bị phải được thoát tài khoản và khóa kích hoạt",
    "dataErased": "dữ liệu cá nhân trên thiết bị phải được xóa",
}
MIN_APPRAISAL_EVIDENCE = 3


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _manufacturer_warranty_meta(item: dict) -> dict:
    if not item.get("manufacturerWarrantyEnabled"):
        return item
    activated = item.get("manufacturerWarrantyActivatedAt")
    total_months = int(item.get("manufacturerWarrantyTotalMonths") or 0)
    if not activated or total_months <= 0:
        return item
    if isinstance(activated, str):
        activated = date.fromisoformat(activated)
    expires_at = _add_months(activated, total_months)
    today = date.today()
    remaining = 0
    if expires_at > today:
        remaining = (expires_at.year - today.year) * 12 + expires_at.month - today.month
        if expires_at.day > today.day:
            remaining += 1
    item["manufacturerWarrantyExpiresAt"] = expires_at.isoformat()
    item["manufacturerWarrantyRemainingMonths"] = max(0, remaining)
    return item


def _validate_saleable_appraisal(payload, *, acquisition_cost: Decimal | None = None) -> None:
    missing_checks = [
        message
        for key, message in REQUIRED_APPRAISAL_CHECKS.items()
        if payload.checklist.get(key) is not True
    ]
    if missing_checks:
        raise BusinessException(
            status_code=400,
            code="REQUIRED_CHECKLIST_INCOMPLETE",
            message=f"Chưa đủ điều kiện thu mua: {missing_checks[0]}.",
        )
    valid_evidence_urls = {
        str(item.get("url") or "").strip()
        for item in payload.evidence
        if isinstance(item, dict) and str(item.get("url") or "").strip()
    }
    if len(valid_evidence_urls) < MIN_APPRAISAL_EVIDENCE:
        raise BusinessException(
            status_code=400,
            code="INSPECTION_EVIDENCE_REQUIRED",
            message=f"Thẩm định đạt phải có ít nhất {MIN_APPRAISAL_EVIDENCE} ảnh thực tế của thiết bị.",
        )

    effective_acquisition_cost = acquisition_cost if acquisition_cost is not None else payload.proposedAcquisitionPrice
    if effective_acquisition_cost is None or payload.proposedSalePrice is None:
        return
    total_cost = effective_acquisition_cost + payload.repairCostEstimate
    if payload.proposedSalePrice <= total_cost:
        raise BusinessException(
            status_code=400,
            code="INVALID_PROPOSED_MARGIN",
            message="Giá bán đề xuất phải lớn hơn tổng giá thu mua và chi phí sửa dự kiến.",
        )


async def create_intake(
    session: AsyncSession,
    *,
    payload: UsedDeviceIntakePayload,
    actor_id: UUID,
) -> dict:
    if payload.productId and not await used_product_repo.product_variant_exists(
        session, product_id=payload.productId, variant_id=payload.variantId
    ):
        raise BusinessException(
            status_code=400,
            code="PRODUCT_VARIANT_NOT_FOUND",
            message="Sản phẩm hoặc biến thể gốc không hợp lệ."
        )
    if await used_product_repo.active_imei_exists(session, payload.imei):
        raise BusinessException(
            status_code=409,
            code="DUPLICATE_ACTIVE_IMEI",
            message="IMEI đã có hồ sơ hàng cũ đang hoạt động."
        )

    if payload.sellerUserId:
        seller_exists = await session.scalar(
            text("SELECT EXISTS(SELECT 1 FROM users WHERE id = :user_id)"),
            {"user_id": payload.sellerUserId}
        )
        if not seller_exists:
            raise BusinessException(
                status_code=404,
                code="SELLER_NOT_FOUND",
                message="Không tìm thấy thông tin người bán trên hệ thống."
            )
    else:
        if payload.sourceType == "USER_BUYBACK" and (not payload.sellerName or not payload.sellerPhone):
            raise BusinessException(
                status_code=400,
                code="SELLER_INFO_REQUIRED",
                message="Nếu không chọn tài khoản thành viên, phải điền họ tên và số điện thoại người bán."
            )

    if payload.sourceType == "RETURNED_USED":
        if payload.productId is None:
            raise BusinessException(
                status_code=400,
                code="RETURNED_PRODUCT_REQUIRED",
                message="Máy hoàn từ đơn hàng phải liên kết với sản phẩm catalog gốc.",
            )
        if not payload.originalOrderId or not payload.returnRequestId:
            raise BusinessException(
                status_code=400,
                code="USED_SOURCE_REQUIRED",
                message="Hàng cũ từ đơn trả phải có đơn gốc và hồ sơ trả hàng."
            )
        matched = await used_product_repo.returned_item_matches_device(
            session,
            order_id=payload.originalOrderId,
            return_request_id=payload.returnRequestId,
            product_id=payload.productId,
            variant_id=payload.variantId,
            imei=payload.imei,
            seller_user_id=payload.sellerUserId,
        )
        if not matched:
            raise BusinessException(
                status_code=409,
                code="USED_SOURCE_MISMATCH",
                message="Thiết bị không khớp với đơn hàng hoặc hồ sơ trả hàng."
            )

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
        raise BusinessException(
            status_code=409,
            code="INTEGRITY_VIOLATION",
            message="IMEI hoặc mã hồ sơ hàng cũ đã tồn tại."
        ) from exc
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
    try:
        intake = await used_product_repo.get_intake_for_update(session, intake_id)
        if not intake:
            raise BusinessException(
                status_code=404,
                code="INTAKE_NOT_FOUND",
                message="Không tìm thấy hồ sơ tiếp nhận hàng cũ."
            )
        current_status = str(intake["status"])
        target_status = payload.status
        seller_address_for_update = payload.sellerAddress
        seller_identity_for_update = payload.sellerIdentityNumber
        payment_reference_for_update = payload.acquisitionPaymentReference
        if target_status not in INTAKE_TRANSITIONS.get(current_status, set()):
            raise BusinessException(
                status_code=409,
                code="INVALID_STATUS_TRANSITION",
                message=f"Không thể chuyển hồ sơ từ {current_status} sang {target_status}."
            )

        # Check if the actor is SUPER_ADMIN
        actor_role = await session.scalar(
            text(
                """
                SELECT r.code 
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :actor_id
                """
            ),
            {"actor_id": actor_id}
        )
        is_super_admin = (actor_role == "SUPER_ADMIN")

        device_id = None
        if target_status == "ACCEPTED":
            appraisal = await used_product_repo.latest_appraisal(session, intake_id)
            if not appraisal:
                raise BusinessException(
                    status_code=409,
                    code="APPRAISAL_NOT_FOUND",
                    message="Hồ sơ chưa có kết quả thẩm định hợp lệ."
                )
            if not appraisal["condition_grade"] or appraisal["condition_score"] is None:
                raise BusinessException(
                    status_code=409,
                    code="INCOMPLETE_APPRAISAL",
                    message="Kết quả thẩm định thiếu hạng hoặc điểm tình trạng."
                )
            if appraisal["proposed_sale_price"] is None:
                raise BusinessException(
                    status_code=409,
                    code="PROPOSED_PRICE_MISSING",
                    message="Kết quả thẩm định chưa có giá bán đề xuất."
                )
            if intake["source_type"] == "USER_BUYBACK":
                seller_address = (payload.sellerAddress or intake.get("seller_address") or "").strip()
                seller_identity_number = (
                    payload.sellerIdentityNumber or intake.get("seller_identity_number") or ""
                ).strip()
                seller_address_for_update = seller_address
                seller_identity_for_update = seller_identity_number
                payment_reference_for_update = (payload.acquisitionPaymentReference or "").strip() or None
                if not seller_address or not seller_identity_number:
                    raise BusinessException(
                        status_code=400,
                        code="SELLER_LEGAL_INFO_REQUIRED",
                        message="Xác nhận thu mua cần địa chỉ và số giấy tờ định danh của người bán.",
                    )
                if not payload.ownershipConfirmed:
                    raise BusinessException(
                        status_code=400,
                        code="OWNERSHIP_CONFIRMATION_REQUIRED",
                        message="Người bán phải xác nhận quyền sở hữu hợp pháp đối với thiết bị.",
                    )
                if not payload.acquisitionPaymentMethod:
                    raise BusinessException(
                        status_code=400,
                        code="ACQUISITION_PAYMENT_REQUIRED",
                        message="Phải chọn phương thức chi trả tiền thu mua.",
                    )
                if (
                    payload.acquisitionPaymentMethod in {"BANK_TRANSFER", "TRADE_IN_CREDIT"}
                    and not (payload.acquisitionPaymentReference or "").strip()
                ):
                    raise BusinessException(
                        status_code=400,
                        code="PAYMENT_REFERENCE_REQUIRED",
                        message="Thanh toán chuyển khoản hoặc bù trừ cần mã tham chiếu.",
                    )
            if not is_super_admin and (actor_id == intake.get("created_by") or actor_id == appraisal.get("inspector_id")):
                raise BusinessException(
                    status_code=400,
                    code="APPROVER_MUST_BE_DIFFERENT",
                    message="Người duyệt hồ sơ thu mua không được trùng với người tiếp nhận hoặc người thẩm định."
                )
            # Check if IMEI already exists in other active requests or in used_devices
            imei_exists = bool(
                (
                    await session.execute(
                        text(
                            """
                            SELECT 1 FROM used_devices WHERE imei = :imei
                            UNION ALL
                            SELECT 1 FROM used_device_intake_requests 
                            WHERE imei = :imei AND id != :exclude_id AND status NOT IN ('REJECTED', 'CANCELLED')
                            LIMIT 1
                            """
                        ),
                        {"imei": intake["imei"], "exclude_id": intake_id}
                    )
                ).scalar_one_or_none()
            )
            if imei_exists:
                raise BusinessException(
                    status_code=409,
                    code="DUPLICATE_ACTIVE_IMEI",
                    message="IMEI này đã có thiết bị hoạt động trên hệ thống."
                )
            try:
                device_id = await used_product_repo.create_device_from_intake(
                    session,
                    intake=intake,
                    appraisal=appraisal,
                    actor_id=actor_id,
                )
            except ValueError as exc:
                raise BusinessException(
                    status_code=409,
                    code="DEVICE_CREATION_FAILED",
                    message=str(exc)
                ) from exc

        await used_product_repo.update_intake_status(
            session,
            intake_id=intake_id,
            status_value=target_status,
            actor_id=actor_id,
            seller_address=seller_address_for_update,
            seller_identity_number=seller_identity_for_update,
            ownership_confirmed=payload.ownershipConfirmed,
            payment_method=payload.acquisitionPaymentMethod,
            payment_reference=payment_reference_for_update,
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
            metadata={
                "paymentMethod": payload.acquisitionPaymentMethod,
                "paymentReference": payment_reference_for_update,
                "ownershipConfirmed": payload.ownershipConfirmed,
            } if target_status == "ACCEPTED" else None,
        )
        await session.commit()
        return {
            "id": str(intake_id),
            "status": target_status,
            "deviceId": str(device_id) if device_id else None,
        }
    except Exception as exc:
        await session.rollback()
        if isinstance(exc, IntegrityError):
            raise BusinessException(
                status_code=409,
                code="DUPLICATE_ACTIVE_IMEI",
                message="IMEI này đã được đăng ký cho thiết bị khác."
            ) from exc
        raise exc


async def inspect_intake(
    session: AsyncSession,
    *,
    intake_id: UUID,
    payload: UsedDeviceInspectionPayload,
    actor_id: UUID,
) -> dict:
    try:
        intake = await used_product_repo.get_intake_for_update(session, intake_id)
        if not intake:
            raise BusinessException(
                status_code=404,
                code="INTAKE_NOT_FOUND",
                message="Không tìm thấy hồ sơ tiếp nhận hàng cũ."
            )
        if intake["status"] not in {"RECEIVED", "INSPECTING"}:
            raise BusinessException(
                status_code=409,
                code="INVALID_INTAKE_STATE",
                message="Hồ sơ chưa ở trạng thái có thể thẩm định."
            )
        if payload.outcome == "APPRAISED":
            if payload.conditionGrade is None or payload.conditionScore is None:
                raise BusinessException(
                    status_code=400,
                    code="INCOMPLETE_INSPECTION_DATA",
                    message="Thẩm định đạt phải có hạng và điểm tình trạng."
                )
            if payload.proposedAcquisitionPrice is None or payload.proposedSalePrice is None:
                raise BusinessException(
                    status_code=400,
                    code="INCOMPLETE_INSPECTION_PRICE",
                    message="Thẩm định đạt phải có giá thu mua và giá bán đề xuất."
                )
            _validate_saleable_appraisal(payload)
        if payload.outcome == "REPAIR_REQUIRED" and payload.repairCostEstimate <= 0:
            raise BusinessException(
                status_code=400,
                code="REPAIR_COST_REQUIRED",
                message="Thiết bị cần sửa chữa phải có chi phí sửa dự kiến lớn hơn 0.",
            )
        evidence_urls = [item.get("url") for item in payload.evidence if isinstance(item, dict) and item.get("url")]
        await media_repo.claim_media_assets(
            session,
            urls=evidence_urls,
            entity_type="USED_INTAKE",
            entity_id=intake_id,
            allowed_folder="used-products",
        )
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
    except Exception as exc:
        await session.rollback()
        raise exc


async def list_devices(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
) -> list[dict]:
    rows = await used_product_repo.list_devices(
        session,
        status_value=status_value,
        search=search,
    )
    return [_manufacturer_warranty_meta(item) for item in rows]


async def list_source_products(session: AsyncSession, search: str) -> list[dict]:
    return await used_product_repo.list_source_products(session, search)


async def list_device_history(session: AsyncSession, device_id: UUID) -> dict:
    history = await used_product_repo.list_device_history(session, device_id)
    if not history:
        raise BusinessException(
            status_code=404,
            code="DEVICE_NOT_FOUND",
            message="Không tìm thấy thiết bị cũ."
        )
    return history


DEVICE_STATUS_TRANSITIONS = {
    "RETURNED_QC": {"REPAIRING", "RETIRED"},
    "REPAIRING": {"RETURNED_QC", "RETIRED"},
}


async def reinspect_device(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload: UsedDeviceInspectionPayload,
    actor_id: UUID,
) -> dict:
    try:
        device = await used_product_repo.get_device_for_listing(session, device_id)
        if not device:
            raise BusinessException(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Không tìm thấy thiết bị cũ."
            )
        current_status = str(device["status"])
        if current_status != "RETURNED_QC":
            raise BusinessException(
                status_code=409,
                code="INVALID_QC_STATE",
                message="Chỉ thiết bị hoàn về chờ QC mới có thể thẩm định lại."
            )
        if payload.outcome == "APPRAISED":
            if not payload.conditionGrade or payload.conditionScore is None:
                raise BusinessException(
                    status_code=400,
                    code="INCOMPLETE_QC_DATA",
                    message="QC đạt phải có hạng và điểm tình trạng."
                )
            if payload.proposedSalePrice is None or payload.proposedSalePrice <= 0:
                raise BusinessException(
                    status_code=400,
                    code="INVALID_QC_PRICE",
                    message="QC đạt phải có giá bán hàng cũ mới."
                )
            _validate_saleable_appraisal(
                payload,
                acquisition_cost=Decimal(str(device["acquisition_cost"] or 0)),
            )
        if payload.outcome == "REPAIR_REQUIRED" and payload.repairCostEstimate <= 0:
            raise BusinessException(
                status_code=400,
                code="REPAIR_COST_REQUIRED",
                message="Thiết bị cần sửa chữa phải có chi phí sửa dự kiến."
            )

        evidence_urls = [item.get("url") for item in payload.evidence if isinstance(item, dict) and item.get("url")]
        await media_repo.claim_media_assets(
            session,
            urls=evidence_urls,
            entity_type="USED_DEVICE",
            entity_id=device_id,
            allowed_folder="used-products",
        )
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
    except Exception as exc:
        await session.rollback()
        raise exc


async def update_device_status(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload,
    actor_id: UUID,
) -> dict:
    try:
        device = await used_product_repo.get_device_for_listing(session, device_id)
        if not device:
            raise BusinessException(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Không tìm thấy thiết bị cũ."
            )
        current_status = str(device["status"])
        target_status = payload.status
        if target_status not in DEVICE_STATUS_TRANSITIONS.get(current_status, set()):
            raise BusinessException(
                status_code=409,
                code="INVALID_STATUS_TRANSITION",
                message=f"Không thể chuyển thiết bị từ {current_status} sang {target_status}."
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
    except Exception as exc:
        await session.rollback()
        raise exc


async def add_device_repair(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload,
    actor_id: UUID,
) -> dict:
    try:
        device = await used_product_repo.get_device_for_listing(session, device_id)
        if not device:
            raise BusinessException(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Không tìm thấy thiết bị cũ.",
            )
        if device["status"] in {"READY_FOR_SALE", "RESERVED", "SOLD", "RETIRED"}:
            raise BusinessException(
                status_code=409,
                code="INVALID_REPAIR_STATE",
                message="Phải ẩn bài đăng trước khi sửa chữa; không thể sửa máy đang giữ, đã bán hoặc đã ngừng kinh doanh.",
            )
        acquisition_cost = Decimal(str(device["acquisition_cost"] or 0))
        approved_sale_price = Decimal(str(device["approved_sale_price"] or 0))
        current_repair_cost = Decimal(
            str(
                await session.scalar(
                    text("SELECT COALESCE(SUM(cost), 0) FROM used_device_repairs WHERE device_id = :device_id"),
                    {"device_id": device_id},
                )
                or 0
            )
        )
        next_total_cost = acquisition_cost + current_repair_cost + payload.cost
        if approved_sale_price > 0 and approved_sale_price <= next_total_cost:
            raise BusinessException(
                status_code=400,
                code="INVALID_ACTUAL_MARGIN",
                message="Chi phí sửa chữa làm giá bán không còn cao hơn tổng giá vốn; phải định giá lại trước.",
            )
        repair_id = await used_product_repo.add_device_repair(
            session,
            device_id=device_id,
            payload=payload,
            actor_id=actor_id,
        )
        await used_product_repo.insert_event(
            session,
            intake_id=device["intake_request_id"],
            device_id=device_id,
            event_type="DEVICE_REPAIR_RECORDED",
            old_status=str(device["status"]),
            new_status=str(device["status"]),
            actor_id=actor_id,
            note=payload.description,
            metadata={"repairId": str(repair_id), "cost": float(payload.cost)},
        )
        await session.commit()
        return {"id": str(repair_id), "deviceId": str(device_id)}
    except Exception as exc:
        await session.rollback()
        raise exc


async def save_listing(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload: UsedDeviceListingPayload,
    actor_id: UUID,
) -> dict:
    try:
        if payload.manufacturerWarrantyEnabled and (
            not payload.manufacturerWarrantyActivatedAt or not payload.manufacturerWarrantyTotalMonths
        ):
            raise BusinessException(
                status_code=400,
                code="MANUFACTURER_WARRANTY_INCOMPLETE",
                message="Bảo hành chính hãng phải có ngày kích hoạt và tổng thời hạn bảo hành.",
            )
        device = await used_product_repo.get_device_for_listing(session, device_id)
        if not device:
            raise BusinessException(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Không tìm thấy thiết bị cũ."
            )
        if device["status"] in {"RESERVED", "SOLD", "RETURNED_QC", "RETIRED"}:
            raise BusinessException(
                status_code=409,
                code="INVALID_DEVICE_STATE",
                message="Thiết bị không thể tạo hoặc sửa bài đăng ở trạng thái hiện tại."
            )
        snapshot = device["original_snapshot"] or {}
        new_reference_price = Decimal(str(snapshot.get("newReferencePrice") or 0))
        sale_price = Decimal(str(device["approved_sale_price"] or 0))
        if sale_price <= 0:
            raise BusinessException(
                status_code=409,
                code="INVALID_SALE_PRICE",
                message="Thiết bị chưa có giá bán hàng cũ hợp lệ."
            )
        if new_reference_price > 0 and sale_price >= new_reference_price and not payload.priceComparisonNote:
            raise BusinessException(
                status_code=400,
                code="COMPARISON_NOTE_REQUIRED",
                message="Giá hàng cũ không thấp hơn giá máy mới; phải ghi rõ lý do so sánh giá."
            )
        listing_id = uuid4()
        listing_slug = f"{slugify(payload.title)}-{str(device['device_code']).lower()}"
        await media_repo.claim_media_assets(
            session,
            urls=payload.images,
            entity_type="USED_DEVICE",
            entity_id=device_id,
            allowed_folder="used-products",
        )
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
            raise BusinessException(
                status_code=409,
                code="DUPLICATE_SLUG",
                message="Slug bài đăng hàng cũ đã tồn tại."
            ) from exc
        return {"id": str(saved_id), "slug": listing_slug, "status": "DRAFT"}
    except Exception as exc:
        if not isinstance(exc, BusinessException):
            await session.rollback()
        raise exc


async def update_device_sale_price(
    session: AsyncSession,
    *,
    device_id: UUID,
    payload: UsedDevicePricePayload,
    actor_id: UUID,
) -> dict:
    try:
        device = await used_product_repo.get_device_for_listing(session, device_id)
        if not device:
            raise BusinessException(status_code=404, code="DEVICE_NOT_FOUND", message="Không tìm thấy thiết bị cũ.")
        if device["status"] in {"RESERVED", "SOLD", "RETURNED_QC", "RETIRED"}:
            raise BusinessException(
                status_code=409,
                code="INVALID_DEVICE_STATE",
                message="Không thể cập nhật giá ở trạng thái hiện tại của thiết bị.",
            )
        acquisition_cost = Decimal(str(device["acquisition_cost"] or 0))
        repair_cost = Decimal(
            str(
                await session.scalar(
                    text("SELECT COALESCE(SUM(cost), 0) FROM used_device_repairs WHERE device_id = :device_id"),
                    {"device_id": device_id},
                )
                or 0
            )
        )
        if payload.salePrice <= acquisition_cost + repair_cost:
            raise BusinessException(
                status_code=400,
                code="INVALID_SALE_MARGIN",
                message="Giá bán mới phải lớn hơn tổng giá thu mua và chi phí sửa chữa.",
            )
        result = await used_product_repo.update_device_sale_price(
            session,
            device_id=device_id,
            sale_price=payload.salePrice,
            reason=payload.reason.strip(),
            actor_id=actor_id,
        )
        await used_product_repo.insert_event(
            session,
            intake_id=device["intake_request_id"],
            device_id=device_id,
            event_type="DEVICE_SALE_PRICE_UPDATED",
            old_status=str(device["status"]),
            new_status="LISTING_REVIEW" if result and result.get("listingStatus") == "PUBLISHED" else str(device["status"]),
            actor_id=actor_id,
            note=payload.reason.strip(),
            metadata={"oldPrice": float(result["oldPrice"] or 0), "newPrice": float(payload.salePrice)},
        )
        await session.commit()
        return {"id": str(device_id), "salePrice": float(payload.salePrice), "requiresApproval": result.get("listingStatus") == "PUBLISHED"}
    except Exception:
        await session.rollback()
        raise


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
    try:
        listing = await used_product_repo.get_listing_for_update(session, listing_id)
        if not listing:
            raise BusinessException(
                status_code=404,
                code="LISTING_NOT_FOUND",
                message="Không tìm thấy bài đăng hàng cũ."
            )
        current_status = str(listing["status"])
        target_status = payload.status
        if target_status not in LISTING_TRANSITIONS.get(current_status, set()):
            raise BusinessException(
                status_code=409,
                code="INVALID_STATUS_TRANSITION",
                message=f"Không thể chuyển bài đăng từ {current_status} sang {target_status}."
            )
        if current_status == "PENDING_APPROVAL" and target_status == "DRAFT" and len((payload.note or "").strip()) < 5:
            raise BusinessException(
                status_code=400,
                code="REVISION_REASON_REQUIRED",
                message="Cần nhập lý do yêu cầu chỉnh sửa bài đăng.",
            )
        # Lock and verify device state to prevent race conditions
        device_res = await session.execute(
            text("SELECT status FROM used_devices WHERE id = :device_id FOR UPDATE"),
            {"device_id": listing["device_id"]}
        )
        device_row = device_res.mappings().first()
        if not device_row:
            raise BusinessException(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Không tìm thấy thiết bị tương ứng."
            )
        
        # Check if the actor is SUPER_ADMIN
        actor_role = await session.scalar(
            text(
                """
                SELECT r.code 
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :actor_id
                """
            ),
            {"actor_id": actor_id}
        )
        is_super_admin = (actor_role == "SUPER_ADMIN")

        dev_status = device_row["status"]
        if dev_status in {"SOLD", "RESERVED", "RETIRED", "REPAIRING", "RETURNED_QC"}:
            raise BusinessException(
                status_code=400,
                code="INVALID_DEVICE_STATE",
                message=f"Thiết bị ở trạng thái {dev_status}, không thể thay đổi trạng thái bài đăng."
            )
        if target_status == "PUBLISHED" and not is_super_admin:
            if actor_id == listing.get("created_by") or actor_id == listing.get("updated_by"):
                raise BusinessException(
                    status_code=400,
                    code="APPROVER_MUST_BE_DIFFERENT",
                    message="Người phê duyệt bài đăng không được trùng với người tạo hoặc cập nhật bài đăng."
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
    except Exception as exc:
        await session.rollback()
        raise exc


async def list_admin_listings(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
) -> list[dict]:
    rows = await used_product_repo.list_admin_listings(
        session,
        status_value=status_value,
        search=search,
    )
    return [_manufacturer_warranty_meta(item) for item in rows]


async def list_public_listings(
    session: AsyncSession,
    *,
    search: str,
    grade: str,
    brand_id: str | None,
    category_id: str | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    sort: str,
    page: int,
    limit: int,
) -> dict:
    if grade and grade.upper() not in {"A", "B", "C"}:
        raise BusinessException(
            status_code=400,
            code="INVALID_DEVICE_GRADE",
            message="Hạng thiết bị không hợp lệ."
        )
    result = await used_product_repo.list_published_devices(
        session,
        search=search,
        grade=grade,
        brand_id=brand_id,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        limit=limit,
    )
    result["items"] = [_manufacturer_warranty_meta(item) for item in result["items"]]
    return result


async def get_public_listing(session: AsyncSession, slug: str) -> dict:
    listing = await used_product_repo.get_published_device(session, slug)
    if not listing:
        raise BusinessException(
            status_code=404,
            code="LISTING_NOT_FOUND",
            message="Không tìm thấy thiết bị cũ đang bán."
        )
    imei = str(listing.get("imei") or "")
    listing["maskedImei"] = f"{imei[:4]}•••••••{imei[-4:]}" if len(imei) >= 8 else "Đã xác minh"
    listing.pop("imei", None)
    return _manufacturer_warranty_meta(listing)


async def create_user_buyback_request(
    session: AsyncSession,
    *,
    payload: UserBuybackRequestPayload,
    actor_id: UUID,
) -> dict:
    if not await used_product_repo.product_variant_exists(
        session,
        product_id=payload.productId,
        variant_id=payload.variantId,
    ):
        raise BusinessException(
            status_code=400,
            code="PRODUCT_VARIANT_NOT_FOUND",
            message="Sản phẩm hoặc biến thể gốc không hợp lệ."
        )
    if await used_product_repo.active_imei_exists(session, payload.imei):
        raise BusinessException(
            status_code=409,
            code="IMEI_ALREADY_EXISTS",
            message="IMEI này đã được đăng ký hoặc đang trong một hồ sơ xử lý khác."
        )

    intake_id = uuid4()
    request_code = await used_product_repo.next_request_code(session)
    
    class TempPayload:
        sourceType = "USER_BUYBACK"
        sellerUserId = actor_id
        sellerName = None
        sellerPhone = None
        originalOrderId = None
        returnRequestId = None
        productId = payload.productId
        variantId = payload.variantId
        imei = payload.imei
        serialNumber = None
        expectedPrice = payload.expectedPrice
        note = payload.note
        
    try:
        await used_product_repo.insert_intake(
            session,
            intake_id=intake_id,
            request_code=request_code,
            payload=TempPayload(),
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
            metadata={"sourceType": "USER_BUYBACK"},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BusinessException(
            status_code=409,
            code="INTEGRITY_VIOLATION",
            message="IMEI hoặc mã hồ sơ hàng cũ đã tồn tại."
        ) from exc
    return {"id": str(intake_id), "requestCode": request_code, "status": "SUBMITTED"}


async def list_user_buyback_requests(
    session: AsyncSession,
    *,
    user_id: UUID,
    page: int,
    limit: int,
) -> dict:
    return await used_product_repo.list_intakes(
        session,
        status_value="",
        search="",
        page=page,
        limit=limit,
        seller_user_id=user_id,
    )
