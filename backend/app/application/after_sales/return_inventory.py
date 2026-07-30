from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import inventory_repo


RETURN_TO_STOCK_REASON = "AFTER_SALES_RETURN_TO_STOCK"


async def ensure_return_to_stock_inbound(
    session: AsyncSession,
    *,
    request: dict,
    items: list[dict],
    actor_id: UUID | None,
    note: str | None,
) -> UUID:
    """Tạo phiếu nhập Nháp cho hàng khách trả đủ điều kiện bán mới."""
    existing = await session.scalar(
        text(
            """
            SELECT id
            FROM inventory_documents
            WHERE return_request_id = :request_id
              AND document_type = 'INBOUND'
              AND reason = :reason
              AND status <> 'CANCELLED'
            FOR UPDATE
            """
        ),
        {"request_id": request["id"], "reason": RETURN_TO_STOCK_REASON},
    )
    if existing:
        return existing

    location = (
        await session.execute(
            text(
                """
                SELECT id, code, name
                FROM inventory_locations
                WHERE is_active = TRUE
                  AND status = 'ACTIVE'
                  AND purpose IN ('STORAGE', 'VIRTUAL')
                ORDER BY CASE WHEN code = 'MAIN' THEN 0 ELSE 1 END, sort_order, code
                LIMIT 1
                """
            )
        )
    ).mappings().first()
    if not location:
        raise HTTPException(
            status_code=409,
            detail="Chưa cấu hình kệ bán hàng để tạo phiếu nhập lại thiết bị khách trả.",
        )

    document_id = uuid4()
    request_code = request.get("request_code") or str(request["id"])
    document_no = f"AS-IN-{request_code}"
    await inventory_repo.insert_inventory_receipt_document(
        session,
        document_id=document_id,
        reference_code=document_no,
        status="DRAFT",
        reason=RETURN_TO_STOCK_REASON,
        supplier_name="Khách hàng trả hàng",
        note=note or f"Chờ kho xác nhận nhập lại thiết bị từ hồ sơ {request_code}.",
        location_id=location["id"],
        created_by=actor_id,
        metadata={
            "afterSalesType": "RETURN",
            "afterSalesRequestId": str(request["id"]),
            "orderId": str(request["order_id"]),
            "inventoryDisposition": "NEW_STOCK",
            "qualityStatus": "PASSED",
            "qualityLabel": "Đạt",
            "qualityNote": note,
            "quarantine": False,
            "sellableStock": True,
        },
    )
    await session.execute(
        text("UPDATE inventory_documents SET return_request_id = :request_id WHERE id = :document_id"),
        {"document_id": document_id, "request_id": request["id"]},
    )

    for item in items:
        product_id = item.get("product_id")
        if not product_id:
            raise HTTPException(status_code=409, detail="Dòng trả hàng chưa xác định được sản phẩm để nhập kho.")
        imeis = [str(item["imei"]).strip()] if item.get("imei") else []
        serial_numbers = [str(item["serial_number"]).strip()] if item.get("serial_number") else []
        await inventory_repo.insert_inventory_receipt_line(
            session,
            line_id=uuid4(),
            document_id=document_id,
            product_id=product_id,
            variant_id=item.get("product_variant_id"),
            location_id=location["id"],
            quantity=int(item.get("quantity") or 1),
            unit_cost=float(item.get("unit_price_snapshot") or 0),
            note="Thiết bị đã đạt QC hậu mãi; kho xác nhận trước khi đưa về tồn bán.",
            imeis=imeis,
            tracks_imei=bool(imeis),
            serial_numbers=serial_numbers,
            tracks_serial_number=bool(serial_numbers),
            reason="Khách hàng trả hàng đạt điều kiện bán mới.",
            storage_location_code=location["code"],
            storage_location_name=location["name"],
        )
    return document_id
