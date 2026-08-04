import unittest

from app.infrastructure.database.repositories.reporting.revenue import (
    _cogs_period_filter_sql,
)


class RevenueCogsPeriodQueryTest(unittest.TestCase):
    def test_cogs_uses_inventory_movement_time(self) -> None:
        cogs_query = " ".join(_cogs_period_filter_sql().split())

        self.assertIn("ilm.created_at >= :from_utc", cogs_query)
        self.assertIn("ilm.created_at < :to_utc", cogs_query)
        self.assertNotIn("o.completed_at >= :from_utc", cogs_query)


if __name__ == "__main__":
    unittest.main()
