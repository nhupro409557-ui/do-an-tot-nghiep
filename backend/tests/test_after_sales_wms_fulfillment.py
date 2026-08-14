import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.application.after_sales.return_inventory import (
    RETURN_TO_STOCK_REASON,
    ensure_return_to_stock_inbound,
)
from fastapi import HTTPException

from app.application.after_sales.fulfillment import (
    _replace_after_sales_order_lines,
    ensure_after_sales_outbound,
    handle_after_sales_order_cancelled,
    validate_after_sales_order_reuse,
)
from app.application.after_sales.schemas import ImeiDispositionRequest, UpdateAfterSalesStatusRequest
from app.application.after_sales.service import admin_update_status, list_requests, sync_warranty_imei_status
from app.application.after_sales.transitions import WARRANTY_TRANSITIONS
from app.application.services.inventory.outbounds import create_outbound_document_from_order
from pydantic import ValidationError


class ReturnToStockInboundTest(unittest.IsolatedAsyncioTestCase):
    async def test_existing_document_is_reused(self) -> None:
        session = AsyncMock()
        document_id = uuid4()
        session.scalar.return_value = document_id
        with patch(
            "app.application.after_sales.return_inventory.inventory_repo.insert_inventory_receipt_document",
            new=AsyncMock(),
        ) as insert_document:
            result = await ensure_return_to_stock_inbound(
                session,
                request={"id": uuid4(), "order_id": uuid4(), "request_code": "RT-001"},
                items=[],
                actor_id=uuid4(),
                note="Đã đạt QC.",
            )
        self.assertEqual(result, document_id)
        insert_document.assert_not_awaited()

    async def test_new_stock_creates_draft_receipt_without_mutating_stock(self) -> None:
        session = AsyncMock()
        session.scalar.return_value = None
        location_result = MagicMock()
        location_result.mappings.return_value.first.return_value = {
            "id": uuid4(), "code": "MAIN", "name": "Kho chính"
        }
        session.execute.side_effect = [location_result, MagicMock()]
        item = {
            "product_id": uuid4(), "product_variant_id": uuid4(), "quantity": 1,
            "imei": "123456789012345", "serial_number": "SERIAL-001",
            "unit_price_snapshot": 1000,
        }
        with patch(
            "app.application.after_sales.return_inventory.inventory_repo.insert_inventory_receipt_document",
            new=AsyncMock(),
        ) as insert_document, patch(
            "app.application.after_sales.return_inventory.inventory_repo.insert_inventory_receipt_line",
            new=AsyncMock(),
        ) as insert_line:
            await ensure_return_to_stock_inbound(
                session,
                request={"id": uuid4(), "order_id": uuid4(), "request_code": "RT-002"},
                items=[item], actor_id=uuid4(), note="Thiết bị nguyên vẹn và đạt QC.",
            )
        self.assertEqual(insert_document.await_args.kwargs["status"], "DRAFT")
        self.assertEqual(insert_document.await_args.kwargs["reason"], RETURN_TO_STOCK_REASON)
        self.assertEqual(insert_line.await_args.kwargs["imeis"], ["123456789012345"])


class AfterSalesOutboundTest(unittest.IsolatedAsyncioTestCase):
    async def test_exchange_order_uses_current_product_warranty_column(self) -> None:
        session = AsyncMock()
        product_id = uuid4()
        variant_id = uuid4()
        request_item_id = uuid4()
        target_result = MagicMock()
        target_result.mappings.return_value.first.return_value = {
            "product_id": product_id,
            "variant_id": variant_id,
            "product_name": "Điện thoại đổi mới",
            "warranty_months": 12,
            "quantity": 1,
        }

        async def execute(statement, _params):
            sql = str(statement)
            if "FROM products p" in sql:
                self.assertIn("p.warranty_period", sql)
                self.assertNotIn("p.warranty_months", sql)
                return target_result
            return MagicMock()

        session.execute.side_effect = execute

        await _replace_after_sales_order_lines(
            session,
            order_id=uuid4(),
            kind="RETURN",
            request={
                "exchange_product_id": product_id,
                "exchange_variant_id": variant_id,
                "exchange_quantity": 1,
            },
            items=[{"id": request_item_id}],
        )

        self.assertEqual(session.execute.await_count, 2)

    async def test_outbound_is_draft_document_from_service_order(self) -> None:
        session = AsyncMock()
        order_id = uuid4()
        document_id = uuid4()
        with patch(
            "app.application.after_sales.fulfillment.ensure_after_sales_order",
            new=AsyncMock(return_value=order_id),
        ), patch(
            "app.application.services.inventory.outbounds.create_outbound_document_from_order",
            new=AsyncMock(return_value=document_id),
        ) as create_outbound:
            result = await ensure_after_sales_outbound(
                session,
                kind="WARRANTY",
                request={"id": uuid4(), "request_code": "WR-001"},
                items=[],
            )
        self.assertEqual(result, document_id)
        create_outbound.assert_awaited_once_with(session, order_id)
        session.execute.assert_awaited_once()

    async def test_warranty_return_cannot_create_inventory_outbound(self) -> None:
        session = AsyncMock()
        order = MagicMock()
        order.order_purpose = "WARRANTY_RETURN"
        session.get.return_value = order
        with self.assertRaises(HTTPException) as raised:
            await create_outbound_document_from_order(session, uuid4())
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("không được phép tạo phiếu xuất kho", raised.exception.detail)

    async def test_cancelled_warranty_return_moves_request_back_to_repair_completed(self) -> None:
        session = AsyncMock()
        warranty_request_id = uuid4()
        request_result = MagicMock()
        request_result.mappings.return_value.first.return_value = {
            "status": "RETURNING_TO_CUSTOMER",
            "user_id": uuid4(),
            "request_code": "WR-RETRY",
        }
        session.execute.side_effect = [request_result, MagicMock(), MagicMock()]
        with patch(
            "app.application.after_sales.fulfillment.after_sales_repo.notify",
            new=AsyncMock(),
        ) as notify:
            changed = await handle_after_sales_order_cancelled(
                session,
                order_id=uuid4(),
                order_purpose="WARRANTY_RETURN",
                warranty_request_id=warranty_request_id,
                changed_by="admin-console",
                reason="Đơn vị vận chuyển không nhận giao.",
            )
        self.assertTrue(changed)
        update_sql = str(session.execute.await_args_list[1].args[0])
        self.assertIn("REPAIR_COMPLETED", update_sql)
        notify.assert_awaited_once()


class WarrantyIdentifierLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_replacement_completion_does_not_restore_defective_identifier_group(self) -> None:
        session = AsyncMock()
        with patch(
            "app.application.after_sales.identifier_groups.lock_identifier_group",
            new=AsyncMock(),
        ) as lock_group:
            await sync_warranty_imei_status(
                session,
                items=[
                    {
                        "product_id": uuid4(),
                        "product_variant_id": uuid4(),
                        "imei": "111111111111111",
                        "replacement_imeis": ["222222222222222"],
                    }
                ],
                target="COMPLETED",
            )

        lock_group.assert_not_awaited()


class AfterSalesContractTest(unittest.TestCase):
    def test_repair_delivery_transitions_are_explicit(self) -> None:
        self.assertEqual(WARRANTY_TRANSITIONS["REPAIRING"], {"REPAIR_COMPLETED"})
        self.assertEqual(
            WARRANTY_TRANSITIONS["REPAIR_COMPLETED"],
            {"READY_TO_RETURN", "RETURNING_TO_CUSTOMER"},
        )

    def test_defective_disposition_rejects_legacy_multi_step_target(self) -> None:
        with self.assertRaises(ValidationError):
            ImeiDispositionRequest(status="RTV_PENDING", reason="Chờ trả nhà cung cấp.")

    def test_reinspection_rejects_order_with_completed_outbound(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_after_sales_order_reuse(
                {
                    "status": "PROCESSING",
                    "tracking_code": None,
                    "payment_status": "PAID",
                    "total_amount": 0,
                },
                has_completed_outbound=True,
                has_paid_transaction=False,
            )
        self.assertEqual(raised.exception.status_code, 409)

    def test_zero_value_unshipped_order_can_be_reused(self) -> None:
        validate_after_sales_order_reuse(
            {
                "status": "CANCELLED",
                "tracking_code": None,
                "payment_status": "PAID",
                "total_amount": 0,
            },
            has_completed_outbound=False,
            has_paid_transaction=False,
        )

    def test_cancelled_order_with_shipment_history_cannot_be_reactivated(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_after_sales_order_reuse(
                {
                    "status": "CANCELLED",
                    "tracking_code": None,
                    "payment_status": "PAID",
                    "total_amount": 0,
                },
                has_completed_outbound=False,
                has_paid_transaction=False,
                has_shipment_event=True,
            )
        self.assertEqual(raised.exception.status_code, 409)

    def test_delivery_details_follow_commerce_minimum_lengths(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateAfterSalesStatusRequest(
                status="RETURNING_TO_CUSTOMER",
                recipient_name="A",
                recipient_phone="123",
                shipping_address="Ngắn",
            )


class CustomerAfterSalesDataTest(unittest.IsolatedAsyncioTestCase):
    async def test_customer_response_redacts_internal_repair_fields(self) -> None:
        session = AsyncMock()
        repository_result = {
            "items": [{
                "id": str(uuid4()),
                "adminNote": "Ghi chú nội bộ",
                "qcNote": "Nội dung QC nội bộ",
                "inventoryDisposition": "REPAIR",
                "inventoryDestination": {"id": str(uuid4())},
                "fulfillmentOutbound": {"documentNo": "PX-NOI-BO"},
                "futureInternalField": "Không được tự động lộ ra API khách hàng",
                "repairSummary": {
                    "diagnosis": "Lỗi nguồn",
                    "action": "Thay linh kiện",
                    "parts": "Mainboard",
                    "cost": 1500000,
                },
            }],
            "page": 1,
            "limit": 10,
            "total": 1,
            "totalPages": 1,
        }
        with patch(
            "app.application.after_sales.service.after_sales_repo.list_requests",
            new=AsyncMock(return_value=repository_result),
        ):
            result = await list_requests(
                session,
                kind="WARRANTY",
                user_id=uuid4(),
                status_value=None,
                page=1,
                limit=10,
                sort="-created_at",
            )
        item = result["items"][0]
        self.assertNotIn("adminNote", item)
        self.assertNotIn("qcNote", item)
        self.assertNotIn("inventoryDisposition", item)
        self.assertNotIn("fulfillmentOutbound", item)
        self.assertNotIn("futureInternalField", item)
        self.assertNotIn("cost", item["repairSummary"])
        self.assertNotIn("parts", item["repairSummary"])
        self.assertEqual(item["repairSummary"]["diagnosis"], "Lỗi nguồn")


class WarrantyQcTransitionTest(unittest.IsolatedAsyncioTestCase):
    async def test_manufacturer_repair_requires_provider_name(self) -> None:
        session = AsyncMock()
        request = {
            "id": uuid4(),
            "user_id": uuid4(),
            "request_code": "WR-MANUFACTURER",
            "status": "WARRANTY_ACCEPTED",
            "resolution_type": "REPAIR",
            "repair_channel": None,
        }
        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ):
            with self.assertRaises(HTTPException) as raised:
                await admin_update_status(
                    session,
                    kind="WARRANTY",
                    request_id=request["id"],
                    actor_id=uuid4(),
                    payload=UpdateAfterSalesStatusRequest(
                        status="REPAIRING",
                        repair_channel="MANUFACTURER",
                    ),
                )
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("tên hãng", raised.exception.detail)

    async def test_received_warranty_can_start_qc_without_reinspection_branch(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        actor_id = uuid4()
        user_id = uuid4()
        request = {
            "id": request_id,
            "user_id": user_id,
            "request_code": "WR-START-QC",
            "status": "RECEIVED",
            "resolution_type": None,
        }
        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.update_request_status",
            new=AsyncMock(),
        ) as update_status, patch(
            "app.application.after_sales.service.after_sales_repo.insert_event",
            new=AsyncMock(),
        ) as insert_event, patch(
            "app.application.after_sales.service.after_sales_repo.notify",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.sync_warranty_imei_status",
            new=AsyncMock(),
        ):
            result = await admin_update_status(
                session,
                kind="WARRANTY",
                request_id=request_id,
                actor_id=actor_id,
                payload=UpdateAfterSalesStatusRequest(
                    status="QC_IN_PROGRESS",
                    note="Bắt đầu kiểm tra chất lượng thiết bị.",
                ),
            )

        self.assertEqual(result["status"], "QC_IN_PROGRESS")
        self.assertEqual(update_status.await_args.kwargs["status_value"], "QC_IN_PROGRESS")
        event_metadata = insert_event.await_args.kwargs.get("metadata") or {}
        self.assertNotEqual(event_metadata.get("action"), "REOPEN_QC")
        session.commit.assert_awaited_once()

    async def test_delivery_replacement_cannot_complete_before_delivery(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        request = {
            "id": request_id,
            "user_id": uuid4(),
            "request_code": "WR-WAIT-DELIVERY",
            "status": "REPLACEMENT_PROCESSING",
            "resolution_type": "REPLACEMENT",
        }
        fulfillment_result = MagicMock()
        fulfillment_result.mappings.return_value.first.return_value = {
            "status": "SHIPPED",
            "fulfillment_method": "DELIVERY",
        }
        session.execute.return_value = fulfillment_result
        session.scalar.return_value = True

        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=[]),
        ):
            with self.assertRaises(HTTPException) as raised:
                await admin_update_status(
                    session,
                    kind="WARRANTY",
                    request_id=request_id,
                    actor_id=uuid4(),
                    payload=UpdateAfterSalesStatusRequest(
                        status="COMPLETED",
                        note="Thử hoàn tất hồ sơ trước khi đơn giao máy hoàn thành.",
                        customer_receipt_confirmed=True,
                    ),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("chưa được giao thành công", raised.exception.detail)
        session.commit.assert_not_awaited()

    async def test_store_pickup_after_repair_does_not_require_retyping_repair_details(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        request = {
            "id": request_id,
            "user_id": uuid4(),
            "request_code": "WR-REPAIR-PICKUP",
            "status": "REPAIR_COMPLETED",
            "resolution_type": "REPAIR",
            "repair_channel": "INTERNAL",
        }
        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.update_request_status",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.insert_event",
            new=AsyncMock(),
        ) as insert_event, patch(
            "app.application.after_sales.service.after_sales_repo.notify",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.sync_warranty_imei_status",
            new=AsyncMock(),
        ):
            result = await admin_update_status(
                session,
                kind="WARRANTY",
                request_id=request_id,
                actor_id=uuid4(),
                payload=UpdateAfterSalesStatusRequest(
                    status="READY_TO_RETURN",
                    return_fulfillment_method="STORE_PICKUP",
                ),
            )

        self.assertEqual(result["status"], "READY_TO_RETURN")
        self.assertIsNone(insert_event.await_args.kwargs["metadata"])

    async def test_delivery_after_repair_does_not_require_retyping_repair_details(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        request = {
            "id": request_id,
            "user_id": uuid4(),
            "request_code": "WR-REPAIR-DELIVERY",
            "status": "REPAIR_COMPLETED",
            "resolution_type": "REPAIR",
            "repair_channel": "INTERNAL",
        }
        ensure_return_order = AsyncMock(return_value={"id": str(uuid4())})
        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.update_request_status",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.insert_event",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.notify",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.sync_warranty_imei_status",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.fulfillment.ensure_after_sales_order",
            new=ensure_return_order,
        ):
            result = await admin_update_status(
                session,
                kind="WARRANTY",
                request_id=request_id,
                actor_id=uuid4(),
                payload=UpdateAfterSalesStatusRequest(
                    status="RETURNING_TO_CUSTOMER",
                    return_fulfillment_method="DELIVERY",
                    recipient_name="Khách kiểm thử",
                    recipient_phone="0900000000",
                    shipping_address="Địa chỉ kiểm thử hợp lệ số 123",
                ),
            )

        self.assertEqual(result["status"], "RETURNING_TO_CUSTOMER")
        self.assertEqual(ensure_return_order.await_args.kwargs["order_purpose"], "WARRANTY_RETURN")


class ReturnOldDeviceFinalizationTest(unittest.IsolatedAsyncioTestCase):
    async def test_manual_exchange_completion_finalizes_old_device_disposition(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        actor_id = uuid4()
        request = {
            "id": request_id,
            "user_id": uuid4(),
            "request_code": "RT-OLD-DEVICE",
            "status": "EXCHANGE_PROCESSING",
            "resolution_type": "EXCHANGE",
            "inventory_disposition": "REPAIR",
        }
        items = [{
            "id": uuid4(),
            "product_id": uuid4(),
            "product_variant_id": uuid4(),
            "imei": "309505790056184",
            "replacement_imeis": ["309505790056143"],
            "replacement_serial_numbers": ["IP17PCO1TB-004"],
        }]
        finalize_disposition = AsyncMock(
            return_value={"targetStatus": "REPAIR_PENDING", "updatedIdentifiers": 2}
        )

        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.get_request_items",
            new=AsyncMock(return_value=items),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.update_request_status",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.insert_event",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.service.after_sales_repo.notify",
            new=AsyncMock(),
        ), patch(
            "app.application.after_sales.return_disposition.finalize_returned_identifier_disposition",
            new=finalize_disposition,
        ):
            result = await admin_update_status(
                session,
                kind="RETURN",
                request_id=request_id,
                actor_id=actor_id,
                payload=UpdateAfterSalesStatusRequest(
                    status="COMPLETED",
                    note="Khách đã nhận máy đổi.",
                    customer_receipt_confirmed=True,
                ),
            )

        self.assertEqual(result["status"], "COMPLETED")
        finalize_disposition.assert_awaited_once_with(
            session,
            request_id=request_id,
            actor_id=actor_id,
        )
        session.commit.assert_awaited_once()

    async def test_exchange_completion_requires_customer_receipt_confirmation(self) -> None:
        session = AsyncMock()
        request_id = uuid4()
        request = {
            "id": request_id,
            "user_id": uuid4(),
            "request_code": "RT-RECEIPT-CONFIRM",
            "status": "EXCHANGE_PROCESSING",
            "resolution_type": "EXCHANGE",
            "inventory_disposition": "REPAIR",
        }
        with patch(
            "app.application.after_sales.service.after_sales_repo.get_request_for_update",
            new=AsyncMock(return_value=request),
        ):
            with self.assertRaises(HTTPException) as raised:
                await admin_update_status(
                    session,
                    kind="RETURN",
                    request_id=request_id,
                    actor_id=uuid4(),
                    payload=UpdateAfterSalesStatusRequest(
                        status="COMPLETED",
                        note="Thử hoàn tất khi chưa xác nhận khách nhận máy.",
                    ),
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("xác nhận khách đã nhận máy", raised.exception.detail)
        session.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
