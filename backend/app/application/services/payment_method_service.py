from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories import payment_method_repo


def check_availability(method) -> tuple[bool, str | None]:
    if not method.is_active:
        return False, method.maintenance_message or "Phương thức thanh toán này hiện đang tạm khóa."
    
    # Check maintenance window
    if method.maintenance_starts_at and method.maintenance_ends_at:
        now = datetime.now(timezone.utc)
        if method.maintenance_starts_at <= now <= method.maintenance_ends_at:
            return False, method.maintenance_message or "Phương thức thanh toán này đang bảo trì."
            
    return True, None


async def list_public_payment_methods(session: AsyncSession) -> list[dict]:
    methods = await payment_method_repo.list_payment_methods(session)
    result = []
    for m in methods:
        is_avail, msg = check_availability(m)
        result.append({
            "id": str(m.id),
            "code": m.code,
            "name": m.name,
            "description": m.description,
            "is_active": m.is_active,
            "is_available": is_avail,
            "maintenance_message": msg,
            "maintenance_starts_at": m.maintenance_starts_at.isoformat() if m.maintenance_starts_at else None,
            "maintenance_ends_at": m.maintenance_ends_at.isoformat() if m.maintenance_ends_at else None,
        })
    return result


async def list_admin_payment_methods(session: AsyncSession) -> list[dict]:
    methods = await payment_method_repo.list_payment_methods(session)
    return [
        {
            "id": str(m.id),
            "code": m.code,
            "name": m.name,
            "description": m.description,
            "is_active": m.is_active,
            "maintenance_message": m.maintenance_message,
            "maintenance_starts_at": m.maintenance_starts_at.isoformat() if m.maintenance_starts_at else None,
            "maintenance_ends_at": m.maintenance_ends_at.isoformat() if m.maintenance_ends_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
        }
        for m in methods
    ]


async def update_payment_method(session: AsyncSession, method_id: UUID, payload: dict) -> dict:
    # Convert ISO string datetimes to timezone-aware datetime objects if they exist
    starts_at = payload.get("maintenance_starts_at")
    ends_at = payload.get("maintenance_ends_at")
    
    params = {**payload}
    if starts_at:
        try:
            params["maintenance_starts_at"] = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
        except ValueError:
            params["maintenance_starts_at"] = None
    else:
        params["maintenance_starts_at"] = None
        
    if ends_at:
        try:
            params["maintenance_ends_at"] = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
        except ValueError:
            params["maintenance_ends_at"] = None
    else:
        params["maintenance_ends_at"] = None

    updated = await payment_method_repo.update_payment_method(session, method_id, params)
    if updated == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found.")
    await session.commit()
    return {"ok": True}
