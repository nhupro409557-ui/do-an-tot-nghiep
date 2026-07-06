from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_role_code, get_current_user_id, require_permission, require_super_admin
from app.api.schemas.admin import (
    InventoryAdjustmentPayload,
    InventoryAdjustmentRequestPayload,
    InventoryAdjustmentRequestStatusPayload,
    InventoryCostAdjustmentPayload,
    InventoryCostAdjustmentStatusPayload,
    InventoryDisposalPayload,
    InventoryDisposalStatusPayload,
    InventoryIdentifierEditDecisionPayload,
    InventoryIdentifierEditRequestPayload,
    InventoryIdentifierLocationRequestPayload,
    InventoryInternalHoldPayload,
    InventoryInternalHoldStatusPayload,
    InventoryLocationPayload,
    InventoryLocationStatusPayload,
    InventoryReceiptAttachmentDecisionPayload,
    InventoryReceiptAttachmentsPayload,
    InventoryReceiptImeiPayload,
    InventoryReceiptPayload,
    InventoryReceiptQualityPayload,
    InventoryReceiptReversePayload,
    InventoryReceiptStatusPayload, InventoryOutboundStatusPayload,
    InventorySettingsPayload,
    InventoryStockCountPayload,
    InventoryStockCountStatusPayload,
    InventoryTransferPayload,
    InventoryTransferStatusPayload,
    VariantInventoryPayload,
    InventoryPutawaySuggestion,
)
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


@router.get("/inventory/reports/aging", dependencies=[Depends(require_permission("inventory:read"))])
async def get_inventory_aging_report(
    search: str = Query(default=""),
    bucket: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.get_inventory_aging_report(session, search, bucket)


@router.get("/inventory/reports/reconciliation", dependencies=[Depends(require_permission("inventory:read"))])
async def get_inventory_reconciliation_report(
    search: str = Query(default=""),
    issue_type: str = Query(default="", alias="issueType"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.get_inventory_reconciliation_report(session, search, issue_type)


@router.get("/inventory/ledger", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_ledger(
    search: str = Query(default=""),
    product_id: str = Query(default="", alias="productId"),
    date_from: str = Query(default="", alias="dateFrom"),
    date_to: str = Query(default="", alias="dateTo"),
    transaction_type: str = Query(default="", alias="transactionType"),
    reason: str = Query(default=""),
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
        reason=reason,
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


@router.get("/inventory/putaway-suggestions", response_model=list[InventoryPutawaySuggestion], dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_putaway_suggestions(
    product_id: UUID = Query(alias="productId"),
    variant_id: UUID | None = Query(default=None, alias="variantId"),
    quantity: int = Query(default=1, ge=1, le=500),
    reason_code: str = Query(default="NK_MUA", alias="reasonCode"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_putaway_suggestions(
        session,
        product_id=product_id,
        variant_id=variant_id,
        quantity=quantity,
        reason_code=reason_code,
    )


@router.get("/inventory/identifier-edit-requests", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_identifier_edit_requests(
    status_filter: str = Query(default="PENDING", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_identifier_edit_requests(session, status_filter)


@router.get("/inventory/stock-counts/due", dependencies=[Depends(require_permission("inventory:read"))])
async def list_products_due_for_cycle_count(
    due_only: bool = Query(default=False, alias="dueOnly"),
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_products_due_for_cycle_count(
        session,
        due_only=due_only,
        search=search,
    )


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


@router.get("/inventory/transfers", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_transfers(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_transfers(session, search)


@router.post("/inventory/transfers", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_transfer_request(
    payload: InventoryTransferPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_transfer_request(session, payload, current_user_id)


@router.patch("/inventory/transfers/{reference_code}/status", dependencies=[Depends(require_super_admin)])
async def update_inventory_transfer_status(
    reference_code: str,
    payload: InventoryTransferStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_transfer_status(session, reference_code, payload, current_user_id)


@router.get("/inventory/internal-holds", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_internal_holds(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_internal_holds(session, search)


@router.post("/inventory/internal-holds", dependencies=[Depends(require_permission("inventory:reserve"))])
async def create_inventory_internal_hold(
    payload: InventoryInternalHoldPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_internal_hold(session, payload, current_user_id)


@router.patch("/inventory/internal-holds/{reference_code}/status", dependencies=[Depends(require_super_admin)])
async def update_inventory_internal_hold_status(
    reference_code: str,
    payload: InventoryInternalHoldStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_internal_hold_status(session, reference_code, payload, current_user_id)


@router.get("/inventory/disposals", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_disposals(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_disposals(session, search)


@router.post("/inventory/disposals", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_disposal(
    payload: InventoryDisposalPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_disposal(session, payload, current_user_id)


@router.patch("/inventory/disposals/{reference_code}/status", dependencies=[Depends(require_super_admin)])
async def update_inventory_disposal_status(
    reference_code: str,
    payload: InventoryDisposalStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_disposal_status(session, reference_code, payload, current_user_id)


@router.get("/inventory/cost-adjustments", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_cost_adjustments(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_cost_adjustments(session, search)


@router.post("/inventory/cost-adjustments", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_cost_adjustment(
    payload: InventoryCostAdjustmentPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_cost_adjustment(session, payload, current_user_id)


@router.patch("/inventory/cost-adjustments/{reference_code}/status", dependencies=[Depends(require_super_admin)])
async def update_inventory_cost_adjustment_status(
    reference_code: str,
    payload: InventoryCostAdjustmentStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_cost_adjustment_status(session, reference_code, payload, current_user_id)


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


@router.get("/inventory/identifier-location-requests", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_identifier_location_requests(
    status: str = Query(default="PENDING"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_inventory_identifier_location_requests(session, status)


@router.post("/inventory/identifier-location-requests", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_inventory_identifier_location_request(
    payload: InventoryIdentifierLocationRequestPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.create_inventory_identifier_location_request(session, payload, current_user_id)


@router.patch("/inventory/identifier-location-requests/{request_id}", dependencies=[Depends(require_super_admin)])
async def decide_inventory_identifier_location_request(
    request_id: UUID,
    payload: InventoryIdentifierEditDecisionPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.decide_inventory_identifier_location_request(session, request_id, payload, current_user_id)


# Receipts
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


@router.patch("/inventory/receipts/{reference_code}/attachments", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_receipt_attachments(
    reference_code: str,
    payload: InventoryReceiptAttachmentsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.update_inventory_receipt_attachments(session, reference_code, payload, current_user_id)


@router.patch("/inventory/receipts/{reference_code}/attachments/decision", dependencies=[Depends(require_super_admin)])
async def decide_inventory_receipt_attachments(
    reference_code: str,
    payload: InventoryReceiptAttachmentDecisionPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await inventory_service.decide_inventory_receipt_attachments(session, reference_code, payload, current_user_id)


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


# Outbound Delivery Documents
from pydantic import BaseModel

class OutboundAllocationPayload(BaseModel):
    locationId: str | None = None
    quantity: int = 0
    imeis: list[str] = []
    serialNumbers: list[str] = []

class OutboundLineUpdatePayload(BaseModel):
    id: str | None = None
    lineId: str | None = None
    locationId: str | None = None
    approvedQuantity: int | None = None
    imeis: list[str] = []
    serialNumbers: list[str] = []
    allocations: list[OutboundAllocationPayload] = []


@router.get("/inventory/outbounds", dependencies=[Depends(require_permission("inventory:read"))])
async def list_inventory_outbounds(
    search: str = Query("", description="Tìm kiếm mã phiếu, mã đơn hàng, người nhận"),
    status: str = Query("", description="Trạng thái phiếu"),
    dateFrom: str = Query("", description="Từ ngày"),
    dateTo: str = Query("", description="Đến ngày"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_service.list_outbound_documents(
        session,
        search=search,
        status=status,
        date_from=dateFrom,
        date_to=dateTo,
    )


@router.get("/inventory/outbound-identifier-pair", dependencies=[Depends(require_permission("inventory:read"))])
async def resolve_outbound_identifier_pair(
    product_id: UUID = Query(alias="productId"),
    variant_id: UUID | None = Query(default=None, alias="variantId"),
    location_id: UUID = Query(alias="locationId"),
    identifier_type: str = Query(alias="identifierType"),
    identifier_value: str = Query(alias="identifierValue"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.resolve_outbound_identifier_pair(
        session,
        product_id=product_id,
        variant_id=variant_id,
        location_id=location_id,
        identifier_type=identifier_type,
        identifier_value=identifier_value,
    )


@router.get("/inventory/outbounds/{document_no}", dependencies=[Depends(require_permission("inventory:read"))])
async def get_inventory_outbound(
    document_no: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.get_outbound_document(session, document_no)


@router.put("/inventory/outbounds/{document_no}", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_outbound(
    document_no: str,
    payload: list[OutboundLineUpdatePayload],
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    lines_data = [item.model_dump() for item in payload]
    return await inventory_service.update_outbound_document_lines(
        session,
        document_no,
        lines_data,
        current_user_id,
    )


@router.patch("/inventory/outbounds/{document_no}/status", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_inventory_outbound_status(
    document_no: str,
    payload: InventoryOutboundStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
    current_role_code: str = Depends(get_current_role_code),
) -> dict:
    return await inventory_service.update_outbound_document_status(
        session,
        document_no,
        status_value=payload.status,
        cancel_reason=payload.cancelReason,
        current_user_id=current_user_id,
        current_role_code=current_role_code,
    )


@router.post("/inventory/outbounds/{document_no}/auto-suggest", dependencies=[Depends(require_permission("inventory:adjust"))])
async def auto_suggest_outbound(
    document_no: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await inventory_service.auto_suggest_outbound_document(session, document_no)
