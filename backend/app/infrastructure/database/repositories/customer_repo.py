import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


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
    return {"items": [dict(row._mapping) for row in result], "page": page, "limit": limit, "total": int(total or 0)}


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


async def list_permissions(session: AsyncSession) -> list[dict]:
    result = await session.execute(text("SELECT id::text, code, module, description FROM permissions ORDER BY module, code"))
    return [dict(row._mapping) for row in result]


async def list_roles(session: AsyncSession) -> list[dict]:
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


async def list_known_permission_codes(session: AsyncSession, codes: list[str]) -> list[str]:
    result = await session.execute(
        text("SELECT code FROM permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
        {"codes": codes},
    )
    return [str(code) for code in result.scalars().all()]


async def delete_user_extra_permissions(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(text("DELETE FROM user_permissions WHERE user_id = :user_id"), {"user_id": user_id})


async def insert_user_extra_permissions(session: AsyncSession, user_id: UUID, codes: list[str]) -> None:
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


async def list_user_extra_permissions(session: AsyncSession, user_id: UUID) -> list[str]:
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


async def get_manual_loyalty_adjustment_total_today(session: AsyncSession, actor_id: UUID) -> int:
    total = await session.scalar(
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
    return int(total or 0)


async def user_exists(session: AsyncSession, user_id: UUID) -> bool:
    return bool(await session.scalar(text("SELECT 1 FROM users WHERE id = :user_id AND status != 'DELETED'"), {"user_id": user_id}))


async def replace_customer_tags(session: AsyncSession, user_id: UUID, tags: list[str]) -> None:
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


async def replace_customer_tags_bulk(session: AsyncSession, user_ids: list[UUID], tags: list[str]) -> None:
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


async def insert_customer_note(session: AsyncSession, *, user_id: UUID, author_id: UUID, content: str) -> dict:
    note = (
        await session.execute(
            text(
                """
                INSERT INTO customer_notes (user_id, author_id, content)
                VALUES (:user_id, :author_id, :content)
                RETURNING id::text, created_at AS "createdAt"
                """
            ),
            {"user_id": user_id, "author_id": author_id, "content": content},
        )
    ).mappings().one()
    return dict(note)


async def get_loyalty_wallet_for_update(session: AsyncSession, user_id: UUID) -> dict | None:
    row = (
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
    return dict(row) if row else None


async def update_loyalty_balance(session: AsyncSession, *, user_id: UUID, balance_after: int) -> None:
    await session.execute(
        text("UPDATE users SET loyalty_points_balance = :balance_after, updated_at = NOW() WHERE id = :user_id"),
        {"user_id": user_id, "balance_after": balance_after},
    )


async def insert_loyalty_adjustment(
    session: AsyncSession,
    *,
    user_id: UUID,
    points: int,
    balance_before: int,
    balance_after: int,
    reason: str,
    metadata: dict,
) -> None:
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
            "points": points,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reason": reason,
            "metadata": json.dumps(metadata, ensure_ascii=False),
        },
    )


async def get_user_for_update(session: AsyncSession, user_id: UUID) -> bool:
    return bool(
        (
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
    )


async def get_active_voucher_for_update(session: AsyncSession, voucher_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, starts_at, ends_at, validity_days_after_claim
                FROM vouchers
                WHERE id = :voucher_id AND status = 'ACTIVE'
                FOR UPDATE
                """
            ),
            {"voucher_id": voucher_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def insert_user_voucher(session: AsyncSession, *, user_id: UUID, voucher_id: UUID, expires_at: object) -> dict | None:
    row = (
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
            {"user_id": user_id, "voucher_id": voucher_id, "expires_at": expires_at},
        )
    ).mappings().first()
    return dict(row) if row else None


async def revoke_user_sessions(session: AsyncSession, *, user_id: UUID, reason: str) -> None:
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


async def get_active_user_id_by_email(session: AsyncSession, email: str) -> UUID | None:
    return await session.scalar(text("SELECT id FROM users WHERE LOWER(email) = :email AND status != 'DELETED'"), {"email": email})


async def get_role_id_by_code(session: AsyncSession, code: str) -> UUID | None:
    return await session.scalar(text("SELECT id FROM roles WHERE code = :code"), {"code": code})


async def insert_staff_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    role_id: UUID,
    email: str,
    password_hash: str,
    full_name: str,
    phone: str | None,
    status: str,
) -> None:
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
            "password_hash": password_hash,
            "full_name": full_name,
            "phone": phone,
            "status": status,
        },
    )


async def bulk_update_user_status(session: AsyncSession, *, user_ids: list[UUID], status: str) -> int:
    result = await session.execute(
        text(
            """
            UPDATE users
            SET status = :status, updated_at = NOW()
            WHERE id IN :user_ids AND status != 'DELETED'
            """
        ).bindparams(bindparam("user_ids", expanding=True)),
        {"status": status, "user_ids": user_ids},
    )
    return int(result.rowcount or 0)


async def get_user_role(session: AsyncSession, user_id: UUID) -> str | None:
    row = (
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
    return str(row["role"]) if row else None


async def get_user_access_for_update(session: AsyncSession, user_id: UUID) -> dict | None:
    row = (
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
    return dict(row) if row else None


async def update_user_role_and_status(session: AsyncSession, *, user_id: UUID, role_id: UUID, status: str) -> None:
    await session.execute(
        text(
            """
            UPDATE users
            SET role_id = :role_id, status = :status, updated_at = NOW()
            WHERE id = :user_id AND status != 'DELETED'
            """
        ),
        {"user_id": user_id, "role_id": role_id, "status": status},
    )


async def get_role(session: AsyncSession, role_id: UUID) -> dict | None:
    row = (
        await session.execute(text("SELECT id::text, code, name FROM roles WHERE id = :id"), {"id": role_id})
    ).mappings().first()
    return dict(row) if row else None


async def list_role_permission_codes(session: AsyncSession, role_id: UUID) -> list[str]:
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
    return [str(code) for code in result.scalars().all()]


async def get_role_code(session: AsyncSession, role_id: UUID) -> str | None:
    return await session.scalar(text("SELECT code FROM roles WHERE id = :id"), {"id": role_id})


async def replace_role_permissions(session: AsyncSession, *, role_id: UUID, permission_codes: list[str]) -> None:
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


async def list_user_ids_by_role(session: AsyncSession, role_id: UUID) -> list[UUID]:
    result = await session.execute(text("SELECT id FROM users WHERE role_id = :role_id"), {"role_id": role_id})
    return list(result.scalars().all())


async def mark_category_migration_running(session: AsyncSession, *, job_id: UUID, category_id: UUID) -> None:
    await session.execute(text("UPDATE category_migration_jobs SET status = 'RUNNING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
    await session.execute(text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :category_id"), {"category_id": category_id})


async def list_category_migration_allowed_fields(session: AsyncSession, category_id: UUID) -> list[dict]:
    fields = await session.scalar(
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
    return list(fields or [])


async def list_products_for_category_migration(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, specifications
            FROM products
            WHERE category_id = :category_id OR subcategory_id = :category_id
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row._mapping) for row in result]


async def update_category_migration_total(session: AsyncSession, *, job_id: UUID, total: int) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET total_products = :total, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "total": total},
    )


async def update_product_specifications(session: AsyncSession, *, product_id: UUID, specifications: dict) -> None:
    await session.execute(
        text("UPDATE products SET specifications = CAST(:specifications AS jsonb), updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "specifications": json.dumps(specifications, ensure_ascii=False)},
    )


async def increment_category_migration_processed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET processed_products = processed_products + 1, updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def complete_category_migration_job(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET status = 'COMPLETED', completed_at = NOW(), updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def fail_category_migration_job(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )


async def reset_category_workflow_status(session: AsyncSession, category_id: UUID) -> None:
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
