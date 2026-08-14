from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.identifier_groups import lock_identifier_group
from app.infrastructure.database.repositories import used_product_repo


async def create_repaired_device_used_intake(
    session: AsyncSession,
    *,
    identifier_id: UUID,
    actor_id: UUID,
    note: str | None = None,
) -> dict:
    identifier = (
        await session.execute(
            text(
                """
                SELECT id, product_id, variant_id, imei AS value, 'IMEI' AS kind
                FROM product_imeis
                WHERE id = :identifier_id
                UNION ALL
                SELECT id, product_id, variant_id, serial_number AS value, 'SERIAL' AS kind
                FROM product_serial_numbers
                WHERE id = :identifier_id
                LIMIT 1
                """
            ),
            {"identifier_id": identifier_id},
        )
    ).mappings().first()
    if not identifier:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã định danh thiết bị đã sửa.")

    group = await lock_identifier_group(
        session,
        product_id=identifier["product_id"],
        variant_id=identifier["variant_id"],
        imei=identifier["value"] if identifier["kind"] == "IMEI" else None,
        serial_number=identifier["value"] if identifier["kind"] == "SERIAL" else None,
    )
    if not group.imeis:
        raise HTTPException(
            status_code=409,
            detail="Quy trình hàng cũ hiện yêu cầu thiết bị có IMEI hợp lệ.",
        )
    if {item.status for item in group.identifiers} != {"REPAIRED"}:
        raise HTTPException(
            status_code=409,
            detail="Chỉ có thể chuyển sang hàng cũ khi toàn bộ IMEI/serial của máy đã sửa xong.",
        )

    imei = group.imeis[0].value
    serial_number = group.serials[0].value if group.serials else None
    existing = (
        await session.execute(
            text(
                """
                SELECT id, request_code, status
                FROM used_device_intake_requests
                WHERE imei = :imei
                  AND status NOT IN ('REJECTED', 'CANCELLED')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"imei": imei},
        )
    ).mappings().first()
    if existing:
        return {
            "id": str(existing["id"]),
            "requestCode": existing["request_code"],
            "status": existing["status"],
            "idempotent": True,
        }

    source = (
        await session.execute(
            text(
                """
                SELECT after_sales_type, after_sales_id
                FROM imei_disposition_events
                WHERE after_sales_id IS NOT NULL
                  AND (
                    imei_id = ANY(CAST(:imei_ids AS UUID[]))
                    OR serial_id = ANY(CAST(:serial_ids AS UUID[]))
                  )
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {
                "imei_ids": [item.id for item in group.imeis],
                "serial_ids": [item.id for item in group.serials],
            },
        )
    ).mappings().first()
    if not source or source["after_sales_type"] not in {"RETURN", "WARRANTY"}:
        raise HTTPException(
            status_code=409,
            detail="Không xác định được hồ sơ hậu mãi đã thu hồi thiết bị này.",
        )

    request_table = "return_requests" if source["after_sales_type"] == "RETURN" else "warranty_requests"
    request = (
        await session.execute(
            text(
                f"""
                SELECT id, request_code, order_id, user_id
                FROM {request_table}
                WHERE id = :request_id
                FOR UPDATE
                """
            ),
            {"request_id": source["after_sales_id"]},
        )
    ).mappings().first()
    if not request:
        raise HTTPException(status_code=409, detail="Hồ sơ hậu mãi nguồn không còn tồn tại.")

    intake_id = uuid4()
    request_code = await used_product_repo.next_request_code(session)
    await session.execute(
        text(
            """
            INSERT INTO used_device_intake_requests (
                id, request_code, source_type, seller_user_id,
                original_order_id, return_request_id, warranty_request_id,
                product_id, variant_id, imei, serial_number, expected_price,
                note, status, created_by, updated_by, received_at
            ) VALUES (
                :id, :request_code, 'AFTER_SALES_REPAIRED', :seller_user_id,
                :order_id, :return_request_id, :warranty_request_id,
                :product_id, :variant_id, :imei, :serial_number, 0,
                :note, 'RECEIVED', :actor_id, :actor_id, NOW()
            )
            """
        ),
        {
            "id": intake_id,
            "request_code": request_code,
            "seller_user_id": request["user_id"],
            "order_id": request["order_id"],
            "return_request_id": request["id"] if source["after_sales_type"] == "RETURN" else None,
            "warranty_request_id": request["id"] if source["after_sales_type"] == "WARRANTY" else None,
            "product_id": identifier["product_id"],
            "variant_id": identifier["variant_id"],
            "imei": imei,
            "serial_number": serial_number,
            "note": (note or "").strip()
            or f"Tiếp nhận máy đã sửa từ hồ sơ hậu mãi {request['request_code']} để thẩm định hàng cũ.",
            "actor_id": actor_id,
        },
    )
    await used_product_repo.insert_event(
        session,
        intake_id=intake_id,
        event_type="AFTER_SALES_REPAIRED_TO_USED_INTAKE",
        old_status=None,
        new_status="RECEIVED",
        actor_id=actor_id,
        note="Admin xác nhận chuyển máy cũ đã sửa sang quy trình thẩm định hàng cũ.",
        metadata={
            "afterSalesType": source["after_sales_type"],
            "afterSalesId": str(request["id"]),
            "identifierIds": [str(item.id) for item in group.identifiers],
        },
    )
    await session.commit()
    return {
        "id": str(intake_id),
        "requestCode": request_code,
        "status": "RECEIVED",
        "idempotent": False,
    }
