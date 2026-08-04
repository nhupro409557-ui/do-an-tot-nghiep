import unittest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.infrastructure.database.naming import TEST_DATABASE_PREFIX, database_name


class AccountPayableDatabaseConstraintTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        if not database_name(settings.database_url).startswith(TEST_DATABASE_PREFIX):
            self.skipTest("Chỉ kiểm tra ràng buộc công nợ trên database kiểm thử cô lập.")
        self.engine = create_async_engine(settings.database_url, poolclass=NullPool)
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        if not hasattr(self, "session"):
            return
        await self.session.close()
        await self.transaction.rollback()
        await self.connection.close()
        await self.engine.dispose()

    async def test_hardening_migration_installs_idempotency_and_invoice_guards(self) -> None:
        payment_index = await self.session.scalar(text("""
            SELECT to_regclass('public.uq_supplier_payments_payable_idempotency') IS NOT NULL
        """))
        invoice_trigger = await self.session.scalar(text("""
            SELECT EXISTS (
                SELECT 1
                FROM pg_trigger
                WHERE tgname = 'trg_account_payables_supplier_invoice_unique'
                  AND NOT tgisinternal
            )
        """))
        fingerprint_column = await self.session.scalar(text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'supplier_payments'
                  AND column_name = 'request_fingerprint'
            )
        """))

        self.assertTrue(payment_index)
        self.assertTrue(invoice_trigger)
        self.assertTrue(fingerprint_column)

    async def test_active_supplier_invoices_have_no_duplicates(self) -> None:
        duplicate_count = await self.session.scalar(text("""
            SELECT COUNT(*)
            FROM (
                SELECT supplier_id, LOWER(BTRIM(invoice_number))
                FROM account_payables
                WHERE supplier_id IS NOT NULL
                  AND NULLIF(BTRIM(invoice_number), '') IS NOT NULL
                  AND status != 'CANCELLED'
                GROUP BY supplier_id, LOWER(BTRIM(invoice_number))
                HAVING COUNT(*) > 1
            ) duplicates
        """))
        self.assertEqual(int(duplicate_count or 0), 0)


if __name__ == "__main__":
    unittest.main()
