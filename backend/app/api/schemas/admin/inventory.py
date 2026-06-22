from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

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
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)

class InventoryReceiptAttachmentPayload(BaseModel):
    type: str = Field(default="OTHER", pattern="^(INVOICE|DELIVERY_NOTE|GOODS_PHOTO|OTHER)$")
    name: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=1000)
    note: str | None = Field(default=None, max_length=500)

class InventoryReceiptDiscrepancyPayload(BaseModel):
    type: str = Field(pattern="^(SHORTAGE|OVERAGE|DAMAGED|WRONG_ITEM|OTHER)$")
    description: str = Field(min_length=1, max_length=500)
    quantity: int | None = Field(default=None, ge=0, le=100000)
    action: str | None = Field(default=None, max_length=500)

class InventoryReceiptPayload(BaseModel):
    referenceCode: str = Field(min_length=1, max_length=120)
    receiptReasonCode: str = Field(default="NK_MUA", max_length=30)
    supplierName: str | None = Field(default=None, max_length=160)
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
    purpose: str = Field(default="STORAGE", pattern="^(STORAGE|WARRANTY|QC|DAMAGED|RETURN|VIRTUAL)$")
    sortOrder: int = Field(default=0, ge=0, le=999999)
    allowMixedSku: bool = True
    lengthCm: float | None = Field(default=None, ge=0, le=100000)
    widthCm: float | None = Field(default=None, ge=0, le=100000)
    heightCm: float | None = Field(default=None, ge=0, le=100000)
    usableRatio: float = Field(default=0.75, gt=0, le=1)
    description: str | None = Field(default=None, max_length=500)

class InventoryLocationStatusPayload(BaseModel):
    isActive: bool

class InventoryReceiptStatusPayload(BaseModel):
    status: str = Field(pattern=RECEIPT_STATUS_PATTERN)
    cancelReason: str | None = Field(default=None, max_length=500)

class InventoryReceiptQualityPayload(BaseModel):
    qualityStatus: str = Field(pattern="^(PENDING|PASSED|FAILED)$")
    qualityNote: str | None = Field(default=None, max_length=500)
    quarantine: bool = False
    quarantineLocation: str | None = Field(default=None, max_length=160)

class InventoryReceiptImeiLinePayload(BaseModel):
    lineId: UUID
    imeis: list[str] = Field(default_factory=list, max_length=500)
    serialNumbers: list[str] = Field(default_factory=list, max_length=500)
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

class InventoryStockCountLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    expectedQuantity: int = Field(ge=0)
    countedQuantity: int = Field(ge=0)
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
