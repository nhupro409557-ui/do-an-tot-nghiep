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


def _serialize_policy(policy) -> dict:
    return {
        "id": str(policy.id),
        "code": policy.code,
        "title": policy.title,
        "content": policy.content,
        "is_active": policy.is_active,
        "version": policy.version,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


async def list_store_policies(session: AsyncSession) -> list[dict]:
    policies = await store_info_repo.list_store_policies(session)
    return [_serialize_policy(policy) for policy in policies]


async def list_public_store_policies(session: AsyncSession) -> list[dict]:
    policies = await store_info_repo.list_store_policies(session)
    return [
        {
            "code": policy.code,
            "title": policy.title,
            "content": policy.content,
            "version": policy.version,
            "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
        }
        for policy in policies
        if policy.is_active
    ]


async def update_store_policy(session: AsyncSession, code: str, payload: dict) -> dict:
    updated = await store_info_repo.update_store_policy(session, code, payload)
    if updated == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy chính sách cửa hàng.",
        )
    await session.commit()
    policies = await store_info_repo.list_store_policies(session)
    policy = next(item for item in policies if item.code == code.upper())
    return _serialize_policy(policy)
