import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.attachments import schedule_attachment_cleanup
from app.infrastructure.database.repositories import after_sales_repo
from app.infrastructure.storage import StorageReadOnlyError, media_storage


async def run_maintenance(session: AsyncSession) -> dict:
    exchange_payment_expired = await session.execute(
        text(
            """
            UPDATE return_requests
            SET status='CLOSED_EXPIRED',
                payment_status='TIMEOUT',
                closed_at=NOW(),
                updated_at=NOW()
            WHERE status='WAITING_FOR_EXCHANGE_PAYMENT'
              AND payment_due_at <= NOW()
            RETURNING id, request_code, user_id
            """
        )
    )
    expired_exchange_rows = exchange_payment_expired.mappings().all()
    for row in expired_exchange_rows:
        await after_sales_repo.release_allocations(session, kind="RETURN", request_id=row["id"])
        await after_sales_repo.insert_event(
            session,
            kind="RETURN",
            reference_id=row["id"],
            old_status="WAITING_FOR_EXCHANGE_PAYMENT",
            new_status="CLOSED_EXPIRED",
            actor_id=None,
            note="Hồ sơ đổi trả đã hết hạn thanh toán chênh lệch.",
            metadata={"reason": "EXCHANGE_PAYMENT_TIMEOUT"},
        )
        await after_sales_repo.notify(
            session,
            user_id=row["user_id"],
            type_value="after_sales",
            title="Hồ sơ đổi trả đã hết hạn thanh toán",
            message=f"Yêu cầu {row['request_code']} đã bị đóng vì quá hạn thanh toán chênh lệch.",
            entity_type="RETURN",
            entity_id=row["id"],
            immediate=True,
            key=f"RETURN:{row['id']}:EXCHANGE_PAYMENT_TIMEOUT",
        )
    released = await session.execute(
        text(
            """
            UPDATE after_sales_allocations
            SET status='RELEASED', released_at=NOW()
            WHERE status='LOCKED' AND expires_at <= NOW()
            RETURNING reference_type, reference_id
            """
        )
    )
    expired_requests = 0
    for kind, table in (("RETURN", "return_requests"), ("WARRANTY", "warranty_requests")):
        result = await session.execute(
            text(
                f"""
                UPDATE {table}
                SET status='CLOSED_EXPIRED', closed_at=NOW(), updated_at=NOW()
                WHERE status='SUBMITTED' AND created_at <= NOW() - INTERVAL '15 days'
                RETURNING id
                """
            )
        )
        ids = [row.id for row in result]
        expired_requests += len(ids)
        for request_id in ids:
            await schedule_attachment_cleanup(session, kind, request_id)
    sla = 0
    for table in ("return_requests", "warranty_requests"):
        result = await session.execute(
            text(
                f"""
                UPDATE {table} SET sla_breached_at=NOW(), updated_at=NOW()
                WHERE sla_breached_at IS NULL AND sla_due_at < NOW()
                  AND status NOT IN ('COMPLETED','REJECTED','CANCELLED','CLOSED_EXPIRED')
                RETURNING id
                """
            )
        )
        sla += len(result.all())
    allocated_waiting = 0
    waiting = await session.execute(
        text(
            """
            SELECT kind, id FROM (
                SELECT 'RETURN' kind, id, sla_due_at, qc_approved_at approved_at
                FROM return_requests WHERE status='WAITING_FOR_STOCK'
                UNION ALL
                SELECT 'WARRANTY' kind, id, sla_due_at, replacement_approved_at approved_at
                FROM warranty_requests WHERE status='WAITING_FOR_STOCK'
            ) queue
            ORDER BY (sla_due_at <= NOW()) DESC, sla_due_at ASC NULLS LAST, approved_at ASC NULLS LAST
            """
        )
    )
    for row in waiting:
        locked_request = await after_sales_repo.get_request_for_update(
            session,
            kind=row.kind,
            request_id=row.id,
        )
        if not locked_request or locked_request["status"] != "WAITING_FOR_STOCK":
            continue
        items = await after_sales_repo.get_request_items(session, kind=row.kind, request_id=row.id)
        if locked_request.get("exchange_product_id"):
            allocated = await after_sales_repo.create_exchange_allocation(session, request=locked_request)
        else:
            allocated = await after_sales_repo.create_allocations(session, kind=row.kind, request_id=row.id, items=items)
        if allocated:
            table = "return_requests" if row.kind == "RETURN" else "warranty_requests"
            if row.kind == "RETURN" and locked_request.get("exchange_product_id"):
                next_status = (
                    "WAITING_FOR_EXCHANGE_PAYMENT"
                    if float(locked_request.get("balance_amount") or 0) > 0
                    else "EXCHANGE_PROCESSING"
                )
                extra_sql = ", payment_due_at = COALESCE(payment_due_at, NOW() + INTERVAL '24 hours')" if next_status == "WAITING_FOR_EXCHANGE_PAYMENT" else ""
            else:
                next_status = "QC_APPROVED" if row.kind == "RETURN" else "REPLACEMENT_APPROVED"
                extra_sql = ""
            await session.execute(
                text(f"UPDATE {table} SET status=:status, updated_at=NOW(){extra_sql} WHERE id=:id AND status='WAITING_FOR_STOCK'"),
                {"status": next_status, "id": row.id},
            )
            allocated_waiting += 1
    voucher_notifications = await session.execute(
        text(
            """
            INSERT INTO notifications
                (id, user_id, type, title, message, entity_type, entity_id,
                 action_url, idempotency_key, available_at)
            SELECT gen_random_uuid(), uv.user_id, 'voucher', 'Voucher sắp hết hạn',
                   'Voucher ' || v.code || ' sẽ hết hạn vào ' || to_char(uv.expires_at, 'DD/MM/YYYY') || '.',
                   'VOUCHER', v.id, '/dashboard',
                   'voucher-expiry:' || uv.id::text, NOW()
            FROM user_vouchers uv
            JOIN vouchers v ON v.id=uv.voucher_id
            WHERE uv.status='AVAILABLE'
              AND uv.expires_at > NOW()
              AND uv.expires_at <= NOW() + INTERVAL '3 days'
            ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
            RETURNING id
            """
        )
    )
    deleted_files = 0
    for attachment in await after_sales_repo.cleanup_due_attachments(session):
        try:
            await asyncio.to_thread(media_storage.delete, attachment["storage_key"])
            await after_sales_repo.mark_attachment_deleted(session, attachment["id"])
            deleted_files += 1
        except (OSError, StorageReadOnlyError):
            continue
    await session.commit()
    return {
        "releasedAllocations": len(released.all()),
        "expiredExchangePayments": len(expired_exchange_rows),
        "expiredRequests": expired_requests,
        "slaBreaches": sla,
        "allocatedWaitingRequests": allocated_waiting,
        "voucherExpiryNotifications": len(voucher_notifications.all()),
        "deletedAttachments": deleted_files,
    }
