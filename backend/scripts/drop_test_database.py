from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.conftest import (  # noqa: E402
    TEST_DATABASE_PREFIX,
    _assert_safe_admin_server,
    _drop_test_database,
    _load_admin_url,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not args.name.startswith(TEST_DATABASE_PREFIX):
        raise RuntimeError("Chỉ được phép xóa database có tiền tố kiểm thử.")

    admin_url = _load_admin_url()
    _assert_safe_admin_server(admin_url)
    asyncio.run(_drop_test_database(admin_url, args.name))


if __name__ == "__main__":
    main()
