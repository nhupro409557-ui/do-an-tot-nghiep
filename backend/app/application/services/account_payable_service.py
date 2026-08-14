import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import AccountPayableAdjustmentPayload, SupplierPaymentPayload, SupplierPaymentReversalPayload
from app.infrastructure.database.repositories import account_payable_repo

MONEY_QUANTUM = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _payable_status(principal_amount: Decimal, paid_amount: Decimal) -> str:
    if paid_amount >= principal_amount:
        return "PAID"
    return "PARTIAL" if paid_amount > 0 else "OPEN"


def supplier_payment_request_fingerprint(payload: SupplierPaymentPayload) -> str:
    canonical_payload = {
        "amount": format(_money(payload.amount), "f"),
        "method": payload.method,
        "note": (payload.note or "").strip() or None,
        "paymentDate": payload.paymentDate.isoformat() if payload.paymentDate else None,
        "referenceNo": (payload.referenceNo or "").strip() or None,
    }
    serialized = json.dumps(canonical_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _legacy_payment_matches_payload(existing_payment: dict, payload: SupplierPaymentPayload) -> bool:
    if _money(existing_payment.get("amount")) != _money(payload.amount):
        return False
    if str(existing_payment.get("method") or "") != payload.method:
        return False
    if (existing_payment.get("referenceNo") or "").strip() != (payload.referenceNo or "").strip():
        return False
    if (existing_payment.get("note") or "").strip() != (payload.note or "").strip():
        return False
    if payload.paymentDate is not None:
        return _parse_datetime(existing_payment.get("paymentDate")) == payload.paymentDate
    return True


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
    principal_amount = _money(source.get("principalAmount"))
    if principal_amount <= 0:
        return None

    metadata = source.get("metadata") or {}
    supplier_id_value = metadata.get("supplierId")
    invoice_number = str(metadata.get("invoiceNumber") or "").strip()
    if not supplier_id_value:
        raise HTTPException(status_code=400, detail="Phiếu nhập mua hàng phải có nhà cung cấp trước khi hoàn tất.")
    if not invoice_number:
        raise HTTPException(status_code=400, detail="Phiếu nhập mua hàng phải có số hóa đơn nhà cung cấp trước khi hoàn tất.")
    try:
        supplier_id = UUID(str(supplier_id_value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Nhà cung cấp của phiếu nhập không hợp lệ.") from exc
    try:
        await account_payable_repo.ensure_supplier_invoice_available(
            session,
            supplier_id=supplier_id,
            invoice_number=invoice_number,
            source_document_id=UUID(str(source["documentId"])),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    normalized_source = {
        **source,
        "metadata": {
            **metadata,
            "invoiceDate": _parse_datetime(metadata.get("invoiceDate")),
        },
    }
    try:
        payment_term_days = max(0, min(int(metadata.get("paymentTermDays") or 0), 365))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Số ngày công nợ của phiếu nhập không hợp lệ.") from exc
    posted_at = _parse_datetime(source.get("postedAt")) or datetime.now(timezone.utc)
    due_date = _parse_datetime(metadata.get("dueDate")) or (posted_at + timedelta(days=payment_term_days))
    payment_mode = str(metadata.get("paymentMode") or "DEBT").upper()
    if payment_mode not in {"DEBT", "PAID"}:
        raise HTTPException(status_code=400, detail="Hình thức thanh toán công nợ không hợp lệ.")

    paid_amount = principal_amount if payment_mode == "PAID" else _money(metadata.get("paidAmount"))
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
    payable_id = UUID(str(payable["id"]))
    if paid_amount > 0:
        await account_payable_repo.ensure_supplier_payment_hardening_schema(session)
        prepayment_key = f"receipt-prepayment:{source['documentId']}"
        existing_payment = await account_payable_repo.get_supplier_payment_by_idempotency_key(
            session,
            payable_id=payable_id,
            idempotency_key=prepayment_key,
        )
        if not existing_payment:
            payment = await account_payable_repo.insert_supplier_payment(
                session,
                payable_id=payable_id,
                supplier_id=supplier_id,
                amount=paid_amount,
                payment_date=posted_at,
                method="OTHER",
                reference_no=invoice_number,
                note="Khoản đã trả trước ghi nhận khi hoàn tất phiếu nhập.",
                created_by=actor_id,
                idempotency_key=prepayment_key,
                request_fingerprint=hashlib.sha256(prepayment_key.encode("utf-8")).hexdigest(),
            )
            await account_payable_repo.insert_payable_event(
                session,
                payable_id=payable_id,
                event_type="PAYMENT_RECORDED",
                amount=paid_amount,
                actor_id=actor_id,
                metadata={
                    "paymentId": payment.get("id"),
                    "method": "OTHER",
                    "referenceNo": invoice_number,
                    "source": "RECEIPT_PREPAYMENT",
                },
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
    await account_payable_repo.ensure_supplier_payment_hardening_schema(session)
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
    idempotency_key: str | None,
) -> dict:
    await account_payable_repo.ensure_supplier_payment_hardening_schema(session)
    normalized_key = idempotency_key.strip() if idempotency_key else ""
    if len(normalized_key) < 8:
        raise HTTPException(status_code=400, detail="Khóa chống ghi nhận trùng phải có ít nhất 8 ký tự.")
    request_fingerprint = supplier_payment_request_fingerprint(payload)
    payable = await account_payable_repo.get_account_payable_for_update(session, payable_id)
    if not payable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công nợ nhà cung cấp.")
    existing_payment = await account_payable_repo.get_supplier_payment_by_idempotency_key(
        session,
        payable_id=payable_id,
        idempotency_key=normalized_key,
    )
    if existing_payment:
        existing_fingerprint = existing_payment.get("requestFingerprint")
        payload_conflicts = (
            existing_fingerprint != request_fingerprint
            if existing_fingerprint
            else not _legacy_payment_matches_payload(existing_payment, payload)
        )
        if payload_conflicts:
            raise HTTPException(
                status_code=409,
                detail="Khóa chống ghi nhận trùng đã được dùng cho một nội dung thanh toán khác.",
            )
        return {
            "ok": True,
            "payment": existing_payment,
            "status": payable["status"],
            "remainingAmount": _money(payable.get("remaining_amount")),
            "idempotentReplay": True,
        }
    if payable["status"] in {"PAID", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Công nợ đã đóng, không thể ghi nhận thêm thanh toán.")

    amount = _money(payload.amount)
    remaining = _money(payable.get("remaining_amount"))
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
        idempotency_key=normalized_key,
        request_fingerprint=request_fingerprint,
    )
    next_paid = _money(payable.get("paid_amount")) + amount
    next_remaining = max(_money(payable.get("principal_amount")) - next_paid, Decimal("0.00"))
    next_status = _payable_status(_money(payable.get("principal_amount")), next_paid)
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
    return {
        "ok": True,
        "payment": payment,
        "status": next_status,
        "remainingAmount": next_remaining,
        "idempotentReplay": False,
    }


async def reverse_supplier_payment(
    session: AsyncSession,
    *,
    payable_id: UUID,
    payload: SupplierPaymentReversalPayload,
    current_user_id: UUID | None,
) -> dict:
    await account_payable_repo.ensure_supplier_payment_hardening_schema(session)
    payable = await account_payable_repo.get_account_payable_for_update(session, payable_id)
    if not payable:
        raise HTTPException(status_code=404, detail="Không tìm thấy công nợ nhà cung cấp.")
    if payable["status"] == "CANCELLED":
        raise HTTPException(status_code=400, detail="Công nợ đã hủy, không thể đảo thanh toán.")
    payment = await account_payable_repo.get_supplier_payment_for_update(
        session,
        payable_id=payable_id,
        payment_id=payload.paymentId,
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán thuộc khoản công nợ này.")
    if payment["status"] == "REVERSED":
        raise HTTPException(status_code=409, detail="Thanh toán này đã được đảo trước đó.")

    reason = payload.reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Lý do đảo thanh toán phải có ít nhất 3 ký tự.")
    amount = _money(payment["amount"])
    next_paid = max(_money(payable.get("paid_amount")) - amount, Decimal("0.00"))
    principal = _money(payable.get("principal_amount"))
    next_remaining = max(principal - next_paid, Decimal("0.00"))
    next_status = _payable_status(principal, next_paid)
    await account_payable_repo.reverse_supplier_payment(
        session,
        payment_id=payload.paymentId,
        reason=reason,
        actor_id=current_user_id,
    )
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
        event_type="PAYMENT_REVERSED",
        amount=amount,
        actor_id=current_user_id,
        metadata={"paymentId": str(payload.paymentId), "reason": reason},
    )
    await session.commit()
    return {"ok": True, "status": next_status, "remainingAmount": next_remaining}


async def create_account_payable_adjustment(
    session: AsyncSession,
    *,
    payable_id: UUID,
    payload: AccountPayableAdjustmentPayload,
    current_user_id: UUID | None,
) -> dict:
    await account_payable_repo.ensure_supplier_payment_hardening_schema(session)
    payable = await account_payable_repo.get_account_payable_for_update(session, payable_id)
    if not payable:
        raise HTTPException(status_code=404, detail="Không tìm thấy công nợ nhà cung cấp.")
    if payable["status"] == "CANCELLED":
        raise HTTPException(status_code=400, detail="Công nợ đã hủy, không thể điều chỉnh.")

    amount = _money(payload.amount)
    reason = payload.reason.strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Lý do điều chỉnh phải có ít nhất 3 ký tự.")
    principal = _money(payable.get("principal_amount"))
    paid = _money(payable.get("paid_amount"))
    next_principal = principal + amount if payload.type == "DEBIT" else principal - amount
    if next_principal < paid:
        raise HTTPException(status_code=400, detail="Điều chỉnh giảm không được làm tổng nghĩa vụ thấp hơn số đã thanh toán.")
    next_remaining = max(next_principal - paid, Decimal("0.00"))
    next_status = _payable_status(next_principal, paid)
    adjustment = await account_payable_repo.insert_account_payable_adjustment(
        session,
        payable_id=payable_id,
        adjustment_type=payload.type,
        amount=amount,
        reason=reason,
        created_by=current_user_id,
    )
    await account_payable_repo.update_payable_principal_totals(
        session,
        payable_id=payable_id,
        principal_amount=next_principal,
        paid_amount=paid,
        remaining_amount=next_remaining,
        status=next_status,
        actor_id=current_user_id,
    )
    await account_payable_repo.insert_payable_event(
        session,
        payable_id=payable_id,
        event_type=f"ADJUSTMENT_{payload.type}",
        amount=amount,
        actor_id=current_user_id,
        metadata={"adjustmentId": adjustment.get("id"), "reason": reason},
    )
    await session.commit()
    return {
        "ok": True,
        "adjustment": adjustment,
        "status": next_status,
        "principalAmount": next_principal,
        "remainingAmount": next_remaining,
    }


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
    if payable and _money(payable.get("paidAmount")) > 0:
        raise HTTPException(
            status_code=409,
            detail="Phiếu nhập đã phát sinh thanh toán công nợ. Phải hoàn hoặc điều chỉnh khoản thanh toán trước khi đảo phiếu.",
        )
