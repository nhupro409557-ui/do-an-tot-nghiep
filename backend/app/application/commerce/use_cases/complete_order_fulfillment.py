from .common import *


def _clean_identifier_values(values: list | None) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text_value = str(value or "").strip()
        if not text_value:
            continue
        if text_value in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Mã định danh bị trùng: {text_value}.")
        cleaned.append(text_value)
        seen.add(text_value)
    return cleaned


class CompleteOrderFulfillmentMixin:
    async def expire_pending_orders(self, *, online_timeout_minutes: int = 15, cod_timeout_hours: int = 24) -> int:
        order_ids = await commerce_repo.list_pending_order_ids_to_expire(
            self._session,
            online_timeout_minutes=online_timeout_minutes,
            cod_timeout_hours=cod_timeout_hours,
        )
        if self._session.in_transaction():
            await self._session.rollback()
        expired_count = 0
        for order_id in order_ids:
            await self.execute(
                order_id=order_id,
                status_value="PAYMENT_FAILED",
                internal_note="Auto cancel overdue pending order.",
                changed_by="system-expirer",
            )
            expired_count += 1
        return expired_count

    async def _mark_payment_refunded(self, order: Order, *, now: datetime) -> None:
        transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
        if not transactions:
            return
        for transaction in transactions:
            if transaction.status == "REFUNDED":
                continue
            if transaction.status in {"PAID", "PENDING"}:
                gateway_result = await self._refund_gateway.refund(
                    provider=transaction.provider,
                    order_code=order.order_code,
                    amount=Decimal(transaction.amount or 0),
                )
                transaction.status = "REFUNDED"
                transaction.raw_response = {
                    **(transaction.raw_response or {}),
                    "refund_marked_at": now.isoformat(),
                    "refund_mode": gateway_result.mode,
                    "refund_provider_ref": gateway_result.provider_ref,
                    "refund_message": gateway_result.message,
                }
                commerce_repo.save_model(self._session, transaction)
        order.payment_status = "REFUNDED"
        order.refunded_at = order.refunded_at or now

    async def _release_or_restock_unshipped_order(self, order: Order, *, reservation_status: str) -> None:
        if await commerce_repo.order_has_inventory_adjustment_reason(
            self._session,
            order_code=order.order_code,
            reason="ORDER_CREATED",
        ):
            await self._restock_order_items(order)
            return
        await commerce_repo.close_active_order_reservations(
            self._session,
            order_id=order.id,
            status=reservation_status,
        )

    async def _ship_order_items(self, order: Order, *, issue_allocations: list | None = None) -> None:
        if await commerce_repo.order_has_inventory_adjustment_reason(
            self._session,
            order_code=order.order_code,
            reason="ORDER_SHIPPED",
        ):
            return
        if await commerce_repo.order_has_inventory_adjustment_reason(
            self._session,
            order_code=order.order_code,
            reason="ORDER_CREATED",
        ):
            await commerce_repo.close_active_order_reservations(
                self._session,
                order_id=order.id,
                status="CONSUMED",
            )
            return

        allocations_by_item_id: dict[str, list[dict]] = {}
        for allocation in issue_allocations or []:
            if isinstance(allocation, dict):
                order_item_id_value = allocation.get("order_item_id") or allocation.get("orderItemId")
                location_id_value = allocation.get("location_id") or allocation.get("locationId")
                quantity_value = allocation.get("quantity")
                imeis_value = allocation.get("imeis")
                serial_numbers_value = allocation.get("serial_numbers") or allocation.get("serialNumbers")
            else:
                order_item_id_value = getattr(allocation, "order_item_id", None)
                location_id_value = getattr(allocation, "location_id", None)
                quantity_value = getattr(allocation, "quantity", None)
                imeis_value = getattr(allocation, "imeis", None)
                serial_numbers_value = getattr(allocation, "serial_numbers", None)
            order_item_id = str(order_item_id_value or "")
            if not order_item_id:
                continue
            allocations_by_item_id.setdefault(order_item_id, []).append(
                {
                    "location_id": location_id_value,
                    "quantity": int(quantity_value or 0),
                    "imeis": imeis_value,
                    "serial_numbers": serial_numbers_value,
                }
            )

        for item in await commerce_repo.list_restock_items(self._session, order_id=order.id, order_code=order.order_code):
            quantity = int(item["quantity"] or 0)
            variant_id = item["order_variant_id"] or item["variant_id"]
            manual_allocations = allocations_by_item_id.get(str(item["id"]), [])
            selected_imeis = _clean_identifier_values(
                [imei for allocation in manual_allocations for imei in (allocation.get("imeis") or [])]
            )
            selected_serials = _clean_identifier_values(
                [serial for allocation in manual_allocations for serial in (allocation.get("serial_numbers") or [])]
            )
            identifiers_supplied = bool(selected_imeis or selected_serials)
            pos_identifier_required = any(
                not allocation.get("location_id") and int(allocation.get("quantity") or 0) == 0
                for allocation in manual_allocations
            )
            if (
                manual_allocations
                and not identifiers_supplied
                and not pos_identifier_required
                and sum(int(allocation.get("quantity") or 0) for allocation in manual_allocations) != quantity
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dòng {item['product_name']}: tổng số lượng xác nhận kệ phải bằng số lượng cần xuất.",
                )
            if identifiers_supplied:
                manual_allocations = []
            if manual_allocations:
                location_ids = [str(allocation.get("location_id") or "") for allocation in manual_allocations]
                if any(not location_id for location_id in location_ids) or len(set(location_ids)) != len(location_ids):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Dòng {item['product_name']}: kệ xác nhận không hợp lệ hoặc bị trùng.",
                    )
            if variant_id:
                inventory_row = await commerce_repo.get_variant_stock_for_update(self._session, variant_id)
                if not inventory_row:
                    continue
                identifier_allocations = await self._resolve_identifier_allocations(
                    product_id=inventory_row["product_id"],
                    variant_id=variant_id,
                    quantity=quantity,
                    product_name=item["product_name"],
                    imeis=selected_imeis,
                    serial_numbers=selected_serials,
                    require_identifiers=pos_identifier_required,
                )
                if identifier_allocations:
                    manual_allocations = identifier_allocations["location_quantities"]
                elif pos_identifier_required:
                    manual_allocations = []
                old_quantity = int(inventory_row["stock_quantity"] or 0)
                new_quantity = old_quantity - quantity
                if new_quantity < 0:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item['product_name']}.")
                await commerce_repo.update_variant_stock(self._session, variant_id=variant_id, quantity=new_quantity)
                try:
                    if manual_allocations:
                        allocations = await commerce_repo.deduct_inventory_levels_from_locations(
                            self._session,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            location_quantities=manual_allocations,
                        )
                    else:
                        allocations = await commerce_repo.deduct_inventory_levels_fifo(
                            self._session,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            quantity=quantity,
                        )
                except ValueError as exc:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
                for allocation in allocations:
                    try:
                        await commerce_repo.consume_inventory_lots_fifo(
                            self._session,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            location_id=allocation["locationId"],
                            quantity=int(allocation["quantity"]),
                            reference_code=order.order_code,
                            order_id=order.id,
                        )
                    except ValueError as exc:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
                    if identifier_allocations:
                        await self._mark_selected_identifiers_sold(
                            order_id=order.id,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            location_id=allocation["locationId"],
                            imeis=identifier_allocations["imeis_by_location"].get(str(allocation["locationId"]), []),
                            serial_numbers=identifier_allocations["serials_by_location"].get(str(allocation["locationId"]), []),
                        )
                    else:
                        await self._mark_fifo_identifiers_sold(
                            order_id=order.id,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            location_id=allocation["locationId"],
                            quantity=int(allocation["quantity"]),
                        )
                    await commerce_repo.insert_inventory_adjustment(
                        self._session,
                        product_id=inventory_row["product_id"],
                        variant_id=variant_id,
                        old_quantity=int(allocation["oldQuantity"]),
                        new_quantity=int(allocation["newQuantity"]),
                        delta=-int(allocation["quantity"]),
                        transaction_type="SALE",
                        reference_code=order.order_code,
                        reason="ORDER_SHIPPED",
                        note=f"Xuất kho khi giao đơn hàng cho {item['product_name']}.",
                        location_code=allocation.get("locationCode"),
                        location_name=allocation.get("locationName"),
                    )
                continue

            if not item["product_id"]:
                continue
            inventory_row = await commerce_repo.get_product_stock_for_update(self._session, item["product_id"])
            if not inventory_row:
                continue
            identifier_allocations = await self._resolve_identifier_allocations(
                product_id=item["product_id"],
                variant_id=None,
                quantity=quantity,
                product_name=item["product_name"],
                imeis=selected_imeis,
                serial_numbers=selected_serials,
                require_identifiers=pos_identifier_required,
            )
            if identifier_allocations:
                manual_allocations = identifier_allocations["location_quantities"]
            elif pos_identifier_required:
                manual_allocations = []
            old_quantity = int(inventory_row["stock_quantity"] or 0)
            new_quantity = old_quantity - quantity
            if new_quantity < 0:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item['product_name']}.")
            await commerce_repo.update_product_stock(self._session, product_id=item["product_id"], quantity=new_quantity)
            try:
                if manual_allocations:
                    allocations = await commerce_repo.deduct_inventory_levels_from_locations(
                        self._session,
                        product_id=item["product_id"],
                        variant_id=None,
                        location_quantities=manual_allocations,
                    )
                else:
                    allocations = await commerce_repo.deduct_inventory_levels_fifo(
                        self._session,
                        product_id=item["product_id"],
                        variant_id=None,
                        quantity=quantity,
                    )
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            for allocation in allocations:
                try:
                    await commerce_repo.consume_inventory_lots_fifo(
                        self._session,
                        product_id=item["product_id"],
                        variant_id=None,
                        location_id=allocation["locationId"],
                        quantity=int(allocation["quantity"]),
                        reference_code=order.order_code,
                        order_id=order.id,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
                if identifier_allocations:
                    await self._mark_selected_identifiers_sold(
                        order_id=order.id,
                        product_id=item["product_id"],
                        variant_id=None,
                        location_id=allocation["locationId"],
                        imeis=identifier_allocations["imeis_by_location"].get(str(allocation["locationId"]), []),
                        serial_numbers=identifier_allocations["serials_by_location"].get(str(allocation["locationId"]), []),
                    )
                else:
                    await self._mark_fifo_identifiers_sold(
                        order_id=order.id,
                        product_id=item["product_id"],
                        variant_id=None,
                        location_id=allocation["locationId"],
                        quantity=int(allocation["quantity"]),
                    )
                await commerce_repo.insert_inventory_adjustment(
                    self._session,
                    product_id=item["product_id"],
                    variant_id=None,
                    old_quantity=int(allocation["oldQuantity"]),
                    new_quantity=int(allocation["newQuantity"]),
                    delta=-int(allocation["quantity"]),
                    transaction_type="SALE",
                    reference_code=order.order_code,
                    reason="ORDER_SHIPPED",
                    note=f"Xuất kho khi giao đơn hàng cho {item['product_name']}.",
                    location_code=allocation.get("locationCode"),
                    location_name=allocation.get("locationName"),
                )

        await commerce_repo.close_active_order_reservations(
            self._session,
            order_id=order.id,
            status="CONSUMED",
        )

    async def _resolve_identifier_allocations(
        self,
        *,
        product_id: UUID,
        variant_id: UUID | None,
        quantity: int,
        product_name: str,
        imeis: list[str],
        serial_numbers: list[str],
        require_identifiers: bool,
    ) -> dict | None:
        imei_stock_count = int(await self._session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM product_imeis
                WHERE product_id = :product_id
                  AND variant_id IS NOT DISTINCT FROM :variant_id
                  AND status = 'IN_STOCK'
                """
            ),
            {"product_id": product_id, "variant_id": variant_id},
        ) or 0)
        serial_stock_count = int(await self._session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM product_serial_numbers
                WHERE product_id = :product_id
                  AND variant_id IS NOT DISTINCT FROM :variant_id
                  AND status = 'IN_STOCK'
                """
            ),
            {"product_id": product_id, "variant_id": variant_id},
        ) or 0)

        if not (require_identifiers or imeis or serial_numbers):
            return None
        if imei_stock_count > 0 and len(imeis) != quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dòng {product_name}: vui lòng quét đúng {quantity} IMEI trước khi thanh toán POS.",
            )
        if serial_stock_count > 0 and len(serial_numbers) != quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dòng {product_name}: vui lòng quét đúng {quantity} serial trước khi thanh toán POS.",
            )
        if len(imeis) > quantity or len(serial_numbers) > quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dòng {product_name}: số mã định danh vượt quá số lượng cần bán.",
            )
        if not imeis and not serial_numbers:
            return None

        quantities_by_location: dict[str, int] = {}
        imeis_by_location: dict[str, list[str]] = {}
        serials_by_location: dict[str, list[str]] = {}

        if imeis:
            imei_rows = (await self._session.execute(
                text(
                    """
                    SELECT imei, location_id
                    FROM product_imeis
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND imei = ANY(CAST(:imeis AS VARCHAR[]))
                      AND status = 'IN_STOCK'
                    FOR UPDATE
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id, "imeis": imeis},
            )).mappings().all()
            if len(imei_rows) != len(imeis):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Dòng {product_name}: IMEI không tồn tại trong kho hoặc không còn sẵn sàng.",
                )
            for row in imei_rows:
                if not row["location_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Dòng {product_name}: IMEI {row['imei']} chưa có vị trí kệ.",
                    )
                location_key = str(row["location_id"])
                imeis_by_location.setdefault(location_key, []).append(str(row["imei"]))
                quantities_by_location[location_key] = max(quantities_by_location.get(location_key, 0), len(imeis_by_location[location_key]))

        if serial_numbers:
            serial_rows = (await self._session.execute(
                text(
                    """
                    SELECT serial_number, location_id
                    FROM product_serial_numbers
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND serial_number = ANY(CAST(:serial_numbers AS VARCHAR[]))
                      AND status = 'IN_STOCK'
                    FOR UPDATE
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id, "serial_numbers": serial_numbers},
            )).mappings().all()
            if len(serial_rows) != len(serial_numbers):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Dòng {product_name}: serial không tồn tại trong kho hoặc không còn sẵn sàng.",
                )
            for row in serial_rows:
                if not row["location_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Dòng {product_name}: serial {row['serial_number']} chưa có vị trí kệ.",
                    )
                location_key = str(row["location_id"])
                serials_by_location.setdefault(location_key, []).append(str(row["serial_number"]))
                quantities_by_location[location_key] = max(
                    quantities_by_location.get(location_key, 0),
                    len(serials_by_location[location_key]),
                )

        total_quantity = sum(quantities_by_location.values())
        if total_quantity != quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dòng {product_name}: số lượng mã theo kệ ({total_quantity}) không khớp số lượng cần bán ({quantity}).",
            )

        return {
            "location_quantities": [
                {"location_id": location_id, "quantity": location_quantity}
                for location_id, location_quantity in quantities_by_location.items()
            ],
            "imeis_by_location": imeis_by_location,
            "serials_by_location": serials_by_location,
        }

    async def _mark_selected_identifiers_sold(
        self,
        *,
        order_id: UUID,
        product_id: UUID,
        variant_id: UUID | None,
        location_id: UUID,
        imeis: list[str],
        serial_numbers: list[str],
    ) -> None:
        if imeis:
            result = await self._session.execute(
                text(
                    """
                    UPDATE product_imeis
                    SET status = 'SOLD', sold_at = NOW(), sold_order_id = :order_id, updated_at = NOW()
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND location_id = :location_id
                      AND imei = ANY(CAST(:imeis AS VARCHAR[]))
                      AND status = 'IN_STOCK'
                    """
                ),
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "location_id": location_id,
                    "imeis": imeis,
                },
            )
            if result.rowcount != len(imeis):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Không thể cập nhật đủ IMEI đã quét.")
        if serial_numbers:
            result = await self._session.execute(
                text(
                    """
                    UPDATE product_serial_numbers
                    SET status = 'SOLD',
                        sold_at = NOW(),
                        service_payload = COALESCE(service_payload, '{}'::jsonb)
                            || jsonb_build_object('soldOrderId', CAST(:order_id AS TEXT)),
                        updated_at = NOW()
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND location_id = :location_id
                      AND serial_number = ANY(CAST(:serial_numbers AS VARCHAR[]))
                      AND status = 'IN_STOCK'
                    """
                ),
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "location_id": location_id,
                    "serial_numbers": serial_numbers,
                },
            )
            if result.rowcount != len(serial_numbers):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Không thể cập nhật đủ serial đã quét.")

    async def _mark_fifo_identifiers_sold(
        self,
        *,
        order_id: UUID,
        product_id: UUID,
        variant_id: UUID | None,
        location_id: UUID,
        quantity: int,
    ) -> None:
        await self._session.execute(
            text(
                """
                UPDATE product_imeis
                SET status = 'SOLD', sold_at = NOW(), sold_order_id = :order_id, updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM product_imeis
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND location_id = :location_id
                      AND status = 'IN_STOCK'
                    ORDER BY received_at ASC
                    LIMIT :quantity
                    FOR UPDATE
                )
                """
            ),
            {
                "order_id": order_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "quantity": quantity,
            },
        )
        await self._session.execute(
            text(
                """
                UPDATE product_serial_numbers
                SET status = 'SOLD',
                    sold_at = NOW(),
                    service_payload = COALESCE(service_payload, '{}'::jsonb)
                        || jsonb_build_object('soldOrderId', CAST(:order_id AS TEXT)),
                    updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM product_serial_numbers
                    WHERE product_id = :product_id
                      AND variant_id IS NOT DISTINCT FROM :variant_id
                      AND location_id = :location_id
                      AND status = 'IN_STOCK'
                    ORDER BY received_at ASC NULLS LAST, created_at ASC
                    LIMIT :quantity
                    FOR UPDATE
                )
                """
            ),
            {
                "order_id": order_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "quantity": quantity,
            },
        )

    async def _restock_order_items(self, order: Order) -> None:
        for item in await commerce_repo.list_restock_items(self._session, order_id=order.id, order_code=order.order_code):
            quantity = int(item["quantity"] or 0)
            variant_id = item["order_variant_id"] or item["variant_id"]
            if variant_id:
                inventory_row = await commerce_repo.get_variant_stock_for_update(self._session, variant_id)
                if not inventory_row:
                    continue
                old_quantity = int(inventory_row["stock_quantity"] or 0)
                new_quantity = old_quantity + quantity
                await commerce_repo.update_variant_stock(self._session, variant_id=variant_id, quantity=new_quantity)
                await commerce_repo.insert_inventory_adjustment(
                    self._session,
                    product_id=inventory_row["product_id"],
                    variant_id=variant_id,
                    old_quantity=old_quantity,
                    new_quantity=new_quantity,
                    delta=quantity,
                    transaction_type="RETURN",
                    reference_code=order.order_code,
                    reason="ORDER_CANCELLED_RESTOCK",
                    note=f"Restock after cancelling order for {item['product_name']}.",
                )
                continue

            if not item["product_id"]:
                continue
            inventory_row = await commerce_repo.get_product_stock_for_update(self._session, item["product_id"])
            if not inventory_row:
                continue
            old_quantity = int(inventory_row["stock_quantity"] or 0)
            new_quantity = old_quantity + quantity
            await commerce_repo.update_product_stock(self._session, product_id=item["product_id"], quantity=new_quantity)
            await commerce_repo.insert_inventory_adjustment(
                self._session,
                product_id=item["product_id"],
                variant_id=None,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                delta=quantity,
                transaction_type="RETURN",
                reference_code=order.order_code,
                reason="ORDER_CANCELLED_RESTOCK",
                note=f"Restock after cancelling order for {item['product_name']}.",
            )
        # Giải phóng các IMEI liên quan đến đơn hàng này về trạng thái sẵn sàng
        await self._session.execute(
            text(
                """
                UPDATE product_imeis
                SET status = 'IN_STOCK', sold_at = NULL, sold_order_id = NULL, updated_at = NOW()
                WHERE sold_order_id = :order_id AND status = 'SOLD'
                """
            ),
            {"order_id": order.id},
        )

    def _send_order_status_email(self, *, order: Order, user: User | None) -> None:
        if not user or not user.email or not settings.smtp_username or not settings.smtp_password:
            return
        sender = settings.smtp_from_email or settings.smtp_username
        status_label = ORDER_STATUS_EMAIL_LABELS.get(order.status, order.status)
        recipient_name = user.full_name or order.recipient_name or user.email
        subject = f"Cập nhật đơn hàng {order.order_code} - {status_label}"
        plain_lines = [
            f"Xin chào {recipient_name},",
            "",
            f"Đơn hàng {order.order_code} của bạn vừa được cập nhật sang trạng thái: {status_label}.",
            f"Tổng thanh toán: {Decimal(order.total_amount or 0):,.0f} VND.",
            f"Phương thức thanh toán: {order.payment_method}.",
        ]
        if order.tracking_code:
            plain_lines.append(f"Mã vận đơn: {order.tracking_code}")
        if order.shipping_provider:
            plain_lines.append(f"Đơn vị vận chuyển: {order.shipping_provider}")
        if order.status == "CANCELLED" and order.cancellation_reason:
            plain_lines.append(f"Lý do hủy: {order.cancellation_reason}")
        plain_lines.extend(["", "Cảm ơn bạn đã mua sắm cùng ElectroMart Việt Nam."])

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = user.email
        message.set_content("\n".join(plain_lines))
        message.add_alternative(
            f"""
            <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
              <h2 style="color:#d70018">Cập nhật đơn hàng {order.order_code}</h2>
              <p>Xin chào <strong>{recipient_name}</strong>,</p>
              <p>Đơn hàng của bạn vừa được cập nhật sang trạng thái <strong>{status_label}</strong>.</p>
              <p><strong>Tổng thanh toán:</strong> {Decimal(order.total_amount or 0):,.0f} VND</p>
              <p><strong>Thanh toán:</strong> {order.payment_method}</p>
              {f'<p><strong>Đơn vị vận chuyển:</strong> {order.shipping_provider}</p>' if order.shipping_provider else ''}
              {f'<p><strong>Mã vận đơn:</strong> {order.tracking_code}</p>' if order.tracking_code else ''}
              {f'<p><strong>Lý do hủy:</strong> {order.cancellation_reason}</p>' if order.status == 'CANCELLED' and order.cancellation_reason else ''}
              <p style="margin-top:16px">Cảm ơn bạn đã mua sắm cùng ElectroMart Việt Nam.</p>
            </div>
            """,
            subtype="html",
        )
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except Exception:
            return
