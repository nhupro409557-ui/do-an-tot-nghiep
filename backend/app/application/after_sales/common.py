from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4


def money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def build_request_code(kind: str) -> str:
    prefix = "RT" if kind == "RETURN" else "WR"
    return f"{prefix}{datetime.now(timezone.utc):%Y%m%d%H%M%S}{str(uuid4())[:4].upper()}"
