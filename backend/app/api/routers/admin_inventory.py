from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_role_code, get_current_user_id, require_permission, require_super_admin
from app.api.schemas.admin import InventoryAdjustmentPayload, InventoryAdjustmentRequestPayload, InventoryAdjustmentRequestStatusPayload, InventoryIdentifierEditDecisionPayload, InventoryIdentifierEditRequestPayload, InventoryLocationPayload, InventoryLocationStatusPayload, InventoryReceiptImeiPayload, InventoryReceiptPayload, InventoryReceiptQualityPayload, InventoryReceiptReversePayload, InventoryReceiptStatusPayload, InventorySettingsPayload, InventoryStockCountPayload, InventoryStockCountStatusPayload, VariantInventoryPayload
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


@router.get("/inventory/levels", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_levels(
    search: str = Query(default=""),
    stock_filter: str = Query(default="", alias="stockFilter"),
    location: str = Query(default=""),
    category_id: str = Query(default="", alias="categoryId"),
    brand_id: str = Query(default="", alias="brandId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.list_inventory_levels(session, search, stock_filter, location, category_id, brand_id, page, page_size)


@router.get("/inventory/locations", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_locations(
    search: str = Query(default=""),
    include_inactive: bool = Query(default=True, alias="includeInactive"),
    zone: str = Query(default=""),
    purpose: str = Query(default=""),
    status: str = Query(default=""),
    aisle: str = Query(default=""),
    shelf: str = Query(default=""),
    bin: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_locations(session, search, include_inactive, zone, purpose, status, aisle, shelf, bin)


@router.post("/inventory/locations", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_location(
    payload: InventoryLocationPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.create_inventory_location(session, payload)


@router.put("/inventory/locations/{location_id}", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_location(
    location_id: UUID,
    payload: InventoryLocationPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.update_inventory_location(session, location_id, payload)


@router.patch("/inventory/locations/{location_id}/status", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_location_status(
    location_id: UUID,
    payload: InventoryLocationStatusPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.update_inventory_location_status(session, location_id, payload)


@router.get("/inventory/dashboard", dependencies=[Depends(require_permission("inventory:read"))])
async def get_inventory_dashboard(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.get_inventory_dashboard(session, search)


@router.get("/inventory/ledger", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_ledger(
    search: str = Query(default=""),
    product_id: str = Query(default="", alias="productId"),
    date_from: str = Query(default="", alias="dateFrom"),
    date_to: str = Query(default="", alias="dateTo"),
    transaction_type: str = Query(default="", alias="transactionType"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.list_inventory_ledger(
        session,
        search=search,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        page=page,
        page_size=page_size,
    )


@router.get("/inventory/identifiers", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_identifiers(
    product_id: UUID = Query(alias="productId"),
    variant_id: UUID | None = Query(default=None, alias="variantId"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.list_inventory_identifiers(session, product_id, variant_id)


@router.get("/inventory/issue-suggestions", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_issue_suggestions(
    product_id: UUID = Query(alias="productId"),
    variant_id: UUID | None = Query(default=None, alias="variantId"),
    quantity: int = Query(default=1, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_issue_suggestions(session, product_id, variant_id, quantity)


@router.get("/inventory/identifier-edit-requests", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_identifier_edit_requests(
    status_filter: str = Query(default="PENDING", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_identifier_edit_requests(session, status_filter)


@router.get("/inventory/stock-counts", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_stock_counts(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_stock_counts(session, search)


@router.post("/inventory/stock-counts", dependencies=[Depends(require_permission("inventory:count"))])
async def create_inventory_stock_count(
    payload: InventoryStockCountPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_stock_count(session, payload, current_user_id)


@router.patch("/inventory/stock-counts/{reference_code}/status", dependencies=[Depends(require_super_admin)])
async def update_inventory_stock_count_status(
    reference_code: str,
    payload: InventoryStockCountStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_stock_count_status(session, reference_code, payload, current_user_id)


@router.get("/inventory/adjustments", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_adjustments(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_adjustments(session, search)


@router.post("/inventory/adjustments", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_adjustment_request(
    payload: InventoryAdjustmentRequestPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_adjustment_request(session, payload, current_user_id)


@router.patch("/inventory/adjustments/{reference_code}/status", dependencies=[Depends(require_super_admin)])
async def update_inventory_adjustment_status(
    reference_code: str,
    payload: InventoryAdjustmentRequestStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_adjustment_status(session, reference_code, payload, current_user_id)


@router.post("/inventory/identifier-edit-requests", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_identifier_edit_request(
    payload: InventoryIdentifierEditRequestPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_identifier_edit_request(session, payload, current_user_id)


@router.patch("/inventory/identifier-edit-requests/{request_id}", dependencies=[Depends(require_super_admin)])
async def decide_inventory_identifier_edit_request(
    request_id: UUID,
    payload: InventoryIdentifierEditDecisionPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.decide_inventory_identifier_edit_request(session, request_id, payload, current_user_id)


@router.get("/inventory/receipts", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_receipts(
    search: str = Query(default=""),
    date_from: str = Query(default="", alias="dateFrom"),
    date_to: str = Query(default="", alias="dateTo"),
    status: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.list_inventory_receipts(session, search, date_from, date_to, status, page, page_size)


@router.get("/inventory/receipts/report", dependencies=[Depends(require_permission("inventory:read"))])
async def get_inventory_receipt_report(
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.get_inventory_receipt_report(session)


@router.get("/inventory/receipts/{reference_code}/export", dependencies=[Depends(require_permission("inventory:read"))])
async def export_inventory_receipt_document(
    reference_code: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    return await inventory_service.export_inventory_receipt_document(session, reference_code, format)


@router.post("/products/{product_id}/inventory/adjust", dependencies=[Depends(require_super_admin)])
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
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_receipt(session, payload, idempotency_key, current_user_id)


@router.put("/inventory/receipts/{reference_code}", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_receipt(
    reference_code: str,
    payload: InventoryReceiptPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
    current_role_code: str = Depends(get_current_role_code),
) -> dict:
    return await inventory_service.update_inventory_receipt(session, reference_code, payload, current_user_id, current_role_code)


@router.patch("/inventory/receipts/{reference_code}/quality", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_receipt_quality(
    reference_code: str,
    payload: InventoryReceiptQualityPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_receipt_quality(session, reference_code, payload, current_user_id)


@router.delete("/inventory/receipts/{reference_code}", dependencies=[Depends(require_permission("inventory:adjust"))])
async def delete_inventory_receipt(
    reference_code: str,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.delete_inventory_receipt(session, reference_code, current_user_id)


@router.patch("/inventory/receipts/{reference_code}/status", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_receipt_status(
    reference_code: str,
    payload: InventoryReceiptStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
    current_role_code: str = Depends(get_current_role_code),
) -> dict:
    return await inventory_service.update_inventory_receipt_status(session, reference_code, payload, current_user_id, current_role_code)


@router.post("/inventory/receipts/{reference_code}/imeis", dependencies=[Depends(require_permission("inventory:adjust"))])
async def submit_inventory_receipt_imeis(
    reference_code: str,
    payload: InventoryReceiptImeiPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.submit_inventory_receipt_imeis(session, reference_code, payload, current_user_id)


@router.post("/inventory/receipts/{reference_code}/reverse", dependencies=[Depends(require_super_admin)])
async def reverse_inventory_receipt(
    reference_code: str,
    payload: InventoryReceiptReversePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.reverse_inventory_receipt(session, reference_code, payload, current_user_id)


@router.patch("/products/{product_id}/variants/{variant_id}/inventory", dependencies=[Depends(require_super_admin)])
async def set_variant_inventory(
    product_id: UUID,
    variant_id: UUID,
    payload: VariantInventoryPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.set_variant_inventory(session, product_id, variant_id, payload)
