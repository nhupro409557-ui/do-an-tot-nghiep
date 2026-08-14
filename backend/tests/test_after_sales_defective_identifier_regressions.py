import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.routers import admin_after_sales
from app.api.routers.admin_after_sales import defective_disposition_report, defective_identifiers
from app.application.after_sales.identifier_groups import LockedIdentifier, LockedIdentifierGroup
from app.application.after_sales.schemas import ImeiDispositionRequest


class DefectiveIdentifierMigrationContractTest(unittest.TestCase):
    def test_repair_pending_is_allowed_in_disposition_event_constraint(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "107_after_sales_repair_pending_disposition_event.sql"
        )

        migration_sql = migration_path.read_text(encoding="utf-8")

        self.assertIn("ALTER TABLE imei_disposition_events", migration_sql)
        self.assertIn("REPAIR_PENDING", migration_sql)
        self.assertIn("imei_disposition_events_new_status_check", migration_sql)

    def test_repaired_is_allowed_for_identifiers_and_disposition_events(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "108_after_sales_repaired_identifier.sql"
        )

        migration_sql = migration_path.read_text(encoding="utf-8")

        self.assertIn("product_imeis_status_check", migration_sql)
        self.assertIn("product_serial_numbers_status_check", migration_sql)
        self.assertIn("imei_disposition_events_new_status_check", migration_sql)
        self.assertIn("REPAIRED", migration_sql)


class DefectiveIdentifierQueryContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_inventory_cost_lookup_cannot_duplicate_identifier_rows(self) -> None:
        session = AsyncMock()
        session.execute.return_value = []

        result = await defective_identifiers(status_value=None, session=session)

        query = str(session.execute.await_args.args[0])
        self.assertEqual(result, [])
        self.assertNotIn("LEFT JOIN inventory_levels il ON il.variant_id", query)
        self.assertEqual(query.count("LEFT JOIN LATERAL"), 4)
        self.assertGreaterEqual(query.count("LIMIT 1"), 4)
        self.assertEqual(
            query.count("(COALESCE(il.average_unit_cost, 0) > 0) DESC"),
            2,
        )
        self.assertIn(
            "(pi.variant_id IS NOT NULL AND il.product_id IS NULL)",
            query,
        )
        self.assertIn(
            "(ps.variant_id IS NOT NULL AND il.product_id IS NULL)",
            query,
        )
        self.assertIn('AS "deviceKey"', query)
        self.assertIn("product_identifier_pairs", query)

    async def test_disposition_report_counts_each_physical_device_once(self) -> None:
        session = AsyncMock()
        summary_result = MagicMock()
        summary_result.mappings.return_value.first.return_value = {}
        grouped_result = MagicMock()
        grouped_result.mappings.return_value.all.return_value = []
        session.execute.side_effect = [summary_result, grouped_result, grouped_result, grouped_result]

        await defective_disposition_report(session=session)

        for call in session.execute.await_args_list:
            query = str(call.args[0])
            self.assertIn("DISTINCT ON (device_key)", query)
            self.assertIn("product_identifier_pairs", query)

    async def test_disposition_cost_lookup_supports_variant_level_inventory(self) -> None:
        identifier_id = uuid4()
        product_id = uuid4()
        variant_id = uuid4()
        actor_id = uuid4()
        session = AsyncMock()
        query_result = MagicMock()
        query_result.first.return_value = SimpleNamespace(
            id=identifier_id,
            status="DEFECTIVE_RETURNED",
            product_id=product_id,
            variant_id=variant_id,
            location_id=None,
            identifier="309505790056135",
            product_name="Điện thoại kiểm thử",
            on_hand_quantity=1,
            average_unit_cost=40990000,
            location_code="KHO-01",
            location_name="Kho kiểm thử",
            type="IMEI",
        )
        session.execute.return_value = query_result
        group = LockedIdentifierGroup(
            pair_id=None,
            imeis=(
                LockedIdentifier(
                    id=identifier_id,
                    value="309505790056135",
                    status="DEFECTIVE_RETURNED",
                    kind="IMEI",
                ),
            ),
            serials=(),
        )

        with patch.object(admin_after_sales, "lock_identifier_group", AsyncMock(return_value=group)):
            await admin_after_sales.update_disposition(
                identifier_id,
                ImeiDispositionRequest(status="REPAIR_PENDING", reason="Chuyển sang sửa chữa."),
                actor_id,
                session,
            )

        query = str(session.execute.await_args_list[0].args[0])
        self.assertIn("LEFT JOIN LATERAL", query)
        self.assertIn("(pi.variant_id IS NOT NULL AND il.product_id IS NULL)", query)
        self.assertIn("(COALESCE(il.average_unit_cost, 0) > 0) DESC", query)

    async def test_repair_pending_can_be_marked_repaired(self) -> None:
        identifier_id = uuid4()
        product_id = uuid4()
        variant_id = uuid4()
        actor_id = uuid4()
        session = AsyncMock()
        query_result = MagicMock()
        query_result.first.return_value = SimpleNamespace(
            id=identifier_id,
            status="REPAIR_PENDING",
            product_id=product_id,
            variant_id=variant_id,
            location_id=None,
            identifier="309505790056135",
            product_name="Điện thoại kiểm thử",
            on_hand_quantity=1,
            average_unit_cost=40990000,
            location_code="KHO-01",
            location_name="Kho kiểm thử",
            type="IMEI",
        )
        session.execute.return_value = query_result
        group = LockedIdentifierGroup(
            pair_id=None,
            imeis=(
                LockedIdentifier(
                    id=identifier_id,
                    value="309505790056135",
                    status="REPAIR_PENDING",
                    kind="IMEI",
                ),
            ),
            serials=(),
        )

        with patch.object(admin_after_sales, "lock_identifier_group", AsyncMock(return_value=group)):
            result = await admin_after_sales.update_disposition(
                identifier_id,
                ImeiDispositionRequest(status="REPAIRED", reason="Thiết bị đã sửa xong."),
                actor_id,
                session,
            )

        self.assertEqual(result["status"], "REPAIRED")
        session.commit.assert_awaited_once()
        event_queries = [str(call.args[0]) for call in session.execute.await_args_list]
        self.assertTrue(any("INSERT INTO imei_disposition_events" in query for query in event_queries))

    async def test_repair_pending_can_be_disposed_when_repair_failed(self) -> None:
        identifier_id = uuid4()
        product_id = uuid4()
        variant_id = uuid4()
        actor_id = uuid4()
        session = AsyncMock()
        query_result = MagicMock()
        query_result.first.return_value = SimpleNamespace(
            id=identifier_id,
            status="REPAIR_PENDING",
            product_id=product_id,
            variant_id=variant_id,
            location_id=None,
            identifier="309505790056135",
            product_name="Điện thoại kiểm thử",
            on_hand_quantity=1,
            average_unit_cost=40990000,
            location_code="KHO-01",
            location_name="Kho kiểm thử",
            type="IMEI",
        )
        session.execute.return_value = query_result
        group = LockedIdentifierGroup(
            pair_id=None,
            imeis=(LockedIdentifier(identifier_id, "309505790056135", "REPAIR_PENDING", "IMEI"),),
            serials=(),
        )

        with patch.object(admin_after_sales, "lock_identifier_group", AsyncMock(return_value=group)):
            result = await admin_after_sales.update_disposition(
                identifier_id,
                ImeiDispositionRequest(status="SCRAP", reason="Sửa chữa không thành công."),
                actor_id,
                session,
            )

        self.assertEqual(result["status"], "SCRAP")

    async def test_defective_returned_cannot_skip_repair_and_be_marked_repaired(self) -> None:
        identifier_id = uuid4()
        product_id = uuid4()
        variant_id = uuid4()
        actor_id = uuid4()
        session = AsyncMock()
        query_result = MagicMock()
        query_result.first.return_value = SimpleNamespace(
            id=identifier_id,
            status="DEFECTIVE_RETURNED",
            product_id=product_id,
            variant_id=variant_id,
            location_id=None,
            identifier="309505790056135",
            product_name="Điện thoại kiểm thử",
            on_hand_quantity=1,
            average_unit_cost=40990000,
            location_code="KHO-01",
            location_name="Kho kiểm thử",
            type="IMEI",
        )
        session.execute.return_value = query_result
        group = LockedIdentifierGroup(
            pair_id=None,
            imeis=(LockedIdentifier(identifier_id, "309505790056135", "DEFECTIVE_RETURNED", "IMEI"),),
            serials=(),
        )

        with patch.object(admin_after_sales, "lock_identifier_group", AsyncMock(return_value=group)):
            with self.assertRaises(HTTPException) as raised:
                await admin_after_sales.update_disposition(
                    identifier_id,
                    ImeiDispositionRequest(status="REPAIRED", reason="Không được bỏ qua bước sửa chữa."),
                    actor_id,
                    session,
                )

        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
