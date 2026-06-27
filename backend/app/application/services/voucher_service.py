import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import VoucherPayload
from app.infrastructure.database.repositories import voucher_repo


def assigned_user_ids(payload: VoucherPayload) -> list[UUID]:
    ids = [*payload.assignedUserIds]
    if payload.assignedUserId:
        ids.append(payload.assignedUserId)
    return list(dict.fromkeys(ids))


def voucher_params(payload: VoucherPayload, voucher_id: UUID) -> dict:
    selected_user_ids = assigned_user_ids(payload)
    return {
        "id": voucher_id,
        "code": payload.code.strip().upper(),
        "discount_type": payload.discountType if payload.discountType in {"FIXED", "PERCENT"} else "FIXED",
        "discount_value": payload.discountAmount,
        "min_order_value": payload.minOrderValue,
        "max_discount": payload.maxDiscount,
        "usage_limit": payload.usageLimit,
        "total_budget_cap": payload.totalBudgetCap,
        "per_user_limit": payload.perUserLimit,
        "per_device_limit": payload.perDeviceLimit,
        "per_ip_limit": payload.perIpLimit,
        "campaign_type": payload.campaignType,
        "audience_type": payload.audienceType,
        "display_title": payload.displayTitle,
        "display_description": payload.displayDescription,
        "public_terms": payload.publicTerms,
        "applicable_channels": json.dumps(payload.applicableChannels),
        "applicable_payment_methods": json.dumps(payload.applicablePaymentMethods),
        "eligible_tiers": json.dumps(payload.eligibleTiers),
        "eligible_user_registered_after": payload.eligibleUserRegisteredAfter,
        "assigned_user_id": selected_user_ids[0] if len(selected_user_ids) == 1 else None,
        "include_product_ids": json.dumps(payload.includeProductIds),
        "exclude_product_ids": json.dumps(payload.excludeProductIds),
        "include_category_ids": json.dumps(payload.includeCategoryIds),
        "exclude_category_ids": json.dumps(payload.excludeCategoryIds),
        "include_brand_ids": json.dumps(payload.includeBrandIds),
        "exclude_brand_ids": json.dumps(payload.excludeBrandIds),
        "first_order_only": payload.firstOrderOnly,
        "hidden_code": payload.hiddenCode,
        "abandoned_cart_only": payload.abandonedCartOnly,
        "validity_days_after_claim": payload.validityDaysAfterClaim,
        "stackable": payload.stackable,
        "refund_policy": payload.refundPolicy,
        "starts_at": payload.startsAt,
        "ends_at": payload.endsAt,
        "internal_note": payload.internalNote,
        "status": payload.status if payload.status in {"ACTIVE", "INACTIVE", "EXPIRED"} else "ACTIVE",
    }


async def list_admin_vouchers(session: AsyncSession) -> list[dict]:
    return await voucher_repo.list_admin_vouchers(session)


async def create_voucher(
    payload: VoucherPayload,
    session: AsyncSession,
) -> dict:
    voucher_id = uuid4()
    await voucher_repo.insert_voucher(session, voucher_params(payload, voucher_id))
    if payload.audienceType == "SPECIFIC_USER":
        await voucher_repo.sync_assigned_user_vouchers(session, voucher_id=voucher_id, user_ids=assigned_user_ids(payload))
    await session.commit()
    return {"id": str(voucher_id)}


async def update_voucher(
    voucher_id: UUID,
    payload: VoucherPayload,
    session: AsyncSession,
) -> dict:
    updated = await voucher_repo.update_voucher(session, voucher_params(payload, voucher_id))
    if updated == 0:
        raise HTTPException(status_code=404, detail="Voucher not found.")
    await voucher_repo.sync_assigned_user_vouchers(
        session,
        voucher_id=voucher_id,
        user_ids=assigned_user_ids(payload) if payload.audienceType == "SPECIFIC_USER" else [],
    )
    await session.commit()
    return {"ok": True}


async def deactivate_voucher(
    voucher_id: UUID,
    session: AsyncSession,
) -> dict:
    updated = await voucher_repo.deactivate_voucher(session, voucher_id)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Voucher not found.")
    await session.commit()
    return {"ok": True}
