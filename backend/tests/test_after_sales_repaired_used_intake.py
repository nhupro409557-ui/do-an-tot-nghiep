import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.application.after_sales.identifier_groups import LockedIdentifier, LockedIdentifierGroup
from app.application.after_sales.used_intake import create_repaired_device_used_intake
from app.application.commerce.use_cases.complete_order import CompleteOrderUseCase


def mapping_result(value):
    result = MagicMock()
    result.mappings.return_value.first.return_value = value
    return result


class RepairedDeviceUsedIntakeTest(unittest.IsolatedAsyncioTestCase):
    async def test_creates_received_intake_for_repaired_identifier_group(self) -> None:
        session = AsyncMock()
        identifier_id = uuid4()
        product_id = uuid4()
        variant_id = uuid4()
        request_id = uuid4()
        order_id = uuid4()
        actor_id = uuid4()
        group = LockedIdentifierGroup(
            pair_id=uuid4(),
            imeis=(LockedIdentifier(identifier_id, "309505790056184", "REPAIRED", "IMEI"),),
            serials=(LockedIdentifier(uuid4(), "IP17PCO1TB-008", "REPAIRED", "SERIAL"),),
        )
        session.execute.side_effect = [
            mapping_result({
                "id": identifier_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "value": "309505790056184",
                "kind": "IMEI",
            }),
            mapping_result(None),
            mapping_result({"after_sales_type": "WARRANTY", "after_sales_id": request_id}),
            mapping_result({
                "id": request_id,
                "request_code": "WR-REPAIRED-001",
                "order_id": order_id,
                "user_id": uuid4(),
            }),
            MagicMock(),
        ]
        with patch(
            "app.application.after_sales.used_intake.lock_identifier_group",
            new=AsyncMock(return_value=group),
        ), patch(
            "app.application.after_sales.used_intake.used_product_repo.next_request_code",
            new=AsyncMock(return_value="CU-20260809-0001"),
        ), patch(
            "app.application.after_sales.used_intake.used_product_repo.insert_event",
            new=AsyncMock(),
        ) as insert_event:
            result = await create_repaired_device_used_intake(
                session,
                identifier_id=identifier_id,
                actor_id=actor_id,
            )

        self.assertEqual(result["status"], "RECEIVED")
        self.assertEqual(result["requestCode"], "CU-20260809-0001")
        insert_event.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_rejects_device_that_is_not_fully_repaired(self) -> None:
        session = AsyncMock()
        identifier_id = uuid4()
        group = LockedIdentifierGroup(
            pair_id=None,
            imeis=(LockedIdentifier(identifier_id, "309505790056184", "REPAIR_PENDING", "IMEI"),),
            serials=(),
        )
        session.execute.return_value = mapping_result({
            "id": identifier_id,
            "product_id": uuid4(),
            "variant_id": uuid4(),
            "value": "309505790056184",
            "kind": "IMEI",
        })
        with patch(
            "app.application.after_sales.used_intake.lock_identifier_group",
            new=AsyncMock(return_value=group),
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_repaired_device_used_intake(
                    session,
                    identifier_id=identifier_id,
                    actor_id=uuid4(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("đã sửa xong", raised.exception.detail)

    async def test_rejects_serial_only_device_without_imei(self) -> None:
        session = AsyncMock()
        identifier_id = uuid4()
        group = LockedIdentifierGroup(
            pair_id=None,
            imeis=(),
            serials=(LockedIdentifier(identifier_id, "SERIAL-ONLY-001", "REPAIRED", "SERIAL"),),
        )
        session.execute.return_value = mapping_result({
            "id": identifier_id,
            "product_id": uuid4(),
            "variant_id": uuid4(),
            "value": "SERIAL-ONLY-001",
            "kind": "SERIAL",
        })
        with patch(
            "app.application.after_sales.used_intake.lock_identifier_group",
            new=AsyncMock(return_value=group),
        ):
            with self.assertRaises(HTTPException) as raised:
                await create_repaired_device_used_intake(
                    session,
                    identifier_id=identifier_id,
                    actor_id=uuid4(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("yêu cầu thiết bị có IMEI", raised.exception.detail)
        session.commit.assert_not_awaited()


class RepairedDeviceUsedIntakeMigrationContractTest(unittest.TestCase):
    def test_migration_adds_dedicated_after_sales_source(self) -> None:
        migration = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "109_after_sales_repaired_used_intake.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("AFTER_SALES_REPAIRED", migration)
        self.assertIn("warranty_request_id", migration)
        self.assertIn("used_device_intake_requests_source_type_check", migration)


class AfterSalesOrderReceiptConfirmationTest(unittest.IsolatedAsyncioTestCase):
    async def test_after_sales_order_cannot_complete_without_confirmation(self) -> None:
        session = AsyncMock()
        session.in_transaction = MagicMock(return_value=True)
        order = SimpleNamespace(
            id=uuid4(),
            status="SHIPPED",
            order_purpose="WARRANTY_RETURN",
        )
        with patch(
            "app.application.commerce.use_cases.complete_order.commerce_repo.get_order_for_update",
            new=AsyncMock(return_value=order),
        ):
            with self.assertRaises(HTTPException) as raised:
                await CompleteOrderUseCase(session=session).execute(
                    order_id=order.id,
                    status_value="COMPLETED",
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("xác nhận khách đã nhận máy", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
