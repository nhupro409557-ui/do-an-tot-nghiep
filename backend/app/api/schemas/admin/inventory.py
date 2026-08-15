from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.api.schemas.media_reference import normalize_media_reference, normalize_media_reference_items

RECEIPT_STATUS_PATTERN = "^(DRAFT|PROCESSING_IMEI|PENDING_APPROVAL|PENDING_SHORTAGE_APPROVAL|APPROVED|COMPLETED|CANCELLED)$"


class InventoryAdjustmentPayload(BaseModel):
    variantId: UUID | None = None
    delta: int | None = None
    quantity: int | None = Field(default=None, ge=0)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    supplierName: str | None = Field(default=None, max_length=160)
    unitCost: float | None = Field(default=None, ge=0)
    locationCode: str | None = Field(default=None, max_length=60)
    locationName: str | None = Field(default=None, max_length=160)
    imeis: list[str] = Field(default_factory=list, max_length=500)
    secondaryImeis: list[str] = Field(default_factory=list, max_length=500)
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)

class InventoryReceiptLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    warehouseLocationId: UUID | None = None
    quantity: int = Field(gt=0, le=500)
    unitCost: float | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    storageLocationCode: str | None = Field(default=None, max_length=60)
    storageLocationName: str | None = Field(default=None, max_length=160)
    imeis: list[str] = Field(default_factory=list, max_length=500)
    secondaryImeis: list[str] = Field(default_factory=list, max_length=500)
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)
    purchaseOrderLineId: UUID | None = None

class InventoryReceiptAttachmentPayload(BaseModel):
    type: str = Field(default="OTHER", pattern="^(INVOICE|DELIVERY_NOTE|GOODS_PHOTO|OTHER)$")
    name: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=1000)
    note: str | None = Field(default=None, max_length=500)

    _normalize_media = field_validator("url", mode="before")(normalize_media_reference)

class InventoryReceiptAttachmentsPayload(BaseModel):
    attachments: list[InventoryReceiptAttachmentPayload] = Field(default_factory=list, max_length=20)

class InventoryReceiptAttachmentDecisionPayload(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)

class InventoryReceiptDiscrepancyPayload(BaseModel):
    lineId: UUID | None = None
    type: str = Field(pattern="^(SHORTAGE|OVERAGE|DAMAGED|WRONG_ITEM|OTHER)$")
    description: str = Field(min_length=1, max_length=500)
    quantity: int | None = Field(default=None, ge=0, le=100000)
    action: str | None = Field(default=None, max_length=500)

class InventoryReceiptPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    receiptReasonCode: str = Field(default="NK_MUA", max_length=30)
    supplierId: UUID | None = None
    supplierName: str | None = Field(default=None, max_length=160)
    purchaseOrderId: UUID | None = None
    invoiceNumber: str | None = Field(default=None, max_length=120)
    invoiceDate: datetime | None = None
    paymentMode: str = Field(default="DEBT", pattern="^(DEBT|PAID)$")
    paymentTermDays: int = Field(default=0, ge=0, le=365)
    dueDate: datetime | None = None
    paidAmount: float = Field(default=0, ge=0)
    discountAmount: float = Field(default=0, ge=0)
    shippingFee: float = Field(default=0, ge=0)
    payableNote: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=500)
    locationCode: str | None = Field(default=None, max_length=60)
    locationName: str | None = Field(default=None, max_length=160)
    qualityStatus: str = Field(default="PENDING", pattern="^(PENDING|PASSED|FAILED)$")
    qualityNote: str | None = Field(default=None, max_length=500)
    quarantine: bool = False
    quarantineLocation: str | None = Field(default=None, max_length=160)
    attachments: list[InventoryReceiptAttachmentPayload] = Field(default_factory=list, max_length=20)
    discrepancies: list[InventoryReceiptDiscrepancyPayload] = Field(default_factory=list, max_length=50)
    status: str = Field(default="DRAFT", pattern=RECEIPT_STATUS_PATTERN)
    lines: list[InventoryReceiptLinePayload] = Field(min_length=1, max_length=100)

class InventoryLocationPayload(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=160)
    zone: str | None = Field(default=None, max_length=160)
    purpose: str = Field(default="STORAGE", pattern="^(STORAGE|WARRANTY|QC|DAMAGED|RETURN|USED|VIRTUAL)$")
    sortOrder: int = Field(default=0, ge=0, le=999999)
    allowMixedSku: bool = True
    lengthCm: float | None = Field(default=None, ge=0, le=100000)
    widthCm: float | None = Field(default=None, ge=0, le=100000)
    heightCm: float | None = Field(default=None, ge=0, le=100000)
    usableRatio: float = Field(default=0.75, gt=0, le=1)
    description: str | None = Field(default=None, max_length=500)

class InventoryLocationStatusPayload(BaseModel):
    isActive: bool


class InventoryLegacyPutawayPayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    locationId: UUID
    quantity: int = Field(gt=0, le=1000000)
    unitCost: float = Field(default=0, ge=0)
    note: str | None = Field(default=None, max_length=500)

class InventoryReceiptStatusPayload(BaseModel):
    status: str = Field(pattern=RECEIPT_STATUS_PATTERN)
    cancelReason: str | None = Field(default=None, max_length=500)

class InventoryOutboundStatusPayload(BaseModel):
    status: str = Field(pattern="^(COMPLETED|CANCELLED|DRAFT|REVERSED)$")
    cancelReason: str | None = Field(default=None, max_length=500)

class InventoryReceiptLineQualityPayload(BaseModel):
    lineId: UUID
    passedQuantity: int = Field(ge=0)
    failedQuantity: int = Field(ge=0)
    notes: str | None = Field(default=None, max_length=500)
    actionType: str | None = Field(default=None, pattern="^(NONE|QUARANTINE|RETURN_TO_SUPPLIER|SCRAP)$")
    images: list[str | dict] = Field(default_factory=list, max_length=12)
    failedLocationId: UUID | None = None
    failedImeis: list[str] = Field(default_factory=list, max_length=500)
    failedSerialNumbers: list[str] = Field(default_factory=list, max_length=500)

    _normalize_media = field_validator("images", mode="before")(normalize_media_reference_items)

class InventoryReceiptQualityPayload(BaseModel):
    qualityStatus: str = Field(pattern="^(PENDING|PASSED|FAILED)$")
    qualityNote: str | None = Field(default=None, max_length=500)
    quarantine: bool = False
    quarantineLocation: str | None = Field(default=None, max_length=160)
    lines: list[InventoryReceiptLineQualityPayload] = Field(default_factory=list)

class InventoryReceiptImeiLinePayload(BaseModel):
    lineId: UUID
    imeis: list[str] = Field(default_factory=list, max_length=500)
    secondaryImeis: list[str] = Field(default_factory=list, max_length=500)
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)
    receivedQuantity: int | None = Field(default=None, ge=0)
    acceptShortage: bool = False
    shortageReason: str | None = Field(default=None, max_length=500)

class InventoryReceiptImeiPayload(BaseModel):
    lines: list[InventoryReceiptImeiLinePayload] = Field(min_length=1, max_length=100)
    shortageReason: str | None = Field(default=None, max_length=500)

class InventoryReceiptReversePayload(BaseModel):
    reason: str = Field(min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=500)

class InventoryIdentifierEditRequestPayload(BaseModel):
    identifierType: str = Field(pattern="^(IMEI|SERIAL)$")
    identifierId: UUID
    newValue: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=5, max_length=500)

class InventoryIdentifierEditDecisionPayload(BaseModel):
    decision: str = Field(pattern="^(APPROVED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)

class InventoryIdentifierLocationRequestPayload(BaseModel):
    identifierType: str = Field(pattern="^(IMEI|SERIAL)$")
    identifierId: UUID | None = None
    identifierValue: str | None = Field(default=None, min_length=1, max_length=120)
    productId: UUID
    variantId: UUID | None = None
    newLocationId: UUID
    reason: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def validate_identifier_reference(self):
        if self.identifierId is None and not (self.identifierValue or "").strip():
            raise ValueError("Phải cung cấp ID hoặc giá trị mã định danh.")
        return self

class InventoryStockCountLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    expectedQuantity: int = Field(ge=0)
    countedQuantity: int = Field(ge=0)
    imeis: list[str] = Field(default_factory=list, max_length=1000)
    serialNumbers: list[str] = Field(default_factory=list, max_length=1000)
    note: str | None = Field(default=None, max_length=500)

class InventoryStockCountPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(default="KIEM_KE_DINH_KY", max_length=120)
    note: str | None = Field(default=None, max_length=500)
    locationCode: str | None = Field(default=None, max_length=60)
    locationName: str | None = Field(default=None, max_length=160)
    lines: list[InventoryStockCountLinePayload] = Field(min_length=1, max_length=1000)

class InventoryStockCountStatusPayload(BaseModel):
    status: str = Field(pattern="^(APPROVED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)

class InventoryAdjustmentRequestLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    currentQuantity: int = Field(ge=0)
    newQuantity: int = Field(ge=0)
    reason: str = Field(min_length=5, max_length=500)
    note: str | None = Field(default=None, max_length=500)

class InventoryAdjustmentRequestPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(default="DIEU_CHINH_THU_CONG", max_length=120)
    note: str | None = Field(default=None, max_length=500)
    locationCode: str | None = Field(default=None, max_length=60)
    locationName: str | None = Field(default=None, max_length=160)
    lines: list[InventoryAdjustmentRequestLinePayload] = Field(min_length=1, max_length=100)

class InventoryAdjustmentRequestStatusPayload(BaseModel):
    status: str = Field(pattern="^(APPROVED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)

class InventoryTransferLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    fromLocationId: UUID
    toLocationId: UUID
    quantity: int = Field(ge=1, le=500)
    imeis: list[str] = Field(default_factory=list, max_length=500)
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)
    identifierPairIds: list[UUID] = Field(default_factory=list, max_length=500)
    targetIdentifierStatus: str | None = Field(
        default=None,
        pattern="^(IN_STOCK|DEFECTIVE_RETURNED|IN_WARRANTY|INSPECTION_PENDING|RETURNED)$",
    )
    note: str | None = Field(default=None, max_length=500)

class InventoryTransferPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(default="CHUYEN_KE", max_length=120)
    note: str | None = Field(default=None, max_length=500)
    lines: list[InventoryTransferLinePayload] = Field(min_length=1, max_length=100)

class InventoryTransferStatusPayload(BaseModel):
    status: str = Field(pattern="^(APPROVED|COMPLETED|CANCELLED|REVERSED)$")
    note: str | None = Field(default=None, max_length=500)

class InventoryInternalHoldLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    locationId: UUID
    quantity: int = Field(ge=1, le=500)
    note: str | None = Field(default=None, max_length=500)
    imeis: list[str] | None = Field(default=None)
    serialNumbers: list[str] | None = Field(default=None)

class InventoryInternalHoldPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    holdType: str = Field(pattern="^(QC_HOLD|CLAIM_HOLD|INTERNAL_HOLD)$")
    reason: str = Field(min_length=5, max_length=500)
    note: str | None = Field(default=None, max_length=500)
    lines: list[InventoryInternalHoldLinePayload] = Field(min_length=1, max_length=100)

class InventoryInternalHoldStatusPayload(BaseModel):
    status: str = Field(pattern="^(APPROVED|COMPLETED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)

class InventoryDisposalLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    locationId: UUID
    quantity: int = Field(ge=1, le=500)
    imeis: list[str] = Field(default_factory=list, max_length=500)
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)
    note: str | None = Field(default=None, max_length=500)

class InventoryDisposalPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    dispositionType: str = Field(pattern="^(SCRAP|LIQUIDATED|OUT_OF_SYSTEM)$")
    reason: str = Field(min_length=5, max_length=500)
    note: str | None = Field(default=None, max_length=500)
    partnerName: str | None = Field(default=None, max_length=160)
    recoveryValue: float | None = Field(default=None, ge=0)
    lines: list[InventoryDisposalLinePayload] = Field(min_length=1, max_length=100)

class InventoryDisposalStatusPayload(BaseModel):
    status: str = Field(pattern="^(APPROVED|COMPLETED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)

class InventoryCostAdjustmentLotPayload(BaseModel):
    lotId: UUID
    newUnitCost: float = Field(ge=0)

class InventoryCostAdjustmentLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    locationId: UUID
    newAverageUnitCost: float = Field(ge=0)
    lotCosts: list[InventoryCostAdjustmentLotPayload] = Field(default_factory=list, max_length=100)
    note: str | None = Field(default=None, max_length=500)

class InventoryCostAdjustmentPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=5, max_length=500)
    note: str | None = Field(default=None, max_length=500)
    lines: list[InventoryCostAdjustmentLinePayload] = Field(min_length=1, max_length=100)

class InventoryCostAdjustmentStatusPayload(BaseModel):
    status: str = Field(pattern="^(APPROVED|COMPLETED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)

class InventorySettingsPayload(BaseModel):
    minimumStock: int = Field(default=0, ge=0)
    blockSaleWhenOutOfStock: bool = True
    cycleCountDays: int | None = Field(default=None, ge=1, le=365)

class VariantInventoryPayload(BaseModel):
    quantity: int = Field(ge=0)
    referenceCode: str = Field(min_length=1, max_length=120)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    reason: str = Field(default="MANUAL_SET", max_length=80)
    note: str | None = Field(default=None, max_length=500)

class InventoryPutawaySuggestion(BaseModel):
    warehouseLocationId: UUID
    locationCode: str
    locationName: str
    availableVolumeCm3: float | None = None
    fillRatio: float | None = None
    fillRatioAfterImport: float | None = None
    matchReason: str
    priority: int  # 1: High, 2: Medium, 3: Low
