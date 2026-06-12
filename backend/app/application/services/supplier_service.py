from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import (
    SupplierBulkStatusPayload,
    SupplierCodeCheckPayload,
    SupplierPayload,
    SupplierStatusPayload,
)
from app.infrastructure.database.repositories import supplier_repo


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


async def list_admin_suppliers(
    session: AsyncSession,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    status_filter: str = "all",
) -> dict:
    return await supplier_repo.list_admin_suppliers(
        session,
        page=page,
        limit=limit,
        search=search,
        status_filter=status_filter,
    )


async def check_supplier_code(payload: SupplierCodeCheckPayload, session: AsyncSession) -> dict:
    available = await supplier_repo.is_supplier_code_available(
        session,
        code=payload.code,
        exclude_id=payload.excludeId,
    )
    return {"available": available}


async def _ensure_supplier_code_available(session: AsyncSession, code: str, exclude_id: UUID | None = None) -> None:
    if not await supplier_repo.is_supplier_code_available(session, code=code, exclude_id=exclude_id):
        raise HTTPException(status_code=409, detail="Mã nhà cung cấp đã tồn tại.")


async def create_supplier(payload: SupplierPayload, session: AsyncSession, current_user_id: UUID) -> dict:
    supplier_id = uuid4()
    code = payload.code.strip()
    await _ensure_supplier_code_available(session, code)
    await supplier_repo.insert_supplier(
        session,
        supplier_id=supplier_id,
        code=code,
        name=payload.name.strip(),
        contact_name=_clean(payload.contactName),
        phone=_clean(payload.phone),
        email=str(payload.email) if payload.email else None,
        address=_clean(payload.address),
        tax_code=_clean(payload.taxCode),
        website=_clean(payload.website),
        note=_clean(payload.note),
        is_active=payload.isActive,
    )
    await supplier_repo.audit_supplier_event(
        session,
        event_type="SUPPLIER_CREATED",
        metadata={"supplierId": str(supplier_id), "code": code, "name": payload.name},
        user_id=current_user_id,
    )
    await session.commit()
    return {"id": str(supplier_id)}


async def update_supplier(
    supplier_id: UUID,
    payload: SupplierPayload,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    if not await supplier_repo.supplier_exists(session, supplier_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp.")
    code = payload.code.strip()
    await _ensure_supplier_code_available(session, code, supplier_id)
    updated = await supplier_repo.update_supplier(
        session,
        supplier_id=supplier_id,
        code=code,
        name=payload.name.strip(),
        contact_name=_clean(payload.contactName),
        phone=_clean(payload.phone),
        email=str(payload.email) if payload.email else None,
        address=_clean(payload.address),
        tax_code=_clean(payload.taxCode),
        website=_clean(payload.website),
        note=_clean(payload.note),
        is_active=payload.isActive,
    )
    if updated == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp.")
    await supplier_repo.audit_supplier_event(
        session,
        event_type="SUPPLIER_UPDATED",
        metadata={"supplierId": str(supplier_id), "code": code, "name": payload.name},
        user_id=current_user_id,
    )
    await session.commit()
    return {"ok": True}


async def update_supplier_status(
    supplier_id: UUID,
    payload: SupplierStatusPayload,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    updated = await supplier_repo.update_supplier_status(session, supplier_id=supplier_id, is_active=payload.isActive)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp.")
    await supplier_repo.audit_supplier_event(
        session,
        event_type="SUPPLIER_STATUS_CHANGED",
        metadata={"supplierIds": [str(supplier_id)], "isActive": payload.isActive},
        user_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "action": "activated" if payload.isActive else "deactivated"}


async def update_suppliers_status(
    payload: SupplierBulkStatusPayload,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    rows = await supplier_repo.list_suppliers_by_ids(session, payload.ids)
    found_ids = {row["id"] for row in rows}
    failed = [{"id": str(supplier_id), "reason": "Không tìm thấy nhà cung cấp."} for supplier_id in payload.ids if supplier_id not in found_ids]
    if rows:
        await supplier_repo.update_suppliers_status(session, supplier_ids=[row["id"] for row in rows], is_active=payload.isActive)
        await supplier_repo.audit_supplier_event(
            session,
            event_type="SUPPLIER_STATUS_CHANGED",
            metadata={"supplierIds": [str(row["id"]) for row in rows], "isActive": payload.isActive, "bulk": True},
            user_id=current_user_id,
        )
        await session.commit()
    return {"updated": len(rows), "failed": failed}


async def delete_supplier(supplier_id: UUID, session: AsyncSession, current_user_id: UUID) -> dict:
    deleted = await supplier_repo.delete_supplier(session, supplier_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp.")
    await supplier_repo.audit_supplier_event(
        session,
        event_type="SUPPLIER_DELETED",
        metadata={"supplierId": str(supplier_id)},
        user_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "action": "deleted"}
