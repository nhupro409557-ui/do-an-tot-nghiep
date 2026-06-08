from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import AttachedServicePayload
from app.infrastructure.database.repositories import attached_service_repo


def _normalize_attached_service_pricing(payload: AttachedServicePayload) -> dict:
    if payload.serviceType == "PRODUCT_SERVICE":
        return {
            "price_mode": "TIERED_AMOUNT",
            "fixed_price": 0,
            "percent_value": 0,
            "base_amount": 0,
        }
    return {
        "price_mode": payload.priceMode,
        "fixed_price": payload.fixedPrice,
        "percent_value": payload.percentValue,
        "base_amount": payload.baseAmount,
    }


async def list_attached_services(session: AsyncSession) -> list[dict]:
    return await attached_service_repo.list_attached_services(session)


async def create_attached_service(session: AsyncSession, payload: AttachedServicePayload) -> dict:
    service_id = uuid4()
    pricing = _normalize_attached_service_pricing(payload)
    await attached_service_repo.insert_attached_service(
        session,
        service_id=service_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        service_type=payload.serviceType,
        attribute_group=payload.attributeGroup or None,
        duration_months=payload.durationMonths,
        is_active=payload.isActive,
        metadata=payload.metadata,
        **pricing,
    )
    await session.commit()
    return {"id": str(service_id)}


async def update_attached_service(
    session: AsyncSession, service_id: UUID, payload: AttachedServicePayload
) -> dict:
    pricing = _normalize_attached_service_pricing(payload)
    metadata = payload.metadata
    if payload.serviceType == "PRODUCT_SERVICE" and not metadata:
        metadata = await attached_service_repo.get_attached_service_metadata(session, service_id) or {}
    updated = await attached_service_repo.update_attached_service(
        session,
        service_id=service_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        service_type=payload.serviceType,
        attribute_group=payload.attributeGroup or None,
        duration_months=payload.durationMonths,
        is_active=payload.isActive,
        metadata=metadata,
        **pricing,
    )
    if updated == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    await session.commit()
    return {"ok": True}


async def delete_attached_service(session: AsyncSession, service_id: UUID) -> dict:
    relation_count = await attached_service_repo.attached_service_relation_count(session, service_id)
    if relation_count is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    if relation_count > 0:
        raise HTTPException(status_code=409, detail="Không thể xóa dịch vụ đang được gắn với sản phẩm. Hãy tắt dịch vụ nếu cần ngừng sử dụng.")
    deleted = await attached_service_repo.hard_delete_attached_service(session, service_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    await session.commit()
    return {"ok": True, "action": "deleted"}


async def deactivate_attached_service(session: AsyncSession, service_id: UUID) -> dict:
    updated = await attached_service_repo.deactivate_attached_service(session, service_id)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    await session.commit()
    return {"ok": True, "action": "deactivated"}


async def reactivate_attached_service(session: AsyncSession, service_id: UUID) -> dict:
    updated = await attached_service_repo.reactivate_attached_service(session, service_id)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    await session.commit()
    return {"ok": True, "action": "reactivated"}
