import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import after_sales_repo, inventory_repo


def _clean_identifier_values(values: list[str], *, label: str, max_length: int) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        if len(normalized) > max_length:
            raise HTTPException(status_code=400, detail=f"{label} vượt quá độ dài cho phép.")
        if normalized in seen:
            raise HTTPException(status_code=400, detail=f"{label} bị trùng trong cùng dòng: {normalized}.")
        cleaned.append(normalized)
        seen.add(normalized)
    return cleaned


async def _resolve_identifier_pair(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    imei: str | None,
    serial_number: str | None,
) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT imei1, imei2, serial_number
            FROM product_identifier_pairs
            WHERE product_id = :product_id
              AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
              AND (
                  (CAST(:imei AS VARCHAR) IS NOT NULL
                   AND (imei1 = CAST(:imei AS VARCHAR) OR imei2 = CAST(:imei AS VARCHAR)))
                  OR
                  (CAST(:serial_number AS VARCHAR) IS NOT NULL
                   AND serial_number = CAST(:serial_number AS VARCHAR))
              )
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "imei": imei,
            "serial_number": serial_number,
        },
    )
    rows = [dict(row) for row in result.mappings().all()]
    if len(rows) > 1:
        raise HTTPException(
            status_code=400,
            detail="IMEI và serial đã nhập không thuộc cùng một thiết bị.",
        )
    if not rows:
        return None
    pair = rows[0]
    if imei and imei not in {pair["imei1"], pair.get("imei2")}:
        raise HTTPException(status_code=400, detail=f"IMEI {imei} không khớp cặp định danh.")
    if serial_number and serial_number != pair["serial_number"]:
        raise HTTPException(
            status_code=400,
            detail=f"Serial {serial_number} không khớp cặp định danh.",
        )
    return pair


async def _lock_replacement_unit(
    session: AsyncSession,
    *,
    item: dict,
    imei: str | None,
    serial_number: str | None,
) -> dict:
    pair = await _resolve_identifier_pair(
        session,
        product_id=item["product_id"],
        variant_id=item.get("product_variant_id"),
        imei=imei,
        serial_number=serial_number,
    )
    primary_imei = pair["imei1"] if pair else imei
    secondary_imei = pair.get("imei2") if pair else None
    resolved_serial = pair["serial_number"] if pair else serial_number

    locations: set[UUID] = set()
    locked_imeis: list[str] = []
    for value in [primary_imei, secondary_imei]:
        if not value:
            continue
        row = (
            await session.execute(
                text(
                    """
                    SELECT id, imei, status, location_id
                    FROM product_imeis
                    WHERE imei = :imei
                      AND product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
                    FOR UPDATE
                    """
                ),
                {
                    "imei": value,
                    "product_id": item["product_id"],
                    "variant_id": item.get("product_variant_id"),
                },
            )
        ).mappings().first()
        if not row or row["status"] != "IN_STOCK" or not row["location_id"]:
            raise HTTPException(
                status_code=409,
                detail=f"IMEI thay thế {value} không còn sẵn sàng trong kho.",
            )
        locations.add(row["location_id"])
        locked_imeis.append(value)

    if resolved_serial:
        serial_row = (
            await session.execute(
                text(
                    """
                    SELECT id, serial_number, status, location_id
                    FROM product_serial_numbers
                    WHERE serial_number = :serial_number
                      AND product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM CAST(:variant_id AS UUID)
                    FOR UPDATE
                    """
                ),
                {
                    "serial_number": resolved_serial,
                    "product_id": item["product_id"],
                    "variant_id": item.get("product_variant_id"),
                },
            )
        ).mappings().first()
        if not serial_row or serial_row["status"] != "IN_STOCK" or not serial_row["location_id"]:
            raise HTTPException(
                status_code=409,
                detail=f"Serial thay thế {resolved_serial} không còn sẵn sàng trong kho.",
            )
        locations.add(serial_row["location_id"])

    if not locked_imeis and not resolved_serial:
        raise HTTPException(
            status_code=400,
            detail="Mỗi thiết bị thay thế phải có ít nhất một IMEI hoặc serial.",
        )
    if len(locations) != 1:
        raise HTTPException(
            status_code=409,
            detail="IMEI và serial của thiết bị thay thế không nằm cùng một vị trí kho.",
        )
    return {
        "primary_imei": primary_imei,
        "secondary_imei": secondary_imei,
        "serial_number": resolved_serial,
        "location_id": next(iter(locations)),
    }


async def _mark_original_identifiers_defective(
    session: AsyncSession,
    *,
    kind: str,
    request_id: UUID,
    item: dict,
    actor_id: UUID,
) -> None:
    original_imei = (item.get("imei") or "").strip() or None
    original_serial = (item.get("serial_number") or "").strip() or None
    pair = await _resolve_identifier_pair(
        session,
        product_id=item["product_id"],
        variant_id=item.get("product_variant_id"),
        imei=original_imei,
        serial_number=original_serial,
    )
    imeis = [
        value
        for value in (
            pair["imei1"] if pair else original_imei,
            pair.get("imei2") if pair else None,
        )
        if value
    ]
    serial_number = pair["serial_number"] if pair else original_serial

    for imei in imeis:
        old_row = (
            await session.execute(
                text("SELECT id, status FROM product_imeis WHERE imei = :imei FOR UPDATE"),
                {"imei": imei},
            )
        ).mappings().first()
        if not old_row or old_row["status"] == "DEFECTIVE_RETURNED":
            continue
        await session.execute(
            text(
                """
                UPDATE product_imeis
                SET status = 'DEFECTIVE_RETURNED', updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": old_row["id"]},
        )
        await session.execute(
            text(
                """
                INSERT INTO imei_disposition_events (
                    id, imei_id, after_sales_type, after_sales_id,
                    old_status, new_status, reason, actor_id
                )
                VALUES (
                    :id, :imei_id, :kind, :request_id,
                    :old_status, 'DEFECTIVE_RETURNED',
                    'Thu hồi từ yêu cầu hậu mãi.', :actor_id
                )
                """
            ),
            {
                "id": uuid4(),
                "imei_id": old_row["id"],
                "kind": kind,
                "request_id": request_id,
                "old_status": old_row["status"],
                "actor_id": actor_id,
            },
        )

    if serial_number:
        old_serial_row = (
            await session.execute(
                text("SELECT id, status FROM product_serial_numbers WHERE serial_number = :serial AND product_id = :product_id FOR UPDATE"),
                {"serial": serial_number, "product_id": item["product_id"]},
            )
        ).mappings().first()
        if old_serial_row and old_serial_row["status"] != "DEFECTIVE_RETURNED":
            await session.execute(
                text(
                    """
                    UPDATE product_serial_numbers
                    SET status = 'DEFECTIVE_RETURNED', updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": old_serial_row["id"]},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO imei_disposition_events (
                        id, serial_id, after_sales_type, after_sales_id,
                        old_status, new_status, reason, actor_id
                    )
                    VALUES (
                        :id, :serial_id, :kind, :request_id,
                        :old_status, 'DEFECTIVE_RETURNED',
                        'Thu hồi từ yêu cầu hậu mãi.', :actor_id
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "serial_id": old_serial_row["id"],
                    "kind": kind,
                    "request_id": request_id,
                    "old_status": old_serial_row["status"],
                    "actor_id": actor_id,
                },
            )

    if item.get("used_device_id"):
        await session.execute(
            text("UPDATE used_devices SET status = 'RETIRED', updated_at = NOW() WHERE id = :uid"),
            {"uid": item["used_device_id"]},
        )


async def complete_replacements(
    session: AsyncSession,
    *,
    kind: str,
    request: dict,
    request_id: UUID,
    items: list[dict],
    replacement_items: list[dict],
    actor_id: UUID,
) -> None:
    request_items_by_id = {item["id"]: item for item in items}
    payload_by_id: dict[UUID, dict] = {}
    for replacement in replacement_items:
        request_item_id = replacement["request_item_id"]
        if request_item_id in payload_by_id:
            raise HTTPException(
                status_code=400,
                detail="Mỗi dòng hậu mãi chỉ được khai báo thiết bị thay thế một lần.",
            )
        payload_by_id[request_item_id] = replacement
    if set(payload_by_id) != set(request_items_by_id):
        raise HTTPException(
            status_code=400,
            detail="Cần khai báo mã định danh thay thế cho đầy đủ từng dòng hậu mãi.",
        )

    used_imeis: set[str] = set()
    used_serial_numbers: set[str] = set()
    units_by_item: dict[UUID, list[dict]] = {}
    groups: dict[tuple[UUID, UUID], dict] = {}

    for item_id, item in request_items_by_id.items():
        replacement = payload_by_id[item_id]
        imeis = _clean_identifier_values(
            replacement.get("imeis", []),
            label="IMEI thay thế",
            max_length=80,
        )
        serial_numbers = _clean_identifier_values(
            replacement.get("serial_numbers", []),
            label="Serial thay thế",
            max_length=120,
        )
        quantity = int(item["quantity"])
        if not imeis and not serial_numbers:
            raise HTTPException(
                status_code=400,
                detail="Mỗi dòng hậu mãi phải có ít nhất một danh sách IMEI hoặc serial thay thế.",
            )
        if imeis and len(imeis) != quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Số IMEI thay thế phải bằng số lượng {quantity} của dòng hậu mãi.",
            )
        if serial_numbers and len(serial_numbers) != quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Số serial thay thế phải bằng số lượng {quantity} của dòng hậu mãi.",
            )

        units: list[dict] = []
        for index in range(quantity):
            unit = await _lock_replacement_unit(
                session,
                item=item,
                imei=imeis[index] if imeis else None,
                serial_number=serial_numbers[index] if serial_numbers else None,
            )
            unit_imeis = {
                value
                for value in (unit["primary_imei"], unit["secondary_imei"])
                if value
            }
            if used_imeis.intersection(unit_imeis):
                raise HTTPException(
                    status_code=400,
                    detail="Một IMEI thay thế đang được dùng cho nhiều dòng hoặc nhiều thiết bị.",
                )
            if unit["serial_number"] and unit["serial_number"] in used_serial_numbers:
                raise HTTPException(
                    status_code=400,
                    detail="Một serial thay thế đang được dùng cho nhiều dòng hoặc nhiều thiết bị.",
                )
            used_imeis.update(unit_imeis)
            if unit["serial_number"]:
                used_serial_numbers.add(unit["serial_number"])
            units.append(unit)

            group_key = (item_id, unit["location_id"])
            group = groups.setdefault(
                group_key,
                {
                    "item": item,
                    "location_id": unit["location_id"],
                    "units": [],
                },
            )
            group["units"].append(unit)
        units_by_item[item_id] = units

    document_lines: list[dict] = []
    for group in groups.values():
        item = group["item"]
        location_id = group["location_id"]
        quantity = len(group["units"])
        level = (
            await session.execute(
                text(
                    """
                    SELECT il.id, il.on_hand_quantity, il.average_unit_cost,
                           loc.code AS location_code, loc.name AS location_name
                    FROM inventory_levels il
                    JOIN inventory_locations loc ON loc.id = il.location_id
                    WHERE il.location_id = :location_id
                      AND (
                          (CAST(:variant_id AS UUID) IS NOT NULL
                           AND il.variant_id = CAST(:variant_id AS UUID))
                          OR
                          (CAST(:variant_id AS UUID) IS NULL
                           AND il.product_id = CAST(:product_id AS UUID))
                      )
                    FOR UPDATE OF il
                    """
                ),
                {
                    "location_id": location_id,
                    "variant_id": item.get("product_variant_id"),
                    "product_id": item["product_id"],
                },
            )
        ).mappings().first()
        if not level or level["on_hand_quantity"] < quantity:
            raise HTTPException(
                status_code=409,
                detail="Tồn kho vật lý tại vị trí của thiết bị thay thế không đủ để xuất.",
            )
        await session.execute(
            text(
                """
                UPDATE inventory_levels
                SET on_hand_quantity = on_hand_quantity - :quantity, updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": level["id"], "quantity": quantity},
        )
        await session.execute(
            text(
                """
                INSERT INTO inventory_adjustment_logs (
                    id, product_id, variant_id, old_quantity, new_quantity, delta,
                    reference_code, reason, note, location_code, location_name
                )
                VALUES (
                    :id, :product_id, :variant_id, :old_quantity, :new_quantity,
                    :delta, :reference_code, 'AFTER_SALES_REPLACEMENT',
                    :note, :location_code, :location_name
                )
                """
            ),
            {
                "id": uuid4(),
                "product_id": item["product_id"],
                "variant_id": item.get("product_variant_id"),
                "old_quantity": level["on_hand_quantity"],
                "new_quantity": level["on_hand_quantity"] - quantity,
                "delta": -quantity,
                "reference_code": request["request_code"],
                "note": f"Xuất {quantity} thiết bị thay thế cho yêu cầu {kind} {request_id}.",
                "location_code": level["location_code"],
                "location_name": level["location_name"],
            },
        )
        document_lines.append(
            {
                "product_id": item["product_id"],
                "variant_id": item.get("product_variant_id"),
                "location_id": location_id,
                "quantity": quantity,
                "unit_cost": float(level["average_unit_cost"] or 0),
                "imeis": [
                    unit["primary_imei"]
                    for unit in group["units"]
                    if unit["primary_imei"]
                ],
                "secondary_imeis": [
                    unit["secondary_imei"]
                    for unit in group["units"]
                    if unit["secondary_imei"]
                ],
                "serial_numbers": [
                    unit["serial_number"]
                    for unit in group["units"]
                    if unit["serial_number"]
                ],
            }
        )

    for item_id, item in request_items_by_id.items():
        quantity = int(item["quantity"])
        if item.get("product_variant_id"):
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET stock_quantity = GREATEST(stock_quantity - :quantity, 0),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": item["product_variant_id"], "quantity": quantity},
            )
        await session.execute(
            text(
                """
                UPDATE products
                SET stock_quantity = GREATEST(stock_quantity - :quantity, 0),
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": item["product_id"], "quantity": quantity},
        )

        units = units_by_item[item_id]
        primary_imeis = [unit["primary_imei"] for unit in units if unit["primary_imei"]]
        secondary_imeis = [unit["secondary_imei"] for unit in units if unit["secondary_imei"]]
        serial_numbers = [unit["serial_number"] for unit in units if unit["serial_number"]]
        for imei in [*primary_imeis, *secondary_imeis]:
            await session.execute(
                text(
                    """
                    UPDATE product_imeis
                    SET status = 'SOLD', location_id = NULL, sold_at = NOW(),
                        sold_order_id = :order_id, updated_at = NOW()
                    WHERE imei = :imei
                    """
                ),
                {"imei": imei, "order_id": request["order_id"]},
            )
        for serial_number in serial_numbers:
            await session.execute(
                text(
                    """
                    UPDATE product_serial_numbers
                    SET status = 'SOLD', location_id = NULL, sold_at = NOW(),
                        service_payload = COALESCE(service_payload, '{}'::jsonb)
                            || jsonb_build_object(
                                'soldOrderId', CAST(CAST(:order_id AS UUID) AS TEXT),
                                'orderId', CAST(CAST(:order_id AS UUID) AS TEXT)
                            ),
                        updated_at = NOW()
                    WHERE serial_number = :serial_number
                    """
                ),
                {"serial_number": serial_number, "order_id": request["order_id"]},
            )

        for imei in [*primary_imeis, *secondary_imeis]:
            await session.execute(
                text("UPDATE used_devices SET status = 'SOLD', updated_at = NOW() WHERE imei = :imei"),
                {"imei": imei},
            )
        for serial_number in serial_numbers:
            await session.execute(
                text("UPDATE used_devices SET status = 'SOLD', updated_at = NOW() WHERE serial_number = :serial"),
                {"serial": serial_number},
            )

        _, item_table = after_sales_repo._table(kind)
        await session.execute(
            text(
                f"""
                UPDATE {item_table}
                SET replacement_imei = :replacement_imei,
                    replacement_imeis = CAST(:replacement_imeis AS jsonb),
                    replacement_secondary_imeis = CAST(:replacement_secondary_imeis AS jsonb),
                    replacement_serial_numbers = CAST(:replacement_serial_numbers AS jsonb)
                WHERE id = :item_id
                """
            ),
            {
                "item_id": item_id,
                "replacement_imei": primary_imeis[0] if primary_imeis else None,
                "replacement_imeis": json.dumps(primary_imeis),
                "replacement_secondary_imeis": json.dumps(secondary_imeis),
                "replacement_serial_numbers": json.dumps(serial_numbers),
            },
        )
        await _mark_original_identifiers_defective(
            session,
            kind=kind,
            request_id=request_id,
            item=item,
            actor_id=actor_id,
        )

    await inventory_repo.insert_after_sales_replacement_outbound(
        session,
        kind=kind,
        request_id=request_id,
        request_code=request["request_code"],
        order_id=request["order_id"],
        lines=document_lines,
        actor_id=actor_id,
    )
    await session.execute(
        text(
            """
            UPDATE after_sales_allocations
            SET status = 'CONSUMED', consumed_at = NOW()
            WHERE reference_type = :kind
              AND reference_id = :request_id
              AND status = 'LOCKED'
            """
        ),
        {"kind": kind, "request_id": request_id},
    )
