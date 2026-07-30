from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def grant_due_birthday_vouchers(session: AsyncSession) -> int:
    result = await session.execute(
        text(
            """
            WITH eligible AS (
                SELECT DISTINCT
                    u.id AS user_id,
                    v.id AS voucher_id,
                    EXTRACT(YEAR FROM CURRENT_DATE)::int AS birthday_year,
                    LEAST(
                        v.ends_at,
                        NOW() + make_interval(days => CASE WHEN v.validity_days_after_claim > 0 THEN v.validity_days_after_claim ELSE 14 END)
                    ) AS expires_at
                FROM users u
                JOIN roles r ON r.id = u.role_id AND r.code = 'CUSTOMER'
                JOIN vouchers v
                  ON v.birthday_only = TRUE
                 AND v.status = 'ACTIVE'
                 AND (v.starts_at IS NULL OR v.starts_at <= NOW())
                 AND (v.ends_at IS NULL OR v.ends_at > NOW())
                 AND (v.usage_limit = 0 OR v.used_count < v.usage_limit)
                 AND (v.total_budget_cap IS NULL OR v.total_discount_used < v.total_budget_cap)
                 AND (
                    v.eligible_tiers = '[]'::jsonb
                    OR EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(v.eligible_tiers) AS tier(value)
                        WHERE UPPER(tier.value) = UPPER(u.loyalty_tier)
                    )
                 )
                WHERE u.status = 'ACTIVE'
                  AND u.deleted_at IS NULL
                  AND u.birth_date IS NOT NULL
                  AND u.birth_date_locked_at IS NOT NULL
                  AND u.phone IS NOT NULL
                  AND BTRIM(u.phone) <> ''
                  AND u.created_at <= NOW() - INTERVAL '30 days'
                  AND EXTRACT(MONTH FROM u.birth_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                  AND EXTRACT(DAY FROM u.birth_date) = EXTRACT(DAY FROM CURRENT_DATE)
                  AND EXISTS (
                      SELECT 1
                      FROM orders o
                      WHERE o.user_id = u.id
                        AND o.status IN ('PAID', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'COMPLETED')
                  )
            ), granted AS (
                INSERT INTO birthday_voucher_grants (id, user_id, voucher_id, birthday_year)
                SELECT gen_random_uuid(), user_id, voucher_id, birthday_year
                FROM eligible
                ON CONFLICT (user_id, voucher_id, birthday_year) DO NOTHING
                RETURNING user_id, voucher_id
            )
            INSERT INTO user_vouchers (id, user_id, voucher_id, status, claimed_at, expires_at, created_at, updated_at)
            SELECT gen_random_uuid(), g.user_id, g.voucher_id, 'AVAILABLE', NOW(), e.expires_at, NOW(), NOW()
            FROM granted g
            JOIN eligible e ON e.user_id = g.user_id AND e.voucher_id = g.voucher_id
            WHERE NOT EXISTS (
                SELECT 1 FROM user_vouchers uv
                WHERE uv.user_id = g.user_id
                  AND uv.voucher_id = g.voucher_id
                  AND uv.status IN ('AVAILABLE', 'RESERVED')
            )
            RETURNING id
            """
        )
    )
    await session.commit()
    return len(result.all())
