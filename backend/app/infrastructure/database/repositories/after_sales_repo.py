from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.warranty_snapshot import (
    order_item_effective_warranty_months_sql,
    order_item_extra_warranty_months_lateral_sql,
)
from app.infrastructure.storage import media_storage


ACTIVE_STATUSES = (
    "SUBMITTED", "RECEIVED", "QC_IN_PROGRESS", "QC_APPROVED", "WARRANTY_ACCEPTED",
    "REPAIRING", "REPAIR_COMPLETED", "REPLACEMENT_APPROVED", "WAITING_FOR_STOCK", "WAITING_FOR_EXCHANGE_PAYMENT",
    "EXCHANGE_PROCESSING", "REFUND_PROCESSING", "REPLACEMENT_PROCESSING",
    "READY_TO_RETURN", "RETURNING_TO_CUSTOMER",
)


def _table(kind: str) -> tuple[str, str]:
    return ("return_requests", "return_request_items") if kind == "RETURN" else (
        "warranty_requests", "warranty_request_items"
    )


async def lock_order(session: AsyncSession, order_id: UUID, user_id: UUID | None = None) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, user_id, status, completed_at, subtotal_amount, discount_amount, shipping_fee, total_amount, voucher_code, payment_method
            FROM orders
            WHERE id = :order_id
              AND (CAST(:user_id AS UUID) IS NULL OR user_id = CAST(:user_id AS UUID))
            FOR UPDATE
            """
        ),
        {"order_id": order_id, "user_id": user_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def get_order_item(session: AsyncSession, order_id: UUID, item_id: UUID) -> dict | None:
    warranty_months_sql = order_item_effective_warranty_months_sql()
    extra_warranty_join_sql = order_item_extra_warranty_months_lateral_sql()
    result = await session.execute(
        text(
            f"""
            SELECT
                oi.id,
                COALESCE(oi.product_id, ud.product_id) AS product_id,
                COALESCE(oi.variant_id, ud.variant_id) AS variant_id,
                oi.used_device_id,
                oi.product_name,
                oi.quantity,
                oi.unit_price,
                oi.total_price,
                oi.attached_services,
                oi.warranty_months_snapshot AS "warrantyMonthsSnapshot",
                {warranty_months_sql} AS "warrantyMonths",
                oi.warranty_months_snapshot IS NULL AS "warrantySnapshotMissing",
                COALESCE(p.name, ud_p.name, 'sản phẩm') AS "currentProductName"
            FROM order_items oi
            LEFT JOIN products p ON p.id = oi.product_id
            LEFT JOIN used_devices ud ON ud.id = oi.used_device_id
            LEFT JOIN products ud_p ON ud_p.id = ud.product_id
            {extra_warranty_join_sql}
            WHERE oi.id = :item_id AND oi.order_id = :order_id
            """
        ),
        {"item_id": item_id, "order_id": order_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def get_exchange_target(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT
                p.id AS product_id,
                pv.id AS variant_id,
                p.name AS product_name,
                pv.sku AS variant_sku,
                COALESCE(pv.sale_price, pv.price, p.sale_price, p.price, 0) AS unit_price,
                COALESCE(pv.is_active, TRUE) AS variant_active,
                p.status AS product_status
            FROM products p
            LEFT JOIN product_variants pv
              ON pv.product_id = p.id
             AND pv.id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
            WHERE p.id = :product_id
              AND (
                CAST(:variant_id AS UUID) IS NULL
                OR pv.id = CAST(:variant_id AS UUID)
              )
              AND p.deleted_at IS NULL
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_purchased_items(session: AsyncSession, user_id: UUID) -> list[dict]:
    warranty_months_sql = order_item_effective_warranty_months_sql()
    extra_warranty_join_sql = order_item_extra_warranty_months_lateral_sql()
    result = await session.execute(
        text(
            f"""
            WITH purchased AS (
                SELECT
                    oi.id AS order_item_id,
                    o.id AS order_id,
                    o.order_code,
                    COALESCE(source_order.completed_at, o.completed_at) AS completed_at,
                    COALESCE(oi.product_id, ud.product_id) AS product_id,
                    COALESCE(oi.variant_id, ud.variant_id) AS variant_id,
                    oi.used_device_id,
                    oi.product_name,
                    oi.quantity,
                    oi.unit_price,
                    oi.total_price,
                    oi.attached_services,
                    oi.warranty_months_snapshot,
                    {warranty_months_sql} AS warranty_months,
                    oi.warranty_months_snapshot IS NULL AS warranty_snapshot_missing,
                    ud.imei AS used_imei,
                    ud.serial_number AS used_serial_number,
                    ud.status AS used_device_status,
                    c.slug AS category_slug
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN orders source_order ON source_order.id = o.source_order_id
                LEFT JOIN used_devices ud ON ud.id = oi.used_device_id
                LEFT JOIN products p ON p.id = oi.product_id
                LEFT JOIN products used_product ON used_product.id = ud.product_id
                LEFT JOIN categories c ON c.id = COALESCE(p.category_id, used_product.category_id)
                {extra_warranty_join_sql}
                WHERE o.user_id = :user_id
                  AND o.status = 'COMPLETED'
            )
            SELECT
                item.order_item_id::text AS "orderItemId",
                item.order_id::text AS "orderId",
                item.order_code AS "orderCode",
                item.completed_at AS "completedAt",
                item.product_id::text AS "productId",
                item.variant_id::text AS "variantId",
                item.used_device_id::text AS "usedDeviceId",
                item.product_id,
                item.variant_id,
                item.used_device_id,
                item.product_name,
                item.product_name AS "productName",
                item.quantity,
                item.unit_price,
                item.unit_price AS "unitPrice",
                item.total_price AS "totalPrice",
                COALESCE(item.attached_services, '[]'::jsonb) AS "attachedServices",
                item.warranty_months_snapshot AS "warrantyMonthsSnapshot",
                item.warranty_months AS "warrantyMonths",
                item.warranty_snapshot_missing AS "warrantySnapshotMissing",
                item.category_slug,
                COALESCE(identifiers.identifiers, '[]'::jsonb) AS identifiers
            FROM purchased item
            LEFT JOIN LATERAL (
                SELECT jsonb_agg(raw.identifier ORDER BY raw.sort_key) AS identifiers
                FROM (
                    SELECT
                        0 AS sort_key,
                        jsonb_build_object(
                            'imei', item.used_imei,
                            'secondaryImei', NULL,
                            'serialNumber', item.used_serial_number,
                            'deviceStatus', item.used_device_status
                        ) AS identifier
                    WHERE item.used_device_id IS NOT NULL

                    UNION ALL

                    SELECT
                        1 AS sort_key,
                        jsonb_build_object(
                            'imei', pi.imei,
                            'secondaryImei',
                                CASE
                                    WHEN pair.imei1 = pi.imei THEN pair.imei2
                                    WHEN pair.imei2 = pi.imei THEN pair.imei1
                                    ELSE NULL
                                END,
                            'serialNumber', pair.serial_number,
                            'deviceStatus', pi.status
                        ) AS identifier
                    FROM product_imeis pi
                    LEFT JOIN product_identifier_pairs pair
                      ON pair.product_id = pi.product_id
                     AND pair.variant_id IS NOT DISTINCT FROM pi.variant_id
                     AND (pair.imei1 = pi.imei OR pair.imei2 = pi.imei)
                    WHERE item.used_device_id IS NULL
                      AND pi.sold_order_id = item.order_id
                      AND pi.product_id = item.product_id
                      AND pi.variant_id IS NOT DISTINCT FROM item.variant_id
                      AND (pair.id IS NULL OR pi.imei = pair.imei1)

                    UNION ALL

                    SELECT
                        2 AS sort_key,
                        jsonb_build_object(
                            'imei', NULL,
                            'secondaryImei', NULL,
                            'serialNumber', psn.serial_number,
                            'deviceStatus', psn.status
                        ) AS identifier
                    FROM product_serial_numbers psn
                    WHERE item.used_device_id IS NULL
                      AND psn.product_id = item.product_id
                      AND psn.variant_id IS NOT DISTINCT FROM item.variant_id
                      AND (
                          psn.service_payload ->> 'soldOrderId' = item.order_id::text
                          OR psn.service_payload ->> 'orderId' = item.order_id::text
                      )
                      AND NOT EXISTS (
                          SELECT 1
                          FROM product_identifier_pairs pair
                          WHERE pair.product_id = psn.product_id
                            AND pair.variant_id IS NOT DISTINCT FROM psn.variant_id
                            AND pair.serial_number = psn.serial_number
                      )
                ) raw
                WHERE raw.identifier ->> 'imei' IS NOT NULL
                   OR raw.identifier ->> 'serialNumber' IS NOT NULL
            ) identifiers ON TRUE
            ORDER BY item.completed_at DESC NULLS LAST, item.order_code DESC, item.order_item_id
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


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


async def get_total_returned_quantity(session: AsyncSession, order_item_id: UUID) -> int:
    result = await session.scalar(
        text(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM return_request_items i
            JOIN return_requests r ON r.id = i.request_id
            WHERE i.order_item_id = :order_item_id
              AND r.status NOT IN ('CANCELLED', 'REJECTED', 'CLOSED_EXPIRED')
            """
        ),
        {"order_item_id": order_item_id},
    )
    return int(result or 0)


async def get_active_warranty_quantity(session: AsyncSession, order_item_id: UUID) -> int:
    result = await session.scalar(
        text(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM warranty_request_items i
            JOIN warranty_requests w ON w.id = i.request_id
            WHERE i.order_item_id = :order_item_id
              AND w.status NOT IN ('CANCELLED', 'REJECTED', 'CLOSED_EXPIRED', 'COMPLETED')
            """
        ),
        {"order_item_id": order_item_id},
    )
    return int(result or 0)


async def has_completed_return_for_identifier(
    session: AsyncSession,
    *,
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
                WHERE r.status = 'COMPLETED'
                  AND ((CAST(:imei AS VARCHAR) IS NOT NULL AND i.imei = CAST(:imei AS VARCHAR))
                       OR (CAST(:serial AS VARCHAR) IS NOT NULL AND i.serial_number = CAST(:serial AS VARCHAR)))
            )
            """
        ),
        {"imei": imei, "serial": serial_number},
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
    has_accessories: bool = True,
    good_appearance: bool = True,
    account_unlocked: bool = True,
    has_vat_invoice: bool = True,
    exchange_product_id: UUID | None = None,
    exchange_variant_id: UUID | None = None,
    exchange_quantity: int = 1,
    exchange_unit_price: float = 0,
) -> None:
    request_table, _ = _table(kind)
    exchange_columns = ""
    exchange_values = ""
    if kind == "RETURN":
        exchange_columns = (
            ", exchange_product_id, exchange_variant_id, exchange_quantity, "
            "exchange_unit_price_snapshot"
        )
        exchange_values = (
            ", CAST(:exchange_product_id AS UUID), CAST(:exchange_variant_id AS UUID), "
            ":exchange_quantity, :exchange_unit_price"
        )
    await session.execute(
        text(
            f"""
            INSERT INTO {request_table}
                (id, request_code, user_id, order_id, status, reason, sla_due_at,
                 has_accessories, good_appearance, account_unlocked, has_vat_invoice{exchange_columns})
            VALUES
                (:id, :code, :user_id, :order_id, 'SUBMITTED', :reason, NOW() + INTERVAL '3 days',
                 :has_accessories, :good_appearance, :account_unlocked, :has_vat_invoice{exchange_values})
            """
        ),
        {
            "id": request_id,
            "code": request_code,
            "user_id": user_id,
            "order_id": order_id,
            "reason": reason,
            "has_accessories": has_accessories,
            "good_appearance": good_appearance,
            "account_unlocked": account_unlocked,
            "has_vat_invoice": has_vat_invoice,
            "exchange_product_id": exchange_product_id,
            "exchange_variant_id": exchange_variant_id,
            "exchange_quantity": exchange_quantity,
            "exchange_unit_price": exchange_unit_price,
        },
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


async def list_events(session: AsyncSession, *, kind: str, reference_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                ev.id::text AS id,
                ev.old_status AS "oldStatus",
                ev.new_status AS "newStatus",
                ev.actor_id::text AS "actorId",
                ev.note,
                ev.metadata,
                ev.created_at AS "createdAt",
                COALESCE(u.full_name, u.email, ev.actor_name) AS "actorName"
            FROM after_sales_events ev
            LEFT JOIN users u ON u.id = ev.actor_id
            WHERE ev.reference_type = :kind
              AND ev.reference_id = :reference_id
            ORDER BY ev.created_at ASC, ev.id ASC
            """
        ),
        {"kind": kind, "reference_id": reference_id},
    )
    return [dict(row._mapping) for row in result]


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
    params = {"kind": kind, "user_id": user_id, "status": status_value, "offset": (page - 1) * limit, "limit": limit}
    order = "DESC" if descending else "ASC"
    customer_fault_select = (
        'COALESCE(r.customer_fault, FALSE)' if kind == "RETURN" else "FALSE"
    )
    depreciation_select = (
        'COALESCE(r.depreciation_fee, 0)' if kind == "RETURN" else "0"
    )
    exchange_select = (
        """
        r.exchange_product_id::text AS "exchangeProductId",
        r.exchange_variant_id::text AS "exchangeVariantId",
        r.exchange_quantity AS "exchangeQuantity",
        r.exchange_unit_price_snapshot AS "exchangeUnitPrice",
        r.exchange_fee AS "exchangeFee",
        r.exchange_shipping_fee AS "exchangeShippingFee",
        r.balance_amount AS "balanceAmount",
        r.payment_status AS "paymentStatus",
        r.payment_due_at AS "paymentDueAt",
        r.exchange_payment_confirmed_at AS "exchangePaymentConfirmedAt",
        r.exchange_payment_reference AS "exchangePaymentReference",
        ep.name AS "exchangeProductName",
        ev.sku AS "exchangeVariantSku",
        COALESCE(ev.storage, ev.configuration, ev.color_name, '') AS "exchangeVariantLabel"
        """
        if kind == "RETURN" else
        """
        NULL AS "exchangeProductId",
        NULL AS "exchangeVariantId",
        0 AS "exchangeQuantity",
        0 AS "exchangeUnitPrice",
        0 AS "exchangeFee",
        0 AS "exchangeShippingFee",
        0 AS "balanceAmount",
        NULL AS "paymentStatus",
        NULL AS "paymentDueAt",
        NULL AS "exchangePaymentConfirmedAt",
        NULL AS "exchangePaymentReference",
        NULL AS "exchangeProductName",
        NULL AS "exchangeVariantSku",
        NULL AS "exchangeVariantLabel"
        """
    )
    repair_summary_select = (
        """
        COALESCE((
            SELECT jsonb_build_object(
                'diagnosis', ev.metadata #>> '{repair,diagnosis}',
                'action', ev.metadata #>> '{repair,action}',
                'parts', ev.metadata #>> '{repair,parts}',
                'cost', COALESCE((ev.metadata #>> '{repair,cost}')::numeric, 0),
                'stage', ev.metadata #>> '{repair,stage}',
                'updatedAt', ev.created_at
            )
            FROM after_sales_events ev
            WHERE ev.reference_type = 'WARRANTY'
              AND ev.reference_id = r.id
              AND ev.metadata ? 'repair'
            ORDER BY ev.created_at DESC
            LIMIT 1
        ), '{}'::jsonb)
        """
        if kind == "WARRANTY" else "'{}'::jsonb"
    )
    repair_route_select = (
        """
        r.repair_channel AS "repairChannel",
        r.repair_provider_name AS "repairProviderName",
        r.repair_sent_at AS "repairSentAt",
        r.return_fulfillment_method AS "returnFulfillmentMethod"
        """
        if kind == "WARRANTY" else
        """
        NULL AS "repairChannel",
        NULL AS "repairProviderName",
        NULL AS "repairSentAt",
        NULL AS "returnFulfillmentMethod"
        """
    )
    inventory_destination_select = """
        COALESCE(
            (SELECT jsonb_build_object(
                'type', 'USED_INTAKE', 'id', intake.id::text,
                'referenceCode', intake.request_code, 'status', intake.status
             ) FROM used_device_intake_requests intake
             WHERE intake.return_request_id = r.id
             ORDER BY intake.created_at DESC LIMIT 1),
            (SELECT jsonb_build_object(
                'type', doc.document_type, 'id', doc.id::text,
                'referenceCode', doc.document_no, 'status', doc.status
             ) FROM inventory_documents doc
             WHERE doc.return_request_id = r.id
               AND doc.document_type IN ('INTERNAL_HOLD', 'DISPOSAL')
             ORDER BY doc.created_at DESC LIMIT 1)
        )
    """ if kind == "RETURN" else "NULL"
    total = await session.scalar(text(f"SELECT COUNT(*) FROM {request_table} r WHERE {' AND '.join(filters)}"), params)
    result = await session.execute(
        text(
            f"""
            SELECT r.id::text AS id, r.request_code AS "requestCode", r.user_id::text AS "userId",
                   r.order_id::text AS "orderId", o.order_code AS "orderCode", r.status, r.reason,
                   r.resolution_type AS "resolutionType", r.admin_note AS "adminNote",
                   {customer_fault_select} AS "customerFault",
                   {depreciation_select} AS "depreciationFee",
                   {"r.inventory_disposition" if kind == "RETURN" else "NULL"} AS "inventoryDisposition",
                   {inventory_destination_select} AS "inventoryDestination",
                   {exchange_select},
                   r.qc_note AS "qcNote", r.sla_due_at AS "slaDueAt",
                   r.sla_breached_at AS "slaBreachedAt", r.created_at AS "createdAt",
                   {repair_route_select},
                   (
                       SELECT jsonb_build_object(
                           'id', fulfillment.id::text,
                           'orderCode', fulfillment.order_code,
                           'status', fulfillment.status,
                           'shippingProvider', fulfillment.shipping_provider,
                           'trackingCode', fulfillment.tracking_code,
                           'fulfillmentMethod', fulfillment.fulfillment_method,
                           'recipientName', fulfillment.recipient_name,
                           'recipientPhone', fulfillment.recipient_phone,
                           'shippingAddress', fulfillment.shipping_address
                       )
                       FROM orders fulfillment
                       WHERE fulfillment.{"return_request_id" if kind == "RETURN" else "warranty_request_id"} = r.id
                       LIMIT 1
                   ) AS "fulfillmentOrder",
                   (
                       SELECT jsonb_build_object(
                           'id', outbound.id::text,
                           'documentNo', outbound.document_no,
                           'status', outbound.status
                       )
                       FROM inventory_documents outbound
                       WHERE outbound.{"return_request_id" if kind == "RETURN" else "warranty_request_id"} = r.id
                         AND outbound.document_type = 'OUTBOUND'
                         AND outbound.status <> 'CANCELLED'
                       ORDER BY outbound.created_at DESC
                       LIMIT 1
                   ) AS "fulfillmentOutbound",
                   {repair_summary_select} AS "repairSummary",
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                           'id', i.id::text, 'orderItemId', i.order_item_id::text,
                           'productId', i.product_id::text, 'variantId', i.product_variant_id::text,
                            'productName', oi.product_name, 'quantity', i.quantity,
                            'imei', i.imei, 'serialNumber', i.serial_number,
                            'replacementImei', i.replacement_imei,
                            'replacementImeis', COALESCE(i.replacement_imeis, '[]'::jsonb),
                            'replacementSecondaryImeis', COALESCE(i.replacement_secondary_imeis, '[]'::jsonb),
                            'replacementSerialNumbers', COALESCE(i.replacement_serial_numbers, '[]'::jsonb)
                       )) FROM {item_table} i
                       JOIN order_items oi ON oi.id = i.order_item_id
                       WHERE i.request_id = r.id
                    ), '[]'::jsonb) AS items
                   ,COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                           'id', a.id::text,
                           'originalName', a.original_name,
                           'url', CASE
                               WHEN a.storage_key LIKE 'uploads/%' THEN :media_public_path || '/' || substr(a.storage_key, 9)
                               ELSE :media_public_path || '/' || ltrim(a.storage_key, '/')
                           END,
                           'contentType', a.content_type,
                           'sizeBytes', a.size_bytes,
                           'createdAt', a.created_at
                       ) ORDER BY a.created_at ASC)
                       FROM after_sales_attachments a
                       WHERE a.reference_type = :kind
                         AND a.reference_id = r.id
                         AND a.status = 'ACTIVE'
                   ), '[]'::jsonb) AS attachments
            FROM {request_table} r
            JOIN orders o ON o.id = r.order_id
            {"LEFT JOIN products ep ON ep.id = r.exchange_product_id LEFT JOIN product_variants ev ON ev.id = r.exchange_variant_id" if kind == "RETURN" else ""}
            WHERE {' AND '.join(filters)}
            ORDER BY r.created_at {order}
            OFFSET :offset LIMIT :limit
            """
        ),
        {**params, "media_public_path": media_storage.public_path},
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
    depreciation_fee: float | None = None,
    repair_channel: str | None = None,
    repair_provider_name: str | None = None,
    return_fulfillment_method: str | None = None,
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
    depreciation_set = ", depreciation_fee = GREATEST(COALESCE(:depreciation_fee, depreciation_fee), 0)" if kind == "RETURN" else ""
    repair_set = ""
    if kind == "WARRANTY":
        repair_set = """
            , repair_channel = COALESCE(:repair_channel, repair_channel)
            , repair_provider_name = CASE
                WHEN CAST(:repair_channel AS VARCHAR) = 'INTERNAL' THEN NULL
                ELSE COALESCE(:repair_provider_name, repair_provider_name)
              END
            , repair_sent_at = CASE
                WHEN CAST(:repair_channel AS VARCHAR) = 'MANUFACTURER'
                     AND CAST(:status AS VARCHAR) = 'REPAIRING'
                    THEN COALESCE(repair_sent_at, NOW())
                ELSE repair_sent_at
              END
            , return_fulfillment_method = COALESCE(:return_fulfillment_method, return_fulfillment_method)
        """
    await session.execute(
        text(
            f"""
            UPDATE {request_table}
            SET status = :status, resolution_type = COALESCE(:resolution_type, resolution_type),
                admin_note = COALESCE(:note, admin_note), updated_at = NOW()
                {fault_set} {depreciation_set} {repair_set} {extra}
            WHERE id = :id
            """
        ),
        {
            "id": request_id, "status": status_value, "resolution_type": resolution_type,
            "note": note, "customer_fault": customer_fault, "depreciation_fee": depreciation_fee,
            "repair_channel": repair_channel,
            "repair_provider_name": repair_provider_name,
            "return_fulfillment_method": return_fulfillment_method,
        },
    )


async def update_return_exchange_financials(
    session: AsyncSession,
    *,
    request_id: UUID,
    exchange_fee: float,
    exchange_shipping_fee: float,
    balance_amount: float,
    payment_status: str,
    payment_due_hours: int | None = None,
) -> None:
    due_sql = "NOW() + (CAST(:payment_due_hours AS INTEGER) * INTERVAL '1 hour')" if payment_due_hours else "NULL"
    await session.execute(
        text(
            f"""
            UPDATE return_requests
            SET exchange_fee = :exchange_fee,
                exchange_shipping_fee = :exchange_shipping_fee,
                balance_amount = :balance_amount,
                payment_status = :payment_status,
                payment_due_at = {due_sql},
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": request_id,
            "exchange_fee": exchange_fee,
            "exchange_shipping_fee": exchange_shipping_fee,
            "balance_amount": balance_amount,
            "payment_status": payment_status,
            "payment_due_hours": payment_due_hours,
        },
    )


async def mark_exchange_payment_paid(
    session: AsyncSession,
    *,
    request_id: UUID,
    reference: str | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE return_requests
            SET payment_status = 'PAID',
                exchange_payment_confirmed_at = NOW(),
                exchange_payment_reference = COALESCE(NULLIF(:reference, ''), exchange_payment_reference),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": request_id, "reference": reference},
    )


async def get_request_items(session: AsyncSession, *, kind: str, request_id: UUID) -> list[dict]:
    _, item_table = _table(kind)
    result = await session.execute(
        text(
            f"""
            SELECT rit.*, oi.used_device_id
            FROM {item_table} rit
            LEFT JOIN order_items oi ON oi.id = rit.order_item_id
            WHERE rit.request_id = :id
            """
        ),
        {"id": request_id},
    )
    return [dict(row._mapping) for row in result]


async def available_stock(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    exclude_kind: str | None = None,
    exclude_request_id: UUID | None = None,
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
                  AND NOT (
                      CAST(:exclude_kind AS VARCHAR) IS NOT NULL
                      AND CAST(:exclude_request_id AS UUID) IS NOT NULL
                      AND reference_type = CAST(:exclude_kind AS VARCHAR)
                      AND reference_id = CAST(:exclude_request_id AS UUID)
                  )
            )
            SELECT GREATEST(physical.qty - after_sales.qty, 0) FROM physical, after_sales
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "exclude_kind": exclude_kind,
            "exclude_request_id": exclude_request_id,
        },
    )
    return int(value or 0)


async def create_allocations_for_lines(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    lines: list[dict],
) -> bool:
    # 1. Group quantities by (product_id, variant_id)
    grouped: dict[tuple[UUID, UUID | None], int] = {}
    for item in lines:
        p_id = item["product_id"]
        v_id = item.get("product_variant_id")
        key = (p_id, v_id)
        grouped[key] = grouped.get(key, 0) + int(item["quantity"])

    # 2. Lock inventory levels and verify stock atomic
    for (p_id, v_id), qty in grouped.items():
        # SELECT FOR UPDATE to lock inventory rows for this product/variant across all locations
        await session.execute(
            text(
                """
                SELECT id FROM inventory_levels
                WHERE product_id = :p_id
                  AND variant_id IS NOT DISTINCT FROM :v_id
                FOR UPDATE
                """
            ),
            {"p_id": p_id, "v_id": v_id},
        )
        avail = await available_stock(
            session,
            product_id=p_id,
            variant_id=v_id,
            exclude_kind=kind,
            exclude_request_id=request_id,
        )
        if avail < qty:
            return False

    # 3. Insert allocations
    for (p_id, v_id), qty in grouped.items():
        await session.execute(
            text(
                """
                INSERT INTO after_sales_allocations
                    (id, reference_type, reference_id, product_id, product_variant_id,
                     quantity, status, expires_at)
                VALUES
                    (:id, :kind, :reference_id, :product_id, :variant_id,
                     :quantity, 'LOCKED', NOW() + INTERVAL '48 hours')
                ON CONFLICT (reference_type, reference_id, product_id, COALESCE(product_variant_id, '00000000-0000-0000-0000-000000000000'::uuid))
                WHERE status = 'LOCKED'
                DO UPDATE SET
                    quantity = after_sales_allocations.quantity + EXCLUDED.quantity
                """
            ),
            {
                "id": uuid4(), "kind": kind, "reference_id": request_id,
                "product_id": p_id, "variant_id": v_id,
                "quantity": qty,
            },
        )
    return True


async def create_allocations(session: AsyncSession, *, kind: str, request_id: UUID, items: list[dict]) -> bool:
    return await create_allocations_for_lines(
        session,
        kind=kind,
        request_id=request_id,
        lines=items,
    )


async def create_exchange_allocation(session: AsyncSession, *, request: dict) -> bool:
    if not request.get("exchange_product_id"):
        return False
    return await create_allocations_for_lines(
        session,
        kind="RETURN",
        request_id=request["id"],
        lines=[
            {
                "product_id": request["exchange_product_id"],
                "product_variant_id": request.get("exchange_variant_id"),
                "quantity": int(request.get("exchange_quantity") or 1),
            }
        ],
    )


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
