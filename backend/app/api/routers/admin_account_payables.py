from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, require_permission
from app.api.schemas.admin import AccountPayableAdjustmentPayload, SupplierPaymentPayload, SupplierPaymentReversalPayload
from app.application.services import account_payable_service
from app.infrastructure.database.session import get_session

router = APIRouter()


@router.get("/account-payables", dependencies=[Depends(require_permission("payable:read"))])
async def list_account_payables(
    search: str = Query(default="", max_length=120),
    status_filter: str = Query(default="ALL", alias="status"),
    supplier_id: UUID | None = Query(default=None, alias="supplierId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await account_payable_service.list_account_payables(
        session,
        search=search,
        status_filter=status_filter,
        supplier_id=supplier_id,
        page=page,
        page_size=page_size,
    )


@router.get("/account-payables/summary", dependencies=[Depends(require_permission("payable:read"))])
async def get_account_payable_summary(session: AsyncSession = Depends(get_session)) -> dict:
    return await account_payable_service.get_account_payable_summary(session)


@router.get("/account-payables/{payable_id}", dependencies=[Depends(require_permission("payable:read"))])
async def get_account_payable_detail(
    payable_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await account_payable_service.get_account_payable_detail(session, payable_id)


@router.post("/account-payables/{payable_id}/payments", dependencies=[Depends(require_permission("payable:pay"))])
async def create_supplier_payment(
    payable_id: UUID,
    payload: SupplierPaymentPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=120),
) -> dict:
    return await account_payable_service.create_supplier_payment(
        session,
        payable_id=payable_id,
        payload=payload,
        current_user_id=current_user_id,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/account-payables/{payable_id}/payment-reversals",
    dependencies=[Depends(require_permission("payable:pay"))],
)
async def reverse_supplier_payment(
    payable_id: UUID,
    payload: SupplierPaymentReversalPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await account_payable_service.reverse_supplier_payment(
        session,
        payable_id=payable_id,
        payload=payload,
        current_user_id=current_user_id,
    )


@router.post(
    "/account-payables/{payable_id}/adjustments",
    dependencies=[Depends(require_permission("payable:pay"))],
)
async def create_account_payable_adjustment(
    payable_id: UUID,
    payload: AccountPayableAdjustmentPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await account_payable_service.create_account_payable_adjustment(
        session,
        payable_id=payable_id,
        payload=payload,
        current_user_id=current_user_id,
    )
