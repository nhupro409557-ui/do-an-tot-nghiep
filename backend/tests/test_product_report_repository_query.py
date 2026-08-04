import unittest

from app.infrastructure.database.repositories.reporting.products import (
    _product_metrics_cte,
)


class ProductReportRepositoryQueryTest(unittest.TestCase):
    def test_uses_original_catalog_identity_for_used_devices(self) -> None:
        query = " ".join(_product_metrics_cte().split())

        self.assertIn(
            "LEFT JOIN used_devices ud ON ud.id = oi.used_device_id",
            query,
        )
        self.assertIn(
            "COALESCE(oi.product_id, ud.product_id) AS product_id",
            query,
        )
        self.assertIn(
            "COALESCE(oi.variant_id, ud.variant_id) AS variant_id",
            query,
        )
        self.assertIn(
            "COALESCE(pv.sku, p.sku, ud.device_code, 'HANG-CU') AS sku",
            query,
        )

    def test_counts_distinct_orders_per_product(self) -> None:
        query = " ".join(_product_metrics_cte().split())

        self.assertIn(
            "COUNT(DISTINCT order_id) FILTER (WHERE sold_in_period)::integer "
            "AS order_count",
            query,
        )


if __name__ == "__main__":
    unittest.main()
