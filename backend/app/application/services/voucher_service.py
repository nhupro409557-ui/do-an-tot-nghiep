import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import VoucherPayload, VoucherUpdatePayload
from app.infrastructure.database.repositories import voucher_repo


def assigned_user_ids(payload: VoucherPayload) -> list[UUID]:
    ids = [*payload.assignedUserIds]
    if payload.assignedUserId:
        ids.append(payload.assignedUserId)
    return list(dict.fromkeys(ids))


def assigned_user_ids_update(payload: VoucherUpdatePayload) -> list[UUID]:
    ids = []
    if payload.assignedUserIds is not None:
        ids.extend(payload.assignedUserIds)
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
        "redemption_points": payload.redemptionPoints,
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
        "birthday_only": payload.birthdayOnly,
        "validity_days_after_claim": payload.validityDaysAfterClaim,
        "stackable": payload.stackable,
        "apply_outside_scope": payload.applyOutsideScope,
        "refund_policy": payload.refundPolicy,
        "starts_at": payload.startsAt,
        "ends_at": payload.endsAt,
        "internal_note": payload.internalNote,
        "status": payload.status if payload.status in {"ACTIVE", "INACTIVE", "EXPIRED"} else "ACTIVE",
    }


def voucher_update_params(payload: VoucherUpdatePayload) -> dict:
    data = {}
    exclude_fields = {"assignedUserId", "assignedUserIds", "scopeType"}
    dumped = payload.model_dump(exclude_unset=True)

    mapping = {
        "code": "code",
        "discountType": "discount_type",
        "discountAmount": "discount_value",
        "minOrderValue": "min_order_value",
        "maxDiscount": "max_discount",
        "usageLimit": "usage_limit",
        "totalBudgetCap": "total_budget_cap",
        "perUserLimit": "per_user_limit",
        "perDeviceLimit": "per_device_limit",
        "perIpLimit": "per_ip_limit",
        "redemptionPoints": "redemption_points",
        "campaignType": "campaign_type",
        "audienceType": "audience_type",
        "displayTitle": "display_title",
        "displayDescription": "display_description",
        "publicTerms": "public_terms",
        "applicableChannels": "applicable_channels",
        "applicablePaymentMethods": "applicable_payment_methods",
        "eligibleTiers": "eligible_tiers",
        "eligibleUserRegisteredAfter": "eligible_user_registered_after",
        "includeProductIds": "include_product_ids",
        "excludeProductIds": "exclude_product_ids",
        "includeCategoryIds": "include_category_ids",
        "excludeCategoryIds": "exclude_category_ids",
        "includeBrandIds": "include_brand_ids",
        "excludeBrandIds": "exclude_brand_ids",
        "firstOrderOnly": "first_order_only",
        "hiddenCode": "hidden_code",
        "abandonedCartOnly": "abandoned_cart_only",
        "birthdayOnly": "birthday_only",
        "validityDaysAfterClaim": "validity_days_after_claim",
        "stackable": "stackable",
        "applyOutsideScope": "apply_outside_scope",
        "refundPolicy": "refund_policy",
        "startsAt": "starts_at",
        "endsAt": "ends_at",
        "internalNote": "internal_note",
        "status": "status",
    }

    for k, v in dumped.items():
        if k in mapping:
            db_col = mapping[k]
            if k == "code" and isinstance(v, str):
                data[db_col] = v.strip().upper()
            elif k in {"applicableChannels", "applicablePaymentMethods", "eligibleTiers",
                       "includeProductIds", "excludeProductIds", "includeCategoryIds",
                       "excludeCategoryIds", "includeBrandIds", "excludeBrandIds"} and isinstance(v, list):
                data[db_col] = json.dumps(v)
            else:
                data[db_col] = v

    # Nếu có gán người dùng cụ thể, cần đảm bảo có assigned_user_id nếu chỉ có 1 user được gán
    if "assignedUserId" in dumped or "assignedUserIds" in dumped:
        selected_user_ids = assigned_user_ids_update(payload)
        data["assigned_user_id"] = selected_user_ids[0] if len(selected_user_ids) == 1 else None

    return data


from datetime import datetime

def parse_datetime(dt_val) -> datetime | None:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str):
        try:
            clean_val = dt_val.replace('T', ' ')
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(clean_val, fmt)
                except ValueError:
                    continue
            return datetime.fromisoformat(dt_val)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_INVALID_DATE_FORMAT",
                    "message": "Định dạng ngày không hợp lệ.",
                    "metadata": {},
                },
            )
    return None


def validate_voucher_rules(state: dict, assigned_user_ids_list: list) -> None:
    # 1. Discount type and amount
    discount_type = state.get("discount_type")
    discount_value = state.get("discount_value")
    if discount_type == "PERCENT" and discount_value is not None and discount_value > 100.0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VOUCHER_ERR_PERCENT_VALUE_LIMIT",
                "message": "Giá trị phần trăm giảm giá không được vượt quá 100%.",
                "metadata": {},
            },
        )

    # 2. Date range
    starts_at = parse_datetime(state.get("starts_at"))
    ends_at = parse_datetime(state.get("ends_at"))
    if starts_at and ends_at and starts_at >= ends_at:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VOUCHER_ERR_INVALID_DATE_RANGE",
                "message": "Ngày bắt đầu phải trước ngày kết thúc.",
                "metadata": {},
            },
        )

    # 3. Audience type constraints
    audience_type = state.get("audience_type")
    if state.get("birthday_only"):
        eligible_tiers = state.get("eligible_tiers")
        if isinstance(eligible_tiers, str):
            try:
                eligible_tiers = json.loads(eligible_tiers)
            except Exception:
                eligible_tiers = []
        if not isinstance(eligible_tiers, list) or not eligible_tiers:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_BIRTHDAY_TIER_REQUIRED",
                    "message": "Voucher sinh nhật phải chọn ít nhất một hạng thành viên.",
                    "metadata": {},
                },
            )
        if int(state.get("redemption_points") or 0) > 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_BIRTHDAY_POINTS_NOT_ALLOWED",
                    "message": "Voucher sinh nhật được cấp tự động nên không thể đồng thời yêu cầu đổi điểm.",
                    "metadata": {},
                },
            )
    if audience_type == "SPECIFIC_USER":
        if not assigned_user_ids_list:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_ASSIGNMENT_REQUIRED",
                    "message": "Voucher giới hạn khách hàng cụ thể phải có ít nhất một tài khoản được gán.",
                    "metadata": {},
                },
            )
    elif audience_type == "MEMBER_TIER":
        eligible_tiers = state.get("eligible_tiers")
        if not eligible_tiers:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_TIER_REQUIRED",
                    "message": "Voucher giới hạn hạng thành viên phải chọn ít nhất một hạng.",
                    "metadata": {},
                },
            )
        if isinstance(eligible_tiers, str):
            try:
                eligible_tiers = json.loads(eligible_tiers)
            except Exception:
                pass
        if not isinstance(eligible_tiers, list) or len(eligible_tiers) == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_TIER_REQUIRED",
                    "message": "Voucher giới hạn hạng thành viên phải chọn ít nhất một hạng.",
                    "metadata": {},
                },
            )
    elif audience_type == "NEW_CUSTOMER":
        if not state.get("first_order_only"):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_FIRST_ORDER_ONLY_REQUIRED",
                    "message": "Voucher cho khách hàng mới phải bật điều kiện chỉ áp dụng đơn hàng đầu tiên (firstOrderOnly).",
                    "metadata": {},
                },
            )
    elif audience_type == "ABANDONED_CART":
        if not state.get("abandoned_cart_only"):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VOUCHER_ERR_ABANDONED_CART_ONLY_REQUIRED",
                    "message": "Voucher cho giỏ hàng bỏ quên phải bật điều kiện chỉ áp dụng cho giỏ hàng bỏ quên (abandonedCartOnly).",
                    "metadata": {},
                },
            )


async def list_admin_vouchers(session: AsyncSession) -> list[dict]:
    return await voucher_repo.list_admin_vouchers(session)


async def create_voucher(
    payload: VoucherPayload,
    session: AsyncSession,
) -> dict:
    state = {
        "discount_type": payload.discountType,
        "discount_value": payload.discountAmount,
        "starts_at": payload.startsAt,
        "ends_at": payload.endsAt,
        "audience_type": payload.audienceType,
        "eligible_tiers": payload.eligibleTiers,
        "first_order_only": payload.firstOrderOnly,
        "abandoned_cart_only": payload.abandonedCartOnly,
    }
    user_ids = assigned_user_ids(payload)
    validate_voucher_rules(state, user_ids)

    # Check unique code
    from sqlalchemy import select
    from app.infrastructure.database.models import Voucher
    existing = await session.scalar(select(Voucher).where(Voucher.code == payload.code.strip().upper()))
    if existing:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VOUCHER_ERR_DUPLICATE_CODE",
                "message": "Mã voucher đã tồn tại.",
                "metadata": {},
            },
        )

    voucher_id = uuid4()
    await voucher_repo.insert_voucher(session, voucher_params(payload, voucher_id))
    if payload.audienceType == "SPECIFIC_USER":
        await voucher_repo.sync_assigned_user_vouchers(session, voucher_id=voucher_id, user_ids=user_ids)
    await session.commit()
    return {"id": str(voucher_id)}


async def update_voucher(
    voucher_id: UUID,
    payload: VoucherUpdatePayload,
    session: AsyncSession,
) -> dict:
    from sqlalchemy import select
    from app.infrastructure.database.models import Voucher

    voucher = await session.scalar(select(Voucher).where(Voucher.id == voucher_id))
    if not voucher:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VOUCHER_ERR_NOT_FOUND",
                "message": "Không tìm thấy voucher.",
                "metadata": {},
            },
        )

    dumped = payload.model_dump(exclude_unset=True)

    # Determine final state after applying updates
    target_state = {
        "discount_type": payload.discountType if payload.discountType is not None else voucher.discount_type,
        "discount_value": payload.discountAmount if payload.discountAmount is not None else voucher.discount_value,
        "starts_at": payload.startsAt if payload.startsAt is not None else voucher.starts_at,
        "ends_at": payload.endsAt if payload.endsAt is not None else voucher.ends_at,
        "audience_type": payload.audienceType if payload.audienceType is not None else voucher.audience_type,
        "eligible_tiers": payload.eligibleTiers if payload.eligibleTiers is not None else voucher.eligible_tiers,
        "first_order_only": payload.firstOrderOnly if payload.firstOrderOnly is not None else voucher.first_order_only,
        "abandoned_cart_only": payload.abandonedCartOnly if payload.abandonedCartOnly is not None else voucher.abandoned_cart_only,
    }

    target_audience_type = target_state["audience_type"]

    # Sync and validate assigned user IDs
    if target_audience_type == "SPECIFIC_USER":
        if "assignedUserId" in dumped or "assignedUserIds" in dumped:
            new_user_ids = assigned_user_ids_update(payload)
        else:
            from app.infrastructure.database.models import UserVoucher
            new_user_ids = list((await session.execute(
                select(UserVoucher.user_id)
                .where(UserVoucher.voucher_id == voucher_id)
                .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED"]))
            )).scalars().all())
    else:
        new_user_ids = []

    validate_voucher_rules(target_state, new_user_ids)

    # Check unique code
    if payload.code is not None:
        code_upper = payload.code.strip().upper()
        if code_upper != voucher.code:
            existing = await session.scalar(select(Voucher).where(Voucher.code == code_upper))
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "VOUCHER_ERR_DUPLICATE_CODE",
                        "message": "Mã voucher đã tồn tại.",
                        "metadata": {},
                    },
                )

    params = voucher_update_params(payload)

    # Update assigned user logic in params
    if target_audience_type != "SPECIFIC_USER":
        params["assigned_user_id"] = None
    elif target_audience_type == "SPECIFIC_USER" and ("assignedUserId" in dumped or "assignedUserIds" in dumped):
        params["assigned_user_id"] = new_user_ids[0] if len(new_user_ids) == 1 else None

    updated = await voucher_repo.update_voucher(session, voucher_id, params)
    if updated == 0:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VOUCHER_ERR_NOT_FOUND",
                "message": "Không tìm thấy voucher.",
                "metadata": {},
            },
        )

    if target_audience_type == "SPECIFIC_USER":
        await voucher_repo.sync_assigned_user_vouchers(
            session,
            voucher_id=voucher_id,
            user_ids=new_user_ids,
        )
    else:
        await voucher_repo.sync_assigned_user_vouchers(
            session,
            voucher_id=voucher_id,
            user_ids=[],
        )

    await session.commit()
    return {"ok": True}


async def deactivate_voucher(
    voucher_id: UUID,
    session: AsyncSession,
) -> dict:
    updated = await voucher_repo.deactivate_voucher(session, voucher_id)
    if updated == 0:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VOUCHER_ERR_NOT_FOUND",
                "message": "Không tìm thấy voucher.",
                "metadata": {},
            },
        )
    await session.commit()
    return {"ok": True}
