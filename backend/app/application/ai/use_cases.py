import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.catalog_embedding_index import search_catalog_index_semantic
from app.application.ai.answer_guidance import build_answer_requirements
from app.application.ai.conversation_memory import (
    ConversationMemoryService,
    ConversationMemorySnapshot,
    resolve_follow_up,
)
from app.application.ai.contracts import FactEnvelope, HandoverInfo
from app.application.ai.gemini_interactions import (
    GeminiInteractionError,
    create_gemini_interaction,
)
from app.application.ai.groq_interactions import (
    GroqInteractionError,
    create_groq_chat_completion,
)
from app.application.ai.local_circuit_breaker import (
    clear_local_model_state,
    is_local_circuit_open,
    record_local_failure,
)
from app.application.ai.schemas import AIAssistantRequest, AIAssistantResponse
from app.application.ai.rollout import is_in_stable_rollout
from app.application.ai.planned_business_support import (
    render_account_support_answer,
    render_cart_support_answer,
    render_product_review_answer,
    render_voucher_support_answer,
)
from app.application.ai.query_planner import ProductQueryPlan, build_product_query_plan
from app.application.ai.service_query_planner import ServiceQueryPlan, build_service_query_plan
from app.application.ai.store_policy_context import (
    get_store_policy_context,
    render_store_policy_answer,
)
from app.application.ai.tool_registry import AIReadToolRegistry, ToolExecutionError
from app.application.ai.intent_router import (
    IntentDecision,
    normalize_text as normalize_routing_text,
    route_intent,
    route_intent_v1,
    urgent_support_topic,
)
from app.application.ai.verification import verify_response
from app.application.services.loyalty_maintenance_service import (
    LOYALTY_TIER_LABELS,
    loyalty_tier_progress,
)
from app.config import settings
from app.infrastructure.cache import mark_redis_unavailable, redis_is_available
from app.infrastructure.database.repositories import ai_repo


REFUSAL_TEXT = (
    "Rất tiếc, mình là trợ lý mua sắm của ElectroMart nên không thể hỗ trợ nội dung này. "
    "Mình có thể giúp bạn tư vấn sản phẩm, chính sách, đơn hàng hoặc điểm tích lũy."
)

ALLOWED_SALES_TERMS = [
    "dien thoai",
    "smartphone",
    "laptop",
    "may tinh",
    "phu kien",
    "tai nghe",
    "sac",
    "gia",
    "so sanh",
    "bao hanh",
    "don hang",
    "giao hang",
    "van chuyen",
    "thanh toan",
    "vnpay",
    "momo",
    "loyalty",
    "diem",
    "voucher",
    "doi tra",
    "hoan tien",
    "khieu nai",
    "san pham",
    "mua",
]

BLOCKED_TERMS = [
    "chinh tri",
    "ton giao",
    "khieu dam",
    "hack",
    "lua dao",
    "vu khi",
    "thu ghet",
    "tu tu",
    "ma tuy",
]

GEMINI_SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý mua sắm của ElectroMart. Luôn trả lời bằng tiếng Việt có dấu đầy đủ, "
    "rõ ràng, tự nhiên và thân thiện. Trả lời trực tiếp trong 2 đến 6 câu; khi khách so sánh "
    "hoặc hỏi nhiều ý, có thể dùng tối đa 8 câu ngắn, mỗi ý một dòng. Không dùng Markdown, dấu **, tiêu đề hoặc bảng. "
    "Chỉ sử dụng dữ liệu được cung cấp trong lượt hỏi. "
    "Không bịa giá, cấu hình, chính sách hoặc trạng thái đơn hàng. Nếu thiếu xác thực hoặc "
    "thiếu mã đơn hàng, hãy yêu cầu khách đăng nhập hoặc cung cấp mã đơn. Nếu khách khiếu nại "
    "hoặc bức xúc, xin lỗi ngắn gọn và đề nghị chuyển nhân viên hỗ trợ. Không thảo luận chính trị, "
    "tôn giáo, thù ghét, tình dục, nội dung nguy hiểm, hack hoặc lừa đảo. Khi context chỉ có "
    "một sản phẩm, chỉ giới thiệu sản phẩm đó và không tự thêm sản phẩm khác. Trước khi trả lời, "
    "hãy kiểm tra tên sản phẩm, số tiền, trạng thái và mốc thời gian trong câu trả lời đều xuất hiện "
    "trong context; nếu dữ liệu không có, nói rõ chưa có thông tin thay vì suy đoán."
)


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    answer_mode: str
    provider_used: str
    model_name: str | None
    fallback_reason: str | None = None
    tool_results: tuple[dict, ...] = ()


def normalize_text(value: str) -> str:
    return normalize_routing_text(value)


def as_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def redact_for_log(value: str) -> str:
    redacted = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL]", value, flags=re.IGNORECASE)
    redacted = re.sub(r"(?<!\d)(?:\+?84|0)\d{9}(?!\d)", "[PHONE]", redacted)
    return re.sub(r"(?<!\d)\d{15}(?!\d)", "[DEVICE_ID]", redacted)


def is_in_sales_scope(message: str) -> bool:
    return route_intent(message).intent not in {"OUT_OF_SCOPE", "UNSAFE_REQUEST"}


def is_blocked(message: str) -> bool:
    return route_intent(message).intent == "UNSAFE_REQUEST"


def classify_intent(message: str) -> str:
    return route_intent_v1(message).intent


def keyword_tokens(message: str) -> list[str]:
    ignored = {
        "toi",
        "minh",
        "can",
        "mua",
        "tu",
        "van",
        "san",
        "pham",
        "nao",
        "gia",
        "duoi",
        "tren",
        "tam",
        "cho",
        "co",
        "khong",
        "cua",
        "hang",
        "muot",
        "tot",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(message))
        if len(token) > 2 and token not in ignored
    ][:8]


def order_code_from_message(message: str) -> str | None:
    match = re.search(r"\b(?:EMV[0-9]{10}|(?:ORD|DH|ORDER)[-_]?[A-Z0-9]{4,})\b", message, flags=re.IGNORECASE)
    return match.group(0).upper().replace("_", "-") if match else None


def after_sales_code_from_message(message: str) -> str | None:
    match = re.search(r"\b(?:WR|RT)[A-Z0-9]{10,}\b", message, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def price_intent_from_message(message: str) -> tuple[int | None, int | None]:
    normalized = normalize_text(message).replace(",", ".")
    if any(term in normalized for term in ("tang ngan sach them", "tang them ngan sach", "them ngan sach")):
        return None, None
    normalized = re.sub(r"\b\d+(?:\.\d+)?\s*%", " ", normalized)
    price_pattern = r"(\d+(?:\.\d+)?)\s*(trieu|tr|cu|m)?(?:\s*(\d{1,3}))?"

    def parse_vnd(raw_value: str) -> int:
        return int(raw_value.replace(".", ""))

    def parse(match: re.Match[str], offset: int = 0) -> int | None:
        major = float(match.group(1 + offset))
        unit = match.group(2 + offset)
        tail = match.group(3 + offset)
        if unit in {"trieu", "tr", "cu", "m"} or major < 1000:
            value = int(major * 1_000_000)
            if tail:
                value += int(tail) * 1000
            return value
        return int(major)

    vnd_range = re.search(
        r"(?:tu\s+)?(\d{1,3}(?:\.\d{3})+)\s*(?:dong)?\s+(?:den|toi)\s+"
        r"(\d{1,3}(?:\.\d{3})+)\s*dong",
        normalized,
    )
    if vnd_range:
        return parse_vnd(vnd_range.group(1)), parse_vnd(vnd_range.group(2))

    million_range = re.search(
        r"(?:tu\s+)?(\d+(?:\.\d+)?)\s+(?:den|toi)\s+(\d+(?:\.\d+)?)\s*(?:trieu|tr|cu|m)\b",
        normalized,
    )
    if million_range:
        return (
            int(float(million_range.group(1)) * 1_000_000),
            int(float(million_range.group(2)) * 1_000_000),
        )

    vnd_under = re.search(
        r"(?:duoi|toi da|khong qua|do lai)\s+(\d{1,3}(?:\.\d{3})+)\s*dong",
        normalized,
    )
    if vnd_under:
        return None, parse_vnd(vnd_under.group(1))

    vnd_under_suffix = re.search(
        r"(\d{1,3}(?:\.\d{3})+)\s*dong\s*(?:do lai|tro xuong)",
        normalized,
    )
    if vnd_under_suffix:
        return None, parse_vnd(vnd_under_suffix.group(1))

    vnd_over = re.search(
        r"(?:tren|hon|tu|toi thieu)\s+(\d{1,3}(?:\.\d{3})+)\s*dong",
        normalized,
    )
    if vnd_over:
        return parse_vnd(vnd_over.group(1)), None

    vnd_exact = re.search(r"(?:dung gia\s+)?(\d{1,3}(?:\.\d{3})+)\s*dong", normalized)
    if vnd_exact:
        value = parse_vnd(vnd_exact.group(1))
        if "dung gia" in normalized:
            return value, value
        return int(value * 0.9), int(value * 1.1)

    under = re.search(rf"(duoi|toi da|khong qua|do lai)\s*{price_pattern}", normalized)
    if under:
        return None, parse(under, 1)

    under_suffix = re.search(rf"{price_pattern}\s*(do lai|tro xuong)", normalized)
    if under_suffix:
        return None, parse(under_suffix)

    over = re.search(rf"(tren|hon|tu|toi thieu)\s*{price_pattern}", normalized)
    if over:
        return parse(over, 1), None

    exact = re.search(price_pattern, normalized)
    if exact and (exact.group(2) or exact.group(3)):
        value = parse(exact)
        if value:
            return int(value * 0.9), int(value * 1.1)

    return None, None


def price_extreme_from_message(message: str) -> str | None:
    normalized = normalize_text(message)
    if any(
        term in normalized
        for term in ["dat nhat", "gia cao nhat", "cao gia nhat", "cao cap nhat"]
    ):
        return "MOST_EXPENSIVE"
    if any(term in normalized for term in ["re nhat", "gia thap nhat", "thap gia nhat"]):
        return "LEAST_EXPENSIVE"
    return None


def effective_product_price(product: dict) -> float:
    sale_price = float(product.get("salePrice") or 0)
    return sale_price if sale_price > 0 else float(product.get("price") or 0)


def format_currency(value) -> str:
    return f"{int(float(value or 0)):,}đ".replace(",", ".")


def format_datetime_vi(value, *, exclusive_end: bool = False) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone(timedelta(hours=7)))
    if exclusive_end:
        parsed -= timedelta(seconds=1)
        return parsed.strftime("%d/%m/%Y")
    return parsed.strftime("%d/%m/%Y %H:%M")


def product_variant_labels(product: dict, *, limit: int = 4) -> list[str]:
    labels: list[str] = []
    variants = (
        product.get("matchedVariants")
        if product.get("variantSelectionRequested")
        else product.get("variants")
    ) or []
    for variant in variants[:limit]:
        parts = [
            str(variant.get("colorName") or "").strip(),
            str(variant.get("storage") or "").strip(),
            str(variant.get("ram") or "").strip(),
            str(variant.get("configuration") or "").strip(),
        ]
        label = " / ".join(dict.fromkeys(part for part in parts if part))
        if label and label not in labels:
            labels.append(label)
    return labels


VARIANT_COLOR_TERMS = (
    "den",
    "trang",
    "xanh",
    "do",
    "vang",
    "tim",
    "hong",
    "xam",
    "bac",
    "cam",
    "nau",
)


def matching_product_variants(product: dict, message: str) -> tuple[bool, list[dict]]:
    normalized = normalize_text(message)
    variants = list(product.get("variants") or [])
    requested_skus = []
    if any(term in normalized for term in ("sku", "ma san pham", "ma model", "ma vach")):
        requested_skus = [
            normalize_text(code)
            for code in re.findall(r"\b[a-z][a-z0-9]*(?:[-_][a-z0-9]+)+\b", normalized)
        ]
    storage_values = re.findall(r"\b(\d+\s*(?:gb|tb))\b", normalized)
    ram_values = re.findall(r"\bram\s*(\d+)\s*gb\b", normalized)
    ram_values += re.findall(r"\b(\d+)\s*gb\s*ram\b", normalized)
    requested_colors = [
        color
        for color in VARIANT_COLOR_TERMS
        if re.search(
            rf"\b(?:mau|ban mau|phien ban)\s+{re.escape(color)}\b"
            rf"|\b(?:con|co san)\s+(?:mau\s+)?{re.escape(color)}\b",
            normalized,
        )
    ]
    original_lower = message.lower()
    if "mẫu đó" in original_lower and "màu đỏ" not in original_lower:
        requested_colors = [color for color in requested_colors if color != "do"]
    has_storage_selector = bool(storage_values) and not (
        "ram" in normalized and "ssd" not in normalized and "dung luong" not in normalized and "ban " not in normalized
    )
    has_selector = bool(requested_skus or ram_values or requested_colors or has_storage_selector)
    if not has_selector:
        return False, []

    matched: list[dict] = []
    for variant in variants:
        sku = normalize_text(str(variant.get("sku") or ""))
        if requested_skus and sku not in requested_skus:
            continue
        searchable = normalize_text(
            " ".join(
                str(variant.get(field) or "")
                for field in ("storage", "ram", "configuration", "colorName", "sku")
            )
            + " "
            + json.dumps(variant.get("specs") or {}, ensure_ascii=False)
        )
        compact_searchable = re.sub(r"\s+", "", searchable)
        if has_storage_selector and not all(
            re.sub(r"\s+", "", value) in compact_searchable for value in storage_values
        ):
            continue
        if ram_values and not all(
            re.search(rf"(?<!\d){re.escape(value)}\s*gb(?![a-z0-9])", searchable) is not None
            for value in ram_values
        ):
            continue
        color_name = normalize_text(str(variant.get("colorName") or ""))
        if requested_colors and not all(color in color_name for color in requested_colors):
            continue
        matched.append(variant)
    return True, matched


def render_stock_product(product: dict) -> str:
    name = str(product.get("name") or "Sản phẩm")
    if product.get("variantSelectionRequested"):
        variants = product.get("matchedVariants") or []
        if not variants:
            return f"{name} chưa ghi nhận biến thể khớp màu, dung lượng, RAM hoặc SKU bạn yêu cầu"
        variant_parts = []
        for variant in variants[:5]:
            label_parts = [
                str(variant.get("colorName") or "").strip(),
                str(variant.get("storage") or "").strip(),
                str(variant.get("ram") or "").strip(),
                str(variant.get("configuration") or "").strip(),
                str(variant.get("sku") or "").strip(),
            ]
            label = " / ".join(dict.fromkeys(part for part in label_parts if part)) or "Biến thể"
            stock = int(variant.get("availableStock") or 0)
            status_text = f"còn {stock} sản phẩm khả dụng" if stock > 0 else "tạm hết hàng"
            variant_parts.append(f"{label}: {status_text}")
        return f"{name}: " + "; ".join(variant_parts)

    stock = int(product.get("availableStock") or 0)
    status_text = f"còn {stock} sản phẩm khả dụng" if stock > 0 else "tạm hết hàng"
    updated_at = format_datetime_vi(product.get("stockUpdatedAt"))
    return f"{name} hiện {status_text}" + (f"; dữ liệu cập nhật lúc {updated_at}" if updated_at else "")


def product_promotion_labels(product: dict, *, limit: int = 3) -> list[str]:
    labels: list[str] = []
    for promotion in (product.get("promotions") or [])[:limit]:
        if isinstance(promotion, str):
            label = promotion.strip()
        elif isinstance(promotion, dict):
            label = str(
                promotion.get("name")
                or promotion.get("title")
                or promotion.get("description")
                or promotion.get("code")
                or ""
            ).strip()
        else:
            label = ""
        label = label.strip(" .;")
        if label and label not in labels:
            labels.append(label)
    return labels


def product_summary(product: dict, *, include_details: bool = True) -> str:
    effective_price = effective_product_price(product)
    original_price = float(product.get("price") or 0)
    stock = int(product.get("availableStock") or 0)
    parts = [
        str(product.get("name") or "Sản phẩm"),
        f"giá hiện tại {format_currency(effective_price)}",
    ]
    if original_price > effective_price > 0:
        parts.append(f"giá gốc {format_currency(original_price)}")
        discount_amount = original_price - effective_price
        discount_percent = round(discount_amount * 100 / original_price)
        parts.append(f"giảm {format_currency(discount_amount)} ({discount_percent}%)")
    parts.append("còn hàng" if stock > 0 else "tạm hết hàng")
    if include_details:
        variants = product_variant_labels(product)
        if variants:
            parts.append("biến thể: " + ", ".join(variants))
        elif product.get("variantSelectionRequested") and product.get("requestedVariantColors"):
            requested_colors = ", ".join(product["requestedVariantColors"])
            available_colors = list(
                dict.fromkeys(
                    str(variant.get("colorName") or "").strip()
                    for variant in product.get("variants") or []
                    if str(variant.get("colorName") or "").strip()
                    and int(variant.get("availableStock") or 0) > 0
                )
            )
            parts.append(f"không có màu {requested_colors} đang bán")
            if available_colors:
                parts.append("màu đang có: " + ", ".join(available_colors[:5]))
        promotions = product_promotion_labels(product)
        if promotions:
            parts.append("ưu đãi: " + ", ".join(promotions))
        warranty = product.get("warrantyPeriod")
        if warranty:
            warranty_text = str(warranty).strip()
            if warranty_text.isdigit():
                warranty_text += " tháng"
            parts.append(f"bảo hành: {warranty_text}")
        if product.get("isUsed"):
            if product.get("conditionGrade"):
                parts.append(f"hạng {product['conditionGrade']}")
            if product.get("batteryHealth") is not None:
                battery_text = str(product["batteryHealth"]).strip()
                parts.append(f"pin {battery_text if battery_text.endswith('%') else battery_text + '%'}")
            if product.get("warrantyMonths") is not None:
                parts.append(f"bảo hành {product['warrantyMonths']} tháng")
    return "; ".join(parts)


def product_battery_summary(product: dict) -> str:
    specifications = product.get("specifications") or {}
    battery = str(specifications.get("battery") or "").strip()
    return f"pin {battery}" if battery else "chưa có dữ liệu pin"


def render_product_fallback(
    intent: str,
    products: list[dict],
    *,
    query_plan: dict | None = None,
) -> str:
    selected = products[:2] if intent == "PRODUCT_COMPARISON" else products[:3]
    if intent == "STOCK_AVAILABILITY":
        return (
            ". ".join(render_stock_product(product) for product in selected)
            + ". Tồn kho có thể thay đổi trước khi đơn hàng được xác nhận."
        )
    if intent == "PRICE_AND_PROMOTION":
        return ". ".join(product_summary(product) for product in selected) + "."
    if intent == "PRODUCT_COMPARISON" and len(selected) == 2:
        first, second = selected
        first_price = effective_product_price(first)
        second_price = effective_product_price(second)
        conclusions: list[str] = []
        if first_price == second_price:
            conclusions.append(f"Hai mẫu đang có cùng giá hiện tại {format_currency(first_price)}")
        else:
            cheaper = first if first_price < second_price else second
            conclusions.append(f"Nếu ưu tiên chi phí, {cheaper.get('name')} đang có giá thấp hơn")

        priorities = set(((query_plan or {}).get("constraints") or {}).get("priorities") or [])
        if "battery" in priorities:
            battery_values = []
            for product in (first, second):
                battery_text = str((product.get("specifications") or {}).get("battery") or "")
                match = re.search(r"(\d{4,5})\s*mah", normalize_text(battery_text))
                battery_values.append(int(match.group(1)) if match else None)
            if all(value is not None for value in battery_values):
                if battery_values[0] == battery_values[1]:
                    conclusions.append("Hai mẫu có dung lượng pin bằng nhau")
                else:
                    winner_index = 0 if battery_values[0] > battery_values[1] else 1
                    winner = (first, second)[winner_index]
                    conclusions.append(
                        f"Nếu ưu tiên pin, {winner.get('name')} tốt hơn về dung lượng "
                        f"với {battery_values[winner_index]} mAh"
                    )
        if not conclusions:
            conclusions.append("Nên chọn theo cấu hình và nhu cầu sử dụng được nêu ở trên")
        return (
            f"{product_summary(first)}; {product_battery_summary(first)}. "
            f"{product_summary(second)}; {product_battery_summary(second)}. "
            + ". ".join(conclusions)
            + "."
        )
    return ". ".join(product_summary(product) for product in selected) + "."


class AIAssistantUseCase:
    def __init__(self, *, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis
        self._tools = AIReadToolRegistry(session=session)
        self._conversation_memory = ConversationMemoryService(session=session, redis=redis)

    async def execute(
        self,
        *,
        user_id: str | None,
        request: AIAssistantRequest,
        traffic_origin: str = "CUSTOMER",
    ) -> AIAssistantResponse:
        if traffic_origin != "SYNTHETIC":
            await self._enforce_rate_limit(user_id=user_id)
        memory = await self._conversation_memory.load(
            conversation_id=request.conversation_id,
            user_id=user_id,
        )
        resolved_message = resolve_follow_up(request.message, memory)
        effective_request = request.model_copy(update={"message": resolved_message})
        v2_enabled = settings.ai_response_v2_enabled and is_in_stable_rollout(
            request.conversation_id,
            settings.ai_chat_v2_percent,
        )
        response_version = "2" if v2_enabled else "1"
        shadow_decision: IntentDecision | None = None
        if v2_enabled and settings.ai_router_v2_enabled:
            decision = route_intent(effective_request.message)
        else:
            decision = route_intent_v1(effective_request.message)
            if settings.ai_shadow_mode_enabled and settings.ai_router_v2_enabled:
                shadow_decision = route_intent(effective_request.message)

        query_plan = None
        if v2_enabled and settings.ai_query_planner_enabled:
            query_plan = build_product_query_plan(
                effective_request.message,
                base_intent=decision.intent,
                base_needs_clarification=decision.needs_clarification,
            )
            if query_plan:
                decision = IntentDecision(
                    intent=query_plan.primary_intent,
                    confidence=query_plan.confidence,
                    route="MODEL" if query_plan.primary_intent == "PRODUCT_COMPARISON" else decision.route,
                    needs_clarification=query_plan.needs_clarification,
                )

        service_query_plan = None
        if v2_enabled and settings.ai_service_query_planner_enabled and query_plan is None:
            service_query_plan = build_service_query_plan(
                effective_request.message,
                base_intent=decision.intent,
            )
            if service_query_plan:
                decision = IntentDecision(
                    intent=service_query_plan.primary_intent,
                    confidence=service_query_plan.confidence,
                    route="MODEL",
                    needs_clarification=False,
                )

        if decision.intent in {"OUT_OF_SCOPE", "UNSAFE_REQUEST", "UNSUPPORTED_REQUEST"}:
            reason = {
                "OUT_OF_SCOPE": "OUT_OF_SALES_SCOPE",
                "UNSAFE_REQUEST": "UNSAFE_REQUEST",
                "UNSUPPORTED_REQUEST": "UNSUPPORTED_ACTION",
            }[decision.intent]
            answer = REFUSAL_TEXT
            if decision.intent == "UNSUPPORTED_REQUEST":
                answer = (
                    "Mình có thể hướng dẫn và kiểm tra thông tin, nhưng không tự hủy đơn, thanh toán, "
                    "hoàn tiền hoặc thay đổi dữ liệu. Bạn hãy thực hiện trong tài khoản hoặc liên hệ nhân viên hỗ trợ."
                )
            response = AIAssistantResponse(
                version=response_version,
                conversation_id=request.conversation_id,
                answer=answer,
                refused=True,
                refusal_reason=reason,
                intent=decision.intent,
                answer_mode="POLICY_REFUSAL",
                provider_used="SYSTEM",
                confidence=decision.confidence,
                verification_passed=True,
            )
            return await self._complete_turn(
                request=request,
                response=response,
                user_id=user_id,
                memory=memory,
                shadow_decision=shadow_decision,
                traffic_origin=traffic_origin,
            )

        if decision.intent == "SMALL_TALK":
            response = AIAssistantResponse(
                version=response_version,
                conversation_id=request.conversation_id,
                answer=(
                    "Chào bạn! Mình có thể tư vấn sản phẩm, kiểm tra giá và tồn kho, "
                    "hoặc hỗ trợ tra cứu đơn hàng, bảo hành và hậu mãi."
                ),
                intent=decision.intent,
                answer_mode="DETERMINISTIC",
                provider_used="SYSTEM",
                confidence=decision.confidence,
                verification_passed=True,
            )
            return await self._complete_turn(
                request=request,
                response=response,
                user_id=user_id,
                memory=memory,
                shadow_decision=shadow_decision,
                traffic_origin=traffic_origin,
            )

        page_product_id = request.page_context.product_id if request.page_context else None
        normalized_message = normalize_text(effective_request.message)
        stock_needs_location = any(
            term in normalized_message
            for term in ("chi nhanh", "gan toi", "cua hang nao", "kho tong", "noi nhan")
        )
        can_resolve_from_page = bool(page_product_id) and (
            decision.intent in {"PRODUCT_SEARCH", "PRICE_AND_PROMOTION", "PRODUCT_REVIEW"}
            or (decision.intent == "STOCK_AVAILABILITY" and not stock_needs_location)
        )
        interaction_state = None
        if decision.needs_clarification and not can_resolve_from_page:
            interaction_state = await self._get_interaction_state(request.conversation_id)
        has_conversation_context = bool(
            (interaction_state and interaction_state.get("interaction_id"))
            or resolved_message != request.message
        )
        if decision.needs_clarification and not can_resolve_from_page and not has_conversation_context:
            clarification_question = (
                "Bạn muốn kiểm tra tại tỉnh/thành phố, quận/huyện hoặc chi nhánh nào?"
                if page_product_id and decision.intent == "STOCK_AVAILABILITY" and stock_needs_location
                else self._initial_clarification_question(decision.intent)
            )
            response = AIAssistantResponse(
                version=response_version,
                conversation_id=request.conversation_id,
                answer=clarification_question,
                intent=decision.intent,
                answer_mode="DETERMINISTIC",
                provider_used="SYSTEM",
                confidence=decision.confidence,
                needs_clarification=True,
                clarification_question=clarification_question,
                verification_passed=True,
            )
            return await self._complete_turn(
                request=request,
                response=response,
                user_id=user_id,
                memory=memory,
                shadow_decision=shadow_decision,
                traffic_origin=traffic_origin,
            )

        await self._cache_dynamic_context(effective_request)
        retrieved_context = await self._retrieve_context(
            intent=decision.intent,
            message=effective_request.message,
            user_id=user_id,
            request=effective_request,
            query_plan=query_plan,
            service_query_plan=service_query_plan,
        )
        if query_plan:
            retrieved_context["query_plan"] = query_plan.model_dump(mode="json")
        retrieved_context["conversation_memory"] = memory.prompt_context()
        if decision.route == "DETERMINISTIC":
            generated = GeneratedAnswer(
                answer=self._fallback_answer(intent=decision.intent, retrieved_context=retrieved_context),
                answer_mode="DETERMINISTIC",
                provider_used="SYSTEM",
                model_name=None,
            )
        else:
            generated = await self._generate_answer(
                effective_request,
                intent=decision.intent,
                retrieved_context=retrieved_context,
            )

        if generated.tool_results:
            self._merge_model_tool_results(retrieved_context, generated.tool_results)

        if is_blocked(generated.answer):
            generated = GeneratedAnswer(
                answer=REFUSAL_TEXT,
                answer_mode="POLICY_REFUSAL",
                provider_used="SYSTEM",
                model_name=None,
                fallback_reason="MODEL_OUTPUT_POLICY_BLOCKED",
            )

        verification = verify_response(
            intent=decision.intent,
            answer=generated.answer,
            context=retrieved_context,
        )
        if v2_enabled and settings.ai_verifier_enabled and not verification.passed:
            generated = GeneratedAnswer(
                answer=self._fallback_answer(
                    intent=decision.intent,
                    retrieved_context=retrieved_context,
                ),
                answer_mode="DATABASE_FALLBACK",
                provider_used="SYSTEM",
                model_name=generated.model_name,
                fallback_reason="VERIFIER_FAILED:" + ",".join(verification.errors),
            )
            verification = verify_response(
                intent=decision.intent,
                answer=generated.answer,
                context=retrieved_context,
            )

        needs_clarification, clarification_question = self._clarification_for_context(
            intent=decision.intent,
            context=retrieved_context,
        )
        handover = None
        if retrieved_context.get("handover_recommended"):
            handover = HandoverInfo(reason="Khách hàng cần nhân viên hỗ trợ tiếp nhận.")

        response = AIAssistantResponse(
            version=response_version,
            conversation_id=request.conversation_id,
            answer=generated.answer,
            intent=decision.intent,
            handover_recommended=bool(retrieved_context.get("handover_recommended")),
            sources=self._sources_for_context(retrieved_context),
            recommended_products=self._verified_products(retrieved_context, verification),
            answer_mode=(
                "GROUNDED_GENERATION"
                if generated.answer_mode == "GEMINI" and verification.passed
                else generated.answer_mode
            ),
            provider_used=generated.provider_used,
            model_name=generated.model_name,
            fallback_reason=generated.fallback_reason,
            confidence=decision.confidence if verification.passed else min(decision.confidence, 0.5),
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            cards=verification.cards,
            source_details=verification.sources,
            handover=handover,
            verification_passed=verification.passed,
        )
        return await self._complete_turn(
            request=request,
            response=response,
            user_id=user_id,
            memory=memory,
            retrieved_context=retrieved_context,
            shadow_decision=shadow_decision,
            traffic_origin=traffic_origin,
        )

    async def _complete_turn(
        self,
        *,
        request: AIAssistantRequest,
        response: AIAssistantResponse,
        user_id: str | None,
        memory: ConversationMemorySnapshot,
        retrieved_context: dict | None = None,
        shadow_decision: IntentDecision | None = None,
        traffic_origin: str = "CUSTOMER",
    ) -> AIAssistantResponse:
        record = await self._conversation_memory.record_turn(
            memory=memory,
            user_message=request.message,
            response=response,
            retrieved_context=retrieved_context,
        )
        recommend_handover = response.handover_recommended or record.should_offer_handover
        if recommend_handover:
            contact = await self._conversation_memory.support_contact()
            phone = contact.get("phone")
            email = contact.get("email")
            support = (retrieved_context or {}).get("support_request") or {}
            support_code = support.get("requestCode") if isinstance(support, dict) else None
            if record.should_offer_handover:
                if phone:
                    contact_text = f"Hotline chăm sóc khách hàng: {phone}."
                elif email:
                    contact_text = f"Email chăm sóc khách hàng: {email}."
                else:
                    contact_text = "Thông tin liên hệ chăm sóc khách hàng chưa được cấu hình."
                display_text = (
                    "Mình chưa giải quyết được yêu cầu của bạn sau vài lần trao đổi. "
                    f"Bạn có muốn liên hệ bộ phận chăm sóc khách hàng không? {contact_text}"
                )
                answer = f"{response.answer.rstrip()} {display_text}"
            else:
                contact_text = (
                    f"Bạn có thể gọi hotline {phone}."
                    if phone
                    else (f"Bạn có thể liên hệ email {email}." if email else "")
                )
                display_text = contact_text or "Nhân viên chăm sóc khách hàng sẽ tiếp nhận yêu cầu của bạn."
                answer = f"{response.answer.rstrip()} {contact_text}".strip()
            response = response.model_copy(
                update={
                    "answer": answer,
                    "handover_recommended": True,
                    "handover": HandoverInfo(
                        reason=(
                            "Chatbot chưa giải quyết được yêu cầu sau nhiều lượt."
                            if record.should_offer_handover
                            else "Khách hàng cần nhân viên hỗ trợ tiếp nhận."
                        ),
                        phone=phone,
                        email=email,
                        display_text=display_text,
                        can_create_ticket=bool(user_id),
                        support_request_code=support_code,
                    ),
                }
            )
        await self._log(
            request=request,
            response=response,
            user_id=user_id,
            shadow_decision=shadow_decision,
            retrieved_context=retrieved_context,
            traffic_origin=traffic_origin,
        )
        return response

    async def _cache_dynamic_context(self, request: AIAssistantRequest) -> None:
        if not redis_is_available():
            return
        cache_key = f"ai:session:{request.conversation_id}"
        try:
            await self._redis.set(
                cache_key,
                json.dumps(request.dynamic_context.model_dump(mode="json"), ensure_ascii=False),
                ex=60 * 30,
            )
        except RedisError:
            mark_redis_unavailable()

    async def _get_interaction_state(self, conversation_id: UUID) -> dict | None:
        if not redis_is_available():
            return None
        try:
            value = await self._redis.get(f"ai:interaction:{conversation_id}")
        except RedisError:
            mark_redis_unavailable()
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if not value:
            return None
        try:
            state = json.loads(str(value))
        except json.JSONDecodeError:
            return {
                "interaction_id": str(value),
                "model": settings.gemini_model,
            }
        return state if isinstance(state, dict) else None

    async def _store_interaction_state(
        self,
        conversation_id: UUID,
        *,
        interaction_id: str,
        model: str,
    ) -> None:
        if not redis_is_available():
            return
        try:
            await self._redis.set(
                f"ai:interaction:{conversation_id}",
                json.dumps(
                    {"interaction_id": interaction_id, "model": model},
                    ensure_ascii=False,
                ),
                ex=60 * 30,
            )
        except RedisError:
            mark_redis_unavailable()

    async def _clear_interaction_id(self, conversation_id: UUID) -> None:
        if not redis_is_available():
            return
        try:
            await self._redis.delete(f"ai:interaction:{conversation_id}")
        except RedisError:
            mark_redis_unavailable()

    async def _retrieve_context(
        self,
        *,
        intent: str,
        message: str,
        user_id: str | None,
        request: AIAssistantRequest,
        query_plan: ProductQueryPlan | None = None,
        service_query_plan: ServiceQueryPlan | None = None,
    ) -> dict:
        if service_query_plan:
            return await self._retrieve_service_plan_context(
                plan=service_query_plan,
                message=message,
                user_id=user_id,
                request=request,
            )
        if intent in {"ORDER_LOOKUP", "SHIPPING_LOOKUP"}:
            order = await self._find_order(message, user_id)
            context = {"order": order}
            if intent == "SHIPPING_LOOKUP" and order.get("orderCode") and user_id:
                try:
                    context["shipping_events"] = await self._tools.execute(
                        name="get_shipping_timeline",
                        arguments={"order_code": str(order["orderCode"])},
                        user_id=user_id,
                    )
                except ToolExecutionError as error:
                    context["tool_error"] = error.code
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "LOYALTY":
            loyalty = None
            if user_id and settings.ai_read_tools_enabled:
                try:
                    loyalty = await self._tools.execute(
                        name="get_my_loyalty",
                        arguments={},
                        user_id=user_id,
                    )
                except ToolExecutionError as error:
                    loyalty = {"tool_error": error.code}
            if loyalty and not loyalty.get("tool_error") and not loyalty.get("needs_auth"):
                loyalty.update(
                    loyalty_tier_progress(
                        current_tier=str(loyalty.get("tier") or "MEMBER"),
                        period_spend_amount=int(loyalty.get("periodSpendAmount") or 0),
                    )
                )
            context = {
                "loyalty": loyalty,
                "cart_items": [item.model_dump(mode="json") for item in request.dynamic_context.cart_items],
            }
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "CART_SUPPORT":
            order = None
            if user_id and settings.ai_read_tools_enabled:
                try:
                    order = await self._tools.execute(
                        name="get_my_latest_order",
                        arguments={},
                        user_id=user_id,
                    )
                except ToolExecutionError as error:
                    order = {"tool_error": error.code}
            context = {
                "message": message,
                "cart_items": [item.model_dump(mode="json") for item in request.dynamic_context.cart_items],
                "order": order,
            }
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "VOUCHER_SUPPORT":
            public_vouchers: list[dict] = []
            user_vouchers = None
            if settings.ai_read_tools_enabled:
                try:
                    public_vouchers = await self._tools.execute(
                        name="list_public_vouchers",
                        arguments={},
                        user_id=user_id,
                    )
                    if user_id:
                        user_vouchers = await self._tools.execute(
                            name="get_my_vouchers",
                            arguments={},
                            user_id=user_id,
                        )
                except ToolExecutionError as error:
                    public_vouchers = [{"tool_error": error.code}]
            context = {
                "message": message,
                "public_vouchers": public_vouchers,
                "user_vouchers": user_vouchers,
                "cart_items": [item.model_dump(mode="json") for item in request.dynamic_context.cart_items],
            }
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "ACCOUNT_SUPPORT":
            account = None
            if user_id and settings.ai_read_tools_enabled:
                try:
                    account = await self._tools.execute(
                        name="get_my_account",
                        arguments={},
                        user_id=user_id,
                    )
                except ToolExecutionError as error:
                    account = {"tool_error": error.code}
            context = {"message": message, "account": account}
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "PRODUCT_REVIEW":
            page_product_id = (
                str(request.page_context.product_id)
                if request.page_context and request.page_context.product_id
                else None
            )
            products = await self._find_products(
                message,
                page_product_id=page_product_id,
                query_plan=query_plan,
            )
            product = products[0] if products else None
            review_insights = None
            review_eligibility = None
            if product and settings.ai_read_tools_enabled:
                try:
                    review_insights = await self._tools.execute(
                        name="get_product_review_insights",
                        arguments={"product_id": str(product["id"])},
                        user_id=user_id,
                    )
                    if user_id:
                        review_eligibility = await self._tools.execute(
                            name="get_my_review_eligibility",
                            arguments={"product_id": str(product["id"])},
                            user_id=user_id,
                        )
                except ToolExecutionError as error:
                    review_insights = {"tool_error": error.code}
            context = {
                "message": message,
                "products": products[:1],
                "product": product,
                "review_insights": review_insights,
                "review_eligibility": review_eligibility,
            }
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "AFTER_SALES_LOOKUP":
            context = {"after_sales": await self._find_after_sales(message, user_id)}
            context["facts"] = self._fact_envelopes(context)
            return context
        if intent == "COMPLAINT":
            normalized = normalize_routing_text(message)
            support_request = None
            if user_id:
                asks_status = any(
                    term in normalized
                    for term in ("ma khieu nai", "da duoc tiep nhan", "theo doi tien do", "tien do khieu nai")
                )
                if asks_status and settings.ai_read_tools_enabled:
                    try:
                        support_request = await self._tools.execute(
                            name="get_my_latest_support_request",
                            arguments={},
                            user_id=user_id,
                        )
                    except ToolExecutionError as error:
                        support_request = {"tool_error": error.code}
                if not support_request and not asks_status:
                    urgent_topic = urgent_support_topic(normalized)
                    category = self._support_category(normalized)
                    support_request = await ai_repo.upsert_user_support_request_for_ai(
                        self._session,
                        user_id=user_id,
                        conversation_id=str(request.conversation_id),
                        category=category,
                        priority="URGENT" if urgent_topic else "HIGH",
                        summary=message,
                    )
            return {
                "handover_recommended": True,
                "reason": "Customer complaint or negative sentiment detected.",
                "urgent_support_topic": urgent_support_topic(normalized),
                "support_request": support_request,
                "support_needs_auth": not user_id,
            }
        if intent in {"STORE_POLICY", "WARRANTY_POLICY"}:
            context = {"store_policy": await get_store_policy_context(self._session, message)}
            context["facts"] = self._fact_envelopes(context)
            return context

        if intent == "USED_PRODUCT_ADVICE":
            products = await self._find_used_products(message)
            context = {"products": products, "used_products": products}
            context["facts"] = self._fact_envelopes(context)
            return context

        products = await self._find_products(
            message,
            page_product_id=str(request.page_context.product_id) if request.page_context and request.page_context.product_id else None,
            query_plan=query_plan,
        )
        context = {
            "products": products,
            "catalog_index": await search_catalog_index_semantic(message),
        }
        context["facts"] = self._fact_envelopes(context)
        return context

    async def _retrieve_service_plan_context(
        self,
        *,
        plan: ServiceQueryPlan,
        message: str,
        user_id: str | None,
        request: AIAssistantRequest,
    ) -> dict:
        context: dict = {
            "message": message,
            "service_query_plan": plan.model_dump(mode="json"),
            "cart_items": [item.model_dump(mode="json") for item in request.dynamic_context.cart_items],
        }

        if {"ORDER_LOOKUP", "SHIPPING_LOOKUP"}.intersection(plan.intents):
            order = await self._find_order(message, user_id)
            context["order"] = order
            if "SHIPPING_LOOKUP" in plan.intents and order.get("orderCode") and user_id:
                try:
                    context["shipping_events"] = await self._tools.execute(
                        name="get_shipping_timeline",
                        arguments={"order_code": str(order["orderCode"])},
                        user_id=user_id,
                    )
                except ToolExecutionError as error:
                    context["shipping_tool_error"] = error.code

        if "AFTER_SALES_LOOKUP" in plan.intents:
            context["after_sales"] = await self._find_after_sales(message, user_id)

        if "LOYALTY" in plan.intents:
            loyalty = None
            if user_id and settings.ai_read_tools_enabled:
                try:
                    loyalty = await self._tools.execute(
                        name="get_my_loyalty",
                        arguments={},
                        user_id=user_id,
                    )
                except ToolExecutionError as error:
                    loyalty = {"tool_error": error.code}
            if loyalty and not loyalty.get("tool_error") and not loyalty.get("needs_auth"):
                loyalty.update(
                    loyalty_tier_progress(
                        current_tier=str(loyalty.get("tier") or "MEMBER"),
                        period_spend_amount=int(loyalty.get("periodSpendAmount") or 0),
                    )
                )
            context["loyalty"] = loyalty

        if "VOUCHER_SUPPORT" in plan.intents:
            public_vouchers: list[dict] = []
            user_vouchers = None
            if settings.ai_read_tools_enabled:
                try:
                    public_vouchers = await self._tools.execute(
                        name="list_public_vouchers",
                        arguments={},
                        user_id=user_id,
                    )
                    if user_id:
                        user_vouchers = await self._tools.execute(
                            name="get_my_vouchers",
                            arguments={},
                            user_id=user_id,
                        )
                except ToolExecutionError as error:
                    public_vouchers = [{"tool_error": error.code}]
            context["public_vouchers"] = public_vouchers
            context["user_vouchers"] = user_vouchers

        if {"STORE_POLICY", "WARRANTY_POLICY"}.intersection(plan.intents):
            context["store_policy"] = await get_store_policy_context(self._session, message)

        context["facts"] = self._fact_envelopes(context)
        return context

    async def _find_products(
        self,
        message: str,
        *,
        page_product_id: str | None = None,
        query_plan: ProductQueryPlan | None = None,
    ) -> list[dict]:
        normalized = normalize_text(message)
        normalized = re.sub(r"\bip\s*([0-9]{1,2})\b(?![-_])", r"iphone \1", normalized)
        min_price, max_price = price_intent_from_message(message)
        price_extreme = price_extreme_from_message(message)
        products = [self._clean_row(row) for row in await ai_repo.list_active_products_for_ai(self._session)]
        for product in products:
            selection_requested, matched_variants = matching_product_variants(product, message)
            if selection_requested:
                product["variantSelectionRequested"] = True
                product["matchedVariants"] = matched_variants

        wants_discounted = any(
            term in normalized
            for term in (
                "dang giam",
                "dang sale",
                "dang co uu dai",
                "dang khuyen mai",
                "giam gia",
                "giam tren",
                "giam nhieu nhat",
                "gia sau khi giam",
            )
        )
        discount_threshold_match = re.search(r"giam\s+(?:tren|hon|tu)\s+(\d{1,3})\s*%", normalized)
        discount_threshold = int(discount_threshold_match.group(1)) if discount_threshold_match else None
        wants_biggest_discount = "giam nhieu nhat" in normalized

        def discount_details(product: dict) -> tuple[float, float]:
            original_price = float(product.get("price") or 0)
            sale_price = effective_product_price(product)
            if original_price <= 0 or sale_price <= 0 or sale_price >= original_price:
                return 0.0, 0.0
            amount = original_price - sale_price
            return amount, amount * 100 / original_price

        if page_product_id:
            normalized_page_product_id = normalize_text(page_product_id)
            page_matches = [
                product
                for product in products
                if normalized_page_product_id
                in {
                    normalize_text(str(product.get("id") or "")),
                    normalize_text(str(product.get("slug") or "")),
                }
            ]
            if page_matches:
                return page_matches[:1]

        wants_newest = any(
            term in normalized
            for term in ("san pham moi nhat", "moi them", "vua them", "moi cap nhat", "hang moi ve")
        )
        if wants_newest:
            wants_phone = any(
                term in normalized
                for term in ("dien thoai", "smartphone", "iphone", "galaxy", "samsung", "oppo", "xiaomi", "realme", "vivo")
            )
            wants_laptop = "laptop" in normalized or "may tinh" in normalized
            filtered_products = []
            for product in products:
                category_slug = normalize_text(str(product.get("categorySlug") or ""))
                category_name = normalize_text(str(product.get("categoryName") or ""))
                is_phone = category_slug in {"smartphones", "dien-thoai"} or "dien thoai" in category_name
                is_laptop = category_slug == "laptops" or "laptop" in category_name
                if wants_phone and not is_phone:
                    continue
                if wants_laptop and not is_laptop:
                    continue
                filtered_products.append(product)
            filtered_products.sort(
                key=lambda product: str(product.get("createdAt") or ""),
                reverse=True,
            )
            return filtered_products[:5]

        stop_tokens = {
            "bao", "ban", "ben", "ca", "cai", "can", "cho", "co", "con", "cua", "dang", "duoc",
            "dai", "gia", "giam", "gi", "hang", "hien", "khong", "khuyen", "ko", "la", "may", "minh",
            "hon", "mua", "nao", "nhat", "pham", "san", "shop", "tat", "thang", "the", "tim", "toi", "tot",
            "tren", "trieu", "tu", "tu van", "uu", "va", "voi", "xem", "sale",
        }

        def query_tokens(value: str) -> list[str]:
            return list(
                dict.fromkeys(
                    token
                    for token in re.findall(r"[a-z0-9]+", value)
                    if len(token) >= 2 and token not in stop_tokens
                )
            )[:10]

        def searchable_text(product: dict) -> str:
            return normalize_text(
                " ".join(
                    str(product.get(field) or "")
                    for field in ["name", "slug", "sku", "brand", "description", "categoryName", "categorySlug"]
                )
                + " "
                + json.dumps(product.get("specifications") or {}, ensure_ascii=False)
                + " "
                + json.dumps(product.get("variants") or [], ensure_ascii=False)
            )

        def text_score(product: dict, fragment: str) -> int:
            name = normalize_text(str(product.get("name") or ""))
            brand = normalize_text(str(product.get("brand") or ""))
            haystack = searchable_text(product)
            tokens = query_tokens(fragment)
            if not tokens:
                return 0
            score = 0
            if name == fragment.strip():
                score += 500
            elif name and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", fragment):
                score += 350 + len(name)
            elif len(fragment.strip()) >= 4 and fragment.strip() in name:
                score += 180
            if brand and re.search(
                rf"(?<![a-z0-9]){re.escape(brand)}(?![a-z0-9])",
                fragment,
            ):
                score += 320
            matched = 0
            for token in tokens:
                if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack):
                    matched += 1
                    score += 36 if any(char.isdigit() for char in token) else 24
            if matched == len(tokens):
                score += 120
            return score

        comparison_text = re.sub(r"^(?:ss|so sanh|phan tich)\s+", "", normalized).strip()
        comparison_parts = [
            part.strip(" ,.-")
            for part in re.split(r"\s+(?:vs|voi|va)\s+", comparison_text)
            if part.strip(" ,.-")
        ]
        if len(comparison_parts) >= 2 and (
            query_plan is None or query_plan.has_explicit_product_pair
        ):
            selected: list[dict] = []
            for part in comparison_parts[:2]:
                candidates = sorted(
                    ((text_score(product, part), product) for product in products),
                    key=lambda item: (
                        item[0],
                        int(float(item[1].get("rating") or 0)),
                        int(item[1].get("favoriteCount") or 0),
                    ),
                    reverse=True,
                )
                if candidates and candidates[0][0] > 0:
                    product = candidates[0][1]
                    if str(product.get("id")) not in {str(item.get("id")) for item in selected}:
                        selected.append(product)
            if len(selected) == 2:
                return selected

        exact_matches = [
            product
            for product in products
            if (name := normalize_text(str(product.get("name") or "")))
            and re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", normalized)
        ]
        if exact_matches:
            longest_name_length = max(len(normalize_text(str(product.get("name") or ""))) for product in exact_matches)
            return [
                product
                for product in exact_matches
                if len(normalize_text(str(product.get("name") or ""))) == longest_name_length
            ][:3]

        requested_codes = re.findall(
            r"\b(?:[a-z][a-z0-9]*[-_][a-z0-9_-]+|(?:sp|lap|nkd)\d+)\b",
            normalized,
        )
        if requested_codes:
            code_matches = [
                product
                for product in products
                if any(
                    re.search(rf"(?<![a-z0-9]){re.escape(code)}(?![a-z0-9])", searchable_text(product))
                    for code in requested_codes
                )
            ]
            if code_matches:
                return code_matches[:5]

        ranked: list[tuple[int, dict]] = []
        tokens = query_tokens(normalized)
        generic_category_tokens = {"dien", "thoai", "smartphone", "phone", "laptop", "tinh", "code", "ssd", "ram"}
        has_specific_tokens = any(
            token not in generic_category_tokens and not (wants_discounted and token.isdigit())
            for token in tokens
        )
        wants_phone = any(
            term in normalized
            for term in ("dien thoai", "smartphone", "iphone", "galaxy", "samsung", "oppo", "xiaomi", "realme", "vivo")
        )
        wants_laptop = "laptop" in normalized or "may tinh" in normalized or "code" in normalized

        def planner_priority_score(product: dict) -> int:
            if not query_plan:
                return 0
            score = 0
            priorities = set(query_plan.constraints.priorities)
            specifications = product.get("specifications") or {}
            if "battery" in priorities:
                battery_match = re.search(r"(\d{4,5})\s*mah", normalize_text(str(specifications.get("battery") or "")))
                if battery_match:
                    score += int(battery_match.group(1))
            if product.get("matchedVariants"):
                score += 100_000
            return score

        for product in products:
            category_slug = normalize_text(str(product.get("categorySlug") or ""))
            category_name = normalize_text(str(product.get("categoryName") or ""))
            is_phone = category_slug in {"smartphones", "dien-thoai"} or "dien thoai" in category_name
            is_laptop = category_slug == "laptops" or "laptop" in category_name
            if wants_phone and not is_phone:
                continue
            if wants_laptop and not is_laptop:
                continue

            price = effective_product_price(product)
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            if query_plan and (
                query_plan.constraints.colors
                or query_plan.constraints.storage
                or query_plan.constraints.ram
            ):
                matched_variants = product.get("matchedVariants") or []
                product["requestedVariantColors"] = query_plan.constraints.colors
                if matched_variants and query_plan.constraints.require_in_stock and not any(
                    int(variant.get("availableStock") or 0) > 0 for variant in matched_variants
                ):
                    continue
            discount_amount, discount_percent = discount_details(product)
            if wants_discounted and discount_amount <= 0:
                continue
            if discount_threshold is not None and discount_percent <= discount_threshold:
                continue

            score = text_score(product, normalized)
            category_match = (wants_phone and is_phone) or (wants_laptop and is_laptop)
            budget_match = min_price is not None or max_price is not None
            if has_specific_tokens and score <= 0 and not price_extreme:
                continue
            if score <= 0 and not category_match and not budget_match and not price_extreme and not wants_discounted:
                continue
            if category_match:
                score += 40
            if budget_match:
                score += 20
            score += int(float(product.get("rating") or 0))
            score += min(int(product.get("favoriteCount") or 0), 20)
            ranked.append((score, product))

        if wants_biggest_discount and ranked:
            ranked.sort(
                key=lambda item: (
                    discount_details(item[1])[1],
                    discount_details(item[1])[0],
                ),
                reverse=True,
            )
            return [ranked[0][1]]

        if price_extreme and ranked:
            reverse = price_extreme == "MOST_EXPENSIVE"
            ranked.sort(key=lambda item: effective_product_price(item[1]), reverse=reverse)
            result_limit = 3 if re.search(r"\b(?:ba|3)\s+san pham\b", normalized) else 1
            return [product for _, product in ranked[:result_limit]]

        if wants_discounted and ranked:
            ranked.sort(
                key=lambda item: (
                    discount_details(item[1])[1],
                    item[0],
                ),
                reverse=True,
            )
            return [product for _, product in ranked[:5]]

        ranked.sort(
            key=lambda item: (planner_priority_score(item[1]), item[0]),
            reverse=True,
        )
        return [product for _, product in ranked[:5]]

    async def _find_used_products(self, message: str) -> list[dict]:
        min_price, max_price = price_intent_from_message(message)
        search_tokens = [
            token
            for token in keyword_tokens(message)
            if token not in {"hang", "may", "dien", "thoai", "laptop"}
        ]
        try:
            result = await self._tools.execute(
                name="search_used_products",
                arguments={
                    "search": " ".join(search_tokens[:3]),
                    "min_price": min_price,
                    "max_price": max_price,
                    "limit": 10,
                },
                user_id=None,
            )
        except ToolExecutionError:
            return []

        products = []
        for item in (result.get("items") or [])[:5]:
            images = item.get("images") or []
            image_url = images[0] if images and isinstance(images[0], str) else None
            if images and isinstance(images[0], dict):
                image_url = images[0].get("url") or images[0].get("src")
            products.append(
                {
                    "id": str(item.get("id") or ""),
                    "slug": item.get("slug"),
                    "name": item.get("title") or item.get("productName"),
                    "price": item.get("salePrice") or 0,
                    "salePrice": item.get("salePrice") or 0,
                    "imageUrl": image_url,
                    "availableStock": 1,
                    "updatedAt": item.get("publishedAt"),
                    "isUsed": True,
                    "conditionGrade": item.get("conditionGrade"),
                    "batteryHealth": item.get("batteryHealth"),
                    "warrantyMonths": item.get("warrantyMonths"),
                }
            )
        return products

    async def _find_order(self, message: str, user_id: str | None) -> dict:
        if not user_id:
            return {"needs_auth": True}

        code = order_code_from_message(message)
        try:
            if code:
                row = await self._tools.execute(
                    name="get_my_order",
                    arguments={"order_code": code},
                    user_id=user_id,
                )
            else:
                row = await self._tools.execute(
                    name="get_my_latest_order",
                    arguments={},
                    user_id=user_id,
                )
        except ToolExecutionError as error:
            return {"tool_error": error.code}
        if row:
            return row
        return {
            "not_found": True,
            "order_code": code,
            "lookup_mode": "CODE" if code else "LATEST",
        }

    async def _find_after_sales(self, message: str, user_id: str | None) -> dict:
        if not user_id:
            return {"needs_auth": True}
        code = after_sales_code_from_message(message)
        try:
            if code:
                row = await self._tools.execute(
                    name="get_after_sales_status",
                    arguments={"request_code": code},
                    user_id=user_id,
                )
            else:
                row = await self._tools.execute(
                    name="get_my_latest_after_sales",
                    arguments={},
                    user_id=user_id,
                )
        except ToolExecutionError as error:
            return {"tool_error": error.code}
        if row:
            return row
        return {
            "not_found": True,
            "request_code": code,
            "lookup_mode": "CODE" if code else "LATEST",
        }

    async def _generate_answer(
        self,
        request: AIAssistantRequest,
        *,
        intent: str,
        retrieved_context: dict,
    ) -> GeneratedAnswer:
        failure_reasons = []
        fallback_eligible = {
            "MODEL_RATE_LIMITED",
            "MODEL_BUSY",
            "MODEL_TIMEOUT",
            "MODEL_CONNECTION_ERROR",
        }
        last_model = None

        if settings.gemini_api_key:
            models = self._models_for_intent(intent)
            for index, model in enumerate(models):
                last_model = model
                if await self._is_model_circuit_open(model):
                    failure_reasons.append(f"{model}:CIRCUIT_OPEN")
                    continue
                try:
                    result = await self._generate_with_model(
                        request,
                        intent=intent,
                        retrieved_context=retrieved_context,
                        model=model,
                    )
                    await self._record_model_success(model)
                    return GeneratedAnswer(
                        answer=result.answer,
                        answer_mode="GEMINI",
                        provider_used="GEMINI",
                        model_name=model,
                        fallback_reason=";".join(failure_reasons) or None,
                        tool_results=result.tool_results,
                    )
                except GeminiInteractionError as error:
                    failure_reasons.append(f"{model}:{error.reason}")
                    if error.reason in fallback_eligible:
                        await self._record_model_failure(model, reason=error.reason)
                    if index == 0 and error.reason not in fallback_eligible:
                        break

        if settings.groq_api_key and settings.groq_model:
            model = settings.groq_model
            last_model = model
            if await self._is_model_circuit_open(model):
                failure_reasons.append(f"{model}:CIRCUIT_OPEN")
            else:
                try:
                    result = await self._call_groq(
                        request,
                        intent=intent,
                        retrieved_context=retrieved_context,
                        model=model,
                    )
                    await self._record_model_success(model)
                    return GeneratedAnswer(
                        answer=result.answer,
                        answer_mode="GROUNDED_GENERATION",
                        provider_used="GROQ",
                        model_name=model,
                        fallback_reason=";".join(failure_reasons) or None,
                    )
                except GroqInteractionError as error:
                    failure_reasons.append(f"{model}:{error.reason}")
                    if error.reason in fallback_eligible:
                        await self._record_model_failure(model, reason=error.reason)

        return GeneratedAnswer(
            answer=self._fallback_answer(intent=intent, retrieved_context=retrieved_context),
            answer_mode="DATABASE_FALLBACK",
            provider_used="SYSTEM",
            model_name=last_model,
            fallback_reason=";".join(failure_reasons) or "MODEL_NOT_CONFIGURED",
        )

    def _models_for_intent(self, intent: str) -> list[str]:
        primary = settings.gemini_model
        lite = settings.gemini_fallback_model
        if not settings.ai_model_routing_enabled:
            ordered = [primary, lite]
        elif intent == "PRODUCT_COMPARISON":
            ordered = [lite, primary]
        elif intent in {
            "PRODUCT_ADVICE",
            "PRODUCT_RECOMMENDATION",
        }:
            ordered = [primary, lite]
        else:
            ordered = [lite, primary]
        return [model for model in dict.fromkeys(ordered) if model]

    async def _is_model_circuit_open(self, model: str) -> bool:
        if not redis_is_available():
            return is_local_circuit_open(model)
        try:
            return bool(await self._redis.get(f"ai:circuit-open:{model}"))
        except RedisError:
            mark_redis_unavailable()
            return is_local_circuit_open(model)

    async def _record_model_failure(self, model: str, *, reason: str | None = None) -> None:
        rate_limited = reason == "MODEL_RATE_LIMITED"
        timed_out = reason == "MODEL_TIMEOUT"
        open_immediately = rate_limited or timed_out
        circuit_seconds = (
            settings.ai_model_rate_limit_circuit_seconds
            if rate_limited
            else settings.ai_model_timeout_circuit_seconds if timed_out else 120
        )
        if not redis_is_available():
            record_local_failure(
                model,
                open_immediately=open_immediately,
                open_seconds=circuit_seconds,
            )
            return
        key = f"ai:model-failures:{model}"
        try:
            if open_immediately:
                await self._redis.set(f"ai:circuit-open:{model}", "1", ex=circuit_seconds)
                await self._redis.delete(key)
                return
            if hasattr(self._redis, "incr"):
                count = int(await self._redis.incr(key))
                if count == 1:
                    await self._redis.expire(key, 60)
            else:
                count = int(await self._redis.get(key) or 0) + 1
                await self._redis.set(key, str(count), ex=60)
            if count >= 3:
                await self._redis.set(f"ai:circuit-open:{model}", "1", ex=120)
                await self._redis.delete(key)
        except RedisError:
            mark_redis_unavailable()
            record_local_failure(
                model,
                open_immediately=open_immediately,
                open_seconds=circuit_seconds,
            )
            return
        except (TypeError, ValueError):
            return

    async def _record_model_success(self, model: str) -> None:
        clear_local_model_state(model)
        if not redis_is_available():
            return
        try:
            await self._redis.delete(f"ai:model-failures:{model}")
        except RedisError:
            mark_redis_unavailable()
            return

    async def _generate_with_model(
        self,
        request: AIAssistantRequest,
        *,
        intent: str,
        retrieved_context: dict,
        model: str,
    ):
        state = await self._get_interaction_state(request.conversation_id)
        previous_interaction_id = (
            str(state.get("interaction_id"))
            if state and state.get("model") == model and state.get("interaction_id")
            else None
        )
        try:
            result = await self._call_gemini(
                request,
                intent=intent,
                retrieved_context=retrieved_context,
                previous_interaction_id=previous_interaction_id,
                model=model,
            )
        except GeminiInteractionError as error:
            if error.reason != "INVALID_INTERACTION_STATE" or not previous_interaction_id:
                raise
            await self._clear_interaction_id(request.conversation_id)
            result = await self._call_gemini(
                request,
                intent=intent,
                retrieved_context=retrieved_context,
                previous_interaction_id=None,
                model=model,
            )

        await self._store_interaction_state(
            request.conversation_id,
            interaction_id=result.interaction_id,
            model=model,
        )
        return result

    async def _call_gemini(
        self,
        request: AIAssistantRequest,
        *,
        intent: str,
        retrieved_context: dict,
        previous_interaction_id: str | None,
        model: str,
    ):
        input_text = self._build_model_input(request, intent, retrieved_context)
        is_primary_model = model == settings.gemini_model
        timeout_seconds = (
            min(settings.gemini_interaction_timeout_seconds, settings.gemini_primary_timeout_seconds)
            if is_primary_model
            else settings.gemini_interaction_timeout_seconds
        )
        max_retries = (
            settings.gemini_primary_max_retries
            if is_primary_model
            else settings.gemini_interaction_max_retries
        )
        return await create_gemini_interaction(
            api_key=settings.gemini_api_key,
            model=model,
            system_instruction=GEMINI_SYSTEM_INSTRUCTION,
            input_text=input_text,
            previous_interaction_id=previous_interaction_id,
            thinking_level=settings.gemini_thinking_level if model.startswith("gemini-3") else None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            tools=self._tool_declarations_for_intent(intent) if settings.ai_read_tools_enabled else None,
            tool_handler=lambda name, arguments: self._handle_model_tool(name, arguments),
            max_tool_calls=4,
        )

    async def _call_groq(
        self,
        request: AIAssistantRequest,
        *,
        intent: str,
        retrieved_context: dict,
        model: str,
    ):
        return await create_groq_chat_completion(
            api_key=settings.groq_api_key,
            model=model,
            system_instruction=GEMINI_SYSTEM_INSTRUCTION,
            input_text=self._build_model_input(request, intent, retrieved_context),
            timeout_seconds=settings.groq_timeout_seconds,
            max_retries=settings.groq_max_retries,
            max_completion_tokens=settings.groq_max_completion_tokens,
            reasoning_effort=settings.groq_reasoning_effort or None,
        )

    @staticmethod
    def _build_model_input(
        request: AIAssistantRequest,
        intent: str,
        retrieved_context: dict,
    ) -> str:
        answer_requirements = build_answer_requirements(
            intent=intent,
            message=request.message,
        )
        return (
            f"Intent: {intent}\n"
            f"Answer requirements: {answer_requirements}\n"
            f"Dynamic context: {json.dumps(request.dynamic_context.model_dump(mode='json'), ensure_ascii=False, default=as_jsonable)}\n"
            f"Database context: {json.dumps(retrieved_context, ensure_ascii=False, default=as_jsonable)}\n"
            f"Customer question: {request.message}"
        )

    def _tool_declarations_for_intent(self, intent: str) -> list[dict]:
        if intent == "USED_PRODUCT_ADVICE":
            return [
                {
                    "type": "function",
                    "name": "search_used_products",
                    "description": "Tìm tối đa 5 sản phẩm cũ đang công khai và sẵn sàng bán.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "maxLength": 120},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                }
            ]
        if intent in {
            "PRODUCT_SEARCH",
            "PRODUCT_RECOMMENDATION",
            "PRODUCT_COMPARISON",
            "PRICE_AND_PROMOTION",
            "STOCK_AVAILABILITY",
        }:
            return [
                {
                    "type": "function",
                    "name": "search_products",
                    "description": "Tìm tối đa 5 sản phẩm mới bằng dữ liệu giá, tồn và biến thể hiện hành.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "maxLength": 500},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                }
            ]
        return []

    async def _handle_model_tool(self, name: str, arguments: dict) -> dict:
        if set(arguments) != {"query"} or not isinstance(arguments.get("query"), str):
            return {"error": "INVALID_INPUT"}
        query = arguments["query"].strip()
        if not query:
            return {"error": "INVALID_INPUT"}
        if name == "search_products":
            return {"products": await self._find_products(query[:500])}
        if name == "search_used_products":
            return {"products": await self._find_used_products(query[:120])}
        return {"error": "TOOL_NOT_ALLOWED"}

    def _merge_model_tool_results(self, context: dict, tool_results: tuple[dict, ...]) -> None:
        for tool_result in tool_results:
            result = tool_result.get("result") or {}
            products = result.get("products") if isinstance(result, dict) else None
            if isinstance(products, list):
                context["products"] = products[:5]
                if tool_result.get("name") == "search_used_products":
                    context["used_products"] = products[:5]
        context["facts"] = self._fact_envelopes(context)

    @staticmethod
    def _support_category(normalized_message: str) -> str:
        if any(term in normalized_message for term in ("the bi lo", "chiem quyen", "otp", "gia mao", "bao mat", "giao dich toi khong")):
            return "SECURITY"
        if any(term in normalized_message for term in ("thanh toan", "hoan tien", "tru tien", "tinh sai gia", "tra gop")):
            return "PAYMENT"
        if any(term in normalized_message for term in ("giao hang", "giao qua tre", "tai xe", "giao nham", "chua nhan")):
            return "ORDER_DELIVERY"
        if any(term in normalized_message for term in ("bao hanh", "doi tra", "san pham", "pin", "dien giat", "boc chay")):
            return "PRODUCT_AFTER_SALES"
        if any(term in normalized_message for term in ("nhan vien", "quan ly", "chi nhanh")):
            return "STAFF_SERVICE"
        return "GENERAL_SUPPORT"

    @staticmethod
    def _support_request_suffix(context: dict) -> str:
        request_data = context.get("support_request") or {}
        if request_data.get("requestCode"):
            status_text = {
                "OPEN": "đã tiếp nhận",
                "IN_PROGRESS": "đang xử lý",
                "WAITING_CUSTOMER": "đang chờ bạn bổ sung thông tin",
                "RESOLVED": "đã xử lý",
                "CLOSED": "đã đóng",
            }.get(str(request_data.get("status") or "").upper(), str(request_data.get("status") or ""))
            return f" Mã hỗ trợ {request_data['requestCode']} hiện {status_text}."
        if context.get("support_needs_auth"):
            return " Bạn vui lòng đăng nhập để hệ thống tạo mã hỗ trợ và theo dõi tiến độ; trường hợp khẩn cấp hãy gọi hotline hoặc số cứu hộ phù hợp."
        if request_data.get("tool_error"):
            return " Hệ thống tạo phiếu hỗ trợ đang tạm gián đoạn; bạn vui lòng liên hệ hotline."
        return ""

    def _fallback_answer(self, *, intent: str, retrieved_context: dict) -> str:
        service_plan = retrieved_context.get("service_query_plan") or {}
        planned_intents = service_plan.get("intents") or []
        if len(planned_intents) > 1:
            section_labels = {
                "ORDER_LOOKUP": "Đơn hàng",
                "SHIPPING_LOOKUP": "Vận chuyển",
                "AFTER_SALES_LOOKUP": "Hậu mãi",
                "LOYALTY": "Điểm thành viên",
                "VOUCHER_SUPPORT": "Voucher",
                "STORE_POLICY": "Chính sách cửa hàng",
                "WARRANTY_POLICY": "Chính sách bảo hành",
            }
            single_context = {**retrieved_context, "service_query_plan": None}
            sections: list[str] = []
            seen_answers: set[str] = set()
            for planned_intent in planned_intents:
                answer = self._fallback_answer(
                    intent=str(planned_intent),
                    retrieved_context=single_context,
                )
                if answer and answer not in seen_answers:
                    label = section_labels.get(str(planned_intent), "Thông tin")
                    sections.append(f"{label}: {answer}")
                    seen_answers.add(answer)
            if sections:
                return "\n\n".join(sections)

        if intent == "CART_SUPPORT":
            return render_cart_support_answer(retrieved_context)
        if intent == "VOUCHER_SUPPORT":
            return render_voucher_support_answer(retrieved_context)
        if intent == "ACCOUNT_SUPPORT":
            return render_account_support_answer(retrieved_context)
        if intent == "PRODUCT_REVIEW":
            return render_product_review_answer(retrieved_context)
        if intent in {"STORE_POLICY", "WARRANTY_POLICY"}:
            return render_store_policy_answer(retrieved_context.get("store_policy") or {})
        if intent in {"ORDER_LOOKUP", "SHIPPING_LOOKUP"}:
            order = retrieved_context.get("order") or {}
            if order.get("needs_auth"):
                return "Bạn vui lòng đăng nhập để mình kiểm tra đơn hàng của riêng bạn."
            if order.get("needs_order_code"):
                return "Bạn vui lòng cung cấp mã đơn hàng để mình kiểm tra trạng thái chính xác."
            if order.get("not_found"):
                if order.get("lookup_mode") == "LATEST":
                    return "Mình chưa tìm thấy đơn hàng nào trong tài khoản của bạn."
                return "Mình chưa tìm thấy đơn hàng này trong tài khoản của bạn. Bạn hãy kiểm tra lại mã đơn."
            if order.get("tool_error"):
                return "Hệ thống tra cứu đơn hàng đang tạm gián đoạn. Bạn vui lòng thử lại sau ít phút."
            if order.get("orderCode"):
                status_text = self._order_status_text(str(order.get("status") or ""))
                payment_text = self._payment_status_text(str(order.get("paymentStatus") or ""))
                total_text = format_currency(order.get("totalAmount")) if order.get("totalAmount") is not None else None
                summary = f"Đơn {order['orderCode']} hiện {status_text}; thanh toán {payment_text}"
                if total_text:
                    summary += f"; tổng tiền {total_text}"
                items = order.get("items") or []
                item_text = ", ".join(
                    f"{item.get('productName')} x{item.get('quantity')}"
                    for item in items[:3]
                    if item.get("productName")
                )
                if item_text:
                    summary += f"; sản phẩm: {item_text}"
                if intent == "SHIPPING_LOOKUP":
                    events = retrieved_context.get("shipping_events") or []
                    if events:
                        latest = events[-1]
                        event_text = latest.get("title") or latest.get("eventCode")
                        description = latest.get("description")
                        tracking = latest.get("trackingCode") or order.get("trackingCode")
                        provider = latest.get("shippingProvider") or order.get("shippingProvider")
                        details = f"Cập nhật vận chuyển mới nhất: {event_text}"
                        if description:
                            details += f" – {description}"
                        if provider:
                            details += f"; đơn vị vận chuyển {provider}"
                        if tracking:
                            details += f"; mã vận đơn {tracking}"
                        return f"{summary}. {details}."
                    tracking = order.get("trackingCode")
                    provider = order.get("shippingProvider")
                    if tracking:
                        shipping_text = f"Mã vận đơn {tracking}"
                        if provider:
                            shipping_text += f", đơn vị vận chuyển {provider}"
                    else:
                        shipping_text = "Đơn chưa có mã vận đơn"
                    return f"{summary}. {shipping_text}."
                return summary + "."
        if intent == "LOYALTY":
            loyalty = retrieved_context.get("loyalty")
            if loyalty and not loyalty.get("tool_error"):
                tier_code = str(loyalty.get("tier") or "").upper()
                tier = LOYALTY_TIER_LABELS.get(tier_code, tier_code or "chưa xếp hạng")
                wallet = self._loyalty_wallet_status_text(str(loyalty.get("walletStatus") or ""))
                spend = int(loyalty.get("periodSpendAmount") or 0)
                points_text = f"{int(loyalty.get('pointsBalance') or 0):,}".replace(",", ".")
                answer = (
                    f"Bạn đang có {points_text} điểm, hạng {tier}; "
                    f"ví điểm {wallet}. Doanh số xét hạng trong kỳ hiện tại là {format_currency(spend)}."
                )
                next_tier = loyalty.get("nextTierLabel")
                amount_needed = int(loyalty.get("amountToNextTier") or 0)
                if next_tier and amount_needed > 0:
                    answer += f" Bạn cần mua thêm {format_currency(amount_needed)} trong kỳ để lên hạng {next_tier}."
                elif next_tier:
                    answer += f" Bạn đã đủ doanh số để lên hạng {next_tier}; hạng sẽ được cập nhật theo quy trình xét hạng."
                else:
                    answer += " Bạn đang ở hạng cao nhất."
                if loyalty.get("periodEndsAt"):
                    answer += (
                        " Kỳ xét hạng kết thúc vào ngày "
                        f"{format_datetime_vi(loyalty['periodEndsAt'], exclusive_end=True)}."
                    )
                return answer
            if loyalty and loyalty.get("tool_error"):
                return "Hệ thống điểm thành viên đang tạm gián đoạn. Bạn vui lòng thử lại sau ít phút."
            return "Bạn vui lòng đăng nhập để mình kiểm tra điểm tích lũy."
        if intent == "AFTER_SALES_LOOKUP":
            request_data = retrieved_context.get("after_sales") or {}
            if request_data.get("needs_auth"):
                return "Bạn vui lòng đăng nhập để mình kiểm tra hồ sơ bảo hành hoặc đổi trả của riêng bạn."
            if request_data.get("needs_request_code"):
                return "Bạn vui lòng cung cấp mã hồ sơ bắt đầu bằng WR hoặc RT để mình kiểm tra chính xác."
            if request_data.get("not_found"):
                if request_data.get("lookup_mode") == "LATEST":
                    return "Mình chưa tìm thấy hồ sơ bảo hành hoặc đổi trả nào trong tài khoản của bạn."
                return "Mình chưa tìm thấy hồ sơ này trong tài khoản của bạn. Bạn hãy kiểm tra lại mã hồ sơ."
            if request_data.get("tool_error"):
                return "Hệ thống hậu mãi đang tạm gián đoạn. Bạn vui lòng thử lại sau ít phút."
            if request_data.get("requestCode"):
                request_type = "bảo hành" if request_data.get("requestType") == "WARRANTY" else "đổi trả"
                answer = (
                    f"Hồ sơ {request_type} {request_data['requestCode']} hiện "
                    f"{self._after_sales_status_text(str(request_data.get('status') or ''))}"
                )
                resolution = request_data.get("resolutionType")
                if resolution:
                    answer += f"; hướng xử lý {self._resolution_type_text(str(resolution))}"
                if request_data.get("slaDueAt"):
                    answer += f"; hạn xử lý dự kiến theo hồ sơ {format_datetime_vi(request_data['slaDueAt'])}"
                events = request_data.get("events") or []
                if events:
                    latest = events[-1]
                    event_status = self._after_sales_status_text(str(latest.get("newStatus") or ""))
                    answer += f". Cập nhật mới nhất: {event_status}"
                    if latest.get("note"):
                        answer += f" – {latest['note']}"
                return answer + "."
        if intent == "COMPLAINT":
            urgent_topic = retrieved_context.get("urgent_support_topic")
            support_suffix = self._support_request_suffix(retrieved_context)
            if urgent_topic == "FIRE_BATTERY":
                return (
                    "Bạn hãy ngừng sử dụng và sạc thiết bị ngay, giữ khoảng cách và không tự tháo hoặc chọc vào pin. "
                    "Nếu có khói hoặc lửa, hãy rời khỏi khu vực và gọi 114; chỉ ngắt nguồn điện khi có thể làm an toàn. "
                    "Mình đề xuất chuyển nhân viên hỗ trợ khẩn cấp, nhưng không thay thế hướng dẫn của cơ quan cứu hộ."
                    + support_suffix
                )
            if urgent_topic == "INJURY_ELECTRIC":
                return (
                    "Bạn không nên chạm trực tiếp vào thiết bị hoặc người còn tiếp xúc với nguồn điện. "
                    "Hãy ngắt nguồn khi có thể làm an toàn, gọi 115 nếu có người bị thương và gọi 114 nếu còn nguy cơ điện hoặc cháy. "
                    "Mình đề xuất chuyển nhân viên hỗ trợ khẩn cấp ngay."
                    + support_suffix
                )
            if urgent_topic == "ACCOUNT_FRAUD":
                return (
                    "Bạn không cung cấp OTP, PIN hoặc CVV cho bất kỳ ai. Hãy liên hệ ngân hàng để khóa thẻ/giao dịch nếu liên quan, "
                    "đổi mật khẩu và đăng xuất các phiên lạ. Chatbot không thể tự khóa tài khoản hoặc dừng giao dịch; "
                    "mình đề xuất chuyển nhân viên hỗ trợ bảo mật ngay."
                    + support_suffix
                )
            if urgent_topic == "COUNTERFEIT":
                return (
                    "Bạn nên ngừng sử dụng nếu nghi ngờ sản phẩm không an toàn, giữ lại sản phẩm, hộp, hóa đơn và hình ảnh làm bằng chứng. "
                    "Mình đề xuất chuyển nhân viên khiếu nại để xác minh nguồn gốc; chatbot không tự kết luận sản phẩm là hàng giả."
                    + support_suffix
                )
            return (
                "Mình rất tiếc vì trải nghiệm của bạn chưa tốt. Mình đã chuyển thông tin đến luồng hỗ trợ để xử lý tiếp."
                + support_suffix
            )
        products = retrieved_context.get("products") or []
        if products:
            return render_product_fallback(
                intent,
                products,
                query_plan=retrieved_context.get("query_plan"),
            )
        catalog_index = retrieved_context.get("catalog_index") or []
        if catalog_index:
            names = ", ".join(item["title"] for item in catalog_index[:3])
            return f"Mình tìm thấy một số thông tin phù hợp trong catalog: {names}."
        return "Mình chưa tìm thấy dữ liệu phù hợp. Bạn có thể nói rõ hơn nhu cầu, ngân sách hoặc sản phẩm bạn quan tâm."

    def _initial_clarification_question(self, intent: str) -> str:
        if intent == "PRODUCT_REVIEW":
            return "Bạn muốn xem đánh giá hoặc trải nghiệm thực tế của sản phẩm nào?"
        if intent == "PRODUCT_COMPARISON":
            return "Bạn muốn so sánh cụ thể hai mẫu máy nào?"
        if intent == "WARRANTY_POLICY":
            return "Bạn cho mình tên sản phẩm hoặc mã đơn hàng để kiểm tra đúng thời hạn bảo hành nhé."
        if intent == "PRODUCT_RECOMMENDATION":
            return "Bạn cần điện thoại, laptop hay phụ kiện, và ngân sách dự kiến khoảng bao nhiêu?"
        if intent == "PRICE_AND_PROMOTION":
            return "Bạn đang hỏi sản phẩm hoặc phiên bản nào, và muốn kiểm tra giá, mã giảm giá hay tổng tiền sau ưu đãi?"
        if intent == "STOCK_AVAILABILITY":
            return "Bạn muốn kiểm tra sản phẩm, màu, dung lượng hoặc SKU nào; cần bao nhiêu sản phẩm và nhận tại khu vực nào?"
        return "Bạn có thể nói rõ hơn thông tin cần kiểm tra không?"

    def _clarification_for_context(self, *, intent: str, context: dict) -> tuple[bool, str | None]:
        if intent in {"ORDER_LOOKUP", "SHIPPING_LOOKUP"}:
            order = context.get("order") or {}
            if order.get("needs_auth"):
                return True, "Bạn có thể đăng nhập để mình kiểm tra đơn hàng của bạn không?"
            if order.get("needs_order_code"):
                return True, "Bạn cho mình xin mã đơn hàng cần kiểm tra nhé?"
        if intent == "AFTER_SALES_LOOKUP":
            request_data = context.get("after_sales") or {}
            if request_data.get("needs_auth"):
                return True, "Bạn có thể đăng nhập để mình kiểm tra hồ sơ hậu mãi của bạn không?"
            if request_data.get("needs_request_code"):
                return True, "Bạn cho mình xin mã hồ sơ WR hoặc RT cần kiểm tra nhé?"
        return False, None

    def _verified_products(self, context: dict, verification) -> list[dict]:
        allowed_ids = {card.id for card in verification.cards}
        return [
            product
            for product in (context.get("products") or [])
            if str(product.get("id") or "") in allowed_ids
        ][:3]

    def _fact_envelopes(self, context: dict) -> list[dict]:
        facts: list[FactEnvelope] = []
        for product in (context.get("products") or [])[:10]:
            product_id = str(product.get("id") or "")
            if not product_id:
                continue
            is_used = bool(product.get("isUsed"))
            facts.append(
                FactEnvelope(
                    fact_id=f"{'used-product' if is_used else 'product'}:{product_id}",
                    source_type="used_product_snapshot" if is_used else "product_snapshot",
                    source_id=product_id,
                    source_version=str(product.get("updatedAt") or product.get("stockUpdatedAt") or "") or None,
                    visibility_scope="PUBLIC",
                    fields={
                        "name": product.get("name"),
                        "price": product.get("price"),
                        "sale_price": product.get("salePrice"),
                        "available_stock": int(product.get("availableStock") or 0),
                        "variants": product.get("variants") or [],
                        "promotions": product.get("promotions") or [],
                        "warranty_period": product.get("warrantyPeriod"),
                        "warranty_policy": product.get("warrantyPolicy") or {},
                        "condition_grade": product.get("conditionGrade"),
                        "battery_health": product.get("batteryHealth"),
                        "warranty_months": product.get("warrantyMonths"),
                    },
                )
            )

        order = context.get("order") or {}
        if order.get("orderCode"):
            facts.append(
                FactEnvelope(
                    fact_id=f"order:{order['orderCode']}",
                    source_type="order_snapshot",
                    source_id=str(order["orderCode"]),
                    source_version=str(order.get("updatedAt") or "") or None,
                    visibility_scope="USER",
                    fields={
                        key: order.get(key)
                        for key in (
                            "status",
                            "paymentStatus",
                            "totalAmount",
                            "shippingProvider",
                            "trackingCode",
                            "shippedAt",
                            "completedAt",
                        )
                    },
                )
            )

        loyalty = context.get("loyalty") or {}
        if loyalty:
            facts.append(
                FactEnvelope(
                    fact_id="loyalty:current-user",
                    source_type="loyalty_snapshot",
                    source_id="current-user",
                    source_version=str(loyalty.get("updatedAt") or "") or None,
                    visibility_scope="USER",
                    fields={
                        "points_balance": loyalty.get("pointsBalance"),
                        "tier": loyalty.get("tier"),
                        "wallet_status": loyalty.get("walletStatus"),
                        "period_spend_amount": loyalty.get("periodSpendAmount"),
                        "period_started_at": loyalty.get("periodStartedAt"),
                        "period_ends_at": loyalty.get("periodEndsAt"),
                        "next_tier": loyalty.get("nextTier"),
                        "next_tier_target": loyalty.get("nextTierTarget"),
                        "amount_to_next_tier": loyalty.get("amountToNextTier"),
                    },
                )
            )

        after_sales = context.get("after_sales") or {}
        if after_sales.get("requestCode"):
            facts.append(
                FactEnvelope(
                    fact_id=f"after-sales:{after_sales['requestCode']}",
                    source_type="after_sales_snapshot",
                    source_id=str(after_sales["requestCode"]),
                    source_version=str(after_sales.get("updatedAt") or "") or None,
                    visibility_scope="USER",
                    fields={
                        "request_type": after_sales.get("requestType"),
                        "status": after_sales.get("status"),
                        "resolution_type": after_sales.get("resolutionType"),
                        "sla_due_at": after_sales.get("slaDueAt"),
                    },
                )
            )

        store_policy = context.get("store_policy") or {}
        if store_policy:
            facts.append(
                FactEnvelope(
                    fact_id=f"store-policy:{store_policy.get('topic') or 'GENERAL'}",
                    source_type="store_policy_snapshot",
                    source_id=str(store_policy.get("topic") or "GENERAL"),
                    source_version=str(store_policy.get("source_version") or "") or None,
                    visibility_scope="PUBLIC",
                    fields={
                        "topic": store_policy.get("topic"),
                        "store": store_policy.get("store") or {},
                        "payment_methods": store_policy.get("payment_methods") or [],
                        "delivery": store_policy.get("delivery") or {},
                        "policies": store_policy.get("policies") or {},
                    },
                )
            )

        review = context.get("review_insights") or {}
        product = context.get("product") or {}
        if review and product.get("id"):
            facts.append(
                FactEnvelope(
                    fact_id=f"product-reviews:{product['id']}",
                    source_type="product_review_snapshot",
                    source_id=str(product["id"]),
                    source_version=str(review.get("updatedAt") or "") or None,
                    visibility_scope="PUBLIC",
                    fields={
                        "average_rating": review.get("averageRating"),
                        "review_count": review.get("reviewCount"),
                        "verified_purchase_count": review.get("verifiedPurchaseCount"),
                        "rating_distribution": review.get("ratingDistribution") or {},
                    },
                )
            )

        account = context.get("account") or {}
        if account and not account.get("tool_error"):
            facts.append(
                FactEnvelope(
                    fact_id="account:current-user",
                    source_type="account_snapshot",
                    source_id="current-user",
                    source_version=str(account.get("updatedAt") or "") or None,
                    visibility_scope="USER",
                    fields={
                        "status": account.get("status"),
                        "address_count": account.get("addressCount"),
                        "active_session_count": account.get("activeSessionCount"),
                        "birth_date_locked": account.get("birthDateLocked"),
                    },
                )
            )

        support_request = context.get("support_request") or {}
        if support_request.get("requestCode"):
            facts.append(
                FactEnvelope(
                    fact_id=f"support:{support_request['requestCode']}",
                    source_type="support_request_snapshot",
                    source_id=str(support_request["requestCode"]),
                    source_version=str(support_request.get("updatedAt") or "") or None,
                    visibility_scope="USER",
                    fields={
                        "category": support_request.get("category"),
                        "priority": support_request.get("priority"),
                        "status": support_request.get("status"),
                    },
                )
            )
        return [fact.model_dump(mode="json") for fact in facts]

    def _order_status_text(self, value: str) -> str:
        return {
            "PENDING": "đang chờ xử lý",
            "CONFIRMED": "đã xác nhận",
            "PROCESSING": "đang chuẩn bị hàng",
            "SHIPPED": "đang giao",
            "DELIVERED": "đã giao",
            "COMPLETED": "đã hoàn tất",
            "CANCELLED": "đã hủy",
            "REFUNDED": "đã hoàn tiền",
        }.get(value.upper(), value.lower() or "chưa xác định")

    def _payment_status_text(self, value: str) -> str:
        return {
            "PENDING": "đang chờ",
            "UNPAID": "chưa thanh toán",
            "PAID": "đã thanh toán",
            "PARTIALLY_PAID": "đã thanh toán một phần",
            "FAILED": "thất bại",
            "REFUND_PENDING": "đang chờ hoàn tiền",
            "REFUNDED": "đã hoàn tiền",
        }.get(value.upper(), value.lower() or "chưa xác định")

    def _loyalty_wallet_status_text(self, value: str) -> str:
        return {
            "ACTIVE": "đang hoạt động",
            "SUSPENDED": "đang tạm khóa",
            "CLOSED": "đã đóng",
        }.get(value.upper(), value.lower() or "chưa xác định")

    def _resolution_type_text(self, value: str) -> str:
        return {
            "REPAIR": "sửa chữa",
            "REPLACEMENT": "đổi máy thay thế",
            "EXCHANGE": "đổi sản phẩm",
            "REFUND": "hoàn tiền",
            "RETURN": "trả hàng",
            "REJECT": "từ chối",
        }.get(value.upper(), value.lower().replace("_", " ") or "chưa xác định")

    def _after_sales_status_text(self, value: str) -> str:
        return {
            "SUBMITTED": "đã tiếp nhận",
            "RECEIVED": "đã nhận máy",
            "QC_IN_PROGRESS": "đang kiểm tra kỹ thuật",
            "WARRANTY_ACCEPTED": "đã chấp nhận bảo hành",
            "REPAIRING": "đang sửa chữa",
            "REPAIR_COMPLETED": "đã sửa xong",
            "REPLACEMENT_APPROVED": "đã duyệt đổi máy",
            "WAITING_FOR_STOCK": "đang chờ máy thay thế",
            "REPLACEMENT_PROCESSING": "đang xử lý máy thay thế",
            "READY_TO_RETURN": "sẵn sàng trả máy",
            "RETURNING_TO_CUSTOMER": "đang gửi trả khách",
            "REFUND_PROCESSING": "đang hoàn tiền",
            "EXCHANGE_PROCESSING": "đang đổi sản phẩm",
            "COMPLETED": "đã hoàn tất",
            "REJECTED": "đã từ chối",
            "CANCELLED": "đã hủy",
            "CLOSED_EXPIRED": "đã đóng do quá hạn",
        }.get(value.upper(), value.lower() or "chưa xác định")

    def _sources_for_context(self, context: dict) -> list[str]:
        sources = []
        if context.get("products"):
            sources.append("products")
        if context.get("catalog_index"):
            sources.append("cocoindex_catalog")
        if context.get("order"):
            sources.append("orders")
        if context.get("shipping_events"):
            sources.append("shipment_events")
        if context.get("loyalty"):
            sources.append("loyalty")
        if context.get("after_sales"):
            sources.append("after_sales")
        if context.get("store_policy"):
            sources.append("store_policy")
        if context.get("public_vouchers") or context.get("user_vouchers"):
            sources.append("vouchers")
        if context.get("review_insights"):
            sources.append("product_reviews")
        if context.get("account"):
            sources.append("account")
        if context.get("support_request"):
            sources.append("support_requests")
        return sources

    def _clean_row(self, row: dict) -> dict:
        return json.loads(json.dumps(row, default=as_jsonable, ensure_ascii=False))

    async def _enforce_rate_limit(self, *, user_id: str | None) -> None:
        if not redis_is_available():
            return
        actor = user_id or "anonymous"
        key = f"rate-limit:ai:{actor}"
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, 60)
            if count > settings.ai_rate_limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="AI assistant rate limit exceeded. Please try again shortly.",
                )
        except RedisError:
            mark_redis_unavailable()
            return

    async def _log(
        self,
        *,
        request: AIAssistantRequest,
        response: AIAssistantResponse,
        user_id: str | None,
        shadow_decision: IntentDecision | None = None,
        retrieved_context: dict | None = None,
        traffic_origin: str = "CUSTOMER",
    ) -> None:
        try:
            parsed_user_id = UUID(user_id) if user_id else None
        except ValueError:
            parsed_user_id = None

        query_plan = (retrieved_context or {}).get("query_plan") or {}
        service_query_plan = (retrieved_context or {}).get("service_query_plan") or {}
        await ai_repo.add_ai_context_log(
            self._session,
            user_id=parsed_user_id,
            conversation_id=request.conversation_id,
            user_message=redact_for_log(request.message),
            assistant_response=redact_for_log(response.answer),
            refusal_reason=response.refusal_reason,
            dynamic_context={
                "cart_item_count": len(request.dynamic_context.cart_items),
                "viewed_product_count": len(request.dynamic_context.viewed_products),
                "has_client_loyalty_context": request.dynamic_context.loyalty is not None,
                "intent": response.intent,
                "sources": response.sources,
                "answer_mode": response.answer_mode,
                "provider_used": response.provider_used,
                "fallback_reason": response.fallback_reason,
                "confidence": response.confidence,
                "verification_passed": response.verification_passed,
                "needs_clarification": response.needs_clarification,
                "shadow_intent": shadow_decision.intent if shadow_decision else None,
                "shadow_route": shadow_decision.route if shadow_decision else None,
                "shadow_confidence": shadow_decision.confidence if shadow_decision else None,
                "planner_intents": query_plan.get("intents") or [],
                "planner_steps": query_plan.get("steps") or [],
                "planner_auto_resolved": bool(query_plan.get("can_auto_resolve")),
                "service_planner_intents": service_query_plan.get("intents") or [],
                "service_planner_steps": service_query_plan.get("steps") or [],
                "traffic_origin": traffic_origin,
            },
            model_provider="GEMINI",
            model_name=response.model_name or "system-fallback",
            log_id=response.response_id,
        )
        await self._session.commit()
