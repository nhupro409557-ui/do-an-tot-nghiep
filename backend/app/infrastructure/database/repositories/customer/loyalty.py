from .common import *

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
