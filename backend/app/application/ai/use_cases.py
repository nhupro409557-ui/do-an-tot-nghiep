import json
import re
import unicodedata
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.schemas import AIAssistantRequest, AIAssistantResponse
from app.config import settings
from app.infrastructure.database.models import AIContextLog


REFUSAL_TEXT = (
    "Rất tiếc, mình là trợ lý mua sắm của Echophone nên không thể hỗ trợ nội dung này. "
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


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return normalized.replace("đ", "d")


def as_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def is_in_sales_scope(message: str) -> bool:
    normalized = normalize_text(message)
    return any(term in normalized for term in ALLOWED_SALES_TERMS)


def is_blocked(message: str) -> bool:
    normalized = normalize_text(message)
    return any(term in normalized for term in BLOCKED_TERMS)


def classify_intent(message: str) -> str:
    normalized = normalize_text(message)
    if any(term in normalized for term in ["don hang", "ma don", "order", "van chuyen", "dang o dau"]):
        return "ORDER_LOOKUP"
    if any(term in normalized for term in ["diem", "tich diem", "loyalty", "hang thanh vien", "voucher"]):
        return "LOYALTY"
    if any(term in normalized for term in ["bao hanh", "doi tra", "hoan tien", "giao hang", "bao mat", "chinh sach"]):
        return "POLICY"
    if any(term in normalized for term in ["khieu nai", "buc", "tuc", "qua te", "that vong", "nhan vien"]):
        return "COMPLAINT"
    return "PRODUCT_ADVICE"


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
    match = re.search(r"\b(?:ORD|DH|ORDER)[-_]?[A-Z0-9]{4,}\b", message, flags=re.IGNORECASE)
    return match.group(0).upper().replace("_", "-") if match else None


def price_intent_from_message(message: str) -> tuple[int | None, int | None]:
    normalized = normalize_text(message).replace(",", ".")
    price_pattern = r"(\d+(?:\.\d+)?)\s*(trieu|tr|cu|m)?(?:\s*(\d{1,3}))?"

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


class AIAssistantUseCase:
    def __init__(self, *, session: AsyncSession, redis: Redis) -> None:
        self._session = session
        self._redis = redis

    async def execute(self, *, user_id: str | None, request: AIAssistantRequest) -> AIAssistantResponse:
        await self._enforce_rate_limit(user_id=user_id)

        if is_blocked(request.message) or not is_in_sales_scope(request.message):
            response = AIAssistantResponse(
                conversation_id=request.conversation_id,
                answer=REFUSAL_TEXT,
                refused=True,
                refusal_reason="OUT_OF_SALES_SCOPE",
                intent="REFUSAL",
            )
            await self._log(request=request, response=response, user_id=user_id)
            return response

        await self._cache_dynamic_context(request)
        intent = classify_intent(request.message)
        retrieved_context = await self._retrieve_context(
            intent=intent,
            message=request.message,
            user_id=user_id,
            request=request,
        )
        answer = await self._generate_answer(
            request,
            intent=intent,
            retrieved_context=retrieved_context,
        )

        if is_blocked(answer):
            answer = REFUSAL_TEXT

        response = AIAssistantResponse(
            conversation_id=request.conversation_id,
            answer=answer,
            intent=intent,
            handover_recommended=bool(retrieved_context.get("handover_recommended")),
            sources=self._sources_for_context(retrieved_context),
            recommended_products=retrieved_context.get("products", [])[:3],
        )
        await self._log(request=request, response=response, user_id=user_id)
        return response

    async def _cache_dynamic_context(self, request: AIAssistantRequest) -> None:
        cache_key = f"ai:session:{request.conversation_id}"
        try:
            await self._redis.setex(
                cache_key,
                60 * 30,
                json.dumps(request.dynamic_context.model_dump(mode="json"), ensure_ascii=False),
            )
        except RedisError:
            pass

    async def _retrieve_context(
        self,
        *,
        intent: str,
        message: str,
        user_id: str | None,
        request: AIAssistantRequest,
    ) -> dict:
        if intent == "POLICY":
            return {"policies": await self._find_policies(message)}
        if intent == "ORDER_LOOKUP":
            return {"order": await self._find_order(message, user_id)}
        if intent == "LOYALTY":
            return {
                "loyalty": request.dynamic_context.loyalty.model_dump(mode="json")
                if request.dynamic_context.loyalty
                else None,
                "cart_items": [item.model_dump(mode="json") for item in request.dynamic_context.cart_items],
            }
        if intent == "COMPLAINT":
            return {
                "handover_recommended": True,
                "reason": "Customer complaint or negative sentiment detected.",
            }
        return {"products": await self._find_products(message)}

    async def _find_products(self, message: str) -> list[dict]:
        tokens = keyword_tokens(message)
        normalized = normalize_text(message)
        if "laptop" in normalized or "may tinh" in normalized or "code" in normalized:
            tokens.extend(["laptop", "ssd", "ram"])
        if "dien thoai" in normalized or "smartphone" in normalized:
            tokens.extend(["dien", "thoai"])
        tokens = [token for token in list(dict.fromkeys(tokens))[:7] if not re.search(r"\d", token)]
        min_price, max_price = price_intent_from_message(message)

        result = await self._session.execute(
            text(
                """
                SELECT p.id::text, p.slug, p.name, p.brand, p.price, p.sale_price AS "salePrice",
                       p.image_url AS "imageUrl", p.description, p.specifications,
                       c.name AS "categoryName", c.slug AS "categorySlug",
                       p.rating, p.review_count AS "reviewCount"
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE p.status = 'ACTIVE'
                ORDER BY p.is_featured DESC, p.rating DESC NULLS LAST, p.created_at DESC
                LIMIT 200
                """
            )
        )
        products = [self._clean_row(dict(row._mapping)) for row in result]
        ranked: list[tuple[int, dict]] = []

        wants_phone = "dien thoai" in normalized or "smartphone" in normalized or "phone" in normalized
        wants_laptop = "laptop" in normalized or "may tinh" in normalized or "code" in normalized

        for product in products:
            price = float(product.get("price") or 0)
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue

            haystack = normalize_text(
                " ".join(
                    str(product.get(field) or "")
                    for field in ["name", "brand", "description", "categoryName", "categorySlug"]
                )
                + " "
                + json.dumps(product.get("specifications") or {}, ensure_ascii=False)
            )

            score = 0
            if wants_phone and ("dien thoai" in haystack or "smartphone" in haystack or product.get("categorySlug") == "smartphones"):
                score += 40
            if wants_laptop and ("laptop" in haystack or product.get("categorySlug") == "laptops"):
                score += 40
            for token in tokens:
                if token in haystack:
                    score += 12
            if min_price is not None or max_price is not None:
                score += 20
            score += int(float(product.get("rating") or 0))

            if score > 0 or min_price is not None or max_price is not None:
                ranked.append((score, product))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [product for _, product in ranked[:5]]

    async def _find_policies(self, message: str) -> list[dict]:
        normalized = normalize_text(message)
        code_hints = []
        if "bao hanh" in normalized:
            code_hints.append("warranty")
        if "giao hang" in normalized or "van chuyen" in normalized:
            code_hints.append("shipping")
        if "doi tra" in normalized or "hoan tien" in normalized:
            code_hints.append("return")
        if "bao mat" in normalized:
            code_hints.append("privacy")

        if code_hints:
            params = {f"code_{index}": code for index, code in enumerate(code_hints)}
            placeholders = ", ".join(f":code_{index}" for index in range(len(code_hints)))
            result = await self._session.execute(
                text(
                    f"""
                    SELECT code, title, regexp_replace(content, '<[^>]+>', ' ', 'g') AS content
                    FROM policies
                    WHERE is_active = TRUE
                      AND (
                        status = 'PUBLISHED'
                        OR (status = 'SCHEDULED' AND scheduled_at IS NOT NULL AND scheduled_at <= NOW())
                      )
                      AND code IN ({placeholders})
                    ORDER BY COALESCE(published_at, updated_at) DESC, updated_at DESC
                    LIMIT 4
                    """
                ),
                params,
            )
        else:
            result = await self._session.execute(
                text(
                    """
                    SELECT code, title, regexp_replace(content, '<[^>]+>', ' ', 'g') AS content
                    FROM policies
                    WHERE is_active = TRUE
                      AND (
                        status = 'PUBLISHED'
                        OR (status = 'SCHEDULED' AND scheduled_at IS NOT NULL AND scheduled_at <= NOW())
                      )
                    ORDER BY COALESCE(published_at, updated_at) DESC, updated_at DESC
                    LIMIT 4
                    """
                )
            )
        return [self._clean_row(dict(row._mapping)) for row in result]

    async def _find_order(self, message: str, user_id: str | None) -> dict:
        if not user_id:
            return {"needs_auth": True}

        code = order_code_from_message(message)
        if not code:
            return {"needs_order_code": True}

        result = await self._session.execute(
            text(
                """
                SELECT o.order_code AS "orderCode", o.status, o.payment_status AS "paymentStatus",
                       o.total_amount AS "totalAmount", o.loyalty_points_earned AS "pointsEarned",
                       o.loyalty_points_used AS "pointsUsed", o.created_at AS "createdAt",
                       COALESCE(jsonb_agg(jsonb_build_object(
                         'productName', oi.product_name,
                         'quantity', oi.quantity,
                         'totalPrice', oi.total_price
                       )) FILTER (WHERE oi.id IS NOT NULL), '[]'::jsonb) AS items
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                WHERE o.user_id = :user_id AND upper(o.order_code) = :order_code
                GROUP BY o.id
                LIMIT 1
                """
            ),
            {"user_id": user_id, "order_code": code},
        )
        row = result.first()
        return self._clean_row(dict(row._mapping)) if row else {"not_found": True, "order_code": code}

    async def _generate_answer(
        self,
        request: AIAssistantRequest,
        *,
        intent: str,
        retrieved_context: dict,
    ) -> str:
        if settings.gemini_api_key:
            try:
                return await self._call_gemini(
                    request,
                    intent=intent,
                    retrieved_context=retrieved_context,
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                pass

        return self._fallback_answer(intent=intent, retrieved_context=retrieved_context)

    async def _call_gemini(
        self,
        request: AIAssistantRequest,
        *,
        intent: str,
        retrieved_context: dict,
    ) -> str:
        prompt = (
            "Bạn là trợ lý mua sắm của Echophone. Luôn trả lời bằng tiếng Việt có dấu đầy đủ, "
            "ngắn gọn, tự nhiên và thân thiện. Không được trả lời tiếng Việt không dấu. "
            "Chỉ sử dụng dữ liệu trong context. Không bịa giá, cấu hình, chính sách hoặc trạng thái đơn hàng. "
            "Nếu thiếu xác thực hoặc thiếu mã đơn hàng, hãy yêu cầu khách đăng nhập/cung cấp mã đơn. "
            "Nếu khách khiếu nại hoặc bức xúc, xin lỗi ngắn gọn và đề nghị chuyển nhân viên hỗ trợ. "
            "Không thảo luận chính trị, tôn giáo, thù ghét, tình dục, nguy hiểm, hack/lừa đảo.\n"
            f"Intent: {intent}\n"
            f"Dynamic context: {json.dumps(request.dynamic_context.model_dump(mode='json'), ensure_ascii=False, default=as_jsonable)}\n"
            f"Database context: {json.dumps(retrieved_context, ensure_ascii=False, default=as_jsonable)}\n"
            f"Customer question: {request.message}"
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": settings.gemini_api_key,
                },
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _fallback_answer(self, *, intent: str, retrieved_context: dict) -> str:
        if intent == "ORDER_LOOKUP":
            order = retrieved_context.get("order") or {}
            if order.get("needs_auth"):
                return "Bạn vui lòng đăng nhập để mình kiểm tra đơn hàng của riêng bạn."
            if order.get("needs_order_code"):
                return "Bạn vui lòng cung cấp mã đơn hàng để mình kiểm tra trạng thái chính xác."
            if order.get("not_found"):
                return "Mình chưa tìm thấy đơn hàng này trong tài khoản của bạn."
        if intent == "POLICY":
            policies = retrieved_context.get("policies") or []
            if policies:
                return f"{policies[0].get('title')}: {policies[0].get('content')}"
        if intent == "LOYALTY":
            loyalty = retrieved_context.get("loyalty")
            if loyalty:
                return f"Bạn đang có {loyalty.get('points_balance', 0)} điểm, hạng {loyalty.get('tier')}."
            return "Bạn vui lòng đăng nhập để mình kiểm tra điểm tích lũy."
        if intent == "COMPLAINT":
            return "Mình rất tiếc vì trải nghiệm của bạn chưa tốt. Mình sẽ đề xuất chuyển nhân viên hỗ trợ để xử lý nhanh hơn."
        products = retrieved_context.get("products") or []
        if products:
            names = ", ".join(product["name"] for product in products[:3])
            return f"Mình tìm thấy một số sản phẩm phù hợp: {names}."
        return "Mình chưa tìm thấy dữ liệu phù hợp. Bạn có thể nói rõ hơn nhu cầu, ngân sách hoặc sản phẩm bạn quan tâm."

    def _sources_for_context(self, context: dict) -> list[str]:
        sources = []
        if context.get("products"):
            sources.append("products")
        if context.get("policies"):
            sources.append("policies")
        if context.get("order"):
            sources.append("orders")
        if context.get("loyalty"):
            sources.append("loyalty")
        return sources

    def _clean_row(self, row: dict) -> dict:
        return json.loads(json.dumps(row, default=as_jsonable, ensure_ascii=False))

    async def _enforce_rate_limit(self, *, user_id: str | None) -> None:
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
            return

    async def _log(
        self,
        *,
        request: AIAssistantRequest,
        response: AIAssistantResponse,
        user_id: str | None,
    ) -> None:
        try:
            parsed_user_id = UUID(user_id) if user_id else None
        except ValueError:
            parsed_user_id = None

        log = AIContextLog(
            id=uuid4(),
            user_id=parsed_user_id,
            conversation_id=request.conversation_id,
            request_scope="SALES_ASSISTANT",
            user_message=request.message,
            assistant_response=response.answer,
            refusal_reason=response.refusal_reason,
            dynamic_context={
                **request.dynamic_context.model_dump(mode="json"),
                "intent": response.intent,
                "sources": response.sources,
            },
            model_provider=request.model_provider,
            model_name=request.model_name,
        )
        self._session.add(log)
        await self._session.commit()
