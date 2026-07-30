import re
import unicodedata

from app.application.ai.contracts import ResponseCard, ResponseSource, VerificationResult


PRODUCT_INTENTS = {
    "PRODUCT_SEARCH",
    "PRODUCT_RECOMMENDATION",
    "PRODUCT_COMPARISON",
    "PRICE_AND_PROMOTION",
    "STOCK_AVAILABILITY",
}


def _version(value) -> str | None:
    return str(value) if value is not None else None


def _effective_price(product: dict) -> int:
    sale_price = int(float(product.get("salePrice") or 0))
    return sale_price if sale_price > 0 else int(float(product.get("price") or 0))


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", normalized.replace("đ", "d")).strip()


def _product_mentioned(answer: str, name: str) -> bool:
    normalized_answer = _normalize(answer)
    normalized_name = _normalize(name)
    if normalized_name in normalized_answer:
        return True
    tokens = normalized_name.split()
    prefix = " ".join(tokens[: min(3, len(tokens))])
    return len(prefix) >= 4 and prefix in normalized_answer


def verify_response(*, intent: str, answer: str, context: dict) -> VerificationResult:
    errors: list[str] = []
    cards: list[ResponseCard] = []
    sources: list[ResponseSource] = []
    products = context.get("products") or []
    seen_ids: set[str] = set()
    matched_products = [
        product
        for product in products[:5]
        if _product_mentioned(answer, str(product.get("name") or ""))
    ]

    if intent in PRODUCT_INTENTS and products and not matched_products:
        errors.append("PRODUCT_NAME_MISSING")
    if intent == "PRODUCT_COMPARISON" and len(products) >= 2:
        for product in products[:2]:
            if not _product_mentioned(answer, str(product.get("name") or "")):
                errors.append("COMPARISON_PRODUCT_MISSING")
                break

    query_plan = context.get("query_plan") or {}
    constraints = query_plan.get("constraints") or {}
    priorities = set(constraints.get("priorities") or [])
    if intent == "PRODUCT_COMPARISON" and "battery" in priorities:
        compact_answer = re.sub(r"[.\s]", "", answer.lower())
        known_batteries: list[int] = []
        for product in products[:2]:
            specifications = product.get("specifications") or {}
            match = re.search(r"(\d{4,5})\s*mah", _normalize(str(specifications.get("battery") or "")))
            if match:
                known_batteries.append(int(match.group(1)))
        claimed_batteries = {
            int(value.replace(".", ""))
            for value in re.findall(r"(\d{1,2}(?:\.\d{3})|\d{4,5})\s*mah", answer.lower())
        }
        if any(str(value) not in compact_answer for value in known_batteries):
            errors.append("BATTERY_FACT_MISSING")
        if claimed_batteries and any(value not in known_batteries for value in claimed_batteries):
            errors.append("BATTERY_CLAIM_MISMATCH")

    requested_colors = constraints.get("colors") or []
    if requested_colors and products:
        normalized_answer = _normalize(answer)
        if not any(_normalize(str(color)) in normalized_answer for color in requested_colors):
            errors.append("COLOR_FACT_MISSING")
        if constraints.get("require_in_stock") and "còn màu" in normalized_answer:
            for product in products[:2 if intent == "PRODUCT_COMPARISON" else 3]:
                variants = product.get("matchedVariants") or []
                if not variants or not any(int(variant.get("availableStock") or 0) > 0 for variant in variants):
                    errors.append("VARIANT_STOCK_CLAIM_MISMATCH")
                    break

    for product in matched_products[:3]:
        product_id = str(product.get("id") or "")
        name = str(product.get("name") or "").strip()
        if not product_id or not name or product_id in seen_ids:
            errors.append("INVALID_PRODUCT_CARD")
            continue
        seen_ids.add(product_id)
        is_used = bool(product.get("isUsed"))
        cards.append(
            ResponseCard(
                type="used_product" if is_used else "product",
                id=product_id,
                reason="Khớp nhu cầu và dữ liệu hiện hành của cửa hàng.",
            )
        )
        sources.append(
            ResponseSource(
                type="used_product_snapshot" if is_used else "product_snapshot",
                id=product_id,
                updated_at=_version(product.get("updatedAt")),
            )
        )

    if intent in PRODUCT_INTENTS and products and not cards:
        errors.append("PRODUCT_CARD_NOT_GROUNDED")

    if intent == "STOCK_AVAILABILITY" and products:
        stocks = [int(product.get("availableStock") or 0) for product in products]
        normalized_answer = answer.lower()
        if "còn hàng" in normalized_answer and not any(stock > 0 for stock in stocks):
            errors.append("STOCK_CLAIM_MISMATCH")
        if "hết hàng" in normalized_answer and any(stock > 0 for stock in stocks):
            errors.append("STOCK_CLAIM_MISMATCH")

    if intent == "PRICE_AND_PROMOTION" and products:
        known_prices: set[int] = set()
        for product in products:
            known_prices.add(_effective_price(product))
            original_price = int(float(product.get("price") or 0))
            if original_price > 0:
                known_prices.add(original_price)
            for variant in product.get("variants") or []:
                for field in ("price", "salePrice"):
                    value = int(float(variant.get(field) or 0))
                    if value > 0:
                        known_prices.add(value)
        price_claim_pattern = (
            r"(?<!trợ )(?<!trị )(?<!định )"
            r"giá(?: bán| hiện tại| ưu đãi| gốc)?[^\d]{0,20}([\d.]{4,})\s*(?:đ|₫)"
        )
        for raw in re.findall(price_claim_pattern, answer.lower()):
            value = int(re.sub(r"\D", "", raw) or 0)
            if value and value not in known_prices:
                errors.append("PRICE_CLAIM_MISMATCH")
                break
        compact_answer = re.sub(r"\D", "", answer)
        if matched_products and not any(
            str(_effective_price(product)) in compact_answer
            for product in matched_products[:3]
        ):
            errors.append("CURRENT_PRICE_MISSING")

    order = context.get("order") or {}
    if order.get("orderCode"):
        if str(order["orderCode"]).lower() not in answer.lower():
            errors.append("ORDER_CODE_MISSING")
        sources.append(
            ResponseSource(
                type="order_snapshot",
                id=str(order["orderCode"]),
                updated_at=_version(order.get("updatedAt")),
            )
        )

    after_sales = context.get("after_sales") or {}
    if after_sales.get("requestCode"):
        if str(after_sales["requestCode"]).lower() not in answer.lower():
            errors.append("AFTER_SALES_CODE_MISSING")
        sources.append(
            ResponseSource(
                type="after_sales_snapshot",
                id=str(after_sales["requestCode"]),
                updated_at=_version(after_sales.get("updatedAt")),
            )
        )

    loyalty = context.get("loyalty") or {}
    if loyalty and loyalty.get("pointsBalance") is not None:
        compact_answer = re.sub(r"\D", "", answer)
        if str(loyalty["pointsBalance"]) not in compact_answer:
            errors.append("LOYALTY_BALANCE_MISSING")
        amount_needed = int(loyalty.get("amountToNextTier") or 0)
        if amount_needed > 0 and str(amount_needed) not in compact_answer:
            errors.append("LOYALTY_PROGRESS_MISSING")

    review = context.get("review_insights") or {}
    product = context.get("product") or {}
    if review and product.get("id"):
        sources.append(
            ResponseSource(
                type="product_review_snapshot",
                id=str(product["id"]),
                updated_at=_version(review.get("updatedAt")),
            )
        )

    return VerificationResult(passed=not errors, errors=errors, cards=cards, sources=sources)
