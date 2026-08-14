from uuid import UUID

from pydantic import BaseModel, Field


class AfterSalesItemInput(BaseModel):
    order_item_id: UUID
    quantity: int = Field(default=1, ge=1)
    imei: str | None = Field(default=None, max_length=80)
    serial_number: str | None = Field(default=None, max_length=120)


class CreateAfterSalesRequest(BaseModel):
    order_id: UUID
    reason: str = Field(min_length=10, max_length=2000)
    items: list[AfterSalesItemInput] = Field(min_length=1, max_length=20)
    has_accessories: bool = True
    good_appearance: bool = True
    account_unlocked: bool = True
    has_vat_invoice: bool = True
    exchange_product_id: UUID | None = None
    exchange_variant_id: UUID | None = None
    exchange_quantity: int = Field(default=1, ge=1, le=20)


class ReplacementItemInput(BaseModel):
    request_item_id: UUID
    imeis: list[str] = Field(default_factory=list, max_length=20)
    serial_numbers: list[str] = Field(default_factory=list, max_length=20)


class UpdateAfterSalesStatusRequest(BaseModel):
    status: str
    resolution_type: str | None = None
    note: str | None = Field(default=None, max_length=4000)
    customer_fault: bool = False
    replacement_imei: str | None = Field(default=None, max_length=80)
    replacement_items: list[ReplacementItemInput] = Field(default_factory=list, max_length=20)
    refund_transaction_ref: str | None = Field(default=None, max_length=160)
    refund_proof_url: str | None = Field(default=None, max_length=500)
    refund_note: str | None = Field(default=None, max_length=1000)
    shipping_deduction: float = Field(default=0, ge=0)
    depreciation_fee: float = Field(default=0, ge=0)
    exchange_payment_reference: str | None = Field(default=None, max_length=160)
    repair_diagnosis: str | None = Field(default=None, max_length=2000)
    repair_action: str | None = Field(default=None, max_length=2000)
    repair_parts: str | None = Field(default=None, max_length=2000)
    repair_cost: float = Field(default=0, ge=0)
    repair_channel: str | None = Field(default=None, pattern="^(INTERNAL|MANUFACTURER)$")
    repair_provider_name: str | None = Field(default=None, max_length=255)
    return_fulfillment_method: str | None = Field(default=None, pattern="^(DELIVERY|STORE_PICKUP)$")
    recipient_name: str | None = Field(default=None, min_length=2, max_length=255)
    recipient_phone: str | None = Field(default=None, min_length=8, max_length=30)
    shipping_address: str | None = Field(default=None, min_length=10, max_length=1000)
    shipping_provider: str | None = Field(default=None, max_length=120)
    customer_receipt_confirmed: bool = False


class RepairedDeviceUsedIntakeRequest(BaseModel):
    confirmed: bool = False
    note: str | None = Field(default=None, max_length=2000)


class InspectAfterSalesRequest(BaseModel):
    result: str
    qc_note: str = Field(min_length=10, max_length=4000)
    customer_fault: bool = False
    depreciation_fee: float = Field(default=0, ge=0)
    shipping_deduction: float = Field(default=0, ge=0)
    exchange_fee: float | None = Field(default=None, ge=0)
    exchange_shipping_fee: float = Field(default=0, ge=0)
    inventory_disposition: str | None = Field(default=None, pattern="^(NEW_STOCK|USED_INTAKE|REPAIR|SCRAP)$")
    repair_channel: str | None = Field(default=None, pattern="^(INTERNAL|MANUFACTURER)$")
    repair_provider_name: str | None = Field(default=None, max_length=255)
    return_fulfillment_method: str | None = Field(default=None, pattern="^(DELIVERY|STORE_PICKUP)$")
    recipient_name: str | None = Field(default=None, min_length=2, max_length=255)
    recipient_phone: str | None = Field(default=None, min_length=8, max_length=30)
    shipping_address: str | None = Field(default=None, min_length=10, max_length=1000)
    shipping_provider: str | None = Field(default=None, max_length=120)


class AfterSalesTimelineNoteRequest(BaseModel):
    note: str = Field(min_length=3, max_length=4000)


class ImeiDispositionRequest(BaseModel):
    status: str = Field(pattern="^(REPAIR_PENDING|REPAIRED|RTV_COMPLETED|LIQUIDATED|SCRAP)$")
    reason: str = Field(default="Xử lý mã định danh lỗi.", min_length=3, max_length=2000)
    document_reference: str | None = Field(default=None, max_length=160)
    partner_name: str | None = Field(default=None, max_length=255)
    recovery_value: float | None = Field(default=None, ge=0)
