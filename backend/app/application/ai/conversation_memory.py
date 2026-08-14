import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.intent_router import normalize_text
from app.application.ai.schemas import AIAssistantResponse
from app.config import settings
from app.infrastructure.cache import mark_redis_unavailable, redis_is_available
from app.infrastructure.database.repositories import ai_repo
from app.infrastructure.database.repositories.store_info_repo import get_store_info


PRODUCT_INTENTS = {
    "PRODUCT_SEARCH",
    "PRODUCT_ADVICE",
    "PRODUCT_RECOMMENDATION",
    "PRODUCT_COMPARISON",
    "PRICE_AND_PROMOTION",
    "STOCK_AVAILABILITY",
    "PRODUCT_REVIEW",
    "WARRANTY_POLICY",
}
ORDER_INTENTS = {"ORDER_LOOKUP", "SHIPPING_LOOKUP", "CART_SUPPORT"}
NEGATIVE_FEEDBACK_TERMS = (
    "khong dung",
    "khong phai",
    "tra loi sai",
    "chua tra loi",
    "khong hieu y",
    "khong lien quan",
    "van chua duoc",
)
AFFIRMATIVE_TERMS = {
    "co",
    "dong y",
    "duoc",
    "ok",
    "toi muon",
    "lien he giup toi",
    "goi nhan vien",
}


@dataclass
class ConversationMemorySnapshot:
    conversation_id: UUID
    user_id: UUID | None
    active_intent: str | None = None
    active_entities: dict = field(default_factory=dict)
    pending_slots: dict = field(default_factory=dict)
    summary: str = ""
    unresolved_streak: int = 0
    last_failure_reason: str | None = None
    handover_offered_at: datetime | None = None
    recent_turns: list[dict] = field(default_factory=list)
    writable: bool = True

    def prompt_context(self) -> dict:
        turns = []
        for turn in self.recent_turns[-settings.ai_conversation_recent_turns :]:
            turns.append(
                {
                    "user": str(turn.get("userMessage") or "")[:500],
                    "assistant": str(turn.get("assistantResponse") or "")[:700],
                    "intent": turn.get("intent"),
                }
            )
        return {
            "summary": self.summary,
            "active_intent": self.active_intent,
            "active_entities": self.active_entities,
            "pending_slots": self.pending_slots,
            "recent_turns": turns,
        }


@dataclass(frozen=True)
class ConversationRecordResult:
    snapshot: ConversationMemorySnapshot
    should_offer_handover: bool
    failure_reason: str | None = None


def _parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _product_entities(entities: dict) -> list[dict]:
    products = entities.get("products") if isinstance(entities, dict) else None
    if not isinstance(products, list):
        return []
    return [item for item in products if isinstance(item, dict) and item.get("name")]


def _ordinal_index(value: str) -> int | None:
    match = re.search(r"\b(?:con|may|mau|san pham|cai)\s+thu\s*(\d+)\b", value)
    if match:
        return max(0, int(match.group(1)) - 1)
    words = {"nhat": 0, "hai": 1, "ba": 2, "tu": 3, "nam": 4}
    match = re.search(r"\b(?:con|may|mau|san pham|cai)\s+thu\s+(nhat|hai|ba|tu|nam)\b", value)
    return words.get(match.group(1)) if match else None


def _is_independent_catalog_extreme_query(value: str) -> bool:
    """Nhận diện câu hỏi cực trị toàn danh mục để không kế thừa sản phẩm cũ."""
    extreme_terms = ("cao nhat", "thap nhat", "dat nhat", "re nhat")
    if not any(term in value for term in extreme_terms):
        return False

    comparison_scope_terms = ("trong hai", "hai san pham", "hai mau", "giua hai")
    if any(term in value for term in comparison_scope_terms):
        return False

    collection_terms = (
        "danh sach san pham",
        "tat ca san pham",
        "toan bo san pham",
        "trong cua hang",
    )
    if any(term in value for term in collection_terms):
        return True

    return bool(
        re.search(
            r"\b(?:san pham|mat hang|dien thoai|laptop|may tinh|tablet|tai nghe|dong ho)\b"
            r".{0,80}\b(?:cao nhat|thap nhat|dat nhat|re nhat)\b",
            value,
        )
    )


def resolve_follow_up(message: str, memory: ConversationMemorySnapshot) -> str:
    """Viết lại câu nối tiếp bằng thực thể đã xác minh; không tự tạo dữ liệu mới."""
    normalized = normalize_text(message)
    if not normalized:
        return message

    if memory.handover_offered_at and normalized.strip(" ?.!") in AFFIRMATIVE_TERMS:
        return "Tôi muốn gặp nhân viên chăm sóc khách hàng."

    if any(term in normalized for term in NEGATIVE_FEEDBACK_TERMS):
        return message

    if _is_independent_catalog_extreme_query(normalized):
        return message

    products = _product_entities(memory.active_entities)
    order = memory.active_entities.get("order") if isinstance(memory.active_entities, dict) else None
    support = memory.active_entities.get("support_request") if isinstance(memory.active_entities, dict) else None

    for product in products:
        if normalize_text(str(product.get("name") or "")) in normalized:
            return message
    if re.search(
        r"\b(?:iphone|ipad|macbook|galaxy|samsung|oppo|xiaomi|redmi|realme|vivo|honor|tecno|meizu|asus|acer|dell|hp|lenovo)\b.{0,30}\b\d+[a-z0-9]*\b",
        normalized,
    ):
        return message

    comparison_follow_up_terms = (
        "cai nao",
        "may nao",
        "con nao",
        "mau nao",
        "cai nao tot hon",
        "may nao tot hon",
        "con nao tot hon",
        "mau nao tot hon",
        "cai nao phu hop hon",
        "nen chon cai nao",
        "so sanh tiep",
    )
    if len(products) >= 2 and any(term in normalized for term in comparison_follow_up_terms):
        return f"So sánh {products[0]['name']} với {products[1]['name']}: {message}"

    ordinal = _ordinal_index(normalized)
    product = products[ordinal] if ordinal is not None and ordinal < len(products) else (products[0] if products else None)
    reference_terms = (
        "no ", "no?", "may nay", "may do", "mau nay", "mau do", "con nay", "con do",
        "cai nay", "cai do", "san pham nay", "san pham do", "con thu", "may thu", "mau thu",
    )
    product_follow_up_terms = (
        "gia", "pin", "camera", "ram", "bo nho", "mau", "con hang", "het hang", "bao hanh",
        "tra gop", "khuyen mai", "sac", "man hinh", "cau hinh", "danh gia", "co tot", "mua duoc",
    )
    is_short = len(normalized.split()) <= 12
    if product and (
        ordinal is not None
        or any(term in normalized for term in reference_terms)
        or (is_short and any(term in normalized for term in product_follow_up_terms))
    ):
        if "mau" in normalized and (" con " in f" {normalized} " or "con hang" in normalized):
            return f"{product['name']} phiên bản được hỏi còn hàng không? {message}"
        return f"Về {product['name']}: {message}"

    order_follow_up_terms = (
        "khi nao toi", "bao gio toi", "dang o dau", "giao toi dau", "doi dia chi", "huy duoc",
        "thanh toan chua", "phi ship", "nguoi nhan", "don do", "don nay",
    )
    if isinstance(order, dict) and order.get("orderCode") and any(
        term in normalized for term in order_follow_up_terms
    ):
        return f"Về đơn hàng {order['orderCode']}: {message}"

    if isinstance(support, dict) and support.get("requestCode") and any(
        term in normalized for term in ("tien do", "xu ly toi dau", "ma do", "khieu nai do", "yeu cau do")
    ):
        return f"Về phiếu hỗ trợ {support['requestCode']}: {message}"
    return message


def _clean_product(product: dict) -> dict | None:
    product_id = product.get("id") or product.get("productId")
    name = product.get("name") or product.get("productName")
    if not name:
        return None
    return {
        "id": str(product_id) if product_id else None,
        "name": str(name)[:255],
        "slug": product.get("slug"),
    }


def active_entities_from_context(
    context: dict,
    previous: dict,
    *,
    preferred_products: list[dict] | None = None,
) -> dict:
    entities = dict(previous or {})
    products: list[dict] = []
    raw_products = (
        preferred_products
        if preferred_products is not None
        else (context.get("products") if isinstance(context, dict) else None)
    )
    if isinstance(raw_products, list):
        for item in raw_products[:5]:
            if isinstance(item, dict):
                cleaned = _clean_product(item)
                if cleaned:
                    products.append(cleaned)
    raw_product = (
        context.get("product")
        if preferred_products is None and isinstance(context, dict)
        else None
    )
    if isinstance(raw_product, dict):
        cleaned = _clean_product(raw_product)
        if cleaned and not any(item.get("id") == cleaned.get("id") for item in products):
            products.insert(0, cleaned)
    if products:
        entities["products"] = products[:5]

    order = context.get("order") if isinstance(context, dict) else None
    if isinstance(order, dict) and order.get("orderCode"):
        entities["order"] = {"orderCode": order.get("orderCode"), "status": order.get("status")}
    support = context.get("support_request") if isinstance(context, dict) else None
    if isinstance(support, dict) and support.get("requestCode"):
        entities["support_request"] = {
            "requestCode": support.get("requestCode"),
            "status": support.get("status"),
        }
    query_plan = context.get("query_plan") if isinstance(context, dict) else None
    if isinstance(query_plan, dict):
        constraints = query_plan.get("constraints") or {}
        if isinstance(constraints, dict):
            entities["query_constraints"] = {
                key: constraints.get(key)
                for key in (
                    "category",
                    "min_price",
                    "max_price",
                    "colors",
                    "storage",
                    "ram",
                    "priorities",
                    "require_in_stock",
                )
                if constraints.get(key) not in (None, [], False)
            }
    return entities


def _summary(intent: str | None, entities: dict) -> str:
    parts = [f"Chủ đề gần nhất: {intent}." if intent else ""]
    products = _product_entities(entities)
    if products:
        parts.append("Sản phẩm đang trao đổi: " + ", ".join(item["name"] for item in products[:5]) + ".")
    order = entities.get("order") if isinstance(entities, dict) else None
    if isinstance(order, dict) and order.get("orderCode"):
        parts.append(f"Đơn hàng đang trao đổi: {order['orderCode']}.")
    support = entities.get("support_request") if isinstance(entities, dict) else None
    if isinstance(support, dict) and support.get("requestCode"):
        parts.append(f"Phiếu hỗ trợ đang trao đổi: {support['requestCode']}.")
    return " ".join(part for part in parts if part)[:2000]


class ConversationMemoryService:
    def __init__(self, *, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis

    @staticmethod
    def _cache_key(conversation_id: UUID) -> str:
        return f"ai:memory:{conversation_id}"

    async def load(self, *, conversation_id: UUID, user_id: str | None) -> ConversationMemorySnapshot:
        parsed_user_id = UUID(user_id) if user_id else None
        if not settings.ai_conversation_memory_enabled or self._session is None:
            return ConversationMemorySnapshot(conversation_id=conversation_id, user_id=parsed_user_id, writable=False)

        row = None
        if redis_is_available():
            try:
                cached = await self._redis.get(self._cache_key(conversation_id))
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8")
                if cached:
                    candidate = json.loads(str(cached))
                    if candidate.get("userId") == (str(parsed_user_id) if parsed_user_id else None):
                        row = candidate
            except (RedisError, json.JSONDecodeError):
                mark_redis_unavailable()

        if row is None:
            row = await ai_repo.get_or_create_ai_conversation_session(
                self._session,
                conversation_id=conversation_id,
                user_id=parsed_user_id,
                ttl_minutes=settings.ai_conversation_memory_ttl_minutes,
            )
        if row is None:
            return ConversationMemorySnapshot(conversation_id=conversation_id, user_id=parsed_user_id, writable=False)

        turns = await ai_repo.get_recent_ai_conversation_turns(
            self._session,
            conversation_id=conversation_id,
            user_id=parsed_user_id,
            limit=settings.ai_conversation_recent_turns,
        )
        return ConversationMemorySnapshot(
            conversation_id=conversation_id,
            user_id=parsed_user_id,
            active_intent=row.get("activeIntent"),
            active_entities=row.get("activeEntities") or {},
            pending_slots=row.get("pendingSlots") or {},
            summary=row.get("summary") or "",
            unresolved_streak=int(row.get("unresolvedStreak") or 0),
            last_failure_reason=row.get("lastFailureReason"),
            handover_offered_at=_parse_datetime(row.get("handoverOfferedAt")),
            recent_turns=turns,
        )

    async def record_turn(
        self,
        *,
        memory: ConversationMemorySnapshot,
        user_message: str,
        response: AIAssistantResponse,
        retrieved_context: dict | None = None,
    ) -> ConversationRecordResult:
        if not memory.writable:
            return ConversationRecordResult(memory, False)

        normalized = normalize_text(user_message)
        explicit_negative = any(term in normalized for term in NEGATIVE_FEEDBACK_TERMS)
        failure_reason = None
        pending_slots: dict = {}
        if explicit_negative:
            failure_reason = "EXPLICIT_NEGATIVE_FEEDBACK"
        elif response.verification_passed is False:
            failure_reason = "VERIFIER_FAILED"
        elif response.needs_clarification:
            pending_slots = {"intent": response.intent, "question": response.clarification_question}
            if memory.pending_slots.get("intent") == response.intent:
                failure_reason = "REPEATED_CLARIFICATION"

        ignored_intents = {"OUT_OF_SCOPE", "UNSAFE_REQUEST", "UNSUPPORTED_REQUEST", "SMALL_TALK"}
        if response.intent in ignored_intents and not explicit_negative:
            failure_reason = None
            pending_slots = {}

        unresolved_streak = memory.unresolved_streak + 1 if failure_reason else 0
        active_intent = (
            memory.active_intent
            if response.intent in ignored_intents
            else (response.intent or memory.active_intent)
        )
        active_entities = active_entities_from_context(
            retrieved_context or {},
            memory.active_entities,
            preferred_products=response.recommended_products or None,
        )
        now = datetime.now(timezone.utc)
        offered_at = memory.handover_offered_at
        cooldown = timedelta(minutes=max(1, settings.ai_handover_cooldown_minutes))
        cooldown_elapsed = offered_at is None or now - offered_at >= cooldown
        should_offer = (
            unresolved_streak >= max(1, settings.ai_handover_failure_threshold)
            and cooldown_elapsed
        )
        if should_offer:
            offered_at = now

        summary = _summary(active_intent, active_entities)
        updated = await ai_repo.update_ai_conversation_session(
            self._session,
            conversation_id=memory.conversation_id,
            user_id=memory.user_id,
            active_intent=active_intent,
            active_entities=active_entities,
            pending_slots=pending_slots,
            summary=summary,
            unresolved_streak=unresolved_streak,
            last_failure_reason=failure_reason,
            handover_offered_at=offered_at,
            ttl_minutes=settings.ai_conversation_memory_ttl_minutes,
        )
        snapshot = ConversationMemorySnapshot(
            conversation_id=memory.conversation_id,
            user_id=memory.user_id,
            active_intent=active_intent,
            active_entities=active_entities,
            pending_slots=pending_slots,
            summary=summary,
            unresolved_streak=unresolved_streak,
            last_failure_reason=failure_reason,
            handover_offered_at=offered_at,
            recent_turns=memory.recent_turns,
            writable=updated,
        )
        if updated and redis_is_available():
            try:
                await self._redis.set(
                    self._cache_key(memory.conversation_id),
                    json.dumps(
                        {
                            "userId": str(memory.user_id) if memory.user_id else None,
                            "activeIntent": active_intent,
                            "activeEntities": active_entities,
                            "pendingSlots": pending_slots,
                            "summary": summary,
                            "unresolvedStreak": unresolved_streak,
                            "lastFailureReason": failure_reason,
                            "handoverOfferedAt": offered_at.isoformat() if offered_at else None,
                        },
                        ensure_ascii=False,
                    ),
                    ex=max(60, settings.ai_conversation_memory_ttl_minutes * 60),
                )
            except RedisError:
                mark_redis_unavailable()
        return ConversationRecordResult(snapshot, should_offer, failure_reason)

    async def support_contact(self) -> dict:
        store = await get_store_info(self._session)
        return {
            "phone": getattr(store, "hotline", None),
            "email": getattr(store, "email", None),
        }
