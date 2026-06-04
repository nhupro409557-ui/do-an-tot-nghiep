import re
import unicodedata
from uuid import UUID, uuid4

from fastapi import HTTPException


DATA_URL_PATTERN = re.compile(r"^data:", re.IGNORECASE)


def slugify(value: str) -> str:
    normalized = value.strip().replace("\u0111", "d").replace("\u0110", "D")
    normalized = unicodedata.normalize("NFD", normalized)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in normalized)
    return "-".join(part for part in slug.split("-") if part) or uuid4().hex[:8]


def sku_code(value: str | None, fallback: str = "SP") -> str:
    slug = slugify(value or fallback)
    parts = [part for part in slug.split("-") if part]
    code = "".join(part[0] for part in parts[:5]).upper()
    return code or fallback


def generate_variant_sku(product_name: str, color_name: str | None, index: int) -> str:
    suffix = sku_code(color_name, f"M{index}")
    return f"{sku_code(product_name)}-{suffix}-{index:02d}"


def generate_inventory_imei(variant_sku: str | None, product_sku: str | None) -> str:
    prefix = re.sub(r"[^A-Z0-9]", "", (variant_sku or product_sku or "IMEI").upper())[:24] or "IMEI"
    return f"{prefix}{uuid4().int % 10_000_000_000:010d}"


def category_path_label(category_id: UUID) -> str:
    return f"c_{str(category_id).replace('-', '')}"


def category_root_id_from_path(path_value: str | None) -> UUID | None:
    if not path_value:
        return None
    label = str(path_value).split(".", 1)[0].strip()
    if not label.startswith("c_"):
        return None
    raw = label[2:]
    if len(raw) != 32:
        return None
    try:
        return UUID(f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}")
    except ValueError:
        return None


def category_branch_cache_key(root_id: UUID | str, stale: bool = False) -> str:
    suffix = "stale" if stale else "active"
    return f"catalog:categories:branch:{root_id}:{suffix}"


def category_is_active(status_value: str, requested_active: bool) -> bool:
    return status_value in {"ACTIVE", "APPROVED"} and requested_active


def category_workflow_status(status_value: str) -> str:
    if status_value == "ACTIVE":
        return "APPROVED"
    if status_value == "INACTIVE":
        return "APPROVED"
    return status_value


def ensure_not_data_url(value: str | None, field_name: str) -> None:
    if value and DATA_URL_PATTERN.match(value):
        raise HTTPException(status_code=400, detail=f"{field_name} must be an uploaded URL, not a Base64 data URL.")


def normalize_status(value: str) -> str:
    return value if value in {"DRAFT", "REVISION_DRAFT", "PENDING", "ACTIVE", "INACTIVE", "ARCHIVED", "MERGED"} else "DRAFT"


def stock_state(quantity: int | None) -> str:
    return "IN_STOCK" if int(quantity or 0) > 0 else "OUT_OF_STOCK"


def display_status(status_value: str | None, quantity: int | None) -> str:
    if status_value == "ACTIVE" and stock_state(quantity) == "OUT_OF_STOCK":
        return "HÃ¡ÂºÂ¿t hÃƒÂ ng"
    labels = {
        "DRAFT": "NhÃƒÂ¡p",
        "PENDING": "ChÃ¡Â»Â duyÃ¡Â»â€¡t",
        "ACTIVE": "Ã„Âang bÃƒÂ¡n",
        "INACTIVE": "TÃ¡ÂºÂ¡m Ã¡ÂºÂ©n",
        "ARCHIVED": "LÃ†Â°u trÃ¡Â»Â¯",
    }
    return labels.get(status_value or "", status_value or "NhÃƒÂ¡p")


def split_relation_tokens(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]
