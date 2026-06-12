from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.api.schemas.admin import InventoryAdjustmentPayload, InventoryReceiptPayload, InventorySettingsPayload, VariantInventoryPayload
from app.infrastructure.database.session import get_session
from app.application.services import inventory_service

router = APIRouter()


@router.get("/products/{product_id}/inventory", dependencies=[Depends(require_permission("inventory:read"))])
async def get_product_inventory(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await inventory_service.get_product_inventory(session, product_id)


@router.patch("/products/{product_id}/inventory/settings", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_product_inventory_settings(
    product_id: UUID,
    payload: InventorySettingsPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.update_product_inventory_settings(session, product_id, payload)


@router.get("/inventory/export", dependencies=[Depends(require_permission("inventory:read"))])
async def export_inventory_snapshot(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> Response:
    return await inventory_service.export_inventory_snapshot(session, search)


@router.get("/inventory/receipts", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_receipts(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_receipts(session, search)


@router.post("/products/{product_id}/inventory/adjust", dependencies=[Depends(require_permission("inventory:adjust"))])
async def adjust_product_inventory(
    product_id: UUID,
    payload: InventoryAdjustmentPayload,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.adjust_product_inventory(session, product_id, payload, idempotency_key)


@router.post("/inventory/receipts", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_receipt(
    payload: InventoryReceiptPayload,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.create_inventory_receipt(session, payload, idempotency_key)


@router.patch("/products/{product_id}/variants/{variant_id}/inventory", dependencies=[Depends(require_permission("inventory:adjust"))])
async def set_variant_inventory(
    product_id: UUID,
    variant_id: UUID,
    payload: VariantInventoryPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.set_variant_inventory(session, product_id, variant_id, payload)
