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
                campaign_type AS "campaignType",
                audience_type AS "audienceType",
                eligible_tiers AS "eligibleTiers",
                eligible_user_registered_after AS "eligibleUserRegisteredAfter",
                assigned_user_id::text AS "assignedUserId",
                include_product_ids AS "includeProductIds",
                exclude_product_ids AS "excludeProductIds",
                include_category_ids AS "includeCategoryIds",
                exclude_category_ids AS "excludeCategoryIds",
                first_order_only AS "firstOrderOnly",
                hidden_code AS "hiddenCode",
                abandoned_cart_only AS "abandonedCartOnly",
                validity_days_after_claim AS "validityDaysAfterClaim",
                stackable,
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
                status,
                status = 'ACTIVE' AS "isActive"
            FROM vouchers
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
                usage_limit, total_budget_cap, per_user_limit, per_device_limit, per_ip_limit,
                campaign_type, audience_type, eligible_tiers, eligible_user_registered_after,
                assigned_user_id, include_product_ids, exclude_product_ids, include_category_ids,
                exclude_category_ids, first_order_only, hidden_code, abandoned_cart_only,
                validity_days_after_claim, stackable, refund_policy, starts_at, ends_at, internal_note, status
            )
            VALUES (
                :id, :code, :discount_type, :discount_value, :min_order_value, :max_discount,
                :usage_limit, :total_budget_cap, :per_user_limit, :per_device_limit, :per_ip_limit,
                :campaign_type, :audience_type, CAST(:eligible_tiers AS jsonb), :eligible_user_registered_after,
                :assigned_user_id, CAST(:include_product_ids AS jsonb), CAST(:exclude_product_ids AS jsonb), CAST(:include_category_ids AS jsonb),
                CAST(:exclude_category_ids AS jsonb), :first_order_only, :hidden_code, :abandoned_cart_only,
                :validity_days_after_claim, :stackable, :refund_policy, :starts_at, :ends_at, :internal_note, :status
            )
            """
        ),
        params,
    )


async def update_voucher(session: AsyncSession, params: dict) -> int:
    result = await session.execute(
        text(
            """
            UPDATE vouchers
            SET code = :code,
                discount_type = :discount_type,
                discount_value = :discount_value,
                min_order_value = :min_order_value,
                max_discount = :max_discount,
                usage_limit = :usage_limit,
                total_budget_cap = :total_budget_cap,
                per_user_limit = :per_user_limit,
                per_device_limit = :per_device_limit,
                per_ip_limit = :per_ip_limit,
                campaign_type = :campaign_type,
                audience_type = :audience_type,
                eligible_tiers = CAST(:eligible_tiers AS jsonb),
                eligible_user_registered_after = :eligible_user_registered_after,
                assigned_user_id = :assigned_user_id,
                include_product_ids = CAST(:include_product_ids AS jsonb),
                exclude_product_ids = CAST(:exclude_product_ids AS jsonb),
                include_category_ids = CAST(:include_category_ids AS jsonb),
                exclude_category_ids = CAST(:exclude_category_ids AS jsonb),
                first_order_only = :first_order_only,
                hidden_code = :hidden_code,
                abandoned_cart_only = :abandoned_cart_only,
                validity_days_after_claim = :validity_days_after_claim,
                stackable = :stackable,
                refund_policy = :refund_policy,
                starts_at = :starts_at,
                ends_at = :ends_at,
                internal_note = :internal_note,
                status = :status,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        params,
    )
    return int(result.rowcount or 0)


async def deactivate_voucher(session: AsyncSession, voucher_id: UUID) -> int:
    result = await session.execute(
        text("UPDATE vouchers SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"),
        {"id": voucher_id},
    )
    return int(result.rowcount or 0)
