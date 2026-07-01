import os
from urllib.parse import urlsplit


TEST_DATABASE_PREFIX = "project_test_"
LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}


def database_name(database_url: str) -> str:
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return urlsplit(normalized).path.lstrip("/")


def assert_isolated_test_database_url(database_url: str) -> None:
    """Dừng ngay nếu một bài test ghi dữ liệu đang trỏ nhầm database thật."""
    parsed = urlsplit(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
    name = parsed.path.lstrip("/")
    if not name.startswith(TEST_DATABASE_PREFIX):
        raise RuntimeError(
            "Đã chặn kiểm thử ghi dữ liệu: database phải có tiền tố "
            f"'{TEST_DATABASE_PREFIX}', hiện tại là '{name or '<trống>'}'."
        )
    if (
        parsed.hostname not in LOCAL_DATABASE_HOSTS
        and os.getenv("ALLOW_REMOTE_TEST_DATABASE") != "1"
    ):
        raise RuntimeError(
            "Đã chặn database test từ xa. Chỉ dùng PostgreSQL local hoặc đặt "
            "ALLOW_REMOTE_TEST_DATABASE=1 cho một máy chủ test chuyên biệt."
        )
