import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_admin_suppliers(session: AsyncSession, *, page: int, limit: int, search: str | None, status_filter: str) -> dict:
    where_clauses = []
    params: dict = {"limit": limit, "offset": (page - 1) * limit}
    if search:
        where_clauses.append("(name ILIKE :search OR code ILIKE :search OR contact_name ILIKE :search OR phone ILIKE :search OR email ILIKE :search OR tax_code ILIKE :search)")
        params["search"] = f"%{search.strip()}%"
    if status_filter == "active":
        where_clauses.append("is_active = TRUE")
    elif status_filter == "inactive":
        where_clauses.append("is_active = FALSE")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    total = int((await session.execute(text(f"SELECT COUNT(*) FROM suppliers {where_sql}"), params)).scalar_one())
    result = await session.execute(
        text(
            f"""
            SELECT
                id::text,
                code,
                name,
                contact_name AS "contactName",
                phone,
                email,
                address,
                tax_code AS "taxCode",
                website,
                note,
                is_active AS "isActive",
                created_at AS "createdAt",
                updated_at AS "updatedAt"
            FROM suppliers
            {where_sql}
            ORDER BY is_active DESC, name
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return {"items": [dict(row._mapping) for row in result], "page": page, "limit": limit, "total": total}


async def is_supplier_code_available(session: AsyncSession, *, code: str, exclude_id: UUID | None = None) -> bool:
    params: dict = {"code": code.strip()}
    exclude_clause = ""
    if exclude_id is not None:
        exclude_clause = "AND id != :exclude_id"
        params["exclude_id"] = exclude_id
    row = (
        await session.execute(
            text(
                f"""
                SELECT 1
                FROM suppliers
                WHERE lower(code) = lower(:code)
                  {exclude_clause}
                """
            ),
            params,
        )
    ).first()
    return row is None


async def supplier_exists(session: AsyncSession, supplier_id: UUID) -> bool:
    row = (await session.execute(text("SELECT 1 FROM suppliers WHERE id = :id"), {"id": supplier_id})).first()
    return row is not None


async def insert_supplier(
    session: AsyncSession,
    *,
    supplier_id: UUID,
    code: str,
    name: str,
    contact_name: str | None,
    phone: str | None,
    email: str | None,
    address: str | None,
    tax_code: str | None,
    website: str | None,
    note: str | None,
    is_active: bool,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO suppliers (
                id, code, name, contact_name, phone, email, address, tax_code, website, note, is_active
            )
            VALUES (
                :id, :code, :name, :contact_name, :phone, :email, :address, :tax_code, :website, :note, :is_active
            )
            """
        ),
        {
            "id": supplier_id,
            "code": code,
            "name": name,
            "contact_name": contact_name,
            "phone": phone,
            "email": email,
            "address": address,
            "tax_code": tax_code,
            "website": website,
            "note": note,
            "is_active": is_active,
        },
    )


async def update_supplier(
    session: AsyncSession,
    *,
    supplier_id: UUID,
    code: str,
    name: str,
    contact_name: str | None,
    phone: str | None,
    email: str | None,
    address: str | None,
    tax_code: str | None,
    website: str | None,
    note: str | None,
    is_active: bool,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE suppliers
            SET code = :code,
                name = :name,
                contact_name = :contact_name,
                phone = :phone,
                email = :email,
                address = :address,
                tax_code = :tax_code,
                website = :website,
                note = :note,
                is_active = :is_active,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": supplier_id,
            "code": code,
            "name": name,
            "contact_name": contact_name,
            "phone": phone,
            "email": email,
            "address": address,
            "tax_code": tax_code,
            "website": website,
            "note": note,
            "is_active": is_active,
        },
    )
    return int(result.rowcount or 0)


async def update_supplier_status(session: AsyncSession, *, supplier_id: UUID, is_active: bool) -> int:
    result = await session.execute(
        text("UPDATE suppliers SET is_active = :is_active, updated_at = NOW() WHERE id = :id"),
        {"id": supplier_id, "is_active": is_active},
    )
    return int(result.rowcount or 0)


async def list_suppliers_by_ids(session: AsyncSession, supplier_ids: list[UUID]) -> list[dict]:
    rows = (
        await session.execute(
            text("SELECT id, code, name FROM suppliers WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": supplier_ids},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def update_suppliers_status(session: AsyncSession, *, supplier_ids: list[UUID], is_active: bool) -> None:
    await session.execute(
        text("UPDATE suppliers SET is_active = :is_active, updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": supplier_ids, "is_active": is_active},
    )


async def delete_supplier(session: AsyncSession, supplier_id: UUID) -> int:
    result = await session.execute(text("DELETE FROM suppliers WHERE id = :id"), {"id": supplier_id})
    return int(result.rowcount or 0)


async def audit_supplier_event(session: AsyncSession, *, event_type: str, metadata: dict, user_id: UUID | None = None) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:user_id, :event_type, CAST(:metadata AS jsonb))
            """
        ),
        {"user_id": user_id, "event_type": event_type, "metadata": json.dumps(metadata, ensure_ascii=False, default=str)},
    )
