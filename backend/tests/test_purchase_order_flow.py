import unittest
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.database.repositories import purchase_order_repo
from app.application.services.inventory.receipt_posting import _aggregate_purchase_receipts
from app.config import settings


class PurchaseOrderFlowIntegrationTest(unittest.IsolatedAsyncioTestCase):
    def test_aggregate_receipt_allocations_by_purchase_order_line(self) -> None:
        line_id = uuid4()
        result = _aggregate_purchase_receipts([
            {"purchaseOrderLineId": line_id, "receivedQuantity": 3},
            {"purchaseOrderLineId": line_id, "receivedQuantity": 2},
            {"purchaseOrderLineId": None, "receivedQuantity": 7},
        ])
        self.assertEqual(result, [{"lineId": str(line_id), "quantity": 5}])

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(settings.database_url, poolclass=NullPool)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.session.close()
        await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def test_receive_two_batches_then_reverse(self) -> None:
        source = (await self.session.execute(text("""
            SELECT s.id AS supplier_id, p.id AS product_id, pv.id AS variant_id
            FROM suppliers s
            CROSS JOIN products p
            JOIN product_variants pv ON pv.product_id = p.id
            WHERE COALESCE(s.is_deleted, FALSE) = FALSE
              AND p.status = 'ACTIVE'
              AND pv.deleted_at IS NULL
            LIMIT 1
        """))).mappings().first()
        if not source:
            self.skipTest("Database kiểm thử chưa có nhà cung cấp và biến thể sản phẩm hoạt động.")

        order_id = uuid4()
        line_id = uuid4()
        await purchase_order_repo.insert_purchase_order(
            self.session,
            {
                "id": order_id,
                "code": f"PO-TEST-{str(order_id)[:8]}",
                "supplier_id": source["supplier_id"],
                "expected_date": None,
                "note": "Kiểm thử tích hợp tự động",
                "discount_amount": 10000,
                "shipping_fee": 20000,
                "created_by": None,
            },
            [{
                "id": line_id,
                "purchase_order_id": order_id,
                "product_id": source["product_id"],
                "variant_id": source["variant_id"],
                "quantity": 10,
                "unit_cost": 100000,
                "note": None,
            }],
        )
        await purchase_order_repo.update_purchase_order_status(self.session, order_id, "APPROVED", None)

        first_status = await purchase_order_repo.receive_purchase_order_lines(
            self.session, order_id, [{"lineId": line_id, "quantity": 4}]
        )
        self.assertEqual(first_status, "PARTIALLY_RECEIVED")
        first = await purchase_order_repo.get_purchase_order(self.session, order_id)
        self.assertEqual(first["lines"][0]["receivedQuantity"], 4)
        self.assertEqual(first["lines"][0]["remainingQuantity"], 6)

        second_status = await purchase_order_repo.receive_purchase_order_lines(
            self.session, order_id, [{"lineId": line_id, "quantity": 6}]
        )
        self.assertEqual(second_status, "COMPLETED")

        reversed_status = await purchase_order_repo.reverse_purchase_order_lines(
            self.session, order_id, [{"lineId": line_id, "quantity": 6}]
        )
        self.assertEqual(reversed_status, "PARTIALLY_RECEIVED")
        final = await purchase_order_repo.get_purchase_order(self.session, order_id)
        self.assertEqual(final["lines"][0]["receivedQuantity"], 4)
        self.assertEqual(final["lines"][0]["remainingQuantity"], 6)

    async def test_reject_receive_over_remaining_quantity(self) -> None:
        source = (await self.session.execute(text("""
            SELECT s.id AS supplier_id, p.id AS product_id, pv.id AS variant_id
            FROM suppliers s CROSS JOIN products p
            JOIN product_variants pv ON pv.product_id = p.id
            WHERE COALESCE(s.is_deleted, FALSE) = FALSE AND p.status = 'ACTIVE' AND pv.deleted_at IS NULL
            LIMIT 1
        """))).mappings().first()
        if not source:
            self.skipTest("Database kiểm thử chưa có dữ liệu danh mục cần thiết.")
        order_id, line_id = uuid4(), uuid4()
        await purchase_order_repo.insert_purchase_order(self.session, {
            "id": order_id, "code": f"PO-LIMIT-{str(order_id)[:8]}", "supplier_id": source["supplier_id"],
            "expected_date": None, "note": None, "discount_amount": 0, "shipping_fee": 0, "created_by": None,
        }, [{"id": line_id, "purchase_order_id": order_id, "product_id": source["product_id"],
             "variant_id": source["variant_id"], "quantity": 2, "unit_cost": 100000, "note": None}])
        with self.assertRaisesRegex(ValueError, "vượt quá"):
            await purchase_order_repo.receive_purchase_order_lines(
                self.session, order_id, [{"lineId": line_id, "quantity": 3}]
            )


if __name__ == "__main__":
    unittest.main()
