from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ACTIVE_STATUSES = (
    "SUBMITTED", "RECEIVED", "QC_IN_PROGRESS", "QC_APPROVED", "WARRANTY_ACCEPTED",
    "REPAIRING", "REPLACEMENT_APPROVED", "WAITING_FOR_STOCK",
    "EXCHANGE_PROCESSING", "REFUND_PROCESSING", "REPLACEMENT_PROCESSING",
    "READY_TO_RETURN",
)


def _table(kind: str) -> tuple[str, str]:
    return ("return_requests", "return_request_items") if kind == "RETURN" else (
        "warranty_requests", "warranty_request_items"
    )


async def lock_order(session: AsyncSession, order_id: UUID, user_id: UUID | None = None) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, user_id, subtotal_amount, discount_amount, shipping_fee, total_amount, voucher_code, payment_method
            FROM orders
            WHERE id = :order_id AND (:user_id IS NULL OR user_id = :user_id)
            FOR UPDATE
            """
        ),
        {"order_id": order_id, "user_id": user_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def get_order_item(session: AsyncSession, order_id: UUID, item_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, product_id, variant_id, product_name, quantity, unit_price, total_price
            FROM order_items WHERE id = :item_id AND order_id = :order_id
            """
        ),
        {"item_id": item_id, "order_id": order_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def identifier_belongs_to_item(
    session: AsyncSession,
    *,
    order_id: UUID,
    product_id: UUID | None,
    variant_id: UUID | None,
    imei: str | None,
    serial_number: str | None,
) -> bool:
    if imei:
        return bool(await session.scalar(
            text(
                """
                SELECT EXISTS(
                    SELECT 1 FROM product_imeis
                    WHERE imei = :value AND sold_order_id = :order_id
                      AND product_id = CAST(:product_id AS UUID)
                      AND (CAST(:variant_id AS UUID) IS NULL OR variant_id = CAST(:variant_id AS UUID))
                      AND status IN ('SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY')
                )
                """
            ),
            {"value": imei, "order_id": order_id, "product_id": product_id, "variant_id": variant_id},
        ))
    if serial_number:
        return bool(await session.scalar(
            text(
                """
                SELECT EXISTS(
                    SELECT 1 FROM product_serial_numbers
                    WHERE serial_number = :value AND product_id = CAST(:product_id AS UUID)
                      AND (CAST(:variant_id AS UUID) IS NULL OR variant_id = CAST(:variant_id AS UUID))
                      AND status IN ('SOLD', 'RETURNED', 'WARRANTY', 'IN_WARRANTY')
                      AND (
                        service_payload ->> 'soldOrderId' = :order_id_text
                        OR service_payload ->> 'orderId' = :order_id_text
                      )
                )
                """
            ),
            {
                "value": serial_number, "order_id_text": str(order_id),
                "product_id": product_id, "variant_id": variant_id,
            },
        ))
    return True


async def has_active_conflict(
    session: AsyncSession,
    *,
    order_item_id: UUID,
    imei: str | None,
    serial_number: str | None,
) -> bool:
    return bool(await session.scalar(
        text(
            """
            SELECT EXISTS(
                SELECT 1
                FROM return_request_items i
                JOIN return_requests r ON r.id = i.request_id
                WHERE r.status = ANY(CAST(:statuses AS VARCHAR[]))
                  AND (i.order_item_id = :order_item_id
                       OR (CAST(:imei AS VARCHAR) IS NOT NULL AND i.imei = CAST(:imei AS VARCHAR))
                       OR (CAST(:serial AS VARCHAR) IS NOT NULL AND i.serial_number = CAST(:serial AS VARCHAR)))
                UNION ALL
                SELECT 1
                FROM warranty_request_items i
                JOIN warranty_requests r ON r.id = i.request_id
                WHERE r.status = ANY(CAST(:statuses AS VARCHAR[]))
                  AND (i.order_item_id = :order_item_id
                       OR (CAST(:imei AS VARCHAR) IS NOT NULL AND i.imei = CAST(:imei AS VARCHAR))
                       OR (CAST(:serial AS VARCHAR) IS NOT NULL AND i.serial_number = CAST(:serial AS VARCHAR)))
            )
            """
        ),
        {
            "statuses": list(ACTIVE_STATUSES), "order_item_id": order_item_id,
            "imei": imei, "serial": serial_number,
        },
    ))


async def insert_request(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    request_code: str,
    user_id: UUID,
    order_id: UUID,
    reason: str,
) -> None:
    request_table, _ = _table(kind)
    await session.execute(
        text(
            f"""
            INSERT INTO {request_table}
                (id, request_code, user_id, order_id, status, reason, sla_due_at)
            VALUES
                (:id, :code, :user_id, :order_id, 'SUBMITTED', :reason, NOW() + INTERVAL '3 days')
            """
        ),
        {"id": request_id, "code": request_code, "user_id": user_id, "order_id": order_id, "reason": reason},
    )


async def insert_item(session: AsyncSession, *, kind: str, values: dict) -> None:
    _, item_table = _table(kind)
    financial_columns = ""
    financial_values = ""
    if kind == "RETURN":
        financial_columns = ", unit_price_snapshot, discount_allocation_snapshot, refundable_amount_snapshot"
        financial_values = ", :unit_price, :discount_allocation, :refundable_amount"
    await session.execute(
        text(
            f"""
            INSERT INTO {item_table}
                (id, request_id, order_item_id, product_id, product_variant_id,
                 quantity, imei, serial_number{financial_columns})
            VALUES
                (:id, :request_id, :order_item_id, :product_id, :variant_id,
                 :quantity, :imei, :serial_number{financial_values})
            """
        ),
        values,
    )


async def insert_event(
    session: AsyncSession, *, kind: str, reference_id: UUID, old_status: str | None,
    new_status: str, actor_id: UUID | None, note: str | None, metadata: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO after_sales_events
                (id, reference_type, reference_id, old_status, new_status, actor_id, note, metadata)
            VALUES (:id, :kind, :reference_id, :old_status, :new_status, :actor_id, :note, CAST(:metadata AS JSONB))
            """
        ),
        {
            "id": uuid4(), "kind": kind, "reference_id": reference_id, "old_status": old_status,
            "new_status": new_status, "actor_id": actor_id, "note": note,
            "metadata": __import__("json").dumps(metadata or {}, ensure_ascii=False),
        },
    )


async def notify(
    session: AsyncSession, *, user_id: UUID, type_value: str, title: str, message: str,
    entity_type: str, entity_id: UUID, immediate: bool = False, key: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO notifications
                (id, user_id, type, title, message, entity_type, entity_id,
                 action_url, idempotency_key, available_at)
            VALUES
                (:id, :user_id, :type, :title, :message, :entity_type, :entity_id,
                 :action_url, :key, NOW() + CASE WHEN :immediate THEN INTERVAL '0 minute' ELSE INTERVAL '2 minutes' END)
            ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
            """
        ),
        {
            "id": uuid4(), "user_id": user_id, "type": type_value, "title": title,
            "message": message, "entity_type": entity_type, "entity_id": entity_id,
            "action_url": "/dashboard", "key": key, "immediate": immediate,
        },
    )


async def list_requests(
    session: AsyncSession, *, kind: str, user_id: UUID | None, status_value: str | None,
    page: int, limit: int, descending: bool = True,
) -> dict:
    request_table, item_table = _table(kind)
    filters = [
        "(CAST(:user_id AS UUID) IS NULL OR r.user_id = CAST(:user_id AS UUID))",
        "(CAST(:status AS VARCHAR) IS NULL OR r.status = CAST(:status AS VARCHAR))",
    ]
    params = {"user_id": user_id, "status": status_value, "offset": (page - 1) * limit, "limit": limit}
    order = "DESC" if descending else "ASC"
    total = await session.scalar(text(f"SELECT COUNT(*) FROM {request_table} r WHERE {' AND '.join(filters)}"), params)
    result = await session.execute(
        text(
            f"""
            SELECT r.id::text AS id, r.request_code AS "requestCode", r.user_id::text AS "userId",
                   r.order_id::text AS "orderId", o.order_code AS "orderCode", r.status, r.reason,
                   r.resolution_type AS "resolutionType", r.admin_note AS "adminNote",
                   r.qc_note AS "qcNote", r.sla_due_at AS "slaDueAt",
                   r.sla_breached_at AS "slaBreachedAt", r.created_at AS "createdAt",
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                           'id', i.id::text, 'orderItemId', i.order_item_id::text,
                           'productId', i.product_id::text, 'variantId', i.product_variant_id::text,
                           'productName', oi.product_name, 'quantity', i.quantity,
                           'imei', i.imei, 'serialNumber', i.serial_number,
                           'replacementImei', i.replacement_imei
                       )) FROM {item_table} i
                       JOIN order_items oi ON oi.id = i.order_item_id
                       WHERE i.request_id = r.id
                   ), '[]'::jsonb) AS items
            FROM {request_table} r
            JOIN orders o ON o.id = r.order_id
            WHERE {' AND '.join(filters)}
            ORDER BY r.created_at {order}
            OFFSET :offset LIMIT :limit
            """
        ),
        params,
    )
    return {
        "items": [dict(row._mapping) for row in result],
        "page": page, "limit": limit, "total": int(total or 0),
        "totalPages": max(1, ((int(total or 0) + limit - 1) // limit)),
    }


async def get_request_for_update(session: AsyncSession, *, kind: str, request_id: UUID) -> dict | None:
    request_table, _ = _table(kind)
    result = await session.execute(
        text(f"SELECT * FROM {request_table} WHERE id = :id FOR UPDATE"),
        {"id": request_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def update_request_status(
    session: AsyncSession, *, kind: str, request_id: UUID, status_value: str,
    resolution_type: str | None, note: str | None, customer_fault: bool,
) -> None:
    request_table, _ = _table(kind)
    extra = ""
    if status_value == "RECEIVED":
        extra += ", received_at = NOW()"
    if status_value in {"QC_APPROVED", "REPLACEMENT_APPROVED"}:
        field = "qc_approved_at" if kind == "RETURN" else "replacement_approved_at"
        extra += f", {field} = NOW()"
    if status_value in {"COMPLETED", "REJECTED", "CANCELLED", "CLOSED_EXPIRED"}:
        extra += ", closed_at = NOW()"
    if status_value == "CANCELLED":
        extra += ", cancelled_at = NOW()"
    fault_set = ", customer_fault = :customer_fault" if kind == "RETURN" else ""
    await session.execute(
        text(
            f"""
            UPDATE {request_table}
            SET status = :status, resolution_type = COALESCE(:resolution_type, resolution_type),
                admin_note = COALESCE(:note, admin_note), updated_at = NOW()
                {fault_set} {extra}
            WHERE id = :id
            """
        ),
        {
            "id": request_id, "status": status_value, "resolution_type": resolution_type,
            "note": note, "customer_fault": customer_fault,
        },
    )


async def get_request_items(session: AsyncSession, *, kind: str, request_id: UUID) -> list[dict]:
    _, item_table = _table(kind)
    result = await session.execute(text(f"SELECT * FROM {item_table} WHERE request_id = :id"), {"id": request_id})
    return [dict(row._mapping) for row in result]


async def available_stock(
    session: AsyncSession, *, product_id: UUID, variant_id: UUID | None,
) -> int:
    value = await session.scalar(
        text(
            """
            WITH physical AS (
                SELECT COALESCE(SUM(on_hand_quantity - reserved_quantity), 0) qty
                FROM inventory_levels
                WHERE (CAST(:variant_id AS UUID) IS NOT NULL AND variant_id = CAST(:variant_id AS UUID))
                   OR (CAST(:variant_id AS UUID) IS NULL AND product_id = CAST(:product_id AS UUID))
            ), after_sales AS (
                SELECT COALESCE(SUM(quantity), 0) qty
                FROM after_sales_allocations
                WHERE status = 'LOCKED'
                  AND product_id = CAST(:product_id AS UUID)
                  AND product_variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
            )
            SELECT GREATEST(physical.qty - after_sales.qty, 0) FROM physical, after_sales
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    return int(value or 0)


async def create_allocations(session: AsyncSession, *, kind: str, request_id: UUID, items: list[dict]) -> bool:
    for item in items:
        if await available_stock(
            session, product_id=item["product_id"], variant_id=item.get("product_variant_id")
        ) < int(item["quantity"]):
            return False
    for item in items:
        await session.execute(
            text(
                """
                INSERT INTO after_sales_allocations
                    (id, reference_type, reference_id, product_id, product_variant_id,
                     quantity, status, expires_at)
                VALUES
                    (:id, :kind, :reference_id, :product_id, :variant_id,
                     :quantity, 'LOCKED', NOW() + INTERVAL '48 hours')
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "id": uuid4(), "kind": kind, "reference_id": request_id,
                "product_id": item["product_id"], "variant_id": item.get("product_variant_id"),
                "quantity": item["quantity"],
            },
        )
    return True


async def release_allocations(session: AsyncSession, *, kind: str, request_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE after_sales_allocations
            SET status = 'RELEASED', released_at = NOW()
            WHERE reference_type = :kind AND reference_id = :id AND status = 'LOCKED'
            """
        ),
        {"kind": kind, "id": request_id},
    )


async def list_transactions(session: AsyncSession, user_id: UUID, page: int, limit: int) -> dict:
    total = await session.scalar(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT pt.id FROM payment_transactions pt JOIN orders o ON o.id = pt.order_id WHERE o.user_id = :uid
                UNION ALL SELECT rt.id FROM refund_transactions rt WHERE rt.user_id = :uid
            ) x
            """
        ),
        {"uid": user_id},
    )
    result = await session.execute(
        text(
            """
            SELECT * FROM (
                SELECT pt.id::text id, 'PAYMENT' AS type, o.order_code AS "orderCode",
                       pt.provider, pt.amount, pt.status, pt.transaction_ref AS "transactionRef",
                       pt.attempt_number AS "attemptNumber", pt.created_at AS "createdAt",
                       pt.checkout_url AS "checkoutUrl"
                FROM payment_transactions pt JOIN orders o ON o.id = pt.order_id
                WHERE o.user_id = :uid
                UNION ALL
                SELECT rt.id::text id, 'REFUND' AS type, o.order_code AS "orderCode",
                       rt.provider, rt.refund_amount AS amount, rt.status,
                       rt.transaction_ref AS "transactionRef", 1 AS "attemptNumber",
                       rt.created_at AS "createdAt", NULL AS "checkoutUrl"
                FROM refund_transactions rt JOIN orders o ON o.id = rt.order_id
                WHERE rt.user_id = :uid
            ) x ORDER BY "createdAt" DESC OFFSET :offset LIMIT :limit
            """
        ),
        {"uid": user_id, "offset": (page - 1) * limit, "limit": limit},
    )
    return {
        "items": [dict(row._mapping) for row in result], "page": page, "limit": limit,
        "total": int(total or 0), "totalPages": max(1, ((int(total or 0) + limit - 1) // limit)),
    }


async def list_shipment_events(session: AsyncSession, order_id: UUID, user_id: UUID) -> list[dict] | None:
    owns = await session.scalar(text("SELECT EXISTS(SELECT 1 FROM orders WHERE id=:oid AND user_id=:uid)"), {"oid": order_id, "uid": user_id})
    if not owns:
        return None
    result = await session.execute(
        text(
            """
            SELECT id::text id, event_code AS "eventCode", title, description,
                   shipping_provider AS "shippingProvider", tracking_code AS "trackingCode",
                   source, occurred_at AS "occurredAt"
            FROM shipment_events WHERE order_id=:oid ORDER BY occurred_at
            """
        ),
        {"oid": order_id},
    )
    return [dict(row._mapping) for row in result]


async def cleanup_due_attachments(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, storage_key FROM after_sales_attachments
            WHERE status='PENDING_DELETE' AND delete_after <= NOW()
            FOR UPDATE SKIP LOCKED
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def mark_attachment_deleted(session: AsyncSession, attachment_id: UUID) -> None:
    await session.execute(
        text("UPDATE after_sales_attachments SET status='DELETED', deleted_at=NOW() WHERE id=:id"),
        {"id": attachment_id},
    )
