from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_admin_vouchers(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                code,
                discount_type AS "discountType",
                discount_value AS "discountAmount",
                min_order_value AS "minOrderValue",
                max_discount AS "maxDiscount",
                usage_limit AS "usageLimit",
                used_count AS "usedCount",
                total_budget_cap AS "totalBudgetCap",
                total_discount_used AS "totalDiscountUsed",
                per_user_limit AS "perUserLimit",
                per_device_limit AS "perDeviceLimit",
                per_ip_limit AS "perIpLimit",
                redemption_points AS "redemptionPoints",
                campaign_type AS "campaignType",
                audience_type AS "audienceType",
                display_title AS "displayTitle",
                display_description AS "displayDescription",
                public_terms AS "publicTerms",
                applicable_channels AS "applicableChannels",
                applicable_payment_methods AS "applicablePaymentMethods",
                eligible_tiers AS "eligibleTiers",
                eligible_user_registered_after AS "eligibleUserRegisteredAfter",
                assigned_user_id::text AS "assignedUserId",
                COALESCE((
                    SELECT jsonb_agg(uv.user_id::text ORDER BY uv.claimed_at DESC)
                    FROM user_vouchers uv
                    WHERE uv.voucher_id = vouchers.id
                      AND uv.status IN ('AVAILABLE', 'RESERVED', 'USED')
                ), '[]'::jsonb) AS "assignedUserIds",
                include_product_ids AS "includeProductIds",
                exclude_product_ids AS "excludeProductIds",
                include_category_ids AS "includeCategoryIds",
                exclude_category_ids AS "excludeCategoryIds",
                include_brand_ids AS "includeBrandIds",
                exclude_brand_ids AS "excludeBrandIds",
                first_order_only AS "firstOrderOnly",
                hidden_code AS "hiddenCode",
                abandoned_cart_only AS "abandonedCartOnly",
                birthday_only AS "birthdayOnly",
                validity_days_after_claim AS "validityDaysAfterClaim",
                stackable,
                apply_outside_scope AS "applyOutsideScope",
                refund_policy AS "refundPolicy",
                starts_at AS "startsAt",
                ends_at AS "endsAt",
                internal_note AS "internalNote",
                status
            FROM vouchers
            ORDER BY created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def list_public_vouchers(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                code,
                discount_type AS "discountType",
                discount_value AS "discountAmount",
                min_order_value AS "minOrderValue",
                max_discount AS "maxDiscount",
                redemption_points AS "redemptionPoints",
                display_title AS "displayTitle",
                display_description AS "displayDescription",
                public_terms AS "publicTerms",
                applicable_channels AS "applicableChannels",
                applicable_payment_methods AS "applicablePaymentMethods",
                stackable,
                ends_at AS "endsAt",
                audience_type AS "audienceType",
                status,
                status = 'ACTIVE' AS "isActive"
            FROM vouchers
            WHERE status = 'ACTIVE'
              AND hidden_code = FALSE
              AND audience_type = 'PUBLIC'
              AND birthday_only = FALSE
              AND (starts_at IS NULL OR starts_at <= NOW())
              AND (ends_at IS NULL OR ends_at > NOW())
              AND (usage_limit = 0 OR used_count < usage_limit)
              AND (total_budget_cap IS NULL OR total_discount_used < total_budget_cap)
            ORDER BY created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def insert_voucher(session: AsyncSession, params: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO vouchers (
                id, code, discount_type, discount_value, min_order_value, max_discount,
                usage_limit, total_budget_cap, per_user_limit, per_device_limit, per_ip_limit, redemption_points,
                campaign_type, audience_type, display_title, display_description, public_terms,
                applicable_channels, applicable_payment_methods, eligible_tiers, eligible_user_registered_after,
                assigned_user_id, include_product_ids, exclude_product_ids, include_category_ids,
                exclude_category_ids, include_brand_ids, exclude_brand_ids, first_order_only, hidden_code, abandoned_cart_only, birthday_only,
                validity_days_after_claim, stackable, apply_outside_scope, refund_policy, starts_at, ends_at, internal_note, status
            )
            VALUES (
                :id, :code, :discount_type, :discount_value, :min_order_value, :max_discount,
                :usage_limit, :total_budget_cap, :per_user_limit, :per_device_limit, :per_ip_limit, :redemption_points,
                :campaign_type, :audience_type, :display_title, :display_description, :public_terms,
                CAST(:applicable_channels AS jsonb), CAST(:applicable_payment_methods AS jsonb), CAST(:eligible_tiers AS jsonb), :eligible_user_registered_after,
                :assigned_user_id, CAST(:include_product_ids AS jsonb), CAST(:exclude_product_ids AS jsonb), CAST(:include_category_ids AS jsonb),
                CAST(:exclude_category_ids AS jsonb), CAST(:include_brand_ids AS jsonb), CAST(:exclude_brand_ids AS jsonb), :first_order_only, :hidden_code, :abandoned_cart_only, :birthday_only,
                :validity_days_after_claim, :stackable, :apply_outside_scope, :refund_policy, :starts_at, :ends_at, :internal_note, :status
            )
            """
        ),
        params,
    )


async def update_voucher(session: AsyncSession, voucher_id: UUID, params: dict) -> int:
    if not params:
        return 0
    set_clauses = []
    query_params = {"id": voucher_id}
    jsonb_cols = {
        "applicable_channels",
        "applicable_payment_methods",
        "eligible_tiers",
        "include_product_ids",
        "exclude_product_ids",
        "include_category_ids",
        "exclude_category_ids",
        "include_brand_ids",
        "exclude_brand_ids",
    }
    for col, val in params.items():
        if col in jsonb_cols:
            set_clauses.append(f"{col} = CAST(:{col} AS jsonb)")
        else:
            set_clauses.append(f"{col} = :{col}")
        query_params[col] = val

    set_str = ", ".join(set_clauses)
    result = await session.execute(
        text(
            f"""
            UPDATE vouchers
            SET {set_str}, updated_at = NOW()
            WHERE id = :id
            """
        ),
        query_params,
    )
    return int(result.rowcount or 0)


async def deactivate_voucher(session: AsyncSession, voucher_id: UUID) -> int:
    result = await session.execute(
        text("UPDATE vouchers SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"),
        {"id": voucher_id},
    )
    return int(result.rowcount or 0)


async def sync_assigned_user_vouchers(session: AsyncSession, *, voucher_id: UUID, user_ids: list[UUID]) -> None:
    keep_user_ids = set(user_ids)

    # 1. Kiểm tra xem có voucher nào đang ở trạng thái RESERVED cho đơn hàng PENDING mà không nằm trong danh sách giữ lại (keep_user_ids) không.
    pending_query = """
        SELECT EXISTS (
            SELECT 1
            FROM user_vouchers uv
            JOIN orders o ON o.voucher_claim_id = uv.id
            WHERE uv.voucher_id = :voucher_id
              AND uv.status = 'RESERVED'
              AND o.status = 'PENDING'
    """
    if keep_user_ids:
        pending_query += " AND NOT (uv.user_id = ANY(:keep_user_ids))"
    pending_query += ")"

    pending = await session.scalar(
        text(pending_query),
        {"voucher_id": voucher_id, "keep_user_ids": list(keep_user_ids)} if keep_user_ids else {"voucher_id": voucher_id}
    )
    if pending:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=409,
            detail={
                "code": "VOUCHER_ERR_RESERVED_ASSIGNMENT",
                "message": "Không thể thu hồi voucher đang được giữ cho đơn hàng chờ thanh toán.",
                "metadata": {}
            }
        )

    # 2. Chỉ thu hồi (REVOKED) những user_voucher có trạng thái AVAILABLE
    revoke_query = """
        UPDATE user_vouchers
        SET status = 'REVOKED', updated_at = NOW()
        WHERE voucher_id = :voucher_id
          AND status = 'AVAILABLE'
    """
    if keep_user_ids:
        revoke_query += " AND NOT (user_id = ANY(:keep_user_ids))"

    await session.execute(
        text(revoke_query),
        {"voucher_id": voucher_id, "keep_user_ids": list(keep_user_ids)} if keep_user_ids else {"voucher_id": voucher_id}
    )

    for user_id in user_ids:
        await session.execute(
            text(
                """
                INSERT INTO user_vouchers (id, user_id, voucher_id, status, expires_at)
                SELECT
                    gen_random_uuid(),
                    :user_id,
                    id,
                    'AVAILABLE',
                    CASE
                        WHEN validity_days_after_claim > 0 THEN NOW() + make_interval(days => validity_days_after_claim)
                        ELSE ends_at
                    END
                FROM vouchers
                WHERE id = :voucher_id
                ON CONFLICT (user_id, voucher_id) WHERE status IN ('AVAILABLE', 'RESERVED', 'USED') DO NOTHING
                """
            ),
            {"voucher_id": voucher_id, "user_id": user_id},
        )


async def expire_available_wallet_vouchers(session: AsyncSession, now: datetime) -> int:
    result = await session.execute(
        text(
            """
            UPDATE user_vouchers
            SET status = 'EXPIRED', updated_at = :now
            WHERE status = 'AVAILABLE'
              AND expires_at IS NOT NULL
              AND expires_at < :now
            """
        ),
        {"now": now},
    )
    return int(result.rowcount or 0)

