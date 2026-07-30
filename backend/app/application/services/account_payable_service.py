from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import SupplierPaymentPayload
from app.infrastructure.database.repositories import account_payable_repo


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


async def ensure_payable_for_completed_receipt(
    session: AsyncSession,
    *,
    document_id: UUID,
    actor_id: UUID | None,
) -> dict | None:
    source = await account_payable_repo.get_receipt_payable_source(session, document_id)
    if not source:
        return None
    if str(source.get("reason") or "").upper() != "NK_MUA":
        return None
    principal_amount = float(source.get("principalAmount") or 0)
    if principal_amount <= 0:
        return None

    metadata = source.get("metadata") or {}
    normalized_source = {
        **source,
        "metadata": {
            **metadata,
            "invoiceDate": _parse_datetime(metadata.get("invoiceDate")),
        },
    }
    payment_term_days = max(0, min(int(metadata.get("paymentTermDays") or 0), 365))
    posted_at = _parse_datetime(source.get("postedAt")) or datetime.now(timezone.utc)
    due_date = _parse_datetime(metadata.get("dueDate")) or (posted_at + timedelta(days=payment_term_days))
    payment_mode = str(metadata.get("paymentMode") or "DEBT").upper()
    if payment_mode not in {"DEBT", "PAID"}:
        raise HTTPException(status_code=400, detail="Hình thức thanh toán công nợ không hợp lệ.")

    paid_amount = principal_amount if payment_mode == "PAID" else float(metadata.get("paidAmount") or 0)
    if paid_amount < 0:
        raise HTTPException(status_code=400, detail="Số tiền đã trả trước không được âm.")
    if paid_amount > principal_amount:
        raise HTTPException(
            status_code=400,
            detail="Số tiền đã trả trước không được vượt quá tổng giá trị phiếu nhập.",
        )

    payable = await account_payable_repo.upsert_payable_from_receipt(
        session,
        source=normalized_source,
        due_date=due_date,
        payment_term_days=payment_term_days,
        paid_amount=paid_amount,
        actor_id=actor_id,
    )
    await account_payable_repo.insert_payable_event(
        session,
        payable_id=payable["id"],
        event_type="UPSERT_FROM_RECEIPT",
        amount=principal_amount,
        actor_id=actor_id,
        metadata={
            "sourceReferenceCode": source.get("referenceCode"),
            "paymentMode": payment_mode,
            "paymentTermDays": payment_term_days,
        },
    )
    return payable


async def list_account_payables(
    session: AsyncSession,
    *,
    search: str = "",
    status_filter: str = "ALL",
    supplier_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    normalized_status = str(status_filter or "ALL").upper()
    if normalized_status not in {"ALL", "OPEN", "PARTIAL", "PAID", "OVERDUE", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Trạng thái công nợ không hợp lệ.")
    return await account_payable_repo.list_account_payables(
        session,
        search=search.strip(),
        status_filter=normalized_status,
        supplier_id=supplier_id,
        page=page,
        page_size=page_size,
    )


async def get_account_payable_detail(session: AsyncSession, payable_id: UUID) -> dict:
    detail = await account_payable_repo.get_account_payable_detail(session, payable_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công nợ nhà cung cấp.")
    return detail


async def get_account_payable_summary(session: AsyncSession) -> dict:
    return await account_payable_repo.get_account_payable_summary(session)


async def create_supplier_payment(
    session: AsyncSession,
    *,
    payable_id: UUID,
    payload: SupplierPaymentPayload,
    current_user_id: UUID | None,
) -> dict:
    payable = await account_payable_repo.get_account_payable_for_update(session, payable_id)
    if not payable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công nợ nhà cung cấp.")
    if payable["status"] in {"PAID", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Công nợ đã đóng, không thể ghi nhận thêm thanh toán.")

    amount = float(payload.amount)
    remaining = float(payable.get("remaining_amount") or 0)
    if amount > remaining:
        raise HTTPException(status_code=400, detail="Số tiền thanh toán không được vượt quá số còn nợ.")

    payment_date = payload.paymentDate or datetime.now(timezone.utc)
    payment = await account_payable_repo.insert_supplier_payment(
        session,
        payable_id=payable_id,
        supplier_id=payable.get("supplier_id"),
        amount=amount,
        payment_date=payment_date,
        method=payload.method,
        reference_no=(payload.referenceNo or "").strip() or None,
        note=(payload.note or "").strip() or None,
        created_by=current_user_id,
    )
    next_paid = float(payable.get("paid_amount") or 0) + amount
    next_remaining = max(float(payable.get("principal_amount") or 0) - next_paid, 0)
    next_status = "PAID" if next_remaining <= 0 else "PARTIAL"
    await account_payable_repo.update_payable_payment_totals(
        session,
        payable_id=payable_id,
        paid_amount=next_paid,
        remaining_amount=next_remaining,
        status=next_status,
        actor_id=current_user_id,
    )
    await account_payable_repo.insert_payable_event(
        session,
        payable_id=payable_id,
        event_type="PAYMENT_RECORDED",
        amount=amount,
        actor_id=current_user_id,
        metadata={"paymentId": payment.get("id"), "method": payload.method, "referenceNo": payload.referenceNo},
    )
    await session.commit()
    return {"ok": True, "payment": payment, "status": next_status, "remainingAmount": next_remaining}


async def cancel_payable_for_reversed_receipt(
    session: AsyncSession,
    *,
    source_document_id: UUID,
    actor_id: UUID | None,
    note: str | None,
) -> None:
    cancelled_rows = await account_payable_repo.cancel_payable_by_source_document(
        session,
        source_document_id=source_document_id,
        actor_id=actor_id,
        note=note,
    )
    for item in cancelled_rows:
        await account_payable_repo.insert_payable_event(
            session,
            payable_id=item["id"],
            event_type="CANCELLED_BY_RECEIPT_REVERSAL",
            actor_id=actor_id,
            metadata={"sourceDocumentId": str(source_document_id), "note": note},
        )


async def ensure_receipt_reversal_allowed(session: AsyncSession, source_document_id: UUID) -> None:
    payable = await account_payable_repo.get_payable_by_source_document(session, source_document_id)
    if payable and float(payable.get("paidAmount") or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Phiếu nhập đã phát sinh thanh toán công nợ. Phải hoàn hoặc điều chỉnh khoản thanh toán trước khi đảo phiếu.",
        )
