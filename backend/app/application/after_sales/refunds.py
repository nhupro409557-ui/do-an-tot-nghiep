from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.common import money
from app.infrastructure.database.repositories import after_sales_repo


async def create_refunds(
    session: AsyncSession,
    request: dict,
    items: list[dict],
    shipping_deduction: float,
    depreciation_fee: float = 0,
) -> None:
    total_gross = sum((money(item["refundable_amount_snapshot"]) for item in items), Decimal("0"))
    deduction = min(money(shipping_deduction), total_gross)
    depreciation = min(money(depreciation_fee), max(total_gross - deduction, Decimal("0")))
    remaining_deduction = deduction
    remaining_depreciation = depreciation
    for index, item in enumerate(items):
        gross = money(item["refundable_amount_snapshot"])
        item_deduction = remaining_deduction if index == len(items) - 1 else money(
            deduction * gross / total_gross
        ) if total_gross else Decimal("0")
        remaining_deduction -= item_deduction
        item_depreciation = remaining_depreciation if index == len(items) - 1 else money(
            depreciation * gross / total_gross
        ) if total_gross else Decimal("0")
        remaining_depreciation -= item_depreciation
        await session.execute(
            text(
                """
                INSERT INTO refund_transactions
                    (id, order_id, order_item_id, return_request_id, user_id, provider,
                     status, gross_amount, shipping_deduction, refund_amount,
                     idempotency_key, metadata)
                VALUES
                    (:id, :order_id, :order_item_id, :request_id, :user_id, :provider,
                     'PROCESSING', :gross, :deduction, :refund,
                     :key, jsonb_build_object('snapshotVersion', 1, 'depreciationFee', :depreciation))
                ON CONFLICT (idempotency_key) DO NOTHING
                """
            ),
            {
                "id": uuid4(),
                "order_id": request["order_id"],
                "order_item_id": item["order_item_id"],
                "request_id": request["id"],
                "user_id": request["user_id"],
                "provider": "MANUAL",
                "gross": gross,
                "deduction": item_deduction,
                "depreciation": item_depreciation,
                "refund": max(gross - item_deduction - item_depreciation, Decimal("0")),
                "key": f"return:{request['id']}:item:{item['order_item_id']}",
            },
        )

    # Thực hiện hoàn tồn kho (restock) nếu hàng hóa QC đạt chất lượng và không phải lỗi khách
    loc_res = await session.execute(
        text("SELECT id FROM inventory_locations WHERE code = 'MAIN'")
    )
    loc_row = loc_res.first()
    location_id = loc_row[0] if loc_row else None
    if not location_id:
        loc_res = await session.execute(
            text("SELECT id FROM inventory_locations LIMIT 1")
        )
        loc_row = loc_res.first()
        location_id = loc_row[0] if loc_row else None

    customer_fault = request.get("customer_fault", False)

    for item in items:
        product_id = item.get("product_id")
        variant_id = item.get("product_variant_id")
        qty = int(item.get("quantity") or 1)
        imei = item.get("imei")
        serial_number = item.get("serial_number")

        if not customer_fault and location_id:
            # Lấy số lượng on_hand_quantity cũ của kho chính để thực hiện log
            level_res = await session.execute(
                text(
                    """
                    SELECT on_hand_quantity FROM inventory_levels
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND location_id = :location_id
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id, "location_id": location_id}
            )
            level_row = level_res.first()
            old_qty = level_row[0] if level_row else 0
            new_qty = old_qty + qty

            await session.execute(
                text(
                    """
                    INSERT INTO inventory_levels (id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, updated_at)
                    VALUES (:id, :product_id, :variant_id, :location_id, :qty, 0, NOW())
                    ON CONFLICT (product_id, COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid), location_id)
                    DO UPDATE SET on_hand_quantity = inventory_levels.on_hand_quantity + EXCLUDED.on_hand_quantity, updated_at = NOW()
                    """
                ),
                {"id": uuid4(), "product_id": product_id, "variant_id": variant_id, "location_id": location_id, "qty": qty}
            )

            # Cập nhật tổng tồn kho cho sản phẩm chính
            await session.execute(
                text("UPDATE products SET stock_quantity = stock_quantity + :qty, updated_at = NOW() WHERE id = :product_id"),
                {"qty": qty, "product_id": product_id}
            )

            # Cập nhật tổng tồn kho cho variant của sản phẩm (nếu có)
            if variant_id:
                await session.execute(
                    text("UPDATE product_variants SET stock_quantity = stock_quantity + :qty, updated_at = NOW() WHERE id = :variant_id"),
                    {"qty": qty, "variant_id": variant_id}
                )

            # Ghi log điều chỉnh tồn kho
            await session.execute(
                text(
                    """
                    INSERT INTO inventory_adjustment_logs (id, product_id, variant_id, old_quantity, new_quantity, delta, reason, note, created_at)
                    VALUES (:id, :product_id, :variant_id, :old_qty, :new_qty, :qty, 'RETURN', :note, NOW())
                    """
                ),
                {
                    "id": uuid4(),
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "old_qty": old_qty,
                    "new_qty": new_qty,
                    "qty": qty,
                    "note": f"Hoàn tồn kho từ yêu cầu đổi trả hoàn tiền {request.get('request_code')}."
                }
            )

            # Phục hồi trạng thái IMEI về IN_STOCK
            if imei:
                await session.execute(
                    text(
                        """
                        UPDATE product_imeis
                        SET status = 'IN_STOCK', sold_at = NULL, sold_order_id = NULL, updated_at = NOW()
                        WHERE imei = :imei AND status = 'SOLD'
                        """
                    ),
                    {"imei": imei}
                )

            # Phục hồi trạng thái Serial Number về IN_STOCK
            if serial_number:
                await session.execute(
                    text(
                        """
                        UPDATE product_serial_numbers
                        SET status = 'IN_STOCK', sold_at = NULL, sold_order_id = NULL, updated_at = NOW()
                        WHERE serial_number = :serial AND status = 'SOLD'
                        """
                    ),
                    {"serial": serial_number}
                )
        else:
            # Nếu là lỗi do phía khách hàng (ví dụ: làm hỏng), chuyển IMEI/Serial sang DEFECTIVE_RETURNED để kiểm tra sau
            if imei:
                await session.execute(
                    text("UPDATE product_imeis SET status = 'DEFECTIVE_RETURNED', updated_at = NOW() WHERE imei = :imei"),
                    {"imei": imei}
                )
            if serial_number:
                await session.execute(
                    text("UPDATE product_serial_numbers SET status = 'DEFECTIVE_RETURNED', updated_at = NOW() WHERE serial_number = :serial"),
                    {"serial": serial_number}
                )
    order_item_count = int(await session.scalar(
        text("SELECT COUNT(*) FROM order_items WHERE order_id=:order_id"),
        {"order_id": request["order_id"]},
    ) or 0)
    returned_item_count = len({item["order_item_id"] for item in items})
    order_discount = money(await session.scalar(
        text("SELECT discount_amount FROM orders WHERE id=:order_id"),
        {"order_id": request["order_id"]},
    ) or 0)
    if returned_item_count == order_item_count and order_discount > 0 and not request.get("customer_fault"):
        await issue_compensation_voucher(session, request=request, amount=order_discount)


async def issue_compensation_voucher(session: AsyncSession, *, request: dict, amount: Decimal) -> None:
    existing = await session.scalar(
        text(
            """
            SELECT EXISTS(
                SELECT 1 FROM compensation_vouchers cv
                JOIN refund_transactions rt ON rt.id=cv.refund_transaction_id
                WHERE rt.return_request_id=:request_id
            )
            """
        ),
        {"request_id": request["id"]},
    )
    if existing:
        return
    refund_id = await session.scalar(
        text(
            """
            SELECT id FROM refund_transactions
            WHERE return_request_id=:request_id
            ORDER BY created_at LIMIT 1
            """
        ),
        {"request_id": request["id"]},
    )
    if not refund_id:
        return
    voucher_id = uuid4()
    user_voucher_id = uuid4()
    code = f"BD{str(request['id']).replace('-', '')[:10].upper()}"
    await session.execute(
        text(
            """
            INSERT INTO vouchers
                (id, code, discount_type, discount_value, min_order_value,
                 usage_limit, per_user_limit, campaign_type, audience_type,
                 assigned_user_id, validity_days_after_claim, hidden_code,
                 refund_policy, internal_note, status, starts_at, ends_at)
            VALUES
                (:id, :code, 'FIXED', :amount, 0, 1, 1, 'CUSTOMER_SERVICE',
                 'SPECIFIC_USER', :user_id, 30, TRUE, 'SHOP_FAULT_ONLY',
                 :note, 'ACTIVE', NOW(), NOW() + INTERVAL '30 days')
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {
            "id": voucher_id,
            "code": code,
            "amount": amount,
            "user_id": request["user_id"],
            "note": f"Voucher đền bù từ yêu cầu {request['request_code']}.",
        },
    )
    actual_voucher_id = await session.scalar(text("SELECT id FROM vouchers WHERE code=:code"), {"code": code})
    await session.execute(
        text(
            """
            INSERT INTO user_vouchers
                (id, user_id, voucher_id, status, claimed_at, expires_at)
            VALUES (:id, :user_id, :voucher_id, 'AVAILABLE', NOW(), NOW() + INTERVAL '30 days')
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": user_voucher_id, "user_id": request["user_id"], "voucher_id": actual_voucher_id},
    )
    actual_user_voucher_id = await session.scalar(
        text(
            """
            SELECT id FROM user_vouchers
            WHERE user_id=:user_id AND voucher_id=:voucher_id
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"user_id": request["user_id"], "voucher_id": actual_voucher_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO compensation_vouchers
                (id, refund_transaction_id, voucher_id, user_voucher_id, source_order_id)
            VALUES (:id, :refund_id, :voucher_id, :user_voucher_id, :order_id)
            ON CONFLICT (refund_transaction_id) DO NOTHING
            """
        ),
        {
            "id": uuid4(),
            "refund_id": refund_id,
            "voucher_id": actual_voucher_id,
            "user_voucher_id": actual_user_voucher_id,
            "order_id": request["order_id"],
        },
    )
    await after_sales_repo.notify(
        session,
        user_id=request["user_id"],
        type_value="voucher",
        title="Bạn nhận được voucher đền bù",
        message=f"Voucher {code} trị giá {int(amount):,}đ có hiệu lực trong 30 ngày.",
        entity_type="VOUCHER",
        entity_id=actual_voucher_id,
        immediate=True,
        key=f"compensation-voucher:{request['id']}",
    )
