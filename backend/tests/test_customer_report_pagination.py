import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from app.infrastructure.database.repositories.reporting.customers import (
    get_customer_report,
)


class _MappingsResult:
    def __init__(self, *, one=None, rows=None) -> None:
        self._one = one
        self._rows = rows or []

    def mappings(self):
        return self

    def one(self):
        return self._one

    def all(self):
        return self._rows


class _ScalarResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self):
        return self.value


class CustomerReportPaginationTest(unittest.IsolatedAsyncioTestCase):
    async def test_page_beyond_end_keeps_total_count(self) -> None:
        session = AsyncMock()
        session.execute.side_effect = [
            _MappingsResult(
                one={
                    "new_customers": 7,
                    "active_customers": 3,
                    "first_time_buyers": 2,
                    "returning_customers": 1,
                }
            ),
            _MappingsResult(rows=[]),
            _ScalarResult(7),
            _MappingsResult(rows=[]),
        ]

        report = await get_customer_report(
            session,
            from_utc=datetime(2026, 7, 1, tzinfo=timezone.utc),
            to_utc=datetime(2026, 8, 1, tzinfo=timezone.utc),
            page=99,
            limit=20,
        )

        self.assertEqual(report["items"], [])
        self.assertEqual(report["total"], 7)
        self.assertEqual(session.execute.await_count, 4)


if __name__ == "__main__":
    unittest.main()
