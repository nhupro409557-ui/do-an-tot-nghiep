from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


LOYALTY_TIER_TARGETS = {
    "MEMBER": 0,
    "SILVER": 30_000_000,
    "GOLD": 80_000_000,
    "DIAMOND": 150_000_000,
}
LOYALTY_TIER_LABELS = {
    "MEMBER": "Thành viên",
    "SILVER": "Bạc",
    "GOLD": "Vàng",
    "DIAMOND": "Kim cương",
}
NEXT_LOYALTY_TIER = {
    "MEMBER": "SILVER",
    "SILVER": "GOLD",
    "GOLD": "DIAMOND",
}


def tier_from_spend(amount: Decimal | int) -> str:
    if amount >= LOYALTY_TIER_TARGETS["DIAMOND"]:
        return "DIAMOND"
    if amount >= LOYALTY_TIER_TARGETS["GOLD"]:
        return "GOLD"
    if amount >= LOYALTY_TIER_TARGETS["SILVER"]:
        return "SILVER"
    return "MEMBER"


def loyalty_tier_progress(*, current_tier: str, period_spend_amount: Decimal | int) -> dict:
    normalized_tier = str(current_tier or "MEMBER").upper()
    spend_amount = max(int(period_spend_amount or 0), 0)
    next_tier = NEXT_LOYALTY_TIER.get(normalized_tier)
    if not next_tier:
        return {
            "nextTier": None,
            "nextTierLabel": None,
            "nextTierTarget": None,
            "amountToNextTier": 0,
        }
    target = LOYALTY_TIER_TARGETS[next_tier]
    return {
        "nextTier": next_tier,
        "nextTierLabel": LOYALTY_TIER_LABELS[next_tier],
        "nextTierTarget": target,
        "amountToNextTier": max(target - spend_amount, 0),
    }


async def upgrade_tier_after_order(
    session: AsyncSession,
    *,
    user,
    order_id: UUID,
    order_amount: Decimal,
) -> None:
    period_spend = Decimal(await session.scalar(
        text(
            """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE user_id = :user_id
              AND status = 'COMPLETED'
              AND completed_at >= :period_start
              AND completed_at < :period_end
              AND id != :order_id
            """
        ),
        {
            "user_id": user.id,
            "period_start": user.loyalty_tier_period_started_at,
            "period_end": user.loyalty_tier_period_ends_at,
            "order_id": order_id,
        },
    ) or 0) + Decimal(order_amount or 0)
    rank = {"MEMBER": 1, "SILVER": 2, "GOLD": 3, "DIAMOND": 4}
    qualified_tier = tier_from_spend(period_spend)
    if rank[qualified_tier] > rank.get(user.loyalty_tier, 1):
        user.loyalty_tier = qualified_tier


async def expire_user_points(session: AsyncSession, *, user_id: UUID) -> int | None:
    row = (await session.execute(text("""
        WITH due AS (
            SELECT id, remaining_points
            FROM loyalty_point_lots
            WHERE user_id = :user_id AND expires_at <= NOW()
              AND expired_at IS NULL AND remaining_points > 0
            FOR UPDATE
        ), marked AS (
            UPDATE loyalty_point_lots l
            SET expired_at = NOW(), remaining_points = 0
            FROM due WHERE l.id = due.id
            RETURNING due.remaining_points
        ), total AS (
            SELECT COALESCE(SUM(remaining_points), 0)::integer AS points FROM marked
        ), deduction AS (
            SELECT LEAST(u.loyalty_points_balance, total.points)::integer AS points
            FROM users u CROSS JOIN total
            WHERE u.id = :user_id AND total.points > 0
            FOR UPDATE OF u
        ), updated AS (
            UPDATE users u
            SET loyalty_points_balance = u.loyalty_points_balance - deduction.points, updated_at = NOW()
            FROM deduction WHERE u.id = :user_id
            RETURNING u.id, u.loyalty_points_balance AS balance_after,
                      deduction.points AS expired_points
        ), logged AS (
            INSERT INTO loyalty_transactions
                (id, user_id, type, points, balance_before, balance_after, reason, metadata)
            SELECT gen_random_uuid(), id, 'EXPIRE', expired_points,
                   balance_after + expired_points, balance_after,
                   'Điểm thưởng đã hết hạn theo tháng phát sinh.', '{}'::jsonb
            FROM updated WHERE expired_points > 0
        )
        SELECT balance_after FROM updated
    """), {"user_id": user_id})).mappings().first()
    return int(row["balance_after"]) if row else None


async def run_maintenance(session: AsyncSession) -> dict:
    expired = await session.execute(
        text(
            """
            WITH due AS (
                SELECT l.id, l.user_id, l.remaining_points AS points
                FROM loyalty_point_lots l
                WHERE l.expires_at <= NOW()
                  AND l.expired_at IS NULL
                  AND l.remaining_points > 0
                FOR UPDATE SKIP LOCKED
            ), marked AS (
                UPDATE loyalty_point_lots l
                SET expired_at = NOW(), remaining_points = 0
                FROM due
                WHERE l.id = due.id
                RETURNING due.user_id, due.points, l.id
            ), totals AS (
                SELECT user_id, SUM(points)::integer AS points
                FROM marked
                GROUP BY user_id
            ), deductions AS (
                SELECT totals.user_id, totals.points AS requested_points,
                       LEAST(u.loyalty_points_balance, totals.points)::integer AS expired_points
                FROM totals
                JOIN users u ON u.id = totals.user_id
                FOR UPDATE OF u
            ), updated AS (
            UPDATE users u
            SET loyalty_points_balance = u.loyalty_points_balance - deductions.expired_points,
                updated_at = NOW()
            FROM deductions
            WHERE u.id = deductions.user_id
            RETURNING u.id, deductions.requested_points, deductions.expired_points,
                      u.loyalty_points_balance AS balance_after
            )
            INSERT INTO loyalty_transactions
                (id, user_id, type, points, balance_before, balance_after, reason, metadata)
            SELECT gen_random_uuid(), id, 'EXPIRE', expired_points,
                   balance_after + expired_points, balance_after,
                   'Điểm thưởng đã hết hạn sau 6 tháng.',
                   jsonb_build_object('requested_points', requested_points)
            FROM updated
            WHERE expired_points > 0
            RETURNING user_id
            """
        )
    )
    expired_users = len(expired.all())

    reviewed = await session.execute(
        text(
            """
            WITH candidates AS (
                SELECT
                    u.id,
                    u.loyalty_tier_period_ends_at <= NOW() AS period_ended,
                    COALESCE(SUM(o.total_amount) FILTER (
                        WHERE o.status = 'COMPLETED'
                          AND o.completed_at >= u.loyalty_tier_period_started_at
                          AND o.completed_at < u.loyalty_tier_period_ends_at
                    ), 0) AS spend_amount
                FROM users u
                LEFT JOIN orders o ON o.user_id = u.id
                WHERE u.loyalty_wallet_status = 'ACTIVE'
                  AND u.loyalty_tier_period_started_at IS NOT NULL
                  AND u.loyalty_tier_period_ends_at <= NOW()
                GROUP BY u.id
            ), qualified AS (
                SELECT id, period_ended,
                    CASE
                        WHEN spend_amount >= 150000000 THEN 'DIAMOND'
                        WHEN spend_amount >= 80000000 THEN 'GOLD'
                        WHEN spend_amount >= 30000000 THEN 'SILVER'
                        ELSE 'MEMBER'
                    END AS qualified_tier
                FROM candidates
            )
            UPDATE users u
            SET loyalty_tier = q.qualified_tier,
                loyalty_tier_period_started_at = u.loyalty_tier_period_ends_at,
                loyalty_tier_period_ends_at = u.loyalty_tier_period_ends_at + INTERVAL '6 months',
                updated_at = NOW()
            FROM qualified q
            WHERE u.id = q.id
            RETURNING u.id
            """
        )
    )
    reviewed_users = len(reviewed.all())
    await session.commit()
    return {"expiredPointUsers": expired_users, "reviewedTierUsers": reviewed_users}
