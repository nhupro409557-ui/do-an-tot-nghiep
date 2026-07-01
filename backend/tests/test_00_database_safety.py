import os

import pytest
from sqlalchemy import text

from app.testing.database_guard import (
    TEST_DATABASE_PREFIX,
    assert_isolated_test_database_url,
)


@pytest.mark.integration
async def test_runner_uses_a_dedicated_test_database(db_session):
    current_database = await db_session.scalar(text("SELECT current_database()"))

    assert current_database == os.environ["TEST_DATABASE_NAME"]
    assert current_database.startswith(TEST_DATABASE_PREFIX)


def test_guard_rejects_a_non_test_database():
    with pytest.raises(RuntimeError, match="Đã chặn kiểm thử ghi dữ liệu"):
        assert_isolated_test_database_url(
            "postgresql+asyncpg://postgres:secret@localhost:5432/postgres"
        )
