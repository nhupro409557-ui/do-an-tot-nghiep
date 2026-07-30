from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.application.after_sales import service
from app.application.after_sales.schemas import CreateAfterSalesRequest
from app.application.services import order_service
from app.application.commerce.use_cases import VoucherService
from app.infrastructure.database.repositories import after_sales_repo
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/me", tags=["Tài khoản khách hàng"])


@router.get("/after-sales/purchased-items")
async def list_my_after_sales_purchased_items(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await service.get_purchased_items(session, user_id=user_id)


@router.get("/returns")
async def list_my_returns(
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    sort: str = Query(default="-created_at", pattern="^-?created_at$"),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.list_requests(
        session, kind="RETURN", user_id=user_id, status_value=status_value,
        page=page, limit=limit, sort=sort,
    )


@router.post("/returns", status_code=status.HTTP_201_CREATED)
async def create_return(
    payload: CreateAfterSalesRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.create_request(session, kind="RETURN", user_id=user_id, payload=payload)


@router.post("/returns/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_return(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    await service.cancel_request(session, kind="RETURN", request_id=request_id, user_id=user_id)


@router.post("/returns/{request_id}/attachments")
async def upload_return_attachments(
    request_id: UUID,
    files: list[UploadFile] = File(...),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await service.add_attachments(
        session, kind="RETURN", request_id=request_id, user_id=user_id, files=files,
    )


@router.get("/warranties")
async def list_my_warranties(
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    sort: str = Query(default="-created_at", pattern="^-?created_at$"),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.list_requests(
        session, kind="WARRANTY", user_id=user_id, status_value=status_value,
        page=page, limit=limit, sort=sort,
    )


@router.post("/warranties", status_code=status.HTTP_201_CREATED)
async def create_warranty(
    payload: CreateAfterSalesRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.create_request(session, kind="WARRANTY", user_id=user_id, payload=payload)


@router.post("/warranties/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_warranty(
    request_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    await service.cancel_request(session, kind="WARRANTY", request_id=request_id, user_id=user_id)


@router.post("/warranties/{request_id}/attachments")
async def upload_warranty_attachments(
    request_id: UUID,
    files: list[UploadFile] = File(...),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await service.add_attachments(
        session, kind="WARRANTY", request_id=request_id, user_id=user_id, files=files,
    )


@router.get("/orders")
async def list_my_orders(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await order_service.list_orders(session, user_id)


@router.get("/orders/{order_id}/shipment")
async def shipment_timeline(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    events = await after_sales_repo.list_shipment_events(session, order_id, user_id)
    if events is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    return events


@router.get("/vouchers")
async def my_vouchers(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list:
    result = await VoucherService(session=session).list_user_vouchers(user_id=user_id)
    return result


@router.get("/transactions")
async def my_transactions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await after_sales_repo.list_transactions(session, user_id, page, limit)


@router.get("/notifications")
async def my_notifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    total = await session.scalar(
        text("SELECT COUNT(*) FROM notifications WHERE user_id=:uid AND available_at <= NOW()"),
        {"uid": user_id},
    )
    result = await session.execute(
        text(
            """
            SELECT id::text id, type, title, message, read, read_at AS "readAt",
                   entity_type AS "entityType", entity_id::text AS "entityId",
                   action_url AS "actionUrl", created_at AS "createdAt"
            FROM notifications
            WHERE user_id=:uid AND available_at <= NOW()
            ORDER BY created_at DESC OFFSET :offset LIMIT :limit
            """
        ),
        {"uid": user_id, "offset": (page - 1) * limit, "limit": limit},
    )
    return {
        "items": [dict(row._mapping) for row in result], "page": page, "limit": limit,
        "total": int(total or 0), "totalPages": max(1, ((int(total or 0) + limit - 1) // limit)),
    }


@router.patch("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await session.execute(
        text(
            """
            UPDATE notifications SET read=TRUE, read_at=COALESCE(read_at, NOW())
            WHERE id=:id AND user_id=:uid
            """
        ),
        {"id": notification_id, "uid": user_id},
    )
    await session.commit()
    return {"ok": True}


@router.patch("/notifications/read-all")
async def read_all_notifications(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await session.execute(
        text("UPDATE notifications SET read=TRUE, read_at=COALESCE(read_at,NOW()) WHERE user_id=:uid"),
        {"uid": user_id},
    )
    await session.commit()
    return {"ok": True}
