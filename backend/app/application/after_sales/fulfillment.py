from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_after_sales_order(
    session: AsyncSession,
    *,
    kind: str,
    request: dict,
    items: list[dict],
) -> UUID:
    """Tạo một đơn giao máy hậu mãi duy nhất cho mỗi hồ sơ đổi máy."""
    request_column = "return_request_id" if kind == "RETURN" else "warranty_request_id"
    existing = (
        await session.execute(
            text(f"SELECT id, status FROM orders WHERE {request_column} = :request_id FOR UPDATE"),
            {"request_id": request["id"]},
        )
    ).mappings().first()
    if existing:
        payment_confirmed = (
            kind != "RETURN"
            or float(request.get("balance_amount") or 0) <= 0
            or str(request.get("payment_status") or "").upper() == "PAID"
        )
        if existing["status"] == "CANCELLED":
            await session.execute(
                text(
                    """
                    UPDATE orders
                    SET status = 'PROCESSING', cancellation_reason = NULL,
                        cancelled_at = NULL, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": existing["id"]},
            )
        if payment_confirmed:
            await session.execute(
                text("UPDATE orders SET payment_status = 'PAID', updated_at = NOW() WHERE id = :id"),
                {"id": existing["id"]},
            )
        return existing["id"]

    source_order = (
        await session.execute(
            text(
                """
                SELECT id, user_id, recipient_name, recipient_phone, recipient_email,
                       shipping_address, shipping_provider
                FROM orders
                WHERE id = :order_id
                FOR UPDATE
                """
            ),
            {"order_id": request["order_id"]},
        )
    ).mappings().first()
    if not source_order:
        raise HTTPException(status_code=409, detail="Không tìm thấy đơn mua gốc để tạo đơn giao máy hậu mãi.")

    order_id = uuid4()
    order_purpose = "RETURN_EXCHANGE" if kind == "RETURN" else "WARRANTY_REPLACEMENT"
    prefix = "DT" if kind == "RETURN" else "BH"
    request_code = request.get("request_code") or str(request["id"])
    order_code = f"{prefix}-{request_code}"
    fulfillment_method = "DELIVERY" if str(source_order.get("shipping_address") or "").strip() else "STORE_PICKUP"
    payment_requirement = (
        "BALANCE_PAYMENT"
        if kind == "RETURN" and float(request.get("balance_amount") or 0) > 0
        else "NO_PAYMENT_REQUIRED"
    )
    payment_status = (
        "PAID"
        if payment_requirement == "NO_PAYMENT_REQUIRED" or str(request.get("payment_status") or "").upper() == "PAID"
        else "PENDING"
    )
    payable_amount = max(float(request.get("balance_amount") or 0), 0) if payment_requirement == "BALANCE_PAYMENT" else 0
    request_id_column = "return_request_id" if kind == "RETURN" else "warranty_request_id"

    await session.execute(
        text(
            f"""
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, voucher_discount_amount,
                loyalty_discount_amount, shipping_fee, total_amount,
                loyalty_points_earned, loyalty_points_used,
                recipient_name, recipient_phone, recipient_email, shipping_address,
                shipping_provider, internal_note, order_type, order_purpose, source_order_id,
                {request_id_column}, payment_requirement, fulfillment_method
            ) VALUES (
                :id, :user_id, :order_code, 'PROCESSING', :payment_method, :payment_status,
                :payable_amount, 0, 0, 0, 0, :payable_amount, 0, 0,
                :recipient_name, :recipient_phone, :recipient_email, :shipping_address,
                :shipping_provider, :internal_note, 'ONLINE', :order_purpose, :source_order_id,
                :request_id, :payment_requirement, :fulfillment_method
            )
            """
        ),
        {
            "id": order_id,
            "user_id": source_order["user_id"],
            "order_code": order_code,
            "payment_method": "NO_PAYMENT" if payment_requirement == "NO_PAYMENT_REQUIRED" else "COD",
            "payment_status": payment_status,
            "payable_amount": payable_amount,
            "recipient_name": source_order["recipient_name"],
            "recipient_phone": source_order["recipient_phone"],
            "recipient_email": source_order["recipient_email"],
            "shipping_address": source_order["shipping_address"] or "Nhận tại cửa hàng",
            "shipping_provider": source_order["shipping_provider"],
            "internal_note": f"Đơn giao máy hậu mãi tự động từ hồ sơ {request_code}.",
            "order_purpose": order_purpose,
            "source_order_id": source_order["id"],
            "request_id": request["id"],
            "payment_requirement": payment_requirement,
            "fulfillment_method": fulfillment_method,
        },
    )

    if kind == "RETURN" and request.get("exchange_product_id"):
        target = (
            await session.execute(
                text(
                    """
                    SELECT p.id AS product_id, pv.id AS variant_id,
                           CASE WHEN pv.id IS NULL THEN p.name
                                ELSE p.name || COALESCE(' - ' || NULLIF(pv.sku, ''), '') END AS product_name,
                           COALESCE(p.warranty_months, 0) AS warranty_months,
                           COALESCE(:quantity, 1) AS quantity
                    FROM products p
                    LEFT JOIN product_variants pv ON pv.id = CAST(:variant_id AS UUID) AND pv.product_id = p.id
                    WHERE p.id = :product_id
                    """
                ),
                {
                    "product_id": request["exchange_product_id"],
                    "variant_id": request.get("exchange_variant_id"),
                    "quantity": int(request.get("exchange_quantity") or 1),
                },
            )
        ).mappings().first()
        order_lines = [
            {
                **dict(target),
                "after_sales_type": kind,
                "after_sales_request_item_id": items[0]["id"] if items else None,
            }
        ] if target else []
    else:
        order_lines = []
        for item in items:
            original = (
                await session.execute(
                    text(
                        """
                        SELECT oi.product_id, oi.variant_id, oi.product_name,
                               oi.warranty_months_snapshot AS warranty_months
                        FROM order_items oi WHERE oi.id = :order_item_id
                        """
                    ),
                    {"order_item_id": item["order_item_id"]},
                )
            ).mappings().first()
            if original:
                order_lines.append({
                    **dict(original),
                    "quantity": int(item.get("quantity") or 1),
                    "after_sales_type": kind,
                    "after_sales_request_item_id": item["id"],
                })

    if not order_lines:
        raise HTTPException(status_code=409, detail="Không xác định được sản phẩm cần giao trong đơn hậu mãi.")
    for line in order_lines:
        await session.execute(
            text(
                """
                INSERT INTO order_items (
                    id, order_id, product_id, variant_id, warranty_months_snapshot,
                    attached_services, product_name, quantity, unit_price, total_price,
                    after_sales_type, after_sales_request_item_id
                ) VALUES (
                    :id, :order_id, :product_id, :variant_id, :warranty_months,
                    '[]'::jsonb, :product_name, :quantity, 0, 0,
                    :after_sales_type, :after_sales_request_item_id
                )
                """
            ),
            {"id": uuid4(), "order_id": order_id, **line},
        )

    await session.execute(
        text(
            """
            INSERT INTO order_history_logs (id, order_id, old_status, new_status, changed_by, note, metadata)
            VALUES (:id, :order_id, NULL, 'PROCESSING', 'after-sales', :note,
                    jsonb_build_object(
                        'afterSalesType', CAST(:kind AS TEXT),
                        'afterSalesRequestId', CAST(CAST(:request_id AS UUID) AS TEXT)
                    ))
            """
        ),
        {
            "id": uuid4(), "order_id": order_id, "kind": kind,
            "request_id": request["id"], "note": f"Tạo tự động từ hồ sơ hậu mãi {request_code}.",
        },
    )
    return order_id


async def ensure_after_sales_outbound(
    session: AsyncSession,
    *,
    kind: str,
    request: dict,
    items: list[dict],
) -> UUID:
    """Phát hành phiếu xuất Nháp từ đơn hậu mãi; kho chịu trách nhiệm chọn mã máy."""
    from app.application.services.inventory.outbounds import create_outbound_document_from_order

    order_id = await ensure_after_sales_order(session, kind=kind, request=request, items=items)
    document_id = await create_outbound_document_from_order(session, order_id)
    if not document_id:
        raise HTTPException(status_code=409, detail="Đơn hậu mãi chưa có sản phẩm đủ điều kiện tạo phiếu xuất kho.")
    request_column = "return_request_id" if kind == "RETURN" else "warranty_request_id"
    request_code = request.get("request_code") or str(request["id"])
    await session.execute(
        text(
            f"""
            UPDATE inventory_documents
            SET {request_column} = :request_id,
                reason = 'AFTER_SALES_REPLACEMENT',
                note = :note,
                metadata = COALESCE(metadata, '{{}}'::jsonb) || jsonb_build_object(
                    'afterSalesType', CAST(:kind AS TEXT),
                    'afterSalesRequestId', CAST(CAST(:request_id AS UUID) AS TEXT)
                )
            WHERE id = :document_id
            """
        ),
        {
            "document_id": document_id,
            "request_id": request["id"],
            "kind": kind,
            "note": f"Phiếu xuất máy hậu mãi cho hồ sơ {request_code}.",
        },
    )
    return document_id


async def finalize_after_sales_outbound(
    session: AsyncSession,
    *,
    document_id: UUID,
    actor_id: UUID | None,
) -> None:
    """Đồng bộ mã máy kho đã xuất về hồ sơ hậu mãi trong cùng giao dịch."""
    document = (
        await session.execute(
            text(
                """
                SELECT d.warranty_request_id, d.return_request_id, d.document_no,
                       o.fulfillment_method
                FROM inventory_documents d
                JOIN orders o ON o.id = d.order_id
                WHERE d.id = :document_id
                """
            ),
            {"document_id": document_id},
        )
    ).mappings().first()
    if not document or not (document["warranty_request_id"] or document["return_request_id"]):
        return

    kind = "WARRANTY" if document["warranty_request_id"] else "RETURN"
    request_id = document["warranty_request_id"] or document["return_request_id"]
    request_table = "warranty_requests" if kind == "WARRANTY" else "return_requests"
    item_table = "warranty_request_items" if kind == "WARRANTY" else "return_request_items"
    request = (
        await session.execute(
            text(f"SELECT * FROM {request_table} WHERE id = :request_id FOR UPDATE"),
            {"request_id": request_id},
        )
    ).mappings().first()
    if not request:
        raise HTTPException(status_code=409, detail="Không tìm thấy hồ sơ hậu mãi liên kết phiếu xuất.")

    lines = (
        await session.execute(
            text("SELECT metadata FROM inventory_document_lines WHERE document_id = :document_id ORDER BY created_at, id"),
            {"document_id": document_id},
        )
    ).mappings().all()
    updated_item_ids: list[UUID] = []
    for line in lines:
        metadata = line.get("metadata") or {}
        request_item_id_value = metadata.get("afterSalesRequestItemId")
        if not request_item_id_value:
            continue
        request_item_id = UUID(str(request_item_id_value))
        allocations = metadata.get("allocations") or []
        imeis = [str(value).strip() for allocation in allocations for value in (allocation.get("imeis") or []) if str(value).strip()]
        serials = [str(value).strip() for allocation in allocations for value in (allocation.get("serialNumbers") or []) if str(value).strip()]
        await session.execute(
            text(
                f"""
                UPDATE {item_table}
                SET replacement_imei = :replacement_imei,
                    replacement_imeis = CAST(:replacement_imeis AS jsonb),
                    replacement_serial_numbers = CAST(:replacement_serial_numbers AS jsonb)
                WHERE id = :item_id AND request_id = :request_id
                """
            ),
            {
                "item_id": request_item_id,
                "request_id": request_id,
                "replacement_imei": imeis[0] if imeis else None,
                "replacement_imeis": __import__("json").dumps(imeis),
                "replacement_serial_numbers": __import__("json").dumps(serials),
            },
        )
        updated_item_ids.append(request_item_id)

    expected_count = int(
        await session.scalar(text(f"SELECT COUNT(*) FROM {item_table} WHERE request_id = :id"), {"id": request_id}) or 0
    )
    if kind == "WARRANTY" and expected_count and len(set(updated_item_ids)) != expected_count:
        raise HTTPException(status_code=409, detail="Phiếu xuất chưa liên kết đủ các dòng thiết bị hậu mãi.")

    if kind == "WARRANTY":
        from app.application.after_sales.replacements import _mark_original_identifiers_defective

        original_items = (
            await session.execute(
                text("SELECT * FROM warranty_request_items WHERE request_id = :request_id ORDER BY created_at, id"),
                {"request_id": request_id},
            )
        ).mappings().all()
        for original_item in original_items:
            await _mark_original_identifiers_defective(
                session,
                kind=kind,
                request_id=request_id,
                item=dict(original_item),
                actor_id=actor_id,
            )
        next_status = "READY_TO_RETURN" if document["fulfillment_method"] == "STORE_PICKUP" else "REPLACEMENT_PROCESSING"
        if request["status"] in {"REPLACEMENT_APPROVED", "REPLACEMENT_PROCESSING"}:
            await session.execute(
                text("UPDATE warranty_requests SET status = :status, updated_at = NOW() WHERE id = :id"),
                {"id": request_id, "status": next_status},
            )

    await session.execute(
        text(
            """
            UPDATE after_sales_allocations
            SET status = 'CONSUMED', consumed_at = NOW()
            WHERE reference_type = :kind AND reference_id = :request_id AND status = 'LOCKED'
            """
        ),
        {"kind": kind, "request_id": request_id},
    )


async def cancel_after_sales_order_for_reinspection(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    reason: str,
) -> None:
    request_column = "return_request_id" if kind == "RETURN" else "warranty_request_id"
    await session.execute(
        text(
            f"""
            UPDATE orders
            SET status = 'CANCELLED', cancellation_reason = :reason,
                cancelled_at = NOW(), updated_at = NOW()
            WHERE {request_column} = :request_id
              AND status NOT IN ('SHIPPED', 'COMPLETED', 'CANCELLED')
            """
        ),
        {"request_id": request_id, "reason": reason},
    )
