import re
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


def validate_supplier_data(payload: SupplierPayload) -> None:
    # 1. Tên bắt buộc, tối thiểu 2 ký tự, tối đa 200 ký tự
    name = payload.name.strip() if payload.name else ""
    if not name:
        raise HTTPException(status_code=400, detail="Tên nhà cung cấp không được trống.")
    if len(name) < 2 or len(name) > 200:
        raise HTTPException(status_code=400, detail="Tên nhà cung cấp phải từ 2 đến 200 ký tự.")

    # 2. Mã nhà cung cấp bắt buộc
    code = payload.code.strip() if payload.code else ""
    if not code:
        raise HTTPException(status_code=400, detail="Mã nhà cung cấp không được trống.")

    # 3. Validate email bằng regex cơ bản nếu có
    email = payload.email.strip() if payload.email else None
    if email:
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            raise HTTPException(status_code=400, detail="Email không hợp lệ.")

    # 4. Validate SĐT bằng regex Việt Nam nếu có
    phone = payload.phone.strip() if payload.phone else None
    if phone:
        phone = re.sub(r"[\s.-]", "", phone)
        phone_regex = r"^(0|\+84)(3|5|7|8|9)\d{8}$"
        if not re.match(phone_regex, phone):
            raise HTTPException(status_code=400, detail="Số điện thoại không hợp lệ.")


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


async def _ensure_supplier_profile_unique(
    session: AsyncSession,
    *,
    name: str,
    email: str | None,
    tax_code: str | None,
    exclude_id: UUID | None = None,
) -> None:
    conflict = await supplier_repo.find_supplier_profile_conflict(
        session,
        name=name,
        email=email,
        tax_code=tax_code,
        exclude_id=exclude_id,
    )
    messages = {
        "name": "Tên nhà cung cấp đã tồn tại.",
        "email": "Email nhà cung cấp đã tồn tại.",
        "tax_code": "Mã số thuế nhà cung cấp đã tồn tại.",
    }
    if conflict:
        raise HTTPException(status_code=409, detail=messages.get(conflict, "Nhà cung cấp đã tồn tại."))


async def create_supplier(payload: SupplierPayload, session: AsyncSession, current_user_id: UUID) -> dict:
    validate_supplier_data(payload)
    supplier_id = uuid4()
    code = payload.code.strip()
    name = payload.name.strip()
    email = str(payload.email).strip() if payload.email else None
    tax_code = _clean(payload.taxCode)
    await _ensure_supplier_code_available(session, code)
    await _ensure_supplier_profile_unique(session, name=name, email=email, tax_code=tax_code)
    phone = _clean(payload.phone)
    if phone:
        phone = re.sub(r"[\s.-]", "", phone)
    await supplier_repo.insert_supplier(
        session,
        supplier_id=supplier_id,
        code=code,
        name=name,
        contact_name=_clean(payload.contactName),
        phone=phone,
        email=email,
        address=_clean(payload.address),
        tax_code=tax_code,
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
    validate_supplier_data(payload)
    if not await supplier_repo.supplier_exists(session, supplier_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp.")
    code = payload.code.strip()
    name = payload.name.strip()
    email = str(payload.email).strip() if payload.email else None
    tax_code = _clean(payload.taxCode)
    await _ensure_supplier_code_available(session, code, supplier_id)
    await _ensure_supplier_profile_unique(session, name=name, email=email, tax_code=tax_code, exclude_id=supplier_id)
    phone = _clean(payload.phone)
    if phone:
        phone = re.sub(r"[\s.-]", "", phone)
    updated = await supplier_repo.update_supplier(
        session,
        supplier_id=supplier_id,
        code=code,
        name=name,
        contact_name=_clean(payload.contactName),
        phone=phone,
        email=email,
        address=_clean(payload.address),
        tax_code=tax_code,
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
    reference_count = await supplier_repo.count_supplier_business_references(session, supplier_id)
    if reference_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Nhà cung cấp đã có chứng từ nghiệp vụ. Hãy ẩn nhà cung cấp thay vì xóa.",
        )
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
