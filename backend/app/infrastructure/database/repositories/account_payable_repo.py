import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _row_dict(row) -> dict:
    if not row:
        return {}
    if hasattr(row, "_mapping"):
        source = dict(row._mapping)
    else:
        source = dict(row)
    return {key: _jsonable_value(value) for key, value in source.items()}


def _jsonable_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _jsonable_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable_value(item) for item in value]
    return value


async def get_receipt_payable_source(session: AsyncSession, document_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    d.id AS "documentId",
                    d.document_no AS "referenceCode",
                    d.supplier_name AS "supplierName",
                    d.reason,
                    d.posted_at AS "postedAt",
                    COALESCE(d.metadata, '{}'::jsonb) AS metadata,
                    COALESCE(SUM(
                        COALESCE((l.metadata->>'receivedQuantity')::integer, l.requested_quantity)
                        * COALESCE(l.unit_cost, 0)
                    ), 0)::numeric(14, 2) AS "principalAmount"
                FROM inventory_documents d
                JOIN inventory_document_lines l ON l.document_id = d.id
                WHERE d.id = :document_id
                  AND d.document_type = 'INBOUND'
                GROUP BY d.id
                """
            ),
            {"document_id": document_id},
        )
    ).mappings().first()
    return _row_dict(row) if row else None


async def upsert_payable_from_receipt(
    session: AsyncSession,
    *,
    source: dict,
    due_date: datetime,
    payment_term_days: int,
    paid_amount: float,
    actor_id: UUID | None,
) -> dict:
    metadata = source.get("metadata") or {}
    supplier_id = metadata.get("supplierId") or None
    principal_amount = float(source.get("principalAmount") or 0)
    clamped_paid = max(0, min(float(paid_amount or 0), principal_amount))
    status = "PAID" if principal_amount <= clamped_paid else ("PARTIAL" if clamped_paid > 0 else "OPEN")
    row = (
        await session.execute(
            text(
                """
                INSERT INTO account_payables (
                    id, supplier_id, supplier_name_snapshot, source_document_id, source_reference_code,
                    invoice_number, invoice_date, principal_amount, paid_amount, remaining_amount,
                    payment_term_days, due_date, status, note, created_by, updated_by
                )
                VALUES (
                    :id, :supplier_id, :supplier_name_snapshot, :source_document_id, :source_reference_code,
                    :invoice_number, :invoice_date, :principal_amount, :paid_amount, :remaining_amount,
                    :payment_term_days, :due_date, :status, :note, :actor_id, :actor_id
                )
                ON CONFLICT (source_document_id)
                DO UPDATE SET
                    supplier_id = EXCLUDED.supplier_id,
                    supplier_name_snapshot = EXCLUDED.supplier_name_snapshot,
                    invoice_number = EXCLUDED.invoice_number,
                    invoice_date = EXCLUDED.invoice_date,
                    principal_amount = EXCLUDED.principal_amount,
                    paid_amount = LEAST(account_payables.paid_amount, EXCLUDED.principal_amount),
                    remaining_amount = GREATEST(EXCLUDED.principal_amount - LEAST(account_payables.paid_amount, EXCLUDED.principal_amount), 0),
                    payment_term_days = EXCLUDED.payment_term_days,
                    due_date = EXCLUDED.due_date,
                    status = CASE
                        WHEN account_payables.status = 'CANCELLED' THEN 'CANCELLED'
                        WHEN EXCLUDED.principal_amount <= LEAST(account_payables.paid_amount, EXCLUDED.principal_amount) THEN 'PAID'
                        WHEN LEAST(account_payables.paid_amount, EXCLUDED.principal_amount) > 0 THEN 'PARTIAL'
                        ELSE 'OPEN'
                    END,
                    note = EXCLUDED.note,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = NOW()
                RETURNING
                    id::text,
                    source_reference_code AS "sourceReferenceCode",
                    principal_amount AS "principalAmount",
                    paid_amount AS "paidAmount",
                    remaining_amount AS "remainingAmount",
                    status
                """
            ),
            {
                "id": uuid4(),
                "supplier_id": supplier_id,
                "supplier_name_snapshot": source.get("supplierName"),
                "source_document_id": source.get("documentId"),
                "source_reference_code": source.get("referenceCode"),
                "invoice_number": metadata.get("invoiceNumber"),
                "invoice_date": metadata.get("invoiceDate"),
                "principal_amount": principal_amount,
                "paid_amount": clamped_paid,
                "remaining_amount": max(principal_amount - clamped_paid, 0),
                "payment_term_days": payment_term_days,
                "due_date": due_date,
                "status": status,
                "note": metadata.get("payableNote"),
                "actor_id": actor_id,
            },
        )
    ).mappings().first()
    return _row_dict(row)


async def insert_payable_event(
    session: AsyncSession,
    *,
    payable_id: UUID | str,
    event_type: str,
    amount: float | None = None,
    actor_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO account_payable_events (id, payable_id, event_type, amount, actor_id, metadata)
            VALUES (:id, :payable_id, :event_type, :amount, :actor_id, CAST(:metadata AS jsonb))
            """
        ),
        {
            "id": uuid4(),
            "payable_id": payable_id,
            "event_type": event_type,
            "amount": amount,
            "actor_id": actor_id,
            "metadata": json.dumps(metadata or {}, ensure_ascii=False, default=str),
        },
    )


async def list_account_payables(
    session: AsyncSession,
    *,
    search: str,
    status_filter: str,
    supplier_id: UUID | None,
    page: int,
    page_size: int,
) -> dict:
    where = []
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}
    if search:
        where.append(
            "(ap.source_reference_code ILIKE :search OR ap.supplier_name_snapshot ILIKE :search OR ap.invoice_number ILIKE :search)"
        )
        params["search"] = f"%{search.strip()}%"
    if supplier_id:
        where.append("ap.supplier_id = :supplier_id")
        params["supplier_id"] = supplier_id
    if status_filter and status_filter != "ALL":
        if status_filter == "OVERDUE":
            where.append("ap.status IN ('OPEN', 'PARTIAL') AND ap.due_date::date < CURRENT_DATE")
        else:
            where.append("ap.status = :status")
            params["status"] = status_filter
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    total = int((await session.execute(text(f"SELECT COUNT(*) FROM account_payables ap {where_sql}"), params)).scalar_one())
    rows = (
        await session.execute(
            text(
                f"""
                SELECT
                    ap.id::text,
                    ap.supplier_id::text AS "supplierId",
                    COALESCE(s.name, ap.supplier_name_snapshot) AS "supplierName",
                    ap.source_document_id::text AS "sourceDocumentId",
                    ap.source_reference_code AS "sourceReferenceCode",
                    ap.invoice_number AS "invoiceNumber",
                    ap.invoice_date AS "invoiceDate",
                    ap.principal_amount AS "principalAmount",
                    ap.paid_amount AS "paidAmount",
                    ap.remaining_amount AS "remainingAmount",
                    ap.payment_term_days AS "paymentTermDays",
                    ap.due_date AS "dueDate",
                    CASE
                        WHEN ap.status IN ('OPEN', 'PARTIAL') AND ap.due_date::date < CURRENT_DATE THEN 'OVERDUE'
                        ELSE ap.status
                    END AS status,
                    ap.note,
                    ap.created_at AS "createdAt",
                    ap.updated_at AS "updatedAt"
                FROM account_payables ap
                LEFT JOIN suppliers s ON s.id = ap.supplier_id
                {where_sql}
                ORDER BY
                    CASE WHEN ap.status IN ('OPEN', 'PARTIAL') AND ap.due_date::date < CURRENT_DATE THEN 0 ELSE 1 END,
                    ap.due_date ASC,
                    ap.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()
    return {"items": [dict(row) for row in rows], "page": page, "pageSize": page_size, "total": total}


async def get_account_payable_for_update(session: AsyncSession, payable_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    ap.id,
                    ap.supplier_id,
                    ap.principal_amount,
                    ap.paid_amount,
                    ap.remaining_amount,
                    ap.status,
                    ap.source_reference_code
                FROM account_payables ap
                WHERE ap.id = :id
                FOR UPDATE
                """
            ),
            {"id": payable_id},
        )
    ).mappings().first()
    return _row_dict(row) if row else None


async def insert_supplier_payment(
    session: AsyncSession,
    *,
    payable_id: UUID,
    supplier_id: UUID | None,
    amount: float,
    payment_date: datetime,
    method: str,
    reference_no: str | None,
    note: str | None,
    created_by: UUID | None,
) -> dict:
    row = (
        await session.execute(
            text(
                """
                INSERT INTO supplier_payments (
                    id, payable_id, supplier_id, payment_code, payment_date,
                    amount, method, reference_no, note, created_by
                )
                VALUES (
                    :id, :payable_id, :supplier_id, :payment_code, :payment_date,
                    :amount, :method, :reference_no, :note, :created_by
                )
                RETURNING id::text, payment_code AS "paymentCode"
                """
            ),
            {
                "id": uuid4(),
                "payable_id": payable_id,
                "supplier_id": supplier_id,
                "payment_code": f"TTNCC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "payment_date": payment_date,
                "amount": amount,
                "method": method,
                "reference_no": reference_no,
                "note": note,
                "created_by": created_by,
            },
        )
    ).mappings().first()
    return _row_dict(row)


async def update_payable_payment_totals(
    session: AsyncSession,
    *,
    payable_id: UUID,
    paid_amount: float,
    remaining_amount: float,
    status: str,
    actor_id: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE account_payables
            SET paid_amount = :paid_amount,
                remaining_amount = :remaining_amount,
                status = :status,
                updated_by = :actor_id,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": payable_id,
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount,
            "status": status,
            "actor_id": actor_id,
        },
    )


async def get_account_payable_detail(session: AsyncSession, payable_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    ap.id::text,
                    ap.supplier_id::text AS "supplierId",
                    COALESCE(s.name, ap.supplier_name_snapshot) AS "supplierName",
                    ap.source_document_id::text AS "sourceDocumentId",
                    ap.source_reference_code AS "sourceReferenceCode",
                    ap.invoice_number AS "invoiceNumber",
                    ap.invoice_date AS "invoiceDate",
                    ap.principal_amount AS "principalAmount",
                    ap.paid_amount AS "paidAmount",
                    ap.remaining_amount AS "remainingAmount",
                    ap.payment_term_days AS "paymentTermDays",
                    ap.due_date AS "dueDate",
                    CASE
                        WHEN ap.status IN ('OPEN', 'PARTIAL') AND ap.due_date::date < CURRENT_DATE THEN 'OVERDUE'
                        ELSE ap.status
                    END AS status,
                    ap.note,
                    ap.created_at AS "createdAt",
                    ap.updated_at AS "updatedAt"
                FROM account_payables ap
                LEFT JOIN suppliers s ON s.id = ap.supplier_id
                WHERE ap.id = :id
                """
            ),
            {"id": payable_id},
        )
    ).mappings().first()
    if not row:
        return None
    detail = dict(row)
    payment_rows = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    payment_code AS "paymentCode",
                    payment_date AS "paymentDate",
                    amount,
                    method,
                    reference_no AS "referenceNo",
                    note,
                    created_at AS "createdAt"
                FROM supplier_payments
                WHERE payable_id = :id
                ORDER BY payment_date DESC, created_at DESC
                """
            ),
            {"id": payable_id},
        )
    ).mappings().all()
    detail["payments"] = [dict(item) for item in payment_rows]
    return detail


async def get_account_payable_summary(session: AsyncSession) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(remaining_amount) FILTER (WHERE status IN ('OPEN', 'PARTIAL')), 0) AS "totalRemaining",
                    COALESCE(SUM(remaining_amount) FILTER (
                        WHERE status IN ('OPEN', 'PARTIAL') AND due_date::date < CURRENT_DATE
                    ), 0) AS "overdueAmount",
                    COALESCE(SUM(remaining_amount) FILTER (
                        WHERE status IN ('OPEN', 'PARTIAL')
                          AND due_date::date >= CURRENT_DATE
                          AND due_date::date <= CURRENT_DATE + INTERVAL '7 days'
                    ), 0) AS "dueSoonAmount",
                    COUNT(*) FILTER (WHERE status IN ('OPEN', 'PARTIAL')) AS "openCount",
                    COUNT(*) FILTER (WHERE status IN ('OPEN', 'PARTIAL') AND due_date::date < CURRENT_DATE) AS "overdueCount"
                FROM account_payables
                """
            )
        )
    ).mappings().first()
    return _row_dict(row)


async def cancel_payable_by_source_document(
    session: AsyncSession,
    *,
    source_document_id: UUID,
    actor_id: UUID | None,
    note: str | None,
) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                UPDATE account_payables
                SET status = 'CANCELLED',
                    remaining_amount = 0,
                    note = COALESCE(:note, note),
                    updated_by = :actor_id,
                    updated_at = NOW()
                WHERE source_document_id = :source_document_id
                  AND status != 'CANCELLED'
                RETURNING id::text, principal_amount AS "principalAmount", paid_amount AS "paidAmount"
                """
            ),
            {"source_document_id": source_document_id, "actor_id": actor_id, "note": note},
        )
    ).mappings().all()
    return [dict(row) for row in rows]
