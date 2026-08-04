import argparse
import json
import re
from pathlib import Path


CATEGORY_RANGES = (
    (1, 15, "product_comparison_basic"),
    (16, 30, "product_comparison_price"),
    (31, 45, "product_comparison_specification"),
    (46, 60, "product_comparison_design"),
    (61, 75, "product_comparison_durability"),
    (76, 90, "product_comparison_warranty"),
    (91, 105, "product_comparison_need"),
    (106, 120, "product_comparison_audience"),
    (121, 135, "product_comparison_experience"),
    (136, 150, "product_comparison_popularity"),
    (151, 165, "product_comparison_availability"),
    (166, 180, "product_comparison_brand"),
    (181, 200, "product_comparison_multiple"),
    (201, 215, "product_comparison_objective"),
    (216, 230, "product_comparison_ambiguous"),
    (231, 250, "product_comparison_advanced"),
)

EXCLUDED_QUESTIONS = {1, 10, 16, 20, 66, 167, 177}
STOCK_QUESTIONS = {151, 152, 153, 157, 159, 162}
SHIPPING_QUESTIONS = {155, 156, 164}
CATALOG_QUESTIONS = {154, 160, 161}
POLICY_OR_CATALOG_QUESTIONS = {158, 165}
PRICE_FLEXIBLE_QUESTIONS = {*range(16, 31), 184, 199, 241, 248}

PLANNED_QUESTIONS = {
    8,
    *range(27, 31),
    *range(61, 76),
    *range(79, 84),
    *range(87, 91),
    *range(134, 151),
    *range(155, 166),
    *range(168, 181),
    *range(193, 201),
    *range(231, 251),
}


def category_for(source_number: int) -> str:
    for start, end, category in CATEGORY_RANGES:
        if start <= source_number <= end:
            return category
    raise ValueError(f"Câu hỏi ngoài phạm vi đánh số: {source_number}")


def expected_for(source_number: int) -> tuple[list[str], str | None]:
    if source_number == 163:
        return ["STORE_POLICY"], "DETERMINISTIC"
    if source_number in STOCK_QUESTIONS:
        return ["STOCK_AVAILABILITY", "PRODUCT_COMPARISON", "PRODUCT_SEARCH"], None
    if source_number in SHIPPING_QUESTIONS:
        return [
            "SHIPPING_LOOKUP",
            "STOCK_AVAILABILITY",
            "PRODUCT_COMPARISON",
            "PRODUCT_RECOMMENDATION",
            "PRODUCT_SEARCH",
        ], None
    if source_number in CATALOG_QUESTIONS:
        return ["PRODUCT_SEARCH", "PRODUCT_COMPARISON", "PRODUCT_RECOMMENDATION"], None
    if source_number in POLICY_OR_CATALOG_QUESTIONS:
        return ["STORE_POLICY", "PRODUCT_SEARCH", "PRODUCT_COMPARISON", "PRODUCT_RECOMMENDATION"], None
    if 76 <= source_number <= 90:
        return ["PRODUCT_COMPARISON", "WARRANTY_POLICY", "STORE_POLICY", "PRODUCT_RECOMMENDATION"], None
    if source_number in PRICE_FLEXIBLE_QUESTIONS:
        return ["PRODUCT_COMPARISON", "PRICE_AND_PROMOTION", "PRODUCT_RECOMMENDATION"], None
    return ["PRODUCT_COMPARISON", "PRODUCT_RECOMMENDATION"], "MODEL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Nhập nhóm câu hỏi so sánh sản phẩm vào fixture AI.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    questions: list[tuple[int, str]] = []
    for line in args.source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if match:
            questions.append((int(match.group(1)), match.group(2)))

    if [number for number, _ in questions] != list(range(1, 251)):
        raise ValueError("Nguồn phải có đủ và đúng thứ tự 250 câu đánh số.")

    rows = []
    for source_number, message in questions:
        if source_number in EXCLUDED_QUESTIONS:
            continue
        expected_intents, expected_route = expected_for(source_number)
        support_level = "PLANNED" if source_number in PLANNED_QUESTIONS else "CLARIFY"
        row = {
            "id": f"product_comparison_domain_{source_number:03d}",
            "category": category_for(source_number),
            "message": message,
            "expected_intents": expected_intents,
            "required_tools": ["search_products"],
            "notes": f"source_question={source_number}; support_level={support_level}",
        }
        if expected_route is not None:
            row["expected_route"] = expected_route
        if 216 <= source_number <= 230:
            row["expected_needs_clarification"] = True
        if source_number == 163:
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
