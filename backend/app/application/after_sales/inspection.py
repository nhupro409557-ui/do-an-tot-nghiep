from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.schemas import InspectAfterSalesRequest
from app.infrastructure.database.repositories import after_sales_repo


RETURN_QC_RESULTS = {
    "APPROVE_EXCHANGE": ("QC_APPROVED", "EXCHANGE"),
    "APPROVE_REFUND": ("QC_APPROVED", "REFUND"),
    "REJECT": ("REJECTED", None),
}
WARRANTY_QC_RESULTS = {
    "ACCEPT_REPAIR": ("WARRANTY_ACCEPTED", "REPAIR"),
    "APPROVE_REPLACEMENT": ("REPLACEMENT_APPROVED", "REPLACEMENT"),
    "REJECT": ("REJECTED", None),
}


async def inspect_request(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    actor_id: UUID,
    payload: InspectAfterSalesRequest,
) -> dict:
    request = await after_sales_repo.get_request_for_update(session, kind=kind, request_id=request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hậu mãi.")
    if request["status"] != "QC_IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Chỉ có thể ghi kết quả QC khi hồ sơ đang ở trạng thái kiểm tra.")

    result = payload.result.upper()
    result_map = RETURN_QC_RESULTS if kind == "RETURN" else WARRANTY_QC_RESULTS
    if result not in result_map:
        raise HTTPException(status_code=400, detail="Kết quả QC không hợp lệ.")

    target, resolution_type = result_map[result]
    items = await after_sales_repo.get_request_items(session, kind=kind, request_id=request_id)
    if target in {"QC_APPROVED", "REPLACEMENT_APPROVED"}:
        locked = await after_sales_repo.create_allocations(
            session,
            kind=kind,
            request_id=request_id,
            items=items,
        )
        if not locked:
            target = "WAITING_FOR_STOCK"

    await after_sales_repo.update_request_status(
        session,
        kind=kind,
        request_id=request_id,
        status_value=target,
        resolution_type=resolution_type,
        note=payload.qc_note,
        customer_fault=payload.customer_fault,
        depreciation_fee=payload.depreciation_fee if kind == "RETURN" else None,
    )
    await _update_qc_note(
        session,
        kind=kind,
        request_id=request_id,
        qc_note=payload.qc_note,
        customer_fault=payload.customer_fault,
    )
    await after_sales_repo.insert_event(
        session,
        kind=kind,
        reference_id=request_id,
        old_status=request["status"],
        new_status=target,
        actor_id=actor_id,
        note=payload.qc_note,
        metadata={
            "action": "QC_INSPECTION",
            "result": result,
            "resolutionType": resolution_type,
            "customerFault": payload.customer_fault,
            "depreciationFee": payload.depreciation_fee if kind == "RETURN" else 0,
        },
    )
    await after_sales_repo.notify(
        session,
        user_id=request["user_id"],
        type_value="after_sales",
        title="Cập nhật kết quả kiểm tra hậu mãi",
        message=f"Yêu cầu {request['request_code']} đã có kết quả QC: {target}.",
        entity_type=kind,
        entity_id=request_id,
        immediate=target == "REJECTED",
        key=f"{kind}:{request_id}:QC:{target}",
    )
    await session.commit()
    return {"id": str(request_id), "status": target, "resolutionType": resolution_type}


async def _update_qc_note(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    qc_note: str,
    customer_fault: bool,
) -> None:
    table = "return_requests" if kind == "RETURN" else "warranty_requests"
    fault_set = ", customer_fault=:customer_fault" if kind == "RETURN" else ""
    await session.execute(
        text(
            f"""
            UPDATE {table}
            SET qc_note=:qc_note, updated_at=NOW()
                {fault_set}
            WHERE id=:id
            """
        ),
        {"id": request_id, "qc_note": qc_note, "customer_fault": customer_fault},
    )
