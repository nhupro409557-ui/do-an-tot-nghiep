import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.routers.admin_schemas import *
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

async def clear_permission_cache(redis: Redis, user_ids: list[UUID]) -> None:
    if not user_ids:
        return
    await redis.delete(*[f"admin_permissions:{user_id}" for user_id in user_ids])


async def ensure_user_permissions_table(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                granted_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, permission_id)
            )
            """
        )
    )
    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id)"))


async def validate_permission_codes(session: AsyncSession, permission_codes: list[str]) -> list[str]:
    codes = sorted(set(permission_codes))
    if not codes:
        return []
    known = (
        await session.execute(
            text("SELECT code FROM permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
            {"codes": codes},
        )
    ).scalars().all()
    if set(known) != set(codes):
        raise HTTPException(status_code=400, detail="One or more permissions are invalid.")
    return codes


async def set_user_extra_permissions(session: AsyncSession, user_id: UUID, permission_codes: list[str]) -> list[str]:
    await ensure_user_permissions_table(session)
    codes = await validate_permission_codes(session, permission_codes)
    await session.execute(text("DELETE FROM user_permissions WHERE user_id = :user_id"), {"user_id": user_id})
    if codes:
        await session.execute(
            text(
                """
                INSERT INTO user_permissions (user_id, permission_id)
                SELECT :user_id, id
                FROM permissions
                WHERE code IN :codes
                ON CONFLICT DO NOTHING
                """
            ).bindparams(bindparam("codes", expanding=True)),
            {"user_id": user_id, "codes": codes},
        )
    return codes


async def list_user_extra_permissions(session: AsyncSession, user_id: UUID) -> list[str]:
    await ensure_user_permissions_table(session)
    result = await session.execute(
        text(
            """
            SELECT p.code
            FROM user_permissions up
            JOIN permissions p ON p.id = up.permission_id
            WHERE up.user_id = :user_id
            ORDER BY p.code
            """
        ),
        {"user_id": user_id},
    )
    return [str(code) for code in result.scalars().all()]


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
    payload = {"resource": resource, **(metadata or {})}
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:actor_id, :event_type, CAST(:metadata AS jsonb))
            """
        ),
        {
            "actor_id": actor_id,
            "event_type": event_type,
            "metadata": json.dumps(
                {
                    **payload,
                    **({"targetUserId": str(target_user_id)} if target_user_id else {}),
                },
                ensure_ascii=False,
            ),
        },
    )


async def ensure_manual_loyalty_limit(
    session: AsyncSession,
    *,
    actor_id: UUID,
    requested_delta: int,
    daily_limit: int = 100000,
) -> None:
    today_total = await session.scalar(
        text(
            """
            SELECT COALESCE(SUM(ABS((metadata->>'delta')::int)), 0)
            FROM loyalty_transactions
            WHERE type = 'ADJUST'
              AND metadata->>'adjustedBy' = :actor_id
              AND created_at >= date_trunc('day', NOW())
            """
        ),
        {"actor_id": str(actor_id)},
    )
    if int(today_total or 0) + abs(requested_delta) > daily_limit:
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
            await session.execute(text("UPDATE category_migration_jobs SET status = 'RUNNING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
            await session.execute(text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :category_id"), {"category_id": category_id})
            fields_result = await session.execute(
                text(
                    """
                    SELECT COALESCE(parent.spec_fields, '[]'::jsonb) || COALESCE(c.spec_fields, '[]'::jsonb) AS fields
                    FROM categories c
                    LEFT JOIN categories parent ON parent.id = c.parent_id
                    WHERE c.id = :category_id
                    """
                ),
                {"category_id": category_id},
            )
            allowed_fields = fields_result.scalar() or []
            allowed_keys = {str(field.get("key")) for field in allowed_fields if field.get("key")}
            products = (
                await session.execute(
                    text(
                        """
                        SELECT id, specifications
                        FROM products
                        WHERE category_id = :category_id OR subcategory_id = :category_id
                        """
                    ),
                    {"category_id": category_id},
                )
            ).mappings().all()
            await session.execute(
                text("UPDATE category_migration_jobs SET total_products = :total, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "total": len(products)},
            )
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
                await session.execute(
                    text("UPDATE products SET specifications = CAST(:specifications AS jsonb), updated_at = NOW() WHERE id = :id"),
                    {"id": product["id"], "specifications": json.dumps(specs, ensure_ascii=False)},
                )
                await session.execute(
                    text("UPDATE category_migration_jobs SET processed_products = processed_products + 1, updated_at = NOW() WHERE id = :id"),
                    {"id": job_id},
                )
            await session.execute(
                text("UPDATE category_migration_jobs SET status = 'COMPLETED', completed_at = NOW(), updated_at = NOW() WHERE id = :id"),
                {"id": job_id},
            )
            await session.execute(
                text(
                    """
                    UPDATE categories
                    SET workflow_status = CASE
                        WHEN status = 'ACTIVE' THEN 'APPROVED'
                        WHEN status = 'INACTIVE' THEN 'APPROVED'
                        ELSE status
                    END,
                    updated_at = NOW()
                    WHERE id = :category_id
                    """
                ),
                {"category_id": category_id},
            )
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE category_migration_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.execute(
                text(
                    """
                    UPDATE categories
                    SET workflow_status = CASE
                        WHEN status = 'ACTIVE' THEN 'APPROVED'
                        WHEN status = 'INACTIVE' THEN 'APPROVED'
                        ELSE status
                    END,
                    updated_at = NOW()
                    WHERE id = :category_id
                    """
                ),
                {"category_id": category_id},
            )
            await session.commit()


async def revoke_users(session: AsyncSession, user_ids: list[UUID], reason: str) -> None:
    for user_id in user_ids:
        await session.execute(
            text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
                VALUES (:user_id, NOW(), :reason)
                ON CONFLICT (user_id)
                DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
                """
            ),
            {"user_id": user_id, "reason": reason},
        )



@router.get("/customers", dependencies=[Depends(require_permission("customer:read"))])
async def list_admin_customers(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ensure_user_permissions_table(session)
    offset = (page - 1) * limit
    search_value = (search or "").strip().lower()
    params: dict[str, object] = {"limit": limit, "offset": offset, "search": f"%{search_value}%"}
    where_clause = """
        WHERE u.status != 'DELETED'
          AND (
            :search = '%%'
            OR LOWER(COALESCE(u.full_name, '')) LIKE :search
            OR LOWER(COALESCE(u.email, '')) LIKE :search
            OR LOWER(COALESCE(r.code, '')) LIKE :search
            OR LOWER(COALESCE(u.loyalty_tier, '')) LIKE :search
            OR LOWER(COALESCE(u.status, '')) LIKE :search
          )
    """
    total = await session.scalar(
        text(
            f"""
            SELECT COUNT(*)
            FROM users u
            JOIN roles r ON r.id = u.role_id
            {where_clause}
            """
        ),
        params,
    )
    result = await session.execute(
        text(
            f"""
            SELECT
                u.id::text,
                u.email,
                u.full_name AS "fullName",
                u.phone,
                u.status,
                r.code AS role,
                u.loyalty_tier AS tier,
                u.loyalty_points_balance AS points,
                COALESCE(
                    jsonb_agg(DISTINCT up_perm.code) FILTER (WHERE up_perm.code IS NOT NULL),
                    '[]'::jsonb
                ) AS "extraPermissionCodes",
                COUNT(o.id) AS "orderCount",
                COALESCE(SUM(o.total_amount), 0) AS "totalSpent",
                u.created_at AS "createdAt"
            FROM users u
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN orders o ON o.user_id = u.id
            LEFT JOIN user_permissions up ON up.user_id = u.id
            LEFT JOIN permissions up_perm ON up_perm.id = up.permission_id
            {where_clause}
            GROUP BY u.id, r.code
            ORDER BY u.created_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        params,
    )
    return {
        "items": [dict(row._mapping) for row in result],
        "page": page,
        "limit": limit,
        "total": int(total or 0),
    }


@router.get("/customers/{user_id}", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_detail(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    await ensure_user_permissions_table(session)
    customer = (
        await session.execute(
            text(
                """
                SELECT
                    u.id::text,
                    u.email,
                    u.full_name AS "fullName",
                    u.phone,
                    u.status,
                    r.code AS role,
                    u.loyalty_tier AS tier,
                    u.loyalty_points_balance AS points,
                    u.loyalty_wallet_status AS "walletStatus",
                    COUNT(o.id) AS "orderCount",
                    COALESCE(SUM(o.total_amount), 0) AS "totalSpent",
                    COALESCE(SUM(o.loyalty_points_earned), 0) AS "totalPointsEarned",
                    COALESCE(SUM(o.loyalty_points_used), 0) AS "totalPointsUsed",
                    u.created_at AS "createdAt",
                    u.updated_at AS "updatedAt"
                FROM users u
                JOIN roles r ON r.id = u.role_id
                LEFT JOIN orders o ON o.user_id = u.id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                GROUP BY u.id, r.code
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if not customer:
        raise HTTPException(status_code=404, detail="User not found.")

    tags = (
        await session.execute(
            text("SELECT tag FROM customer_tags WHERE user_id = :user_id ORDER BY tag"),
            {"user_id": user_id},
        )
    ).scalars().all()
    notes = (
        await session.execute(
            text(
                """
                SELECT COUNT(*) AS count, MAX(created_at) AS "lastCreatedAt"
                FROM customer_notes
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    voucher_count = await session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM user_vouchers
            WHERE user_id = :user_id AND status IN ('AVAILABLE', 'RESERVED', 'USED')
            """
        ),
        {"user_id": user_id},
    )
    return {
        **dict(customer),
        "tags": [str(tag) for tag in tags],
        "extraPermissionCodes": await list_user_extra_permissions(session, user_id),
        "noteCount": int(notes["count"] or 0) if notes else 0,
        "lastNoteAt": notes["lastCreatedAt"] if notes else None,
        "voucherCount": int(voucher_count or 0),
    }


@router.get("/customers/{user_id}/overview", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_overview(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await get_admin_customer_detail(user_id, session)


@router.get("/customers/{user_id}/orders", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_orders(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                o.id::text,
                o.order_code AS "orderCode",
                o.status,
                o.payment_method AS "paymentMethod",
                o.payment_status AS "paymentStatus",
                o.total_amount AS "totalAmount",
                o.loyalty_points_earned AS "pointsEarned",
                o.loyalty_points_used AS "pointsUsed",
                o.created_at AS "createdAt",
                o.updated_at AS "updatedAt"
            FROM orders o
            WHERE o.user_id = :user_id
            ORDER BY o.created_at DESC
            LIMIT 100
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/customers/{user_id}/loyalty-history", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_loyalty_history(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                lt.id::text,
                lt.order_id::text AS "orderId",
                lt.type,
                lt.points,
                lt.balance_before AS "balanceBefore",
                lt.balance_after AS "balanceAfter",
                lt.reason,
                lt.metadata,
                lt.created_at AS "createdAt"
            FROM loyalty_transactions lt
            WHERE lt.user_id = :user_id
            ORDER BY lt.created_at DESC
            LIMIT 200
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/customers/{user_id}/notes", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_notes(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                n.id::text,
                n.user_id::text AS "userId",
                n.author_id::text AS "authorId",
                author.full_name AS "authorName",
                n.content,
                n.created_at AS "createdAt",
                n.updated_at AS "updatedAt"
            FROM customer_notes n
            LEFT JOIN users author ON author.id = n.author_id
            WHERE n.user_id = :user_id
            ORDER BY n.created_at DESC
            LIMIT 100
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/customers/{user_id}/audit-logs", dependencies=[Depends(require_permission("customer:read"))])
async def get_admin_customer_audit_logs(user_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                user_id::text AS "userId",
                event_type AS "eventType",
                metadata,
                created_at AS "createdAt"
            FROM security_audit_logs
            WHERE metadata->>'targetUserId' = :user_id
               OR metadata->>'userId' = :user_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"user_id": str(user_id)},
    )
    return [dict(row._mapping) for row in result]


@router.put("/customers/{user_id}/tags", dependencies=[Depends(require_permission("customer:update"))])
async def update_admin_customer_tags(
    user_id: UUID,
    payload: CustomerTagsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    tags = normalize_customer_tags(payload.tags)
    exists = await session.scalar(text("SELECT 1 FROM users WHERE id = :user_id AND status != 'DELETED'"), {"user_id": user_id})
    if not exists:
        raise HTTPException(status_code=404, detail="User not found.")
    await session.execute(text("DELETE FROM customer_tags WHERE user_id = :user_id"), {"user_id": user_id})
    if tags:
        await session.execute(
            text(
                """
                INSERT INTO customer_tags (user_id, tag)
                SELECT :user_id, tag
                FROM unnest(CAST(:tags AS text[])) AS tag
                """
            ),
            {"user_id": user_id, "tags": tags},
        )
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


@router.put("/customers/tags/bulk", dependencies=[Depends(require_permission("customer:update"))])
async def bulk_update_admin_customer_tags(
    payload: CustomerBulkTagsPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    tags = normalize_customer_tags(payload.tags)
    user_ids = list(dict.fromkeys(payload.userIds))
    await session.execute(
        text("DELETE FROM customer_tags WHERE user_id IN :user_ids").bindparams(bindparam("user_ids", expanding=True)),
        {"user_ids": user_ids},
    )
    if tags:
        for user_id in user_ids:
            await session.execute(
                text(
                    """
                    INSERT INTO customer_tags (user_id, tag)
                    SELECT :user_id, tag
                    FROM unnest(CAST(:tags AS text[])) AS tag
                    """
                ),
                {"user_id": user_id, "tags": tags},
            )
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_customer_tags_bulk_updated",
        resource="customer_bulk_tags",
        metadata={"userIds": [str(user_id) for user_id in user_ids], "tags": tags, "affectedUsers": len(user_ids)},
    )
    await session.commit()
    return {"ok": True, "affectedUsers": len(user_ids), "tags": tags}


@router.post("/customers/{user_id}/notes", dependencies=[Depends(require_permission("customer:update"))])
async def create_admin_customer_note(
    user_id: UUID,
    payload: CustomerNotePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    exists = await session.scalar(text("SELECT 1 FROM users WHERE id = :user_id AND status != 'DELETED'"), {"user_id": user_id})
    if not exists:
        raise HTTPException(status_code=404, detail="User not found.")
    note = (
        await session.execute(
            text(
                """
                INSERT INTO customer_notes (user_id, author_id, content)
                VALUES (:user_id, :author_id, :content)
                RETURNING id::text, created_at AS "createdAt"
                """
            ),
            {"user_id": user_id, "author_id": current_user_id, "content": payload.content.strip()},
        )
    ).mappings().one()
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


@router.post("/customers/{user_id}/loyalty-adjustments", dependencies=[Depends(require_permission("customer:loyalty_adjust"))])
async def create_admin_customer_loyalty_adjustment(
    user_id: UUID,
    payload: CustomerLoyaltyAdjustmentPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    if payload.delta == 0:
        raise HTTPException(status_code=400, detail="Delta must not be 0.")
    await ensure_manual_loyalty_limit(session, actor_id=current_user_id, requested_delta=payload.delta)
    user = (
        await session.execute(
            text(
                """
                SELECT loyalty_points_balance, loyalty_wallet_status
                FROM users
                WHERE id = :user_id AND status != 'DELETED'
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user["loyalty_wallet_status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail="Loyalty wallet is not active.")
    balance_before = int(user["loyalty_points_balance"] or 0)
    balance_after = balance_before + payload.delta
    if balance_after < 0:
        raise HTTPException(status_code=400, detail="Insufficient loyalty points for this adjustment.")
    await session.execute(
        text("UPDATE users SET loyalty_points_balance = :balance_after, updated_at = NOW() WHERE id = :user_id"),
        {"user_id": user_id, "balance_after": balance_after},
    )
    await session.execute(
        text(
            """
            INSERT INTO loyalty_transactions (user_id, type, points, balance_before, balance_after, reason, metadata)
            VALUES (
                :user_id,
                'ADJUST',
                :points,
                :balance_before,
                :balance_after,
                :reason,
                CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "user_id": user_id,
            "points": abs(payload.delta),
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reason": payload.reason.strip(),
            "metadata": json.dumps(
                {
                    "delta": payload.delta,
                    "adjustedBy": str(current_user_id),
                    "source": "admin_manual_adjustment",
                },
                ensure_ascii=False,
            ),
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


@router.post("/customers/{user_id}/vouchers", dependencies=[Depends(require_permission("customer:issue_voucher"))])
async def issue_admin_customer_voucher(
    user_id: UUID,
    payload: CustomerVoucherIssuePayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user = (
        await session.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE id = :user_id AND status != 'DELETED'
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        )
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    voucher = (
        await session.execute(
            text(
                """
                SELECT id, starts_at, ends_at, validity_days_after_claim
                FROM vouchers
                WHERE id = :voucher_id AND status = 'ACTIVE'
                FOR UPDATE
                """
            ),
            {"voucher_id": payload.voucherId},
        )
    ).mappings().first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found or inactive.")
    claimed = (
        await session.execute(
            text(
                """
                INSERT INTO user_vouchers (id, user_id, voucher_id, status, expires_at)
                VALUES (
                    gen_random_uuid(),
                    :user_id,
                    :voucher_id,
                    'AVAILABLE',
                    :expires_at
                )
                ON CONFLICT (user_id, voucher_id) WHERE status IN ('AVAILABLE', 'RESERVED', 'USED') DO NOTHING
                RETURNING id::text, voucher_id::text AS "voucherId", expires_at AS "expiresAt"
                """
            ),
            {
                "user_id": user_id,
                "voucher_id": payload.voucherId,
                "expires_at": voucher["ends_at"] or (
                    datetime.now(timezone.utc) + timedelta(days=int(voucher["validity_days_after_claim"] or 0))
                    if int(voucher["validity_days_after_claim"] or 0) > 0
                    else None
                ),
            },
        )
    ).mappings().first()
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


@router.post("/staff", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("sys:manage_users"))])
async def create_staff_account(
    payload: StaffCreatePayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    await ensure_user_permissions_table(session)
    email = payload.email.lower().strip()
    existing = await session.scalar(text("SELECT id FROM users WHERE LOWER(email) = :email AND status != 'DELETED'"), {"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists.")
    role_id = await session.scalar(text("SELECT id FROM roles WHERE code = 'STAFF_ADMIN'"))
    if role_id is None:
        raise HTTPException(status_code=404, detail="Staff role not found.")
    user_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO users (
                id, role_id, email, password_hash, full_name, phone, status,
                marketing_opt_in, profile, addresses, loyalty_points_balance,
                loyalty_tier, loyalty_wallet_status, created_at, updated_at
            )
            VALUES (
                :id, :role_id, :email, :password_hash, :full_name, :phone, :status,
                FALSE, '{}'::jsonb, '[]'::jsonb, 0, 'MEMBER', 'ACTIVE', NOW(), NOW()
            )
            """
        ),
        {
            "id": user_id,
            "role_id": role_id,
            "email": email,
            "password_hash": pwd_context.hash(payload.password),
            "full_name": payload.fullName.strip(),
            "phone": payload.phone,
            "status": payload.status,
        },
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


@router.patch("/users/status/bulk", dependencies=[Depends(require_permission("sys:manage_users"))])
async def bulk_update_user_status(
    payload: CustomerBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user_ids = list(dict.fromkeys(payload.userIds))
    result = await session.execute(
        text(
            """
            UPDATE users
            SET status = :status, updated_at = NOW()
            WHERE id IN :user_ids AND status != 'DELETED'
            """
        ).bindparams(bindparam("user_ids", expanding=True)),
        {"status": payload.status, "user_ids": user_ids},
    )
    await revoke_users(session, user_ids, "bulk_status_changed")
    await clear_permission_cache(redis, user_ids)
    await audit_admin_event(
        session,
        actor_id=current_user_id,
        event_type="admin_user_status_bulk_updated",
        resource="customer_access_bulk",
        metadata={"userIds": [str(user_id) for user_id in user_ids], "status": payload.status, "affectedUsers": result.rowcount},
    )
    await session.commit()
    return {"ok": True, "affectedUsers": result.rowcount}


@router.get("/users/{user_id}/permissions", dependencies=[Depends(require_permission("sys:manage_users"))])
async def get_user_extra_permissions(user_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    exists = await session.scalar(text("SELECT 1 FROM users WHERE id = :user_id AND status != 'DELETED'"), {"user_id": user_id})
    if not exists:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"userId": str(user_id), "permissionCodes": await list_user_extra_permissions(session, user_id)}


@router.put("/users/{user_id}/permissions", dependencies=[Depends(require_permission("sys:manage_users"))])
async def update_user_extra_permissions(
    user_id: UUID,
    payload: UserPermissionsPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    user = (
        await session.execute(
            text(
                """
                SELECT r.code AS role
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user["role"] != "STAFF_ADMIN":
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
        metadata={"before": before, "after": after, "role": user["role"]},
    )
    await session.commit()
    return {"ok": True, "permissionCodes": after}


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_permission("sys:manage_users"))])
async def update_user_role(
    user_id: UUID,
    payload: UserRolePayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    before = (
        await session.execute(
            text(
                """
                SELECT r.code AS role, u.status
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    if before is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if before["role"] == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Super Admin cannot be managed from staff/customer access.")
    role_id = (
        await session.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": payload.role})
    ).scalar_one_or_none()
    if role_id is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    result = await session.execute(
        text(
            """
            UPDATE users
            SET role_id = :role_id, status = :status, updated_at = NOW()
            WHERE id = :user_id AND status != 'DELETED'
            """
        ),
        {"user_id": user_id, "role_id": role_id, "status": payload.status},
    )
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


@router.get("/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def list_permissions(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, module, description
            FROM permissions
            ORDER BY module, code
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/roles", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def list_roles(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, name
            FROM roles
            WHERE code IN ('CUSTOMER', 'STAFF_ADMIN')
            ORDER BY CASE code WHEN 'STAFF_ADMIN' THEN 1 ELSE 2 END
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def get_role_permissions(role_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    role = (
        await session.execute(text("SELECT id::text, code, name FROM roles WHERE id = :id"), {"id": role_id})
    ).mappings().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")
    if role["code"] == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Super Admin permissions are not managed here.")
    result = await session.execute(
        text(
            """
            SELECT p.code
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = :role_id
            ORDER BY p.code
            """
        ),
        {"role_id": role_id},
    )
    return {**dict(role), "permissionCodes": [str(code) for code in result.scalars().all()]}


@router.put("/roles/{role_id}/permissions", dependencies=[Depends(require_permission("sys:manage_roles"))])
async def update_role_permissions(
    role_id: UUID,
    payload: RolePermissionsPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    role = (
        await session.execute(text("SELECT code FROM roles WHERE id = :id"), {"id": role_id})
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    previous_permission_codes = (
        await session.execute(
            text(
                """
                SELECT p.code
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = :role_id
                ORDER BY p.code
                """
            ),
            {"role_id": role_id},
        )
    ).scalars().all()
    if role == "SUPER_ADMIN":
        raise HTTPException(status_code=400, detail="Super Admin permissions are not managed here.")
    permission_codes = sorted(set(payload.permissionCodes))
    unknown = (
        await session.execute(
            text("SELECT code FROM permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
            {"codes": permission_codes or ["__none__"]},
        )
    ).scalars().all()
    if set(unknown) != set(permission_codes):
        raise HTTPException(status_code=400, detail="One or more permissions are invalid.")

    await session.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": role_id})
    if permission_codes:
        await session.execute(
            text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :role_id, id
                FROM permissions
                WHERE code IN :codes
                ON CONFLICT DO NOTHING
                """
            ).bindparams(bindparam("codes", expanding=True)),
            {"role_id": role_id, "codes": list(permission_codes)},
        )
    users = (
        await session.execute(text("SELECT id FROM users WHERE role_id = :role_id"), {"role_id": role_id})
    ).scalars().all()
    user_ids = list(users)
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


