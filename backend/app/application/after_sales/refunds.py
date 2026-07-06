from decimal import Decimal
from uuid import UUID, uuid4

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
    *,
    status_value: str = "PROCESSING",
    transaction_ref: str | None = None,
    proof_url: str | None = None,
    processed_by: UUID | None = None,
    processed_note: str | None = None,
) -> None:
    refund_status = status_value.upper()
    total_gross = sum((money(item["refundable_amount_snapshot"]) for item in items), Decimal("0"))
    deduction = min(money(shipping_deduction), total_gross)
    depreciation = min(money(depreciation_fee), max(total_gross - deduction, Decimal("0")))
    remaining_deduction = deduction
    remaining_depreciation = depreciation

    for index, item in enumerate(items):
        gross = money(item["refundable_amount_snapshot"])
        item_deduction = (
            remaining_deduction
            if index == len(items) - 1
            else money(deduction * gross / total_gross)
            if total_gross
            else Decimal("0")
        )
        remaining_deduction -= item_deduction
        item_depreciation = (
            remaining_depreciation
            if index == len(items) - 1
            else money(depreciation * gross / total_gross)
            if total_gross
            else Decimal("0")
        )
        remaining_depreciation -= item_depreciation
        await session.execute(
            text(
                """
                INSERT INTO refund_transactions
                    (id, order_id, order_item_id, return_request_id, user_id, provider,
                     status, gross_amount, shipping_deduction, refund_amount,
                     transaction_ref, idempotency_key, metadata, completed_at)
                VALUES
                    (:id, :order_id, :order_item_id, :request_id, :user_id, :provider,
                     CAST(:status_value AS VARCHAR), :gross, :deduction, :refund,
                     :transaction_ref, :key,
                     jsonb_strip_nulls(jsonb_build_object(
                         'snapshotVersion', 1,
                         'depreciationFee', CAST(:depreciation AS NUMERIC),
                         'proofUrl', CAST(:proof_url AS TEXT),
                         'processedBy', CAST(:processed_by AS TEXT),
                         'processedNote', CAST(:processed_note AS TEXT)
                     )),
                     CASE WHEN CAST(:status_value AS VARCHAR) = 'COMPLETED' THEN NOW() ELSE NULL END)
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
                "status_value": refund_status,
                "transaction_ref": transaction_ref,
                "proof_url": proof_url,
                "processed_by": str(processed_by) if processed_by else None,
                "processed_note": processed_note,
                "key": f"return:{request['id']}:item:{item['id']}",
            },
        )

    location_id = await session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'QC-01'"))
    if not location_id:
        location_id = await session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'MAIN'"))
    if not location_id:
        location_id = await session.scalar(text("SELECT id FROM inventory_locations LIMIT 1"))

    customer_fault = request.get("customer_fault", False)
    reference_code = request.get("request_code") or f"RETURN-{request['id']}"

    import json

    if location_id:
        inbound_doc_id = uuid4()
        inbound_doc_no = f"AS-IN-{reference_code}"
        await session.execute(
            text(
                """
                INSERT INTO inventory_documents (
                    id, document_no, document_type, status, target_location_id,
                    return_request_id, reference_code, reason, note,
                    costing_method, created_by, approved_by, posted_by,
                    approved_at, posted_at, metadata
                )
                VALUES (
                    :id, :document_no, 'INBOUND', 'COMPLETED', :location_id,
                    :request_id, :reference_code, 'AFTER_SALES_RETURN',
                    :note, 'FIFO', :actor_id, :actor_id, :actor_id,
                    NOW(), NOW(), CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": inbound_doc_id,
                "document_no": inbound_doc_no,
                "location_id": location_id,
                "request_id": request["id"],
                "reference_code": reference_code,
                "note": f"Nhập kho hàng trả lại từ hồ sơ hậu mãi {reference_code}.",
                "actor_id": processed_by or request["user_id"],
                "metadata": json.dumps({
                    "afterSalesType": "RETURN",
                    "afterSalesRequestId": str(request["id"]),
                    "requestCode": reference_code,
                    "stockMutationSkipped": True
                }, ensure_ascii=False),
            }
        )

        for item in items:
            product_id = item.get("product_id")
            variant_id = item.get("product_variant_id")
            qty = int(item.get("quantity") or 1)
            imei = item.get("imei")
            serial_number = item.get("serial_number")

            level_res = await session.execute(
                text(
                    """
                    SELECT on_hand_quantity FROM inventory_levels
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND location_id = :location_id
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id, "location_id": location_id},
            )
            level_row = level_res.first()
            old_qty = level_row[0] if level_row else 0
            new_qty = old_qty + qty

            await session.execute(
                text(
                    """
                    INSERT INTO inventory_levels (
                        id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, updated_at
                    )
                    VALUES (:id, :product_id, :variant_id, :location_id, :qty, 0, NOW())
                    ON CONFLICT (product_id, COALESCE(variant_id, '00000000-0000-0000-0000-000000000000'::uuid), location_id)
                    DO UPDATE SET
                        on_hand_quantity = inventory_levels.on_hand_quantity + EXCLUDED.on_hand_quantity,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": uuid4(),
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "location_id": location_id,
                    "qty": qty,
                },
            )

            await session.execute(
                text(
                    """
                    INSERT INTO inventory_adjustment_logs (
                        id, product_id, variant_id, old_quantity, new_quantity, delta,
                        reason, reference_code, note, created_at
                    )
                    VALUES (
                        :id, :product_id, :variant_id, :old_qty, :new_qty, :qty,
                        'RETURN', :reference_code, :note, NOW()
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "old_qty": old_qty,
                    "new_qty": new_qty,
                    "qty": qty,
                    "reference_code": reference_code,
                    "note": f"Nhập kho cách ly (trả hàng) từ yêu cầu đổi trả hoàn tiền {reference_code}.",
                },
            )

            imeis = [imei] if imei else []
            serial_numbers = [serial_number] if serial_number else []

            if imei:
                await session.execute(
                    text(
                        """
                        UPDATE product_imeis
                        SET status = 'DEFECTIVE_RETURNED',
                            sold_at = NULL,
                            sold_order_id = NULL,
                            location_id = :location_id,
                            updated_at = NOW()
                        WHERE imei = :imei AND status = 'SOLD'
                        """
                    ),
                    {"imei": imei, "location_id": location_id},
                )
                imei_id = await session.scalar(
                    text("SELECT id FROM product_imeis WHERE imei = :imei"),
                    {"imei": imei}
                )
                if imei_id:
                    await session.execute(
                        text(
                            """
                            INSERT INTO imei_disposition_events (
                                id, imei_id, after_sales_type, after_sales_id,
                                old_status, new_status, reason, actor_id
                            )
                            VALUES (
                                :id, :imei_id, 'RETURN', :request_id,
                                'SOLD', 'DEFECTIVE_RETURNED',
                                'Thu hồi trả hàng hoàn tiền.', :actor_id
                            )
                            """
                        ),
                        {
                            "id": uuid4(),
                            "imei_id": imei_id,
                            "request_id": request["id"],
                            "actor_id": processed_by,
                        }
                    )

            if serial_number:
                await session.execute(
                    text(
                        """
                        UPDATE product_serial_numbers
                        SET status = 'DEFECTIVE_RETURNED',
                            sold_at = NULL,
                            sold_order_id = NULL,
                            location_id = :location_id,
                            updated_at = NOW()
                        WHERE serial_number = :serial AND status = 'SOLD'
                        """
                    ),
                    {"serial": serial_number, "location_id": location_id},
                )
                serial_id = await session.scalar(
                    text("SELECT id FROM product_serial_numbers WHERE serial_number = :serial AND product_id = :product_id"),
                    {"serial": serial_number, "product_id": product_id}
                )
                if serial_id:
                    await session.execute(
                        text(
                            """
                            INSERT INTO imei_disposition_events (
                                id, serial_id, after_sales_type, after_sales_id,
                                old_status, new_status, reason, actor_id
                            )
                            VALUES (
                                :id, :serial_id, 'RETURN', :request_id,
                                'SOLD', 'DEFECTIVE_RETURNED',
                                'Thu hồi trả hàng hoàn tiền.', :actor_id
                            )
                            """
                        ),
                        {
                            "id": uuid4(),
                            "serial_id": serial_id,
                            "request_id": request["id"],
                            "actor_id": processed_by,
                        }
                    )

            line_metadata = json.dumps({
                "tracksImei": bool(imeis),
                "imeis": imeis,
                "tracksSerialNumber": bool(serial_numbers),
                "serialNumbers": serial_numbers,
                "stockMutationSkipped": True
            }, ensure_ascii=False)

            identifier_note = ", ".join(
                [f"IMEI: {im}" for im in imeis] + [f"Serial: {sn}" for sn in serial_numbers]
            )

            await session.execute(
                text(
                    """
                    INSERT INTO inventory_document_lines (
                        id, document_id, product_id, variant_id, location_id,
                        requested_quantity, expected_quantity, approved_quantity,
                        unit_cost, note, metadata
                    )
                    VALUES (
                        :id, :document_id, :product_id, :variant_id, :location_id,
                        :quantity, :quantity, :quantity,
                        :unit_cost, :note, CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "document_id": inbound_doc_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "location_id": location_id,
                    "quantity": qty,
                    "unit_cost": float(item.get("unit_price") or 0),
                    "note": identifier_note or "Không có mã định danh.",
                    "metadata": line_metadata,
                }
            )

            if item.get("used_device_id"):
                await session.execute(
                    text("UPDATE used_devices SET status = 'RETURNED_QC', updated_at = NOW() WHERE id = :uid"),
                    {"uid": item["used_device_id"]},
                )

    order_item_count = int(
        await session.scalar(
            text("SELECT COUNT(*) FROM order_items WHERE order_id=:order_id"),
            {"order_id": request["order_id"]},
        )
        or 0
    )
    returned_item_count = len({item["order_item_id"] for item in items})
    order_discount = money(
        await session.scalar(
            text("SELECT discount_amount FROM orders WHERE id=:order_id"),
            {"order_id": request["order_id"]},
        )
        or 0
    )
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
    ref_clean = reference_code.replace('-', '').replace('_', '').upper()
    code = f"BD{ref_clean}"
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
