from .documents import adjust_product_inventory
from .common import *
from .common import validate_identifier_pairs

async def set_variant_inventory(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID,
    payload: VariantInventoryPayload,
) -> dict:
    return await adjust_product_inventory(
        session,
        product_id,
        InventoryAdjustmentPayload(
            variantId=variant_id,
            quantity=payload.quantity,
            transactionType=payload.transactionType,
            referenceCode=payload.referenceCode,
            reason=payload.reason,
            note=payload.note,
        ),
        idempotency_key=payload.referenceCode,
    )


async def create_outbound_document_from_order(session: AsyncSession, order_id: UUID) -> UUID | None:
    from app.infrastructure.database.models import Order
    from app.infrastructure.database.repositories import commerce_repo

    order = await session.get(Order, order_id, with_for_update=True)
    if not order:
        return None
    if order.order_purpose == "WARRANTY_RETURN":
        raise HTTPException(status_code=409, detail="Đơn gửi lại máy đã sửa không được phép tạo phiếu xuất kho.")

    # Check if outbound document already exists
    res = await session.execute(
        text(
            """
            SELECT id, status
            FROM inventory_documents
            WHERE order_id = :order_id
              AND document_type = 'OUTBOUND'
            FOR UPDATE
            """
        ),
        {"order_id": order_id},
    )
    row = res.first()
    document_id = None
    if row:
        if row[1] == "CANCELLED":
            await session.execute(
                text(
                    """
                    UPDATE inventory_documents
                    SET status = 'DRAFT',
                        document_no = :document_no,
                        cancelled_at = NULL,
                        cancelled_by = NULL,
                        note = 'Phát hành lại phiếu xuất khi đơn hàng tiếp tục xử lý.'
                    WHERE id = :document_id
                    """
                ),
                {"document_id": row[0], "document_no": f"OUT-{order.order_code}"},
            )
            await session.execute(
                text("DELETE FROM inventory_document_lines WHERE document_id = :document_id"),
                {"document_id": row[0]},
            )
            document_id = row[0]
        else:
            return row[0]

    items = await commerce_repo.list_restock_items(session, order_id=order_id, order_code=order.order_code)
    shippable_items = [item for item in items if not item.get("used_device_id")]
    if not shippable_items:
        return None

    # Get default WAREHOUSE location (code = 'MAIN')
    location_row = await inventory_repo.get_inventory_location_by_code(session, "MAIN")
    location_id = location_row["id"] if location_row else None

    document_id = document_id or uuid4()
    document_no = f"OUT-{order.order_code}"

    if not row:
        await inventory_repo.insert_inventory_outbound_document(
            session,
            document_id=document_id,
            document_no=document_no,
            status="DRAFT",
            reason="SO_OUTBOUND",
            note=f"Phiếu xuất kho tự động cho đơn hàng {order.order_code}",
            source_location_id=location_id,
            order_id=order_id,
        )

    for item in shippable_items:
        product_id = item["product_id"]
        variant_id = item["order_variant_id"] or item["variant_id"]

        # Check product tracking policy
        policy_row = await inventory_repo.get_product_inventory_policy(session, product_id)
        tracks_imei = _policy_tracks_imei(policy_row)
        tracks_serial = _policy_tracks_serial_number(policy_row)

        # Suggest suggested location based on highest on_hand stock level
        suggested_location_id = None
        if variant_id:
            sql_levels = """
                SELECT il.location_id
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                WHERE il.variant_id = :variant_id
                  AND GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0
                ORDER BY (loc.code = 'MAIN') ASC,
                         GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) DESC
                LIMIT 1
            """
            res_levels = await session.execute(text(sql_levels), {"variant_id": variant_id})
            row_level = res_levels.first()
            if row_level:
                suggested_location_id = row_level[0]
        else:
            sql_levels = """
                SELECT il.location_id
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                WHERE il.product_id = :product_id
                  AND il.variant_id IS NULL
                  AND GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0
                ORDER BY (loc.code = 'MAIN') ASC,
                         GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) DESC
                LIMIT 1
            """
            res_levels = await session.execute(text(sql_levels), {"product_id": product_id})
            row_level = res_levels.first()
            if row_level:
                suggested_location_id = row_level[0]

        if not suggested_location_id:
            suggested_location_id = location_id

        line_id = uuid4()
        await inventory_repo.insert_inventory_outbound_line(
            session,
            line_id=line_id,
            document_id=document_id,
            product_id=product_id,
            variant_id=variant_id,
            location_id=suggested_location_id,
            quantity=item["quantity"],
            unit_cost=None,
            note=None,
            imeis=[],
            tracks_imei=tracks_imei,
            serial_numbers=[],
            tracks_serial_number=tracks_serial,
        )
        if item.get("after_sales_request_item_id"):
            await session.execute(
                text(
                    """
                    UPDATE inventory_document_lines
                    SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                        'orderItemId', CAST(CAST(:order_item_id AS UUID) AS TEXT),
                        'afterSalesType', CAST(:after_sales_type AS TEXT),
                        'afterSalesRequestItemId', CAST(CAST(:request_item_id AS UUID) AS TEXT)
                    )
                    WHERE id = :line_id
                    """
                ),
                {
                    "line_id": line_id,
                    "order_item_id": item["id"],
                    "after_sales_type": item.get("after_sales_type"),
                    "request_item_id": item["after_sales_request_item_id"],
                },
            )

    return document_id


async def list_outbound_documents(
    session: AsyncSession,
    search: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    return await inventory_repo.list_inventory_outbound_documents(
        session,
        search=search,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


async def resolve_outbound_identifier_pair(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    identifier_type: str,
    identifier_value: str,
) -> dict:
    normalized_type = identifier_type.upper()
    cleaned_value = identifier_value.strip()
    if normalized_type == "SERIAL":
        cleaned_value = cleaned_value.upper()
    if normalized_type not in {"IMEI", "SERIAL"} or not cleaned_value:
        raise HTTPException(status_code=400, detail="Mã định danh không hợp lệ.")

    pair = await inventory_repo.get_identifier_pair_for_outbound(
        session,
        product_id=product_id,
        variant_id=variant_id,
        location_id=location_id,
        identifier_type=normalized_type,
        identifier_value=cleaned_value,
    )
    if not pair:
        raise HTTPException(status_code=404, detail="Không tìm thấy cặp IMEI/serial còn trong kho tại kệ đã chọn.")
    return {
        "imei": pair.get("imei") or pair.get("imei1"),
        "imei1": pair.get("imei1"),
        "imei2": pair.get("imei2"),
        "serialNumber": pair["serialNumber"],
    }


async def get_outbound_document(session: AsyncSession, document_no: str) -> dict:
    doc = await inventory_repo.get_inventory_outbound_document(session, document_no)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")

    # Load lines
    lines = await inventory_repo.list_inventory_outbound_lines(session, doc["id"])
    for line in lines:
        line["availableLocations"] = await inventory_repo.list_level_issue_candidates(
            session,
            line["productId"],
            line["variantId"],
        )
    doc["lines"] = lines
    return doc


async def _determine_outbound_status(session: AsyncSession, document_id: UUID) -> str:
    lines = await inventory_repo.list_inventory_outbound_lines(session, document_id)
    if not lines:
        return "DRAFT"

    any_allocated = False
    all_fully_allocated = True

    for line in lines:
        allocations = line.get("allocations") or line.get("metadata", {}).get("allocations") or []
        if isinstance(allocations, str):
            import json
            try:
                allocations = json.loads(allocations)
            except Exception:
                allocations = []

        if not allocations:
            all_fully_allocated = False
            continue

        any_allocated = True
        total_qty = sum(int(a.get("quantity") or 0) for a in allocations)

        if total_qty != line["quantity"]:
            all_fully_allocated = False
            continue

        # Check IMEI/Serial for each allocation
        for alloc in allocations:
            qty = int(alloc.get("quantity") or 0)
            if line.get("tracksImei") and len(alloc.get("imeis") or []) != qty:
                all_fully_allocated = False
                break
            if line.get("tracksSerialNumber") and len(alloc.get("serialNumbers") or []) != qty:
                all_fully_allocated = False
                break
        else:
            continue

        all_fully_allocated = False

    if all_fully_allocated:
        return "PICKED"
    elif any_allocated:
        return "PICKING"
    else:
        return "DRAFT"


async def update_outbound_document_lines(
    session: AsyncSession,
    document_no: str,
    lines_data: list,
    current_user_id: UUID | None = None,
) -> dict:
    await session.execute(
        text(
            """
            SELECT id
            FROM inventory_documents
            WHERE document_no = :document_no
              AND document_type = 'OUTBOUND'
            FOR UPDATE
            """
        ),
        {"document_no": document_no},
    )
    doc = await inventory_repo.get_inventory_outbound_document(session, document_no)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")

    if doc["status"] in ("COMPLETED", "CANCELLED"):
        raise HTTPException(status_code=400, detail="Không thể cập nhật phiếu xuất kho đã hoàn tất hoặc đã hủy.")

    document_lines = await inventory_repo.list_inventory_outbound_lines(session, doc["id"])
    document_line_ids = {str(item["id"]) for item in document_lines}

    for line in lines_data:
        line_id_str = line.get("lineId") or line.get("id")
        if not line_id_str:
            continue
        if str(line_id_str) not in document_line_ids:
            raise HTTPException(
                status_code=400,
                detail="Dòng hàng không thuộc phiếu xuất kho đang cập nhật.",
            )
        line_id = UUID(str(line_id_str))
        location_id_str = line.get("locationId")
        location_id = UUID(str(location_id_str)) if location_id_str else None

        approved_quantity = int(line.get("approvedQuantity") or line.get("quantity") or 0)
        imeis = [str(item).strip() for item in (line.get("imeis") or []) if str(item).strip()]
        serial_numbers = _clean_serial_numbers(line.get("serialNumbers") or [])

        # Load location details for code/name to store in metadata
        storage_location_code = None
        storage_location_name = None
        if location_id:
            loc = await inventory_repo.get_inventory_location_by_id(session, location_id)
            if loc:
                storage_location_code = loc["code"]
                storage_location_name = loc["name"]

        allocations = line.get("allocations") or []
        allocations_data = []
        seen_allocation_locations: set[UUID] = set()
        for alloc in allocations:
            alloc_loc_id = alloc.get("locationId") or alloc.get("location_id")
            alloc_loc_uuid = UUID(str(alloc_loc_id)) if alloc_loc_id else None
            if alloc_loc_uuid and alloc_loc_uuid in seen_allocation_locations:
                raise HTTPException(
                    status_code=400,
                    detail="Mỗi kệ chỉ được phân bổ một lần trong cùng dòng hàng.",
                )
            if alloc_loc_uuid:
                seen_allocation_locations.add(alloc_loc_uuid)

            alloc_loc_code = None
            alloc_loc_name = None
            if alloc_loc_uuid:
                loc = await inventory_repo.get_inventory_location_by_id(session, alloc_loc_uuid)
                if loc:
                    alloc_loc_code = loc["code"]
                    alloc_loc_name = loc["name"]

            alloc_quantity = int(alloc.get("quantity") or 0)
            if alloc_quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Số lượng phân bổ tại mỗi kệ phải lớn hơn 0.",
                )

            allocations_data.append({
                "locationId": str(alloc_loc_uuid) if alloc_loc_uuid else None,
                "locationCode": alloc_loc_code,
                "locationName": alloc_loc_name,
                "quantity": alloc_quantity,
                "imeis": [str(x).strip() for x in (alloc.get("imeis") or []) if str(x).strip()],
                "serialNumbers": _clean_serial_numbers(alloc.get("serialNumbers") or []),
            })

        await inventory_repo.update_inventory_outbound_line(
            session,
            line_id=line_id,
            location_id=location_id,
            approved_quantity=approved_quantity,
            imeis=imeis,
            serial_numbers=serial_numbers,
            storage_location_code=storage_location_code,
            storage_location_name=storage_location_name,
            allocations=allocations_data,
        )

    # Automatically calculate and update the outbound document's status based on pick progress
    new_status = await _determine_outbound_status(session, doc["id"])
    if doc["status"] != new_status:
        await inventory_repo.update_inventory_outbound_status(
            session,
            document_id=doc["id"],
            status=new_status,
            actor_id=current_user_id,
        )

    await session.commit()
    return {"ok": True, "referenceCode": document_no}


async def _post_inventory_outbound(
    session: AsyncSession,
    document_id: UUID,
    reference_code: str,
    note: str | None,
    order_id: UUID,
) -> None:
    document_lines = await inventory_repo.list_inventory_outbound_lines(session, document_id)
    touched_products: set[UUID] = set()

    from app.infrastructure.database.models import Order
    from app.infrastructure.database.repositories import commerce_repo
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng liên kết.")

    for index, line in enumerate(document_lines, start=1):
        product_id = line["productId"]
        variant_id = line["variantId"]
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial_number = bool(line.get("tracksSerialNumber"))
        quantity = int(line["quantity"])

        line_metadata = line.get("metadata") or {}
        allocations_list = line_metadata.get("allocations") or []

        if not allocations_list:
            location_id = line.get("locationId")
            if not location_id:
                raise HTTPException(status_code=400, detail=f"Dòng {index} ({line['productName']}): Chưa chọn vị trí kệ để xuất hàng.")
            imeis = [str(item).strip() for item in (line.get("imeis") or []) if str(item).strip()]
            serial_numbers = _clean_serial_numbers(line.get("serialNumbers") or [])
            allocations_list = [{
                "locationId": str(location_id),
                "quantity": quantity,
                "imeis": imeis,
                "serialNumbers": serial_numbers
            }]

        total_allocated_qty = sum(int(a.get("quantity") or 0) for a in allocations_list)
        if total_allocated_qty != quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index} ({line['productName']}): Tổng số lượng phân bổ trên các kệ ({total_allocated_qty}) phải bằng số lượng yêu cầu ({quantity})."
            )

        allocation_location_ids = [str(a.get("locationId") or "") for a in allocations_list]
        if len(allocation_location_ids) != len(set(allocation_location_ids)):
            raise HTTPException(
                status_code=400,
                detail=f"Dòng {index} ({line['productName']}): Mỗi kệ chỉ được phân bổ một lần.",
            )

        for alloc in allocations_list:
            alloc_location_id_str = alloc.get("locationId")
            if not alloc_location_id_str:
                raise HTTPException(status_code=400, detail=f"Dòng {index} ({line['productName']}): Có phân bổ chưa chọn vị trí kệ.")
            alloc_location_id = UUID(alloc_location_id_str)
            alloc_qty = int(alloc.get("quantity") or 0)

            stock_level = await inventory_repo.get_inventory_level(session, product_id, variant_id, alloc_location_id)
            available_quantity = int((stock_level or {}).get("availableQuantity") or 0)
            if not stock_level or available_quantity < alloc_qty:
                loc_code = stock_level["locationCode"] if stock_level else alloc_location_id_str
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {index} ({line['productName']}): Kệ {loc_code} không đủ tồn kho khả dụng để xuất. (Cần {alloc_qty}, khả dụng {available_quantity})"
                )

            alloc_imeis = [str(item).strip() for item in (alloc.get("imeis") or []) if str(item).strip()]
            alloc_serials = _clean_serial_numbers(alloc.get("serialNumbers") or [])

            await validate_identifier_pairs(
                session,
                product_id=product_id,
                variant_id=variant_id,
                imeis=alloc_imeis,
                serial_numbers=alloc_serials,
                line_index=index,
            )
            if tracks_imei:
                if len(alloc_imeis) != alloc_qty:
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: Số IMEI quét ({len(alloc_imeis)}) tại kệ phải khớp số lượng cần xuất ({alloc_qty}).")
                imei_statuses = await inventory_repo.list_imei_statuses_by_location(session, product_id, variant_id, alloc_location_id, alloc_imeis)
                if len(imei_statuses) != len(alloc_imeis):
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: Một hoặc nhiều IMEI không hợp lệ hoặc không có sẵn tại kệ đã chọn.")

            if tracks_serial_number:
                if len(alloc_serials) != alloc_qty:
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: Số serial quét ({len(alloc_serials)}) tại kệ phải khớp số lượng cần xuất ({alloc_qty}).")
                serial_statuses = await inventory_repo.list_serial_statuses_by_location(session, product_id, variant_id, alloc_location_id, alloc_serials)
                if len(serial_statuses) != len(alloc_serials):
                    raise HTTPException(status_code=400, detail=f"Dòng {index}: Một hoặc nhiều số serial không hợp lệ hoặc không có sẵn tại kệ đã chọn.")

        inventory_row = await commerce_repo.get_variant_stock_for_update(session, variant_id) if variant_id else await commerce_repo.get_product_stock_for_update(session, product_id)
        if not inventory_row:
            raise HTTPException(status_code=404, detail=f"Dòng {index}: Không tìm thấy thông tin tồn kho tổng thể.")

        old_total_quantity = int(inventory_row["stock_quantity"] or 0)
        new_total_quantity = old_total_quantity - quantity
        if new_total_quantity < 0:
            raise HTTPException(status_code=409, detail=f"Dòng {index}: Tồn kho tổng thể không đủ để xuất ({line['productName']}).")

        if variant_id:
            await commerce_repo.update_variant_stock(session, variant_id=variant_id, quantity=new_total_quantity)
            touched_products.add(product_id)
        else:
            await commerce_repo.update_product_stock(session, product_id=product_id, quantity=new_total_quantity)

        for alloc in allocations_list:
            alloc_location_id = UUID(alloc.get("locationId"))
            loc_res = await session.execute(
                text("SELECT code, name, status, purpose FROM inventory_locations WHERE id = :location_id"),
                {"location_id": alloc_location_id}
            )
            loc = loc_res.mappings().first()
            if not loc:
                raise HTTPException(status_code=404, detail=f"Dòng {index}: Không tìm thấy thông tin kệ {alloc.get('locationId')}.")
            if loc["status"] != "ACTIVE":
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {index}: Kệ {loc['name']} không hoạt động hoặc đang bị khóa.",
                )
            if loc["purpose"] not in {"STORAGE", "VIRTUAL"}:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dòng {index}: Không thể xuất kho bán hàng từ kệ {loc['name']} (mục đích: {loc['purpose']}).",
                )
            alloc_qty = int(alloc.get("quantity") or 0)
            alloc_imeis = [str(item).strip() for item in (alloc.get("imeis") or []) if str(item).strip()]
            alloc_serials = _clean_serial_numbers(alloc.get("serialNumbers") or [])

            await commerce_repo.consume_inventory_lots_fifo(
                session,
                product_id=product_id if not variant_id else inventory_row["product_id"],
                variant_id=variant_id,
                location_id=alloc_location_id,
                quantity=alloc_qty,
                reference_code=order.order_code,
                order_id=order.id,
            )

            levels = await commerce_repo.deduct_inventory_levels_from_locations(
                session,
                product_id=product_id if not variant_id else inventory_row["product_id"],
                variant_id=variant_id,
                location_quantities=[{"location_id": alloc_location_id, "quantity": alloc_qty}]
            )

            if (
                loc["code"] != "MAIN"
                and order.order_purpose in {"WARRANTY_REPLACEMENT", "RETURN_EXCHANGE"}
            ):
                main_mirror_update = await session.execute(
                    text(
                        """
                        UPDATE inventory_levels il
                        SET on_hand_quantity = il.on_hand_quantity - :quantity,
                            updated_at = NOW()
                        FROM inventory_locations main_loc
                        WHERE main_loc.id = il.location_id
                          AND main_loc.code = 'MAIN'
                          AND il.product_id = :product_id
                          AND il.variant_id IS NOT DISTINCT FROM :variant_id
                          AND il.on_hand_quantity - :quantity >= il.reserved_quantity
                        RETURNING il.id
                        """
                    ),
                    {
                        "quantity": alloc_qty,
                        "product_id": product_id if not variant_id else inventory_row["product_id"],
                        "variant_id": variant_id,
                    },
                )
                if main_mirror_update.first() is None:
                    main_mirror_exists = bool(
                        await session.scalar(
                            text(
                                """
                                SELECT EXISTS(
                                    SELECT 1
                                    FROM inventory_levels il
                                    JOIN inventory_locations main_loc ON main_loc.id = il.location_id
                                    WHERE main_loc.code = 'MAIN'
                                      AND il.product_id = :product_id
                                      AND il.variant_id IS NOT DISTINCT FROM :variant_id
                                )
                                """
                            ),
                            {
                                "product_id": product_id if not variant_id else inventory_row["product_id"],
                                "variant_id": variant_id,
                            },
                        )
                    )
                    if main_mirror_exists:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"Dòng {index}: Tồn kho tổng tại MAIN không đủ để đồng bộ xuất máy hậu mãi. "
                                "Vui lòng đối soát tồn kho trước khi thử lại."
                            ),
                        )

            for allocation in levels:
                if tracks_imei:
                    imei_update = await session.execute(
                        text(
                            """
                            UPDATE product_imeis
                            SET status = 'SOLD',
                                location_id = NULL,
                                sold_at = NOW(),
                                sold_order_id = :order_id,
                                updated_at = NOW()
                            WHERE id IN (
                                SELECT id FROM product_imeis
                                WHERE product_id = :product_id
                                  AND (variant_id IS NOT DISTINCT FROM :variant_id)
                                  AND location_id = :location_id
                                  AND (
                                      imei = ANY(:imeis)
                                      OR imei IN (
                                          SELECT pair.imei2
                                          FROM product_identifier_pairs pair
                                          WHERE pair.product_id = :product_id
                                            AND pair.variant_id IS NOT DISTINCT FROM :variant_id
                                            AND pair.imei2 IS NOT NULL
                                            AND (
                                                pair.imei1 = ANY(:imeis)
                                                OR pair.serial_number = ANY(:serial_numbers)
                                            )
                                      )
                                  )
                                  AND status = 'IN_STOCK'
                            )
                            """
                        ),
                        {
                            "order_id": order.id,
                            "product_id": product_id if not variant_id else inventory_row["product_id"],
                            "variant_id": variant_id,
                            "location_id": allocation["locationId"],
                            "imeis": alloc_imeis,
                            "serial_numbers": alloc_serials,
                        }
                    )
                    if int(imei_update.rowcount or 0) < len(alloc_imeis):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"Dòng {index}: Không thể cập nhật đủ IMEI đã quét. "
                                "Mã có thể vừa bị xuất ở giao dịch khác."
                            ),
                        )
                if tracks_serial_number:
                    serial_update = await session.execute(
                        text(
                            """
                            UPDATE product_serial_numbers
                            SET status = 'SOLD',
                                location_id = NULL,
                                sold_at = NOW(),
                                service_payload = COALESCE(service_payload, '{}'::jsonb)
                                    || jsonb_build_object('soldOrderId', CAST(:order_id AS TEXT)),
                                updated_at = NOW()
                            WHERE id IN (
                                SELECT id FROM product_serial_numbers
                                WHERE product_id = :product_id
                                  AND (variant_id IS NOT DISTINCT FROM :variant_id)
                                  AND location_id = :location_id
                                  AND serial_number = ANY(:serial_numbers)
                                  AND status = 'IN_STOCK'
                            )
                            """
                        ),
                        {
                            "order_id": str(order.id),
                            "product_id": product_id if not variant_id else inventory_row["product_id"],
                            "variant_id": variant_id,
                            "location_id": allocation["locationId"],
                            "serial_numbers": alloc_serials,
                        }
                    )
                    if int(serial_update.rowcount or 0) < len(alloc_serials):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"Dòng {index}: Không thể cập nhật đủ serial đã quét. "
                                "Serial có thể vừa bị xuất ở giao dịch khác."
                            ),
                        )

                await commerce_repo.insert_inventory_adjustment(
                    session,
                    product_id=product_id if not variant_id else inventory_row["product_id"],
                    variant_id=variant_id,
                    old_quantity=int(allocation["oldQuantity"]),
                    new_quantity=int(allocation["newQuantity"]),
                    delta=-int(allocation["quantity"]),
                    transaction_type="SALE",
                    reference_code=reference_code,
                    reason="ORDER_SHIPPED",
                    note=f"Xuất kho thực tế từ kệ theo phiếu xuất {reference_code} cho {line['productName']}.",
                    location_code=allocation.get("locationCode"),
                    location_name=allocation.get("locationName"),
                )

    for product_id in touched_products:
        await sync_parent_price_from_variants(session, product_id)


async def post_outbound_document(
    session: AsyncSession,
    document_no: str,
    current_user_id: UUID | None = None,
    current_role_code: str | None = None,
) -> dict:
    if current_role_code != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ có Quản trị viên cấp cao (Super Admin) mới được phép hoàn tất phiếu xuất kho.")

    # Luôn khóa đơn hàng trước phiếu xuất để thống nhất thứ tự khóa với luồng cập nhật đơn.
    initial_row = (
        await session.execute(
            text(
                """
                SELECT order_id
                FROM inventory_documents
                WHERE document_no = :document_no
                  AND document_type = 'OUTBOUND'
                """
            ),
            {"document_no": document_no},
        )
    ).first()
    if not initial_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")

    from app.infrastructure.database.models import Order
    order = await session.get(Order, initial_row[0], with_for_update=True)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng liên kết.")
    if (
        order.order_purpose == "RETURN_EXCHANGE"
        and order.payment_requirement == "BALANCE_PAYMENT"
        and order.payment_status != "PAID"
    ):
        raise HTTPException(
            status_code=409,
            detail="Đơn đổi máy còn tiền chênh lệch chưa được xác nhận thanh toán, không thể xuất kho.",
        )

    # Select document FOR UPDATE after locking its order.
    res = await session.execute(
        text(
            """
            SELECT id, status, order_id, document_no, note
            FROM inventory_documents
            WHERE document_no = :document_no AND document_type = 'OUTBOUND'
            FOR UPDATE
            """
        ),
        {"document_no": document_no},
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")

    doc = dict(row)
    if doc["status"] == "COMPLETED":
        raise HTTPException(status_code=400, detail="Phiếu xuất kho này đã được hoàn tất trước đó.")

    if doc["status"] != "PICKED":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể xác nhận xuất kho khi phiếu xuất ở trạng thái Đã đóng đủ hàng."
        )

    from app.application.commerce.use_cases import CompleteOrderUseCase
    complete_order_use_case = CompleteOrderUseCase(session=session)
    if order.status == "PAID":
        await complete_order_use_case.execute(
            order_id=order.id,
            status_value="PROCESSING",
            changed_by="warehouse-outbound",
            run_external_side_effects=False,
        )
    elif order.status != "PROCESSING":
        raise HTTPException(
            status_code=409,
            detail="Chỉ có thể xuất kho khi đơn hàng đang ở trạng thái Đã thanh toán hoặc Đang xử lý.",
        )

    # Post physical inventory outbound logic
    try:
        await _post_inventory_outbound(
            session,
            document_id=doc["id"],
            reference_code=doc["document_no"],
            note=doc["note"],
            order_id=doc["order_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Update document status to COMPLETED
    await inventory_repo.update_inventory_outbound_status(
        session,
        document_id=doc["id"],
        status="COMPLETED",
        actor_id=current_user_id,
    )

    from app.application.after_sales.fulfillment import finalize_after_sales_outbound
    await finalize_after_sales_outbound(
        session,
        document_id=doc["id"],
        actor_id=current_user_id,
    )

    # Sync order status to SHIPPED and trigger order side effects
    await complete_order_use_case.execute(
        order_id=doc["order_id"],
        status_value="SHIPPED",
        changed_by="warehouse-outbound",
        run_external_side_effects=False,
    )

    # Commit all changes atomically (both physical inventory reduction and order status update)
    await session.commit()

    try:
        await complete_order_use_case.run_committed_shipping_side_effects(order_id=doc["order_id"])
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").error(
            "Xuất kho đã commit nhưng tác vụ vận chuyển/thông báo thất bại: %s",
            exc,
        )

    return {"ok": True, "referenceCode": document_no, "status": "COMPLETED"}


async def update_outbound_document_status(
    session: AsyncSession,
    document_no: str,
    *,
    status_value: str,
    cancel_reason: str | None = None,
    current_user_id: UUID | None = None,
    current_role_code: str | None = None,
) -> dict:
    normalized_status = status_value.strip().upper()
    if normalized_status == "COMPLETED":
        return await post_outbound_document(
            session,
            document_no,
            current_user_id,
            current_role_code,
        )

    if normalized_status == "REVERSED":
        _ensure_super_admin_inventory_action(current_role_code, "đảo phiếu xuất kho")
        return await reverse_completed_outbound(
            session,
            document_no,
            current_user_id,
        )

    res = await session.execute(
        text(
            """
            SELECT id, status
            FROM inventory_documents
            WHERE document_no = :document_no AND document_type = 'OUTBOUND'
            FOR UPDATE
            """
        ),
        {"document_no": document_no},
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")
    doc = dict(row)

    if normalized_status == "DRAFT":
        if doc["status"] != "CANCELLED":
            raise HTTPException(status_code=400, detail="Chỉ phiếu xuất đã hủy mới có thể phát hành lại (chuyển về Nháp).")
        order_status = await session.scalar(
            text(
                """
                SELECT o.status
                FROM orders o
                JOIN inventory_documents d ON d.order_id = o.id
                WHERE d.id = :document_id
                FOR UPDATE OF o
                """
            ),
            {"document_id": doc["id"]},
        )
        if order_status not in {"PAID", "PROCESSING"}:
            raise HTTPException(
                status_code=409,
                detail="Chỉ có thể phát hành lại phiếu khi đơn hàng đang chờ xử lý kho.",
            )
        await inventory_repo.update_inventory_outbound_status(
            session,
            document_id=doc["id"],
            status="DRAFT",
            note="Phát hành lại phiếu xuất đã hủy.",
            actor_id=current_user_id,
        )
        await session.commit()
        return {"ok": True, "referenceCode": document_no, "status": "DRAFT"}

    if normalized_status != "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Phiếu xuất kho chỉ hỗ trợ chuyển trạng thái thủ công sang Hoàn tất, Đã hủy hoặc Nháp (phát hành lại).",
        )
    _ensure_super_admin_inventory_action(current_role_code, "hủy phiếu xuất kho")
    reason = (cancel_reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Cần nhập lý do hủy phiếu xuất kho.")

    if doc["status"] == "COMPLETED":
        raise HTTPException(status_code=400, detail="Không thể hủy phiếu xuất kho đã hoàn tất.")
    if doc["status"] == "CANCELLED":
        raise HTTPException(status_code=400, detail="Phiếu xuất kho này đã được hủy trước đó.")

    await inventory_repo.update_inventory_outbound_status(
        session,
        document_id=doc["id"],
        status="CANCELLED",
        note=reason,
        actor_id=current_user_id,
    )
    await session.commit()
    return {"ok": True, "referenceCode": document_no, "status": "CANCELLED"}


async def auto_suggest_outbound_document(
    session: AsyncSession,
    document_no: str,
) -> dict:
    await session.execute(
        text(
            """
            SELECT id
            FROM inventory_documents
            WHERE document_no = :document_no
              AND document_type = 'OUTBOUND'
            FOR UPDATE
            """
        ),
        {"document_no": document_no},
    )
    # Lấy thông tin phiếu
    doc = await inventory_repo.get_inventory_outbound_document(session, document_no)
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")
    if doc["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Chỉ có thể gợi ý kệ xuất khi phiếu xuất ở trạng thái Nháp.")

    lines = await inventory_repo.list_inventory_outbound_lines(session, doc["id"])
    for line in lines:
        product_id = line["productId"]
        variant_id = line["variantId"]
        quantity = int(line["quantity"])
        allocations_data = []
        remaining_quantity = quantity
        candidates = await inventory_repo.list_level_issue_candidates(
            session,
            product_id=product_id,
            variant_id=variant_id,
        )
        for candidate in candidates:
            if remaining_quantity <= 0:
                break
            available_quantity = int(candidate.get("availableQuantity") or 0)
            if available_quantity <= 0:
                continue
            suggested_quantity = min(available_quantity, remaining_quantity)
            allocations_data.append({
                "locationId": str(candidate["locationId"]),
                "locationCode": candidate.get("locationCode"),
                "locationName": candidate.get("locationName"),
                "quantity": suggested_quantity,
                "imeis": [],
                "serialNumbers": [],
            })
            remaining_quantity -= suggested_quantity

        selected_location_id = UUID(allocations_data[0]["locationId"]) if allocations_data else None
        storage_location_code = allocations_data[0]["locationCode"] if allocations_data else None
        storage_location_name = allocations_data[0]["locationName"] if allocations_data else None

        await inventory_repo.update_inventory_outbound_line(
            session,
            line_id=line["id"],
            location_id=selected_location_id,
            approved_quantity=sum(item["quantity"] for item in allocations_data),
            imeis=[],
            serial_numbers=[],
            storage_location_code=storage_location_code,
            storage_location_name=storage_location_name,
            allocations=allocations_data,
        )

    # Automatically calculate and update the outbound document's status based on pick progress
    new_status = await _determine_outbound_status(session, doc["id"])
    if doc["status"] != new_status:
        await inventory_repo.update_inventory_outbound_status(
            session,
            document_id=doc["id"],
            status=new_status,
            actor_id=None,
        )

    await session.commit()
    return {"ok": True, "referenceCode": document_no}


async def reverse_completed_outbound(
    session: AsyncSession,
    document_no: str,
    actor_id: UUID | None = None,
) -> dict:
    from datetime import datetime, timezone
    # 1. Lock the outbound document FOR UPDATE
    res = await session.execute(
        text(
            """
            SELECT id, status, order_id, document_no
            FROM inventory_documents
            WHERE document_no = :document_no AND document_type = 'OUTBOUND'
            FOR UPDATE
            """
        ),
        {"document_no": document_no},
    )
    doc = res.mappings().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu xuất kho.")
    if doc["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail="Chỉ đảo phiếu xuất kho đã hoàn tất.")

    # 2. Get order for update
    from app.infrastructure.database.models import Order
    from app.infrastructure.database.repositories import commerce_repo
    order = await commerce_repo.get_order_for_update(session, doc["order_id"])
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng liên kết.")
    if order.status != "SHIPPED":
        raise HTTPException(
            status_code=409,
            detail="Chỉ có thể đảo phiếu khi đơn hàng đang ở trạng thái Đang giao hàng.",
        )
    if order.payment_status == "PAID":
        raise HTTPException(
            status_code=409,
            detail=(
                "Đơn hàng đã thanh toán không thể hủy bằng thao tác đảo phiếu. "
                "Vui lòng xử lý hoàn hàng và hoàn tiền theo đúng quy trình."
            ),
        )

    # 3. Restock items, restore FIFO lots, and IMEI/serial numbers
    from app.application.commerce.use_cases import CompleteOrderUseCase
    complete_order_use_case = CompleteOrderUseCase(session=session)
    await complete_order_use_case._restock_order_items(order)
    await commerce_repo.close_active_order_reservations(
        session,
        order_id=order.id,
        status="CANCELLED",
    )

    # 4. Update order status to CANCELLED to maintain consistency
    order.status = "CANCELLED"
    order.cancellation_reason = "Đảo phiếu xuất kho đã hoàn tất."
    order.cancelled_at = datetime.now(timezone.utc)
    commerce_repo.save_model(session, order)
    await session.execute(
        text(
            """
            UPDATE payment_transactions
            SET status = 'FAILED',
                failed_at = NOW(),
                raw_response = COALESCE(raw_response, '{}'::jsonb)
                    || jsonb_build_object('failure_message', 'Đơn hàng đã bị hủy khi đảo phiếu xuất kho.')
            WHERE order_id = :order_id
              AND status = 'PENDING'
            """
        ),
        {"order_id": order.id},
    )
    await complete_order_use_case._insert_order_history(
        order=order,
        old_status="SHIPPED",
        new_status="CANCELLED",
        changed_by="warehouse-outbound-reversal",
        note="Đảo phiếu xuất kho đã hoàn tất.",
    )

    # 5. Update outbound document status to REVERSED
    await inventory_repo.update_inventory_outbound_status(
        session,
        document_id=doc["id"],
        status="REVERSED",
        note="Đảo phiếu xuất kho đã hoàn tất.",
        actor_id=actor_id,
    )

    await session.commit()
    return {"ok": True, "referenceCode": document_no, "status": "REVERSED"}
