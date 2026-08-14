import asyncio
import unittest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.after_sales.identifier_groups import lock_identifier_group
from app.application.after_sales.return_inventory import ensure_return_to_stock_inbound
from app.config import settings
from app.infrastructure.database.naming import TEST_DATABASE_PREFIX, database_name
from app.infrastructure.database.repositories import after_sales_repo


class AfterSalesIdentifierGroupDatabaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        if not database_name(settings.database_url).startswith(TEST_DATABASE_PREFIX):
            self.skipTest("Chỉ kiểm tra khóa đồng thời trên database kiểm thử cô lập.")
        self.engine = create_async_engine(settings.database_url, poolclass=NullPool)

    async def asyncTearDown(self) -> None:
        if hasattr(self, "engine"):
            await self.engine.dispose()

    async def test_imei1_and_imei2_lock_in_the_same_order_without_deadlock(self) -> None:
        async with self.engine.connect() as connection:
            pair = (
                await connection.execute(
                    text(
                        """
                        SELECT product_id, variant_id, imei1, imei2
                        FROM product_identifier_pairs
                        WHERE imei2 IS NOT NULL
                        ORDER BY id
                        LIMIT 1
                        """
                    )
                )
            ).mappings().first()
        if not pair:
            self.skipTest("Database kiểm thử chưa có thiết bị IMEI kép.")

        async def lock_by_imei(value: str) -> tuple[str, ...]:
            async with self.engine.begin() as connection:
                await connection.execute(text("SET LOCAL lock_timeout = '2s'"))
                session = AsyncSession(bind=connection, expire_on_commit=False)
                try:
                    group = await lock_identifier_group(
                        session,
                        product_id=pair["product_id"],
                        variant_id=pair["variant_id"],
                        imei=value,
                    )
                    await asyncio.sleep(0.05)
                    return group.imei_values
                finally:
                    await session.close()

        imei1_values, imei2_values = await asyncio.wait_for(
            asyncio.gather(lock_by_imei(pair["imei1"]), lock_by_imei(pair["imei2"])),
            timeout=5,
        )
        self.assertEqual(imei1_values, imei2_values)

    async def test_warranty_status_update_accepts_empty_optional_repair_fields(self) -> None:
        async with self.engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                request = (
                    await connection.execute(
                        text("SELECT id, status FROM warranty_requests ORDER BY created_at DESC LIMIT 1")
                    )
                ).mappings().first()
                if not request:
                    self.skipTest("Database kiểm thử chưa có hồ sơ bảo hành.")

                await after_sales_repo.update_request_status(
                    session,
                    kind="WARRANTY",
                    request_id=request["id"],
                    status_value=request["status"],
                    resolution_type=None,
                    note="Kiểm tra cập nhật trạng thái với trường sửa chữa để trống.",
                    customer_fault=False,
                )
                await session.flush()
            finally:
                await session.close()
                await transaction.rollback()

    async def test_return_to_stock_uses_current_inventory_location_schema(self) -> None:
        async with self.engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                request = (
                    await connection.execute(
                        text("SELECT * FROM return_requests ORDER BY created_at DESC LIMIT 1")
                    )
                ).mappings().first()
                if not request:
                    self.skipTest("Database kiểm thử chưa có hồ sơ đổi trả.")
                items = (
                    await connection.execute(
                        text(
                            """
                            SELECT *
                            FROM return_request_items
                            WHERE request_id = :request_id
                            """
                        ),
                        {"request_id": request["id"]},
                    )
                ).mappings().all()
                if not items:
                    self.skipTest("Hồ sơ đổi trả kiểm thử chưa có sản phẩm.")

                document_id = await ensure_return_to_stock_inbound(
                    session,
                    request=dict(request),
                    items=[dict(item) for item in items],
                    actor_id=None,
                    note="Kiểm tra tạo phiếu nhập hàng trả với schema vị trí hiện tại.",
                )
                self.assertIsNotNone(document_id)
                await session.flush()
            finally:
                await session.close()
                await transaction.rollback()


if __name__ == "__main__":
    unittest.main()
