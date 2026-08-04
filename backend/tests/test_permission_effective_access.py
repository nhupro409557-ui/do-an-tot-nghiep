import unittest

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.infrastructure.database.repositories import auth_repo


class EffectivePermissionIntegrationTest(unittest.IsolatedAsyncioTestCase):
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

    async def _staff_user_id(self):
        return (await self.session.execute(text("""
            SELECT u.id FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE r.code = 'STAFF_ADMIN' AND u.status = 'ACTIVE'
            LIMIT 1
        """))).scalar_one_or_none()

    async def test_role_grant_and_user_grant_are_effective(self) -> None:
        user_id = await self._staff_user_id()
        if not user_id:
            self.skipTest("Chưa có tài khoản Staff Admin đang hoạt động để kiểm thử.")

        await self.session.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT u.role_id, p.id FROM users u CROSS JOIN permissions p
            WHERE u.id = :user_id AND p.code = 'service:read'
            ON CONFLICT DO NOTHING
        """), {"user_id": user_id})
        await self.session.execute(text("""
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT :user_id, id FROM permissions WHERE code = 'flash_sale:create'
            ON CONFLICT DO NOTHING
        """), {"user_id": user_id})

        effective = set(await auth_repo.list_permissions_for_user(self.session, user_id))
        self.assertIn("service:read", effective)
        self.assertIn("flash_sale:create", effective)

    async def test_user_deny_overrides_role_and_direct_grants(self) -> None:
        user_id = await self._staff_user_id()
        if not user_id:
            self.skipTest("Chưa có tài khoản Staff Admin đang hoạt động để kiểm thử.")

        await self.session.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT u.role_id, p.id FROM users u CROSS JOIN permissions p
            WHERE u.id = :user_id AND p.code = 'service:update'
            ON CONFLICT DO NOTHING
        """), {"user_id": user_id})
        await self.session.execute(text("""
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT :user_id, id FROM permissions WHERE code = 'service:update'
            ON CONFLICT DO NOTHING
        """), {"user_id": user_id})
        await self.session.execute(text("""
            INSERT INTO user_permission_denials (user_id, permission_id)
            SELECT :user_id, id FROM permissions WHERE code = 'service:update'
            ON CONFLICT DO NOTHING
        """), {"user_id": user_id})

        effective = set(await auth_repo.list_permissions_for_user(self.session, user_id))
        self.assertNotIn("service:update", effective)

    async def test_dedicated_service_and_flash_sale_permissions_exist(self) -> None:
        expected = {
            "service:read", "service:create", "service:update", "service:delete",
            "flash_sale:read", "flash_sale:create", "flash_sale:update", "flash_sale:delete",
        }
        actual = set((await self.session.execute(text("""
            SELECT code FROM permissions
            WHERE module IN ('service', 'flash_sale')
        """))).scalars().all())
        self.assertTrue(expected.issubset(actual))

    async def test_super_admin_has_every_registered_permission(self) -> None:
        all_codes = set(await auth_repo.list_all_permission_codes(self.session))
        self.assertIn("service:delete", all_codes)
        self.assertIn("flash_sale:delete", all_codes)


if __name__ == "__main__":
    unittest.main()
