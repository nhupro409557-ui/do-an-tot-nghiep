import unittest

from app.application.services.inventory.common import _shape_inventory_level_row


class InventoryOverviewLogicTest(unittest.TestCase):
    def test_physical_and_available_stock_use_location_levels(self) -> None:
        row = _shape_inventory_level_row({
            "productId": "product-1",
            "variantId": "variant-1",
            "variantStock": 45,
            "levelPhysicalStock": 55,
            "levelSellableStock": 50,
            "reservationReservedQuantity": 5,
        })
        self.assertEqual(row["catalogStock"], 45)
        self.assertEqual(row["physicalStock"], 55)
        self.assertEqual(row["sellableStock"], 50)
        self.assertEqual(row["availableStock"], 45)

    def test_catalog_stock_without_location_is_not_physical_stock(self) -> None:
        row = _shape_inventory_level_row({
            "productId": "product-1",
            "variantId": "variant-1",
            "variantStock": 20,
        })
        self.assertEqual(row["catalogStock"], 20)
        self.assertEqual(row["physicalStock"], 0)
        self.assertEqual(row["availableStock"], 0)

    def test_stale_identifiers_are_hidden_when_policy_is_disabled(self) -> None:
        row = _shape_inventory_level_row({
            "productId": "product-1",
            "levelPhysicalStock": 10,
            "levelSellableStock": 10,
            "imeiReservedQuantity": 3,
            "serialReservedQuantity": 2,
            "primaryImei": "123456789012345",
            "supplementalImeiQuantity": 4,
            "inStockImeiQuantity": 10,
            "inStockSerialQuantity": 10,
        })
        self.assertFalse(row["tracksImei"])
        self.assertFalse(row["tracksSerialNumber"])
        self.assertEqual(row["reservedStock"], 0)
        self.assertEqual(row["availableStock"], 10)
        self.assertIsNone(row["primaryImei"])
        self.assertEqual(row["supplementalImei"], 0)
        self.assertEqual(row["imeiSummary"]["inStock"], 0)
        self.assertEqual(row["serialNumberSummary"]["inStock"], 0)


if __name__ == "__main__":
    unittest.main()
