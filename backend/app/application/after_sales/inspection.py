from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.after_sales.schemas import InspectAfterSalesRequest
from app.infrastructure.database.repositories import after_sales_repo, inventory_repo, used_product_repo
from app.application.after_sales.fulfillment import ensure_after_sales_order, ensure_after_sales_outbound
from app.application.after_sales.return_inventory import ensure_return_to_stock_inbound


DEFAULT_EXCHANGE_FEE_RATE = Decimal("0.05")
EXCHANGE_PAYMENT_DUE_HOURS = 24


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


def _requires_replacement_allocation(kind: str, resolution_type: str | None) -> bool:
    return kind == "WARRANTY" and resolution_type == "REPLACEMENT"


def _money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


async def _create_return_disposition_document(
    session: AsyncSession,
    *,
    request: dict,
    items: list[dict],
    disposition: str,
    actor_id: UUID,
    note: str,
) -> UUID:
    is_repair = disposition == "REPAIR"
    location_id = await session.scalar(text("""
        SELECT id FROM inventory_locations
                    WHERE status = 'ACTIVE'
                      AND purpose IN ('DAMAGED', 'WARRANTY', 'QC', 'RETURN')
        ORDER BY CASE purpose
            WHEN 'DAMAGED' THEN 1 WHEN 'WARRANTY' THEN 2
            WHEN 'QC' THEN 3 ELSE 4 END, sort_order, code
        LIMIT 1
    """))
    if not location_id:
        raise HTTPException(status_code=409, detail="Chưa cấu hình vị trí kho cách ly để tiếp nhận hàng sửa chữa/thanh lý.")

    document_id = uuid4()
    request_code = request.get("request_code") or str(request["id"])
    reference_code = f"AS-{'REPAIR' if is_repair else 'SCRAP'}-{request_code}"
    if is_repair:
        await inventory_repo.insert_inventory_internal_hold_document(
            session, document_id=document_id, reference_code=reference_code,
            hold_type="REPAIR", reason="AFTER_SALES_RETURN_REPAIR", note=note, created_by=actor_id,
        )
    else:
        await inventory_repo.insert_inventory_disposal_document(
            session, document_id=document_id, reference_code=reference_code,
            disposition_type="SCRAP", reason="AFTER_SALES_RETURN_SCRAP", note=note,
            partner_name=None, recovery_value=None, created_by=actor_id,
        )
    await session.execute(text("""
        UPDATE inventory_documents
        SET return_request_id = :request_id,
            metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                'afterSalesType', 'RETURN', 'afterSalesRequestId', CAST(CAST(:request_id AS UUID) AS TEXT),
                'orderId', CAST(CAST(:order_id AS UUID) AS TEXT), 'inventoryDisposition', CAST(:disposition AS TEXT),
                'sellableStock', FALSE
            )
        WHERE id = :document_id
    """), {
        "document_id": document_id, "request_id": request["id"],
        "order_id": request.get("order_id"), "disposition": disposition,
    })
    for item in items:
        variant_id = item.get("product_variant_id")
        common = dict(
            session=session, line_id=uuid4(), document_id=document_id,
            product_id=None if variant_id else item.get("product_id"), variant_id=variant_id,
            location_id=location_id, quantity=int(item.get("quantity") or 1),
            reason="Thiết bị hoàn về không đủ điều kiện nhập kho bán mới.", note=note,
            imeis=[str(item["imei"])] if item.get("imei") else [],
            serial_numbers=[str(item["serial_number"])] if item.get("serial_number") else [],
        )
        if is_repair:
            await inventory_repo.insert_inventory_internal_hold_line(hold_type="REPAIR", **common)
        else:
            await inventory_repo.insert_inventory_disposal_line(disposition_type="SCRAP", **common)
    return document_id


def _return_exchange_amounts(request: dict, items: list[dict], payload: InspectAfterSalesRequest) -> dict:
    old_gross = sum(_money(item.get("unit_price_snapshot")) * int(item.get("quantity") or 0) for item in items)
    old_credit_before_deduction = sum(_money(item.get("refundable_amount_snapshot")) for item in items)
    depreciation = min(_money(payload.depreciation_fee), old_credit_before_deduction)
    shipping_deduction = min(
        _money(payload.shipping_deduction),
        max(old_credit_before_deduction - depreciation, Decimal("0")),
    )
    old_credit = max(old_credit_before_deduction - depreciation - shipping_deduction, Decimal("0"))
    exchange_fee = (
        _money(payload.exchange_fee)
        if payload.exchange_fee is not None
        else (old_gross * DEFAULT_EXCHANGE_FEE_RATE).quantize(Decimal("0.01"))
    )
    exchange_shipping_fee = _money(payload.exchange_shipping_fee)
    new_total = _money(request.get("exchange_unit_price_snapshot")) * int(request.get("exchange_quantity") or 1)
    balance = new_total + exchange_fee + exchange_shipping_fee - old_credit
    return {
        "oldCredit": old_credit,
        "exchangeFee": exchange_fee,
        "exchangeShippingFee": exchange_shipping_fee,
        "balanceAmount": balance,
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
    if kind == "WARRANTY" and resolution_type == "REPAIR":
        if payload.repair_channel not in {"INTERNAL", "MANUFACTURER"}:
            raise HTTPException(status_code=400, detail="Vui lòng chọn sửa tại cửa hàng hoặc gửi bảo hành hãng.")
        if payload.repair_channel == "MANUFACTURER" and not (payload.repair_provider_name or "").strip():
            raise HTTPException(status_code=400, detail="Vui lòng nhập tên hãng hoặc trung tâm bảo hành.")
    items = await after_sales_repo.get_request_items(session, kind=kind, request_id=request_id)
    if kind == "RETURN" and resolution_type in {"REFUND", "EXCHANGE"}:
        if not payload.inventory_disposition:
            raise HTTPException(status_code=400, detail="Phải chọn hướng xử lý tồn kho cho thiết bị hoàn về.")
        if payload.inventory_disposition == "USED_INTAKE":
            invalid_items = [item for item in items if int(item.get("quantity") or 0) != 1 or not str(item.get("imei") or "").strip()]
            if invalid_items:
                raise HTTPException(status_code=400, detail="Chuyển sang hàng cũ yêu cầu mỗi dòng có số lượng 1 và IMEI đã được xác nhận.")
            await used_product_repo.create_intakes_from_return(
                session, request=request, items=items, actor_id=actor_id,
            )
        elif payload.inventory_disposition in {"REPAIR", "SCRAP"}:
            await _create_return_disposition_document(
                session, request=request, items=items,
                disposition=payload.inventory_disposition, actor_id=actor_id, note=payload.qc_note,
            )
        elif payload.inventory_disposition == "NEW_STOCK":
            await ensure_return_to_stock_inbound(
                session,
                request=request,
                items=items,
                actor_id=actor_id,
                note=payload.qc_note,
            )
        await session.execute(
            text("UPDATE return_requests SET inventory_disposition = :value WHERE id = :id"),
            {"id": request_id, "value": payload.inventory_disposition},
        )
    exchange_amounts = None
    has_exchange_target = kind == "RETURN" and resolution_type == "EXCHANGE" and request.get("exchange_product_id")
    if has_exchange_target:
        locked = await after_sales_repo.create_exchange_allocation(session, request=request)
        if not locked:
            target = "WAITING_FOR_STOCK"
        else:
            exchange_amounts = _return_exchange_amounts(request, items, payload)
            if exchange_amounts["balanceAmount"] > 0:
                target = "WAITING_FOR_EXCHANGE_PAYMENT"
            else:
                target = "EXCHANGE_PROCESSING"
        if exchange_amounts is None:
            exchange_amounts = _return_exchange_amounts(request, items, payload)
        payment_status = "PENDING" if exchange_amounts["balanceAmount"] > 0 else "NO_PAYMENT_REQUIRED"
        await after_sales_repo.update_return_exchange_financials(
            session,
            request_id=request_id,
            exchange_fee=float(exchange_amounts["exchangeFee"]),
            exchange_shipping_fee=float(exchange_amounts["exchangeShippingFee"]),
            balance_amount=float(exchange_amounts["balanceAmount"]),
            payment_status=payment_status,
            payment_due_hours=EXCHANGE_PAYMENT_DUE_HOURS if payment_status == "PENDING" and target != "WAITING_FOR_STOCK" else None,
        )
    elif _requires_replacement_allocation(kind, resolution_type):
        locked = await after_sales_repo.create_allocations(
            session,
            kind=kind,
            request_id=request_id,
            items=items,
        )
        if not locked:
            target = "WAITING_FOR_STOCK"

    if resolution_type in {"REPLACEMENT", "EXCHANGE"}:
        fulfillment_request = dict(request)
        if payload.return_fulfillment_method:
            fulfillment_request["fulfillment_method"] = payload.return_fulfillment_method
        for field in ("recipient_name", "recipient_phone", "shipping_address", "shipping_provider"):
            value = getattr(payload, field, None)
            if value:
                fulfillment_request[field] = value.strip()
        if exchange_amounts:
            fulfillment_request["balance_amount"] = exchange_amounts["balanceAmount"]
        await ensure_after_sales_order(
            session,
            kind=kind,
            request=fulfillment_request,
            items=items,
        )
        if target in {"REPLACEMENT_APPROVED", "EXCHANGE_PROCESSING"}:
            await ensure_after_sales_outbound(
                session,
                kind=kind,
                request=fulfillment_request,
                items=items,
            )

    await after_sales_repo.update_request_status(
        session,
        kind=kind,
        request_id=request_id,
        status_value=target,
        resolution_type=resolution_type,
        note=payload.qc_note,
        customer_fault=payload.customer_fault,
        depreciation_fee=payload.depreciation_fee if kind == "RETURN" else None,
        repair_channel=payload.repair_channel if kind == "WARRANTY" and resolution_type == "REPAIR" else None,
        repair_provider_name=payload.repair_provider_name if kind == "WARRANTY" and resolution_type == "REPAIR" else None,
        return_fulfillment_method=payload.return_fulfillment_method if kind == "WARRANTY" and resolution_type == "REPLACEMENT" else None,
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
            "shippingDeduction": payload.shipping_deduction if kind == "RETURN" else 0,
            "exchangeFee": float(exchange_amounts["exchangeFee"]) if exchange_amounts else 0,
            "exchangeShippingFee": float(exchange_amounts["exchangeShippingFee"]) if exchange_amounts else 0,
            "balanceAmount": float(exchange_amounts["balanceAmount"]) if exchange_amounts else 0,
            "hasAccessories": request.get("has_accessories"),
            "goodAppearance": request.get("good_appearance"),
            "accountUnlocked": request.get("account_unlocked"),
            "hasVatInvoice": request.get("has_vat_invoice"),
            "inventoryDisposition": payload.inventory_disposition if kind == "RETURN" else None,
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
    if kind == "WARRANTY":
        from app.application.after_sales.service import sync_warranty_imei_status
        await sync_warranty_imei_status(session, items=items, target=target)
        if target in {"WARRANTY_ACCEPTED", "REPAIRING"}:
            for item in items:
                if item.get("used_device_id"):
                    transitioned = await used_product_repo.transition_after_sales_device(
                        session,
                        device_id=item["used_device_id"],
                        target_status="REPAIRING",
                        allowed_statuses={"SOLD", "REPAIRING"},
                        event_type="DEVICE_WARRANTY_QC_ACCEPTED",
                        note=f"QC chấp nhận bảo hành theo yêu cầu {request['request_code']}.",
                        metadata={"requestId": str(request_id), "requestCode": request["request_code"]},
                    )
                    if not transitioned:
                        raise HTTPException(status_code=409, detail="Trạng thái thiết bị cũ không hợp lệ để tiếp nhận sửa chữa bảo hành.")
        elif target == "REJECTED":
            for item in items:
                if item.get("used_device_id"):
                    transitioned = await used_product_repo.transition_after_sales_device(
                        session,
                        device_id=item["used_device_id"],
                        target_status="SOLD",
                        allowed_statuses={"REPAIRING", "SOLD"},
                        event_type="DEVICE_WARRANTY_QC_REJECTED",
                        note=f"QC từ chối bảo hành theo yêu cầu {request['request_code']}.",
                        metadata={"requestId": str(request_id), "requestCode": request["request_code"]},
                    )
                    if not transitioned:
                        raise HTTPException(status_code=409, detail="Trạng thái thiết bị cũ không hợp lệ để kết thúc QC bảo hành.")
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
