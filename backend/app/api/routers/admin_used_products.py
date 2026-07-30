from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, get_user_permissions, require_permission
from app.api.schemas.admin.used_product import (
    UsedDeviceInspectionPayload,
    UsedDeviceIntakePayload,
    UsedDeviceListingPayload,
    UsedDeviceListingStatusPayload,
    UsedDeviceLifecyclePayload,
    UsedDevicePricePayload,
    UsedDeviceRepairPayload,
    UsedDeviceStatusPayload,
)
from app.application.services import used_product_service
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/used-products", tags=["Admin - Hàng cũ"])


@router.get("/source-products", dependencies=[Depends(require_permission("used_product:read"))])
async def list_source_products(
    search: str = Query(default="", max_length=120),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await used_product_service.list_source_products(session, search)


@router.get("/intakes", dependencies=[Depends(require_permission("used_product:read"))])
async def list_intakes(
    status_value: str = Query(default="", alias="status", max_length=30),
    search: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.list_intakes(
        session,
        status_value=status_value,
        search=search,
        page=page,
        limit=limit,
    )


@router.post(
    "/intakes",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def create_intake(
    payload: UsedDeviceIntakePayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.create_intake(
        session,
        payload=payload,
        actor_id=actor_id,
    )


@router.patch(
    "/intakes/{intake_id}/status",
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def update_intake_status(
    intake_id: UUID,
    payload: UsedDeviceStatusPayload,
    actor_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.status == "ACCEPTED" and "used_product:approve" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xác nhận thu mua hàng cũ.")
    return await used_product_service.update_intake_status(
        session,
        intake_id=intake_id,
        payload=payload,
        actor_id=actor_id,
    )


@router.post(
    "/intakes/{intake_id}/inspections",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def inspect_intake(
    intake_id: UUID,
    payload: UsedDeviceInspectionPayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.inspect_intake(
        session,
        intake_id=intake_id,
        payload=payload,
        actor_id=actor_id,
    )


@router.get("/devices", dependencies=[Depends(require_permission("used_product:read"))])
async def list_devices(
    status_value: str = Query(default="", alias="status", max_length=30),
    search: str = Query(default="", max_length=120),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await used_product_service.list_devices(
        session,
        status_value=status_value,
        search=search,
    )


@router.get("/devices/{device_id}/history", dependencies=[Depends(require_permission("used_product:read"))])
async def list_device_history(
    device_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.list_device_history(session, device_id)


@router.post(
    "/devices/{device_id}/repairs",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def add_device_repair(
    device_id: UUID,
    payload: UsedDeviceRepairPayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.add_device_repair(
        session,
        device_id=device_id,
        payload=payload,
        actor_id=actor_id,
    )


@router.put(
    "/devices/{device_id}/listing",
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def save_listing(
    device_id: UUID,
    payload: UsedDeviceListingPayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.save_listing(
        session,
        device_id=device_id,
        payload=payload,
        actor_id=actor_id,
    )


@router.patch(
    "/devices/{device_id}/price",
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def update_device_sale_price(
    device_id: UUID,
    payload: UsedDevicePricePayload,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await used_product_service.update_device_sale_price(
        session, device_id=device_id, payload=payload, actor_id=actor_id
    )


@router.patch(
    "/devices/{device_id}/status",
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def update_device_status(
    device_id: UUID,
    payload: UsedDeviceLifecyclePayload,
    actor_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.status in {"READY_FOR_PRICING", "RETIRED"} and "used_product:approve" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền duyệt kết quả QC hàng cũ.")
    return await used_product_service.update_device_status(
        session,
        device_id=device_id,
        payload=payload,
        actor_id=actor_id,
    )


@router.post(
    "/devices/{device_id}/reinspection",
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def reinspect_device(
    device_id: UUID,
    payload: UsedDeviceInspectionPayload,
    actor_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.outcome in {"APPRAISED", "REJECTED"} and "used_product:approve" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền duyệt kết quả QC lại hàng cũ.")
    return await used_product_service.reinspect_device(
        session,
        device_id=device_id,
        payload=payload,
        actor_id=actor_id,
    )


@router.get("/listings", dependencies=[Depends(require_permission("used_product:read"))])
async def list_listings(
    status_value: str = Query(default="", alias="status", max_length=30),
    search: str = Query(default="", max_length=120),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await used_product_service.list_admin_listings(
        session,
        status_value=status_value,
        search=search,
    )


@router.patch(
    "/listings/{listing_id}/status",
    dependencies=[Depends(require_permission("used_product:manage"))],
)
async def update_listing_status(
    listing_id: UUID,
    payload: UsedDeviceListingStatusPayload,
    actor_id: UUID = Depends(get_current_user_id),
    permissions: set[str] = Depends(get_user_permissions),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.status == "PUBLISHED" and "used_product:approve" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền duyệt đăng bán hàng cũ.")
    return await used_product_service.update_listing_status(
        session,
        listing_id=listing_id,
        payload=payload,
        actor_id=actor_id,
    )
