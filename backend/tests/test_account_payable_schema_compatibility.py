from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from app.infrastructure.database.repositories import account_payable_repo


class AccountPayableSchemaCompatibilityTest(IsolatedAsyncioTestCase):
    async def test_missing_supplier_payment_columns_are_created_once(self) -> None:
        session = AsyncMock()
        session.scalar = AsyncMock(side_effect=[False, False])
        session.execute = AsyncMock()

        await account_payable_repo.ensure_supplier_payment_hardening_schema(session)

        statements = "\n".join(str(call.args[0]) for call in session.execute.await_args_list)
        self.assertIn("pg_advisory_xact_lock", statements)
        self.assertIn("ADD COLUMN IF NOT EXISTS status", statements)
        self.assertIn("uq_supplier_payments_payable_idempotency", statements)
        self.assertIn("idx_supplier_payments_active", statements)

    async def test_existing_schema_does_not_run_ddl(self) -> None:
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=True)
        session.execute = AsyncMock()

        await account_payable_repo.ensure_supplier_payment_hardening_schema(session)

        session.execute.assert_not_awaited()
