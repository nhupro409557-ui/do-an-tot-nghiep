import argparse
import json
import re
from pathlib import Path


CATEGORY_RANGES = (
    (1, 20, "price_promotion_basic"),
    (21, 40, "price_promotion_budget_search"),
    (41, 60, "price_promotion_discount"),
    (61, 80, "price_promotion_timing"),
    (81, 100, "price_promotion_voucher"),
    (101, 120, "price_promotion_conditions"),
    (121, 135, "price_promotion_stacking"),
    (136, 155, "price_promotion_bundle_gift"),
    (156, 175, "price_promotion_member"),
    (176, 195, "price_promotion_payment"),
    (196, 210, "price_promotion_shipping"),
    (211, 225, "price_promotion_price_change"),
    (226, 240, "price_promotion_invoice_tax"),
    (241, 255, "price_promotion_refund_return"),
    (256, 270, "price_promotion_ambiguous"),
    (271, 295, "price_promotion_advanced"),
)

# 12 thuộc biến thể kích cỡ ngoài catalog điện tử; 53–54 thuộc mỹ phẩm/quần áo.
# 23, 24 và 51 đã có nguyên văn trong các fixture sản phẩm trước đó.
EXCLUDED_QUESTIONS = {12, 23, 24, 51, 53, 54}

LIVE_QUESTIONS = {
    21,
    22,
    25,
    27,
    28,
    29,
    30,
    31,
    32,
    35,
    47,
    48,
    49,
    50,
    52,
    161,
    164,
    197,
    198,
    201,
    226,
    227,
}

CLARIFY_QUESTIONS = {
    *range(1, 7),
    10,
    11,
    *range(13, 16),
    19,
    26,
    33,
    34,
    *range(37, 47),
    *range(55, 81),
    *range(83, 97),
    *range(101, 156),
    *range(156, 161),
    *range(162, 176),
    196,
    *range(199, 211),
    *range(211, 226),
    *range(229, 256),
    *range(256, 296),
}


def category_for(source_number: int) -> str:
    for start, end, category in CATEGORY_RANGES:
        if start <= source_number <= end:
            return category
    raise ValueError(f"Câu hỏi ngoài phạm vi đánh số: {source_number}")


def expected_for(category: str) -> tuple[list[str], str | None]:
    if category == "price_promotion_discount":
        return ["PRICE_AND_PROMOTION"], "DETERMINISTIC"
    if category == "price_promotion_timing":
        return ["PRICE_AND_PROMOTION"], "DETERMINISTIC"
    if category == "price_promotion_voucher":
        return ["VOUCHER_SUPPORT", "PRICE_AND_PROMOTION", "STORE_POLICY"], "DETERMINISTIC"
    if category in {"price_promotion_conditions", "price_promotion_stacking"}:
        return ["VOUCHER_SUPPORT", "PRICE_AND_PROMOTION", "STORE_POLICY", "LOYALTY"], "DETERMINISTIC"
    if category == "price_promotion_member":
        return ["VOUCHER_SUPPORT", "LOYALTY", "PRICE_AND_PROMOTION", "STORE_POLICY"], "DETERMINISTIC"
    if category in {"price_promotion_payment", "price_promotion_shipping", "price_promotion_invoice_tax"}:
        return ["STORE_POLICY", "PRICE_AND_PROMOTION"], "DETERMINISTIC"
    if category == "price_promotion_price_change":
        return ["PRICE_AND_PROMOTION", "STORE_POLICY", "STOCK_AVAILABILITY"], "DETERMINISTIC"
    if category == "price_promotion_refund_return":
        return ["VOUCHER_SUPPORT", "STORE_POLICY", "PRICE_AND_PROMOTION", "LOYALTY"], "DETERMINISTIC"
    if category == "price_promotion_ambiguous":
        return ["PRICE_AND_PROMOTION"], "DETERMINISTIC"
    if category == "price_promotion_budget_search":
        return ["PRICE_AND_PROMOTION", "PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON"], None
    if category == "price_promotion_bundle_gift":
        return [
            "PRICE_AND_PROMOTION",
            "STORE_POLICY",
            "PRODUCT_SEARCH",
            "PRODUCT_RECOMMENDATION",
            "WARRANTY_POLICY",
        ], None
    if category == "price_promotion_advanced":
        return [
            "PRICE_AND_PROMOTION",
            "STORE_POLICY",
            "PRODUCT_RECOMMENDATION",
            "PRODUCT_COMPARISON",
            "LOYALTY",
            "PRODUCT_SEARCH",
        ], None
    return ["PRICE_AND_PROMOTION", "STORE_POLICY", "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"], None


def main() -> None:
    parser = argparse.ArgumentParser(description="Nhập nhóm câu hỏi giá và khuyến mãi vào fixture AI.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    questions: list[tuple[int, str]] = []
    for line in args.source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if match:
            questions.append((int(match.group(1)), match.group(2)))

    if [number for number, _ in questions] != list(range(1, 296)):
        raise ValueError("Nguồn phải có đủ và đúng thứ tự 295 câu đánh số.")

    rows = []
    for source_number, message in questions:
        if source_number in EXCLUDED_QUESTIONS:
            continue
        category = category_for(source_number)
        expected_intents, expected_route = expected_for(category)
        support_level = (
            "LIVE"
            if source_number in LIVE_QUESTIONS
            else "CLARIFY"
            if source_number in CLARIFY_QUESTIONS
            else "PLANNED"
        )
        row = {
            "id": f"price_promotion_domain_{source_number:03d}",
            "category": category,
            "message": message,
            "expected_intents": expected_intents,
            "required_tools": ["search_products"],
            "notes": f"source_question={source_number}; support_level={support_level}",
        }
        if expected_route is not None:
            row["expected_route"] = expected_route
        if 256 <= source_number <= 270:
            row["expected_needs_clarification"] = True
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Đã ghi {len(rows)} câu vào {args.output}")


if __name__ == "__main__":
    main()
