from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories import store_info_repo


async def get_store_info(session: AsyncSession) -> dict:
    info = await store_info_repo.get_store_info(session)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thông tin cửa hàng chưa được cấu hình."
        )
    return {
        "id": str(info.id),
        "name": info.name,
        "hotline": info.hotline,
        "email": info.email,
        "address": info.address,
        "description": info.description,
        "lat": info.lat,
        "lng": info.lng,
        "updated_at": info.updated_at.isoformat() if info.updated_at else None,

    }


async def update_store_info(session: AsyncSession, payload: dict) -> dict:
    updated = await store_info_repo.update_store_info(session, payload)
    if updated == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể cập nhật thông tin cửa hàng."
        )
    await session.commit()
    return {"ok": True}
