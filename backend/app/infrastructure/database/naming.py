from urllib.parse import urlsplit


TEST_DATABASE_PREFIX = "project_test_"


def database_name(database_url: str) -> str:
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return urlsplit(normalized).path.lstrip("/")
