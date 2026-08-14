import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai.intent_router import normalize_text


PLANNABLE_PRODUCT_INTENTS = {
    "PRODUCT_SEARCH",
    "PRODUCT_RECOMMENDATION",
    "PRODUCT_COMPARISON",
    "PRICE_AND_PROMOTION",
    "STOCK_AVAILABILITY",
    "PRODUCT_REVIEW",
}

PlannerStep = Literal[
    "search_products",
    "get_product_details",
    "get_variant_stock",
    "get_active_promotions",
    "compare_products",
]


class ProductQueryConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["PHONE", "LAPTOP", "TABLET", "ACCESSORY"] | None = None
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    colors: list[str] = Field(default_factory=list, max_length=5)
    storage: list[str] = Field(default_factory=list, max_length=5)
    ram: list[str] = Field(default_factory=list, max_length=5)
    priorities: list[str] = Field(default_factory=list, max_length=8)
    require_in_stock: bool = False


class ProductQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_intent: str
    intents: list[str] = Field(min_length=1, max_length=8)
    constraints: ProductQueryConstraints
    steps: list[PlannerStep] = Field(min_length=1, max_length=8)
    has_explicit_product_pair: bool = False
    can_auto_resolve: bool = False
    needs_clarification: bool = False
    confidence: float = Field(ge=0, le=1)


COLOR_TERMS = {
    "den": "Đen",
    "trang": "Trắng",
    "xanh": "Xanh",
    "do": "Đỏ",
    "vang": "Vàng",
    "tim": "Tím",
    "hong": "Hồng",
    "xam": "Xám",
    "bac": "Bạc",
    "cam": "Cam",
    "nau": "Nâu",
}

PRIORITY_TERMS = {
    "battery": ("pin", "dung luong pin", "thoi luong pin"),
    "camera": ("camera", "chup anh", "quay video"),
    "performance": ("hieu nang", "choi game", "gaming", "chip", "manh hon", "muot"),
    "display": ("man hinh", "tan so quet", "do sang"),
    "charging": ("sac nhanh", "toc do sac"),
    "price": ("gia tot", "re hon", "tiet kiem", "gia re"),
    "durability": ("ben hon", "chong nuoc", "do ben"),
}

COMPARISON_TERMS = (
    "so sanh",
    "doi chieu",
    "khac nhau",
    "mau nao tot hon",
    "may nao tot hon",
    "con nao tot hon",
    "cai nao tot hon",
    "nen chon mau nao",
    "nen mua may nao",
)

STOCK_TERMS = (
    "con hang",
    "co san",
    "ton kho",
    "het hang",
    "con mau",
    "phien ban nao con",
)

PROMOTION_TERMS = ("khuyen mai", "giam gia", "uu dai", "voucher", "sale")

PRODUCT_TOKEN_PATTERN = re.compile(
    r"\b(?:iphone|ipad|macbook|galaxy|samsung|oppo|xiaomi|redmi|realme|vivo|honor|"
    r"tecno|meizu|asus|acer|dell|hp|lenovo)\b",
)


def _price_constraints(normalized: str) -> tuple[int | None, int | None]:
    match = re.search(
        r"(?:(duoi|toi da|khong qua|tren|hon|tu|toi thieu|khoang|tam)\s*)?"
        r"(\d+(?:[.,]\d+)?)\s*(trieu|tr|cu)\b",
        normalized,
    )
    if not match:
        return None, None
    qualifier = match.group(1) or "khoang"
    value = int(float(match.group(2).replace(",", ".")) * 1_000_000)
    if qualifier in {"duoi", "toi da", "khong qua"}:
        return None, value
    if qualifier in {"tren", "hon", "tu", "toi thieu"}:
        return value, None
    return int(value * 0.9), int(value * 1.1)


def _category(normalized: str) -> str | None:
    if any(term in normalized for term in ("dien thoai", "smartphone", "iphone", "galaxy")):
        return "PHONE"
    if any(term in normalized for term in ("laptop", "may tinh xach tay", "macbook")):
        return "LAPTOP"
    if any(term in normalized for term in ("may tinh bang", "tablet", "ipad")):
        return "TABLET"
    if any(term in normalized for term in ("phu kien", "tai nghe", "cu sac", "cap sac", "op lung")):
        return "ACCESSORY"
    return None


def _unique_matches(normalized: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    return [key for key, terms in mapping.items() if any(term in normalized for term in terms)]


def _requested_colors(normalized: str, original: str) -> list[str]:
    colors: list[str] = []
    original_lower = original.lower()
    for term, display in COLOR_TERMS.items():
        if term == "do" and "mẫu đó" in original_lower and "màu đỏ" not in original_lower:
            continue
        patterns = (
            rf"\b(?:mau|ban mau|phien ban)\s+{re.escape(term)}\b",
            rf"\b(?:con|co san)\s+(?:mau\s+)?{re.escape(term)}\b",
        )
        if any(re.search(pattern, normalized) for pattern in patterns):
            colors.append(display)
    return colors


def _has_explicit_pair(normalized: str) -> bool:
    for connector in re.finditer(r"\b(?:voi|vs|va)\b", normalized):
        left = normalized[: connector.start()]
        right = normalized[connector.end() :]
        if PRODUCT_TOKEN_PATTERN.search(left) and PRODUCT_TOKEN_PATTERN.search(right):
            return True
    return False


def build_product_query_plan(
    message: str,
    *,
    base_intent: str,
    base_needs_clarification: bool = False,
) -> ProductQueryPlan | None:
    if base_intent not in PLANNABLE_PRODUCT_INTENTS:
        return None

    normalized = normalize_text(message)
    comparison_requested = any(term in normalized for term in COMPARISON_TERMS)
    primary_intent = "PRODUCT_COMPARISON" if comparison_requested else base_intent
    category = _category(normalized)
    min_price, max_price = _price_constraints(normalized)
    colors = _requested_colors(normalized, message)
    raw_storage = [
        re.sub(r"\s+", "", value).upper()
        for value in re.findall(r"\b\d+\s*(?:gb|tb)\b", normalized)
    ]
    ram_numbers = re.findall(r"\bram\s*(\d+)\s*gb\b", normalized)
    ram_numbers += re.findall(r"\b(\d+)\s*gb\s*ram\b", normalized)
    ram = [f"{value}GB" for value in ram_numbers]
    storage = [value for value in raw_storage if value not in ram]
    priorities = _unique_matches(normalized, PRIORITY_TERMS)
    stock_requested = any(term in normalized for term in STOCK_TERMS)
    promotion_requested = any(term in normalized for term in PROMOTION_TERMS)
    explicit_pair = _has_explicit_pair(normalized)

    product_signal = bool(
        comparison_requested
        or category
        or min_price is not None
        or max_price is not None
        or colors
        or storage
        or ram
        or priorities
        or stock_requested
        or promotion_requested
    )
    if not product_signal:
        return None

    intents = [primary_intent]
    if not explicit_pair and primary_intent == "PRODUCT_COMPARISON":
        intents.append("PRODUCT_SEARCH")
    if min_price is not None or max_price is not None or promotion_requested:
        intents.append("PRICE_AND_PROMOTION")
    if stock_requested or colors or storage or ram:
        intents.append("STOCK_AVAILABILITY")
    if priorities:
        intents.append("PRODUCT_REVIEW")
    intents = list(dict.fromkeys(intents))

    steps: list[PlannerStep] = []
    if not explicit_pair:
        steps.append("search_products")
    steps.append("get_product_details")
    if stock_requested or colors or storage or ram:
        steps.append("get_variant_stock")
    if promotion_requested:
        steps.append("get_active_promotions")
    if primary_intent == "PRODUCT_COMPARISON":
        steps.append("compare_products")

    has_selection_constraints = bool(
        category
        and (
            min_price is not None
            or max_price is not None
            or colors
            or storage
            or ram
            or priorities
        )
    )
    can_auto_resolve = primary_intent != "PRODUCT_COMPARISON" or explicit_pair or has_selection_constraints
    needs_clarification = base_needs_clarification and not can_auto_resolve
    confidence = 0.96 if explicit_pair else (0.90 if can_auto_resolve else 0.78)

    return ProductQueryPlan(
        primary_intent=primary_intent,
        intents=intents,
        constraints=ProductQueryConstraints(
            category=category,
            min_price=min_price,
            max_price=max_price,
            colors=list(dict.fromkeys(colors)),
            storage=list(dict.fromkeys(storage)),
            ram=list(dict.fromkeys(ram)),
            priorities=priorities,
            require_in_stock=stock_requested,
        ),
        steps=steps,
        has_explicit_product_pair=explicit_pair,
        can_auto_resolve=can_auto_resolve,
        needs_clarification=needs_clarification,
        confidence=confidence,
    )
