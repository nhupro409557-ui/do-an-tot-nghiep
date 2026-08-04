import argparse
import json
import re
from pathlib import Path


CATEGORY_RANGES = (
    (1, 15, "product_advice_basic"),
    (16, 35, "product_advice_need"),
    (36, 55, "product_advice_budget"),
    (56, 75, "product_advice_audience"),
    (76, 95, "product_advice_attribute"),
    (96, 115, "product_advice_brand"),
    (116, 135, "product_advice_comparison"),
    (136, 150, "product_advice_replacement"),
    (151, 170, "product_advice_gift"),
    (171, 190, "product_advice_review"),
    (191, 205, "product_advice_long_term"),
    (206, 220, "product_advice_ambiguous"),
    (221, 245, "product_advice_advanced"),
)

EXCLUDED_QUESTIONS = {103, 162}
POLICY_QUESTIONS = {52, 165, 166}
COMPARISON_QUESTIONS = {
    101,
    102,
    112,
    113,
    114,
    *range(116, 136),
    138,
    144,
    150,
    187,
    202,
    228,
    230,
}
FLEXIBLE_COMPARISON_QUESTIONS = {46, 47, 48}
REPLACEMENT_QUESTIONS = set(range(136, 151))
REVIEW_QUESTIONS = set(range(171, 191))
LONG_TERM_QUESTIONS = set(range(191, 205))

PLANNED_QUESTIONS = {
    2,
    3,
    6,
    46,
    47,
    49,
    51,
    53,
    54,
    55,
    71,
    72,
    74,
    75,
    *range(96, 101),
    *range(104, 116),
    165,
    *range(171, 205),
    *range(221, 246),
}
LIVE_QUESTIONS = {7, 37, 52, 166, 205}


def category_for(source_number: int) -> str:
    for start, end, category in CATEGORY_RANGES:
        if start <= source_number <= end:
            return category
    raise ValueError(f"Câu hỏi ngoài phạm vi đánh số: {source_number}")


def expected_for(source_number: int) -> tuple[list[str], str | None]:
    if source_number in POLICY_QUESTIONS:
        return ["STORE_POLICY"], "DETERMINISTIC"
    if source_number == 205:
        return ["WARRANTY_POLICY"], "MODEL"
    if source_number == 7:
        return ["PRODUCT_SEARCH"], "MODEL"
    if source_number in {37, 49}:
        return ["PRICE_AND_PROMOTION"], "DETERMINISTIC"
    if source_number in FLEXIBLE_COMPARISON_QUESTIONS:
        return ["PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON", "PRICE_AND_PROMOTION"], None
    if source_number in REPLACEMENT_QUESTIONS:
        return ["PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON", "STOCK_AVAILABILITY"], None
    if source_number in COMPARISON_QUESTIONS:
        return ["PRODUCT_COMPARISON", "PRODUCT_RECOMMENDATION"], "MODEL"
    if source_number in REVIEW_QUESTIONS:
        return ["PRODUCT_REVIEW", "PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON"], None
    if source_number in LONG_TERM_QUESTIONS:
        return ["PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON"], "MODEL"
    return ["PRODUCT_RECOMMENDATION"], "MODEL"


def support_level_for(source_number: int) -> str:
    if source_number in PLANNED_QUESTIONS:
        return "PLANNED"
    if source_number in LIVE_QUESTIONS:
        return "LIVE"
    return "CLARIFY"


def main() -> None:
    parser = argparse.ArgumentParser(description="Nhập nhóm câu hỏi tư vấn sản phẩm vào fixture AI.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    questions: list[tuple[int, str]] = []
    for line in args.source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if match:
            questions.append((int(match.group(1)), match.group(2)))

    if [number for number, _ in questions] != list(range(1, 246)):
        raise ValueError("Nguồn phải có đủ và đúng thứ tự 245 câu đánh số.")

    rows = []
    for source_number, message in questions:
        if source_number in EXCLUDED_QUESTIONS:
            continue
        expected_intents, expected_route = expected_for(source_number)
        support_level = support_level_for(source_number)
        row = {
            "id": f"product_advice_domain_{source_number:03d}",
            "category": category_for(source_number),
            "message": message,
            "expected_intents": expected_intents,
            "required_tools": ["search_products"],
            "notes": f"source_question={source_number}; support_level={support_level}",
        }
        if expected_route is not None:
            row["expected_route"] = expected_route
        if 206 <= source_number <= 220:
            row["expected_needs_clarification"] = True
        if source_number in POLICY_QUESTIONS:
            row["required_tools"] = []
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Đã ghi {len(rows)} câu vào {args.output}")


if __name__ == "__main__":
    main()
