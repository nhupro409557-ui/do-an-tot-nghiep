from uuid import UUID

from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, require_permission
from app.api.schemas.admin import *
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session
from app.application.services import customer_service

# Exporting these for backward compatibility (e.g. category_service.py)
from app.application.services.customer_service import (
    enqueue_category_cache_refresh,
    process_category_migration_job,
)

router = APIRouter()


@router.get("/customers", dependencies=[Depends(require_permission("customer:read"))])
async def list_admin_customers(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    role: Literal["CUSTOMER", "STAFF_ADMIN"] = "CUSTOMER",
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await customer_service.list_admin_customers(session, search, page, limit, role)


@router.get("/customers/{user_id}", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_detail(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await customer_service.get_admin_customer_detail(session, user_id)


@router.get("/customers/{user_id}/overview", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_overview(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await customer_service.get_admin_customer_detail(session, user_id)


@router.get("/customers/{user_id}/orders", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_orders(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.get_admin_customer_orders(session, user_id)


@router.get("/customers/{user_id}/loyalty-history", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_loyalty_history(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.get_admin_customer_loyalty_history(session, user_id)


@router.get("/customers/{user_id}/loyalty-history-page", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_loyalty_history_page(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await customer_service.get_admin_customer_loyalty_history_page(session, user_id, page, limit)


@router.get("/customers/{user_id}/loyalty-history/{transaction_id}/allocations", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_loyalty_allocations(user_id: UUID, transaction_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.get_admin_customer_loyalty_allocations(session, user_id, transaction_id)


@router.get("/customers/{user_id}/notes", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_notes(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.get_admin_customer_notes(session, user_id)


@router.get("/customers/{user_id}/audit-logs", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_audit_logs(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.get_admin_customer_audit_logs(session, user_id)


@router.put("/customers/{user_id}/tags", dependencies=[Depends(require_permission("customer:update"))])
async def update_admin_customer_tags(
    user_id: UUID,
    payload: CustomerTagsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.update_admin_customer_tags(session, user_id, payload, current_user_id)


@router.patch("/customers/{user_id}/profile", dependencies=[Depends(require_permission("customer:update"))])
async def update_admin_customer_profile(
    user_id: UUID,
    payload: CustomerProfilePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.update_admin_customer_profile(session, user_id, payload, current_user_id)


@router.put("/customers/tags/bulk", dependencies=[Depends(require_permission("customer:update"))])
async def bulk_update_admin_customer_tags(
    payload: CustomerBulkTagsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.bulk_update_admin_customer_tags(session, payload, current_user_id)


@router.post("/customers/{user_id}/notes", dependencies=[Depends(require_permission("customer:update"))])
async def create_admin_customer_note(
    user_id: UUID,
    payload: CustomerNotePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.create_admin_customer_note(session, user_id, payload, current_user_id)


@router.post("/customers/{user_id}/loyalty-adjustments", dependencies=[Depends(require_permission("customer:loyalty_adjust"))])
async def create_admin_customer_loyalty_adjustment(
    user_id: UUID,
    payload: CustomerLoyaltyAdjustmentPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.create_admin_customer_loyalty_adjustment(session, user_id, payload, current_user_id)


@router.post("/customers/{user_id}/vouchers", dependencies=[Depends(require_permission("customer:issue_voucher"))])
async def issue_admin_customer_voucher(
    user_id: UUID,
    payload: CustomerVoucherIssuePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.issue_admin_customer_voucher(session, user_id, payload, current_user_id)


@router.post("/staff", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sys:manage_users"))])
async def create_staff_account(
    payload: StaffCreatePayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.create_staff_account(session, redis, payload, current_user_id)


@router.patch("/users/status/bulk", dependencies=[Depends(require_permission("sys:manage_users"))])
async def bulk_update_user_status(
    payload: CustomerBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.bulk_update_user_status(session, redis, payload, current_user_id)


@router.get("/users/{user_id}/permissions", dependencies=[Depends(require_permission("sys:manage_users"))])
async def get_user_extra_permissions(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.get_user_extra_permissions(session, user_id, current_user_id)


@router.put("/users/{user_id}/permissions", dependencies=[Depends(require_permission("sys:manage_users"))])
async def update_user_extra_permissions(
    user_id: UUID,
    payload: UserPermissionsPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.update_user_extra_permissions(session, redis, user_id, payload, current_user_id)


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_permission("sys:manage_users"))])
async def update_user_role(
    user_id: UUID,
    payload: UserRolePayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.update_user_role(session, redis, user_id, payload, current_user_id)


@router.get("/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def list_permissions(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.list_permissions(session)


@router.get("/roles", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def list_roles(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await customer_service.list_roles(session)


@router.get("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def get_role_permissions(role_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await customer_service.get_role_permissions(session, role_id)


@router.put("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def update_role_permissions(
    role_id: UUID,
    payload: RolePermissionsPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await customer_service.update_role_permissions(session, redis, role_id, payload, current_user_id)
