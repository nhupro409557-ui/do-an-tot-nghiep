from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.identifier_groups import (
    lock_identifier_group,
    update_locked_identifier_group_status,
)
from app.infrastructure.database.repositories import after_sales_repo


FINAL_IDENTIFIER_STATUS = {
    "REPAIR": "REPAIR_PENDING",
    "SCRAP": "SCRAP",
}


async def finalize_returned_identifier_disposition(
    session: AsyncSession,
    *,
    request_id: UUID,
    actor_id: UUID | None,
) -> dict:
    """Kết thúc xử lý máy khách trả mà không đưa thiết bị vào tồn bán."""
    request = await after_sales_repo.get_request_for_update(
        session,
        kind="RETURN",
        request_id=request_id,
    )
    disposition = str((request or {}).get("inventory_disposition") or "").upper()
    target_status = FINAL_IDENTIFIER_STATUS.get(disposition)
    if not request or not target_status:
        return {"targetStatus": None, "updatedIdentifiers": 0}

    items = await after_sales_repo.get_request_items(
        session,
        kind="RETURN",
        request_id=request_id,
    )
    updated_identifiers = 0
    for item in items:
        imei = str(item.get("imei") or "").strip() or None
        serial_number = str(item.get("serial_number") or "").strip() or None
        if not imei and not serial_number:
            continue
        group = await lock_identifier_group(
            session,
            product_id=item["product_id"],
            variant_id=item.get("product_variant_id"),
            imei=imei,
            serial_number=serial_number,
        )
        changed = await update_locked_identifier_group_status(
            session,
            group=group,
            target_status=target_status,
            allowed_statuses={"SOLD", "DEFECTIVE_RETURNED", "INSPECTION_PENDING"},
            clear_location=True,
        )
        for identifier in changed:
            await session.execute(
                text(
                    """
                    INSERT INTO imei_disposition_events (
                        id, imei_id, serial_id, after_sales_type, after_sales_id,
                        old_status, new_status, reason, actor_id
                    ) VALUES (
                        :id, :imei_id, :serial_id, 'RETURN', :request_id,
                        :old_status, :new_status, :reason, :actor_id
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "imei_id": identifier.id if identifier.kind == "IMEI" else None,
                    "serial_id": identifier.id if identifier.kind == "SERIAL" else None,
                    "request_id": request_id,
                    "old_status": identifier.status,
                    "new_status": target_status,
                    "reason": (
                        "Chuyển máy khách trả sang hàng chờ sửa chữa."
                        if disposition == "REPAIR"
                        else "Hủy thiết bị khách trả theo kết quả QC."
                    ),
                    "actor_id": actor_id,
                },
            )
        updated_identifiers += len(changed)

    document_reason = (
        "AFTER_SALES_RETURN_REPAIR"
        if disposition == "REPAIR"
        else "AFTER_SALES_RETURN_SCRAP"
    )
    await session.execute(
        text(
            """
            UPDATE inventory_documents
            SET status = 'COMPLETED',
                approved_by = COALESCE(approved_by, :actor_id),
                posted_by = COALESCE(posted_by, :actor_id),
                approved_at = COALESCE(approved_at, NOW()),
                posted_at = COALESCE(posted_at, NOW()),
                metadata = COALESCE(metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'offLedgerReturnedItem', TRUE,
                        'identifierTargetStatus', CAST(:target_status AS TEXT)
                    )
            WHERE return_request_id = :request_id
              AND reason = :reason
              AND status IN ('DRAFT', 'APPROVED')
            """
        ),
        {
            "request_id": request_id,
            "reason": document_reason,
            "target_status": target_status,
            "actor_id": actor_id,
        },
    )
    return {
        "targetStatus": target_status,
        "updatedIdentifiers": updated_identifiers,
    }
