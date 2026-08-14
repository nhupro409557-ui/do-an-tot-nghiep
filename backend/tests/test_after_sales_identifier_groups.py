import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.application.after_sales.identifier_groups import lock_identifier_group


def _mapping_result(*rows: dict) -> MagicMock:
    result = MagicMock()
    mappings = result.mappings.return_value
    mappings.first.return_value = rows[0] if rows else None
    mappings.all.return_value = list(rows)
    return result


class AfterSalesIdentifierGroupTest(unittest.IsolatedAsyncioTestCase):
    async def test_imei2_resolves_and_locks_the_whole_physical_device(self) -> None:
        session = AsyncMock()
        product_id = uuid4()
        variant_id = uuid4()
        pair_id = uuid4()
        imei1_id = uuid4()
        imei2_id = uuid4()
        serial_id = uuid4()
        session.execute.side_effect = [
            _mapping_result({
                "id": pair_id,
                "imei1": "111111111111111",
                "imei2": "222222222222222",
                "serial_number": "SERIAL-01",
            }),
            _mapping_result(
                {"id": imei1_id, "identifier": "111111111111111", "status": "SOLD"},
                {"id": imei2_id, "identifier": "222222222222222", "status": "SOLD"},
            ),
            _mapping_result({"id": serial_id, "identifier": "SERIAL-01", "status": "SOLD"}),
        ]

        group = await lock_identifier_group(
            session,
            product_id=product_id,
            variant_id=variant_id,
            imei="222222222222222",
        )

        self.assertEqual(group.pair_id, pair_id)
        self.assertEqual(group.imei_values, ("111111111111111", "222222222222222"))
        self.assertEqual(group.serial_values, ("SERIAL-01",))
        self.assertEqual(session.execute.await_count, 3)
        first_sql = str(session.execute.await_args_list[0].args[0])
        second_sql = str(session.execute.await_args_list[1].args[0])
        self.assertIn("product_identifier_pairs", first_sql)
        self.assertIn("ORDER BY imei", second_sql)

    async def test_unpaired_identifier_is_locked_as_a_single_device(self) -> None:
        session = AsyncMock()
        product_id = uuid4()
        imei_id = uuid4()
        session.execute.side_effect = [
            _mapping_result(),
            _mapping_result({"id": imei_id, "identifier": "333333333333333", "status": "SOLD"}),
        ]

        group = await lock_identifier_group(
            session,
            product_id=product_id,
            variant_id=None,
            imei="333333333333333",
        )

        self.assertIsNone(group.pair_id)
        self.assertEqual(group.imei_values, ("333333333333333",))
        self.assertEqual(group.serial_values, ())


if __name__ == "__main__":
    unittest.main()
