import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.attachments import schedule_attachment_cleanup
from app.infrastructure.database.repositories import after_sales_repo


async def run_maintenance(session: AsyncSession) -> dict:
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
        if await after_sales_repo.create_allocations(session, kind=row.kind, request_id=row.id, items=items):
            table = "return_requests" if row.kind == "RETURN" else "warranty_requests"
            next_status = "QC_APPROVED" if row.kind == "RETURN" else "REPLACEMENT_APPROVED"
            await session.execute(
                text(f"UPDATE {table} SET status=:status, updated_at=NOW() WHERE id=:id AND status='WAITING_FOR_STOCK'"),
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
            path = Path(attachment["storage_key"])
            if path.exists():
                os.remove(path)
            await after_sales_repo.mark_attachment_deleted(session, attachment["id"])
            deleted_files += 1
        except OSError:
            continue
    await session.commit()
    return {
        "releasedAllocations": len(released.all()),
        "expiredRequests": expired_requests,
        "slaBreaches": sla,
        "allocatedWaitingRequests": allocated_waiting,
        "voucherExpiryNotifications": len(voucher_notifications.all()),
        "deletedAttachments": deleted_files,
    }
