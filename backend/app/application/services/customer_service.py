from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, status
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import *
from app.infrastructure.database.repositories import customer_repo
from app.infrastructure.database.session import AsyncSessionFactory

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

async def clear_permission_cache(redis: Redis, user_ids: list[UUID]) -> None:
    if not user_ids:
        return
    try:
        await redis.delete(*[f"admin_permissions:{user_id}" for user_id in user_ids])
    except Exception:
        pass


async def ensure_user_permissions_table(session: AsyncSession) -> None:
    await customer_repo.ensure_user_permissions_table(session)


async def validate_permission_codes(session: AsyncSession, permission_codes: list[str]) -> list[str]:
    codes = sorted(set(permission_codes))
    if not codes:
        return []
    known = await customer_repo.list_known_permission_codes(session, codes)
    if set(known) != set(codes):
        raise HTTPException(status_code=400, detail="One or more permissions are invalid.")
    return codes


async def set_user_extra_permissions(session: AsyncSession, user_id: UUID, permission_codes: list[str]) -> list[str]:
    await ensure_user_permissions_table(session)
    codes = await validate_permission_codes(session, permission_codes)
    await customer_repo.delete_user_extra_permissions(session, user_id)
    if codes:
        await customer_repo.insert_user_extra_permissions(session, user_id, codes)
    return codes


async def list_user_extra_permissions(session: AsyncSession, user_id: UUID) -> list[str]:
    await ensure_user_permissions_table(session)
    return await customer_repo.list_user_extra_permissions(session, user_id)


def normalize_customer_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = str(tag or "").strip()
        if not value:
            continue
        value = value[:60]
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return normalized[:20]


async def audit_admin_event(
    session: AsyncSession,
    *,
    actor_id: UUID,
    event_type: str,
    resource: str,
    target_user_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    await customer_repo.audit_admin_event(
        session,
        actor_id=actor_id,
        event_type=event_type,
        resource=resource,
        target_user_id=target_user_id,
        metadata=metadata,
    )


async def ensure_manual_loyalty_limit(
    session: AsyncSession,
    *,
    actor_id: UUID,
    requested_delta: int,
    daily_limit: int = 100000,
) -> None:
    today_total = await customer_repo.get_manual_loyalty_adjustment_total_today(session, actor_id)
    if today_total + abs(requested_delta) > daily_limit:
        raise HTTPException(
            status_code=429,
            detail="Daily manual loyalty adjustment limit exceeded for this admin.",
        )


async def refresh_category_cache(
    session: AsyncSession,
    redis: Redis | None = None,
    affected_root_ids: list[UUID] | None = None,
    removed_root_ids: list[UUID] | None = None,
) -> None:
    if not redis:
        return
    try:
        from app.application.services.category_service import rebuild_category_branch_cache
        await rebuild_category_branch_cache(session, redis, affected_root_ids=affected_root_ids, removed_root_ids=removed_root_ids)
    except Exception:
        pass


def enqueue_category_cache_refresh(
    background_tasks: BackgroundTasks,
    redis: Redis | None = None,
    affected_root_ids: list[UUID] | None = None,
    removed_root_ids: list[UUID] | None = None,
) -> None:
    async def _refresh() -> None:
        async with AsyncSessionFactory() as session:
            await refresh_category_cache(session, redis, affected_root_ids=affected_root_ids, removed_root_ids=removed_root_ids)

    background_tasks.add_task(_refresh)


async def process_category_migration_job(job_id: UUID, category_id: UUID, old_parent_id: UUID | None, new_parent_id: UUID | None) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await customer_repo.mark_category_migration_running(session, job_id=job_id, category_id=category_id)
            allowed_fields = await customer_repo.list_category_migration_allowed_fields(session, category_id)
            allowed_keys = {str(field.get("key")) for field in allowed_fields if field.get("key")}
            products = await customer_repo.list_products_for_category_migration(session, category_id)
            await customer_repo.update_category_migration_total(session, job_id=job_id, total=len(products))
            for product in products:
                specs = dict(product["specifications"] or {})
                legacy_specs = dict(specs.get("_legacySpecs") or {})
                for key in list(specs.keys()):
                    if key.startswith("_"):
                        continue
                    if key not in allowed_keys:
                        legacy_specs[key] = specs.pop(key)
                if legacy_specs:
                    specs["_legacySpecs"] = legacy_specs
                await customer_repo.update_product_specifications(session, product_id=product["id"], specifications=specs)
                await customer_repo.increment_category_migration_processed(session, job_id)
            await customer_repo.complete_category_migration_job(session, job_id)
            await customer_repo.reset_category_workflow_status(session, category_id)
            await session.commit()
        except Exception as exc:
            await customer_repo.fail_category_migration_job(session, job_id=job_id, error=str(exc))
            await customer_repo.reset_category_workflow_status(session, category_id)
            await session.commit()


async def revoke_users(session: AsyncSession, user_ids: list[UUID], reason: str) -> None:
    for user_id in user_ids:
        await customer_repo.revoke_user_sessions(session, user_id=user_id, reason=reason)


async def list_admin_customers(
    session: AsyncSession,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
    role_code: str = "CUSTOMER",
) -> dict:
    if role_code not in {"CUSTOMER", "STAFF_ADMIN"}:
        raise HTTPException(status_code=400, detail="Loại tài khoản không hợp lệ.")
    await ensure_user_permissions_table(session)
    return await customer_repo.list_admin_customers(
        session,
        search=search,
        page=page,
        limit=limit,
        role_code=role_code,
    )


async def ensure_customer_account(session: AsyncSession, user_id: UUID) -> None:
    if await customer_repo.get_user_role(session, user_id) != "CUSTOMER":
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản khách hàng.")


async def get_admin_customer_detail(session: AsyncSession, user_id: UUID) -> dict:
    await ensure_user_permissions_table(session)
    customer = await customer_repo.get_admin_customer_summary(session, user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="User not found.")
    notes = await customer_repo.get_customer_note_summary(session, user_id)
    return {
        **customer,
        "tags": await customer_repo.list_customer_tags(session, user_id),
        "extraPermissionCodes": await list_user_extra_permissions(session, user_id),
        "noteCount": int(notes["count"] or 0) if notes else 0,
        "lastNoteAt": notes["lastCreatedAt"] if notes else None,
        "voucherCount": await customer_repo.count_customer_vouchers(session, user_id),
    }

async def get_admin_customer_orders(session: AsyncSession, user_id: UUID) -> list[dict]:
    await ensure_customer_account(session, user_id)
    return await customer_repo.list_customer_orders(session, user_id)

async def get_admin_customer_loyalty_history(session: AsyncSession, user_id: UUID) -> list[dict]:
    await ensure_customer_account(session, user_id)
    return await customer_repo.list_customer_loyalty_history(session, user_id)

async def get_admin_customer_notes(session: AsyncSession, user_id: UUID) -> list[dict]:
    await ensure_customer_account(session, user_id)
    return await customer_repo.list_customer_notes(session, user_id)

async def get_admin_customer_audit_logs(session: AsyncSession, user_id: UUID) -> list[dict]:
    await ensure_customer_account(session, user_id)
    return await customer_repo.list_customer_audit_logs(session, user_id)

async def update_admin_customer_tags(
    session: AsyncSession,
    user_id: UUID,
    payload: CustomerTagsPayload,
    current_user_id: UUID,
) -> dict:
    tags = normalize_customer_tags(payload.tags)
    await ensure_customer_account(session, user_id)
    await customer_repo.replace_customer_tags(session, user_id, tags)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_tags_updated",
        resource="customer",
        target_user_id=user_id,
        metadata={"tags": tags},
    )
    await session.commit()
    return {"ok": True, "tags": tags}


async def bulk_update_admin_customer_tags(
    session: AsyncSession,
    payload: CustomerBulkTagsPayload,
    current_user_id: UUID,
) -> dict:
    tags = normalize_customer_tags(payload.tags)
    user_ids = list(dict.fromkeys(payload.userIds))
    for user_id in user_ids:
        await ensure_customer_account(session, user_id)
    await customer_repo.replace_customer_tags_bulk(session, user_ids, tags)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_tags_bulk_updated",
        resource="customer_bulk_tags",
        metadata={"userIds": [str(user_id) for user_id in user_ids], "tags": tags, "affectedUsers": len(user_ids)},
    )
    await session.commit()
    return {"ok": True, "affectedUsers": len(user_ids), "tags": tags}


async def create_admin_customer_note(
    session: AsyncSession,
    user_id: UUID,
    payload: CustomerNotePayload,
    current_user_id: UUID,
) -> dict:
    await ensure_customer_account(session, user_id)
    note = await customer_repo.insert_customer_note(
        session,
        user_id=user_id,
        author_id=current_user_id,
        content=payload.content.strip(),
    )
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_note_created",
        resource="customer",
        target_user_id=user_id,
        metadata={"noteId": note["id"]},
    )
    await session.commit()
    return {"ok": True, **dict(note)}


async def create_admin_customer_loyalty_adjustment(
    session: AsyncSession,
    user_id: UUID,
    payload: CustomerLoyaltyAdjustmentPayload,
    current_user_id: UUID,
) -> dict:
    if payload.delta == 0:
        raise HTTPException(status_code=400, detail="Delta must not be 0.")
    await ensure_customer_account(session, user_id)
    await ensure_manual_loyalty_limit(session, actor_id=current_user_id, requested_delta=payload.delta)
    user = await customer_repo.get_loyalty_wallet_for_update(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user["loyalty_wallet_status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail="Loyalty wallet is not active.")
    balance_before = int(user["loyalty_points_balance"] or 0)
    balance_after = balance_before + payload.delta
    if balance_after < 0:
        raise HTTPException(status_code=400, detail="Insufficient loyalty points for this adjustment.")
    await customer_repo.update_loyalty_balance(session, user_id=user_id, balance_after=balance_after)
    await customer_repo.insert_loyalty_adjustment(
        session,
        user_id=user_id,
        points=abs(payload.delta),
        balance_before=balance_before,
        balance_after=balance_after,
        reason=payload.reason.strip(),
        metadata={
            "delta": payload.delta,
            "adjustedBy": str(current_user_id),
            "source": "admin_manual_adjustment",
        },
    )
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_loyalty_adjusted",
        resource="customer",
        target_user_id=user_id,
        metadata={"delta": payload.delta, "balanceBefore": balance_before, "balanceAfter": balance_after},
    )
    await session.commit()
    return {"ok": True, "balanceBefore": balance_before, "balanceAfter": balance_after}


async def issue_admin_customer_voucher(
    session: AsyncSession,
    user_id: UUID,
    payload: CustomerVoucherIssuePayload,
    current_user_id: UUID,
) -> dict:
    await ensure_customer_account(session, user_id)
    if not await customer_repo.get_user_for_update(session, user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    voucher = await customer_repo.get_active_voucher_for_update(session, payload.voucherId)
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found or inactive.")
    expires_at = voucher["ends_at"] or (
        datetime.now(timezone.utc) + timedelta(days=int(voucher["validity_days_after_claim"] or 0))
        if int(voucher["validity_days_after_claim"] or 0) > 0
        else None
    )
    claimed = await customer_repo.insert_user_voucher(
        session,
        user_id=user_id,
        voucher_id=payload.voucherId,
        expires_at=expires_at,
    )
    if not claimed:
        raise HTTPException(status_code=409, detail="Customer already owns this voucher.")
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_voucher_issued",
        resource="customer",
        target_user_id=user_id,
        metadata={"voucherId": str(payload.voucherId), "note": payload.note},
    )
    await session.commit()
    return {"ok": True, **dict(claimed)}


async def create_staff_account(
    session: AsyncSession,
    redis: Redis,
    payload: StaffCreatePayload,
    current_user_id: UUID,
) -> dict:
    await ensure_user_permissions_table(session)
    email = payload.email.lower().strip()
    if await customer_repo.get_active_user_id_by_email(session, email):
        raise HTTPException(status_code=409, detail="Email already exists.")
    role_id = await customer_repo.get_role_id_by_code(session, "STAFF_ADMIN")
    if role_id is None:
        raise HTTPException(status_code=404, detail="Staff role not found.")
    user_id = uuid4()
    await customer_repo.insert_staff_user(
        session,
        user_id=user_id,
        role_id=role_id,
        email=email,
        password_hash=pwd_context.hash(payload.password),
        full_name=payload.fullName.strip(),
        phone=payload.phone,
        status=payload.status,
    )
    extra_permissions = await set_user_extra_permissions(session, user_id, [])
    await clear_permission_cache(redis, [user_id])
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_staff_created",
        resource="staff",
        target_user_id=user_id,
        metadata={"email": email, "status": payload.status, "extraPermissionCodes": extra_permissions},
    )
    await session.commit()
    return {"ok": True, "id": str(user_id), "extraPermissionCodes": extra_permissions}


async def bulk_update_user_status(
    session: AsyncSession,
    redis: Redis,
    payload: CustomerBulkStatusPayload,
    current_user_id: UUID,
) -> dict:
    user_ids = list(dict.fromkeys(payload.userIds))
    for user_id in user_ids:
        await ensure_customer_account(session, user_id)
    affected_users = await customer_repo.bulk_update_user_status(session, user_ids=user_ids, status=payload.status)
    await revoke_users(session, user_ids, "bulk_status_changed")
    await clear_permission_cache(redis, user_ids)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_user_status_bulk_updated",
        resource="customer_access_bulk",
        metadata={"userIds": [str(user_id) for user_id in user_ids], "status": payload.status, "affectedUsers": affected_users},
    )
    await session.commit()
    return {"ok": True, "affectedUsers": affected_users}


async def get_user_extra_permissions(session: AsyncSession, user_id: UUID, current_user_id: UUID) -> dict:
    if user_id == current_user_id:
        raise HTTPException(status_code=403, detail="Bạn không thể xem hoặc điều chỉnh quyền của chính mình.")
    if not await customer_repo.user_exists(session, user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"userId": str(user_id), "permissionCodes": await list_user_extra_permissions(session, user_id)}


async def update_user_extra_permissions(
    session: AsyncSession,
    redis: Redis,
    user_id: UUID,
    payload: UserPermissionsPayload,
    current_user_id: UUID,
) -> dict:
    if user_id == current_user_id:
        raise HTTPException(status_code=403, detail="Bạn không thể xem hoặc điều chỉnh quyền của chính mình.")
    role = await customer_repo.get_user_role(session, user_id)
    if not role:
        raise HTTPException(status_code=404, detail="User not found.")
    if role != "STAFF_ADMIN":
        raise HTTPException(status_code=400, detail="Only Staff Admin accounts can receive extra permissions.")
    before = await list_user_extra_permissions(session, user_id)
    after = await set_user_extra_permissions(session, user_id, payload.permissionCodes)
    await revoke_users(session, [user_id], "user_permissions_changed")
    await clear_permission_cache(redis, [user_id])
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_user_permissions_updated",
        resource="user_permissions",
        target_user_id=user_id,
        metadata={"before": before, "after": after, "role": role},
    )
    await session.commit()
    return {"ok": True, "permissionCodes": after}


async def update_user_role(
    session: AsyncSession,
    redis: Redis,
    user_id: UUID,
    payload: UserRolePayload,
    current_user_id: UUID,
) -> dict:
    before = await customer_repo.get_user_access_for_update(session, user_id)
    if before is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if before["role"] == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Super Admin cannot be managed from staff/customer access.")
    role_id = await customer_repo.get_role_id_by_code(session, payload.role)
    if role_id is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    await customer_repo.update_user_role_and_status(session, user_id=user_id, role_id=role_id, status=payload.status)
    extra_permissions: list[str] | None = None
    if payload.role == "STAFF_ADMIN" and payload.permissionCodes is not None:
        extra_permissions = await set_user_extra_permissions(session, user_id, payload.permissionCodes)
    elif payload.role != "STAFF_ADMIN":
        extra_permissions = await set_user_extra_permissions(session, user_id, [])
    await revoke_users(session, [user_id], "role_changed")
    await clear_permission_cache(redis, [user_id])
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_user_access_updated",
        resource="customer_access",
        target_user_id=user_id,
        metadata={
            "before": dict(before),
            "after": {"role": payload.role, "status": payload.status},
            "extraPermissionCodes": extra_permissions,
        },
    )
    await session.commit()
    return {"ok": True}


async def list_permissions(session: AsyncSession) -> list[dict]:
    return await customer_repo.list_permissions(session)

async def list_roles(session: AsyncSession) -> list[dict]:
    return await customer_repo.list_roles(session)

async def get_role_permissions(session: AsyncSession, role_id: UUID) -> dict:
    role = await customer_repo.get_role(session, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")
    if role["code"] == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Super Admin permissions are not managed here.")
    return {**role, "permissionCodes": await customer_repo.list_role_permission_codes(session, role_id)}


async def update_role_permissions(
    session: AsyncSession,
    redis: Redis,
    role_id: UUID,
    payload: RolePermissionsPayload,
    current_user_id: UUID,
) -> dict:
    role = await customer_repo.get_role_code(session, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    previous_permission_codes = await customer_repo.list_role_permission_codes(session, role_id)
    if role == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Super Admin permissions are not managed here.")
    if role == "STAFF_ADMIN":
        raise HTTPException(
            status_code=400,
            detail="Staff Admin uses per-account permissions. Update the staff account permissions instead.",
        )
    permission_codes = sorted(set(payload.permissionCodes))
    unknown = await customer_repo.list_known_permission_codes(session, permission_codes or ["__none__"])
    if set(unknown) != set(permission_codes):
        raise HTTPException(status_code=400, detail="One or more permissions are invalid.")

    await customer_repo.replace_role_permissions(session, role_id=role_id, permission_codes=list(permission_codes))
    user_ids = await customer_repo.list_user_ids_by_role(session, role_id)
    await revoke_users(session, user_ids, "permissions_changed")
    await clear_permission_cache(redis, user_ids)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_role_permissions_updated",
        resource="role_permissions",
        metadata={
            "roleId": str(role_id),
            "roleCode": role,
            "before": list(previous_permission_codes),
            "after": list(permission_codes),
            "affectedUsers": len(user_ids),
        },
    )
    await session.commit()
    return {"ok": True, "permissionCodes": list(permission_codes)}
