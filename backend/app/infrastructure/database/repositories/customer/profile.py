from .common import *

async def list_admin_customers(
    session: AsyncSession,
    *,
    search: str | None,
    page: int,
    limit: int,
    role_code: str,
) -> dict:
    offset = (page - 1) * limit
    search_value = (search or "").strip().lower()
    params: dict[str, object] = {
        "limit": limit,
        "offset": offset,
        "search": f"%{search_value}%",
        "role_code": role_code,
    }
    where_clause = """
        WHERE u.status != 'DELETED'
          AND r.code = :role_code
          AND (
            :search = '%%'
            OR LOWER(COALESCE(u.full_name, '')) LIKE :search
            OR LOWER(COALESCE(u.email, '')) LIKE :search
            OR LOWER(COALESCE(u.phone, '')) LIKE :search
            OR LOWER(COALESCE(r.code, '')) LIKE :search
            OR LOWER(COALESCE(u.loyalty_tier, '')) LIKE :search
            OR LOWER(COALESCE(u.status, '')) LIKE :search
          )
    """
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
                COALESCE(order_agg."orderCount", 0) AS "orderCount",
                COALESCE(order_agg."totalSpent", 0) AS "totalSpent",
                COALESCE(perm_agg."extraPermissionCodes", '[]'::jsonb) AS "extraPermissionCodes",
                u.created_at AS "createdAt",
                COUNT(*) OVER() AS "_totalCount"
            FROM users u
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS "orderCount",
                       COALESCE(SUM(o.total_amount), 0) AS "totalSpent"
                FROM orders o
                WHERE o.user_id = u.id
            ) order_agg ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE(
                    jsonb_agg(DISTINCT p.code) FILTER (WHERE p.code IS NOT NULL),
                    '[]'::jsonb
                ) AS "extraPermissionCodes"
                FROM user_permissions up
                JOIN permissions p ON p.id = up.permission_id
                WHERE up.user_id = u.id
            ) perm_agg ON true
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        params,
    )
    rows = [dict(row._mapping) for row in result]
    total = int(rows[0]["_totalCount"]) if rows else 0
    for row in rows:
        del row["_totalCount"]
    return {"items": rows, "page": page, "limit": limit, "total": total}


async def get_admin_customer_summary(session: AsyncSession, user_id: UUID) -> dict | None:
    row = (
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
                WHERE u.id = :user_id
                  AND u.status != 'DELETED'
                  AND r.code = 'CUSTOMER'
                GROUP BY u.id, r.code
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_customer_profile_for_update(session: AsyncSession, user_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    u.full_name AS "fullName",
                    u.phone,
                    u.loyalty_tier AS tier,
                    u.loyalty_wallet_status AS "walletStatus"
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id
                  AND u.status != 'DELETED'
                  AND r.code = 'CUSTOMER'
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_customer_profile(
    session: AsyncSession,
    *,
    user_id: UUID,
    full_name: str,
    phone: str | None,
    tier: str,
    wallet_status: str,
) -> None:
    await session.execute(
        text(
            """
            UPDATE users
            SET full_name = :full_name,
                phone = :phone,
                loyalty_tier = :tier,
                loyalty_wallet_status = :wallet_status,
                profile = COALESCE(profile, '{}'::jsonb)
                    || jsonb_build_object(
                        'displayName',
                        CAST(:profile_full_name AS text),
                        'phone',
                        CAST(:profile_phone AS text)
                    ),
                updated_at = NOW()
            WHERE id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "full_name": full_name,
            "phone": phone,
            "profile_full_name": full_name,
            "profile_phone": phone,
            "tier": tier,
            "wallet_status": wallet_status,
        },
    )


async def list_customer_tags(session: AsyncSession, user_id: UUID) -> list[str]:
    result = await session.execute(text("SELECT tag FROM customer_tags WHERE user_id = :user_id ORDER BY tag"), {"user_id": user_id})
    return [str(tag) for tag in result.scalars().all()]


async def get_customer_note_summary(session: AsyncSession, user_id: UUID) -> dict:
    row = (
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
    return dict(row) if row else {"count": 0, "lastCreatedAt": None}


async def count_customer_vouchers(session: AsyncSession, user_id: UUID) -> int:
    return int(
        await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM user_vouchers
                WHERE user_id = :user_id AND status IN ('AVAILABLE', 'RESERVED', 'USED')
                """
            ),
            {"user_id": user_id},
        )
        or 0
    )


async def list_customer_orders(session: AsyncSession, user_id: UUID) -> list[dict]:
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


async def list_customer_loyalty_history(session: AsyncSession, user_id: UUID) -> list[dict]:
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
                actor.id::text AS "actorId",
                actor.full_name AS "actorName",
                actor.email AS "actorEmail",
                lt.created_at AS "createdAt"
            FROM loyalty_transactions lt
            LEFT JOIN users actor ON actor.id::text = lt.metadata->>'adjustedBy'
            WHERE lt.user_id = :user_id
            ORDER BY lt.created_at DESC
            LIMIT 200
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


async def list_customer_notes(session: AsyncSession, user_id: UUID) -> list[dict]:
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


async def list_customer_audit_logs(session: AsyncSession, user_id: UUID) -> list[dict]:
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
