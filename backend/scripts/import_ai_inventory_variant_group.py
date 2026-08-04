import argparse
import json
import re
from pathlib import Path


CATEGORY_RANGES = (
    (1, 15, "inventory_variant_basic_stock"),
    (16, 30, "inventory_variant_quantity"),
    (31, 50, "inventory_variant_versions"),
    (51, 70, "inventory_variant_colors"),
    (71, 90, "inventory_variant_sizes"),
    (91, 110, "inventory_variant_configuration"),
    (111, 130, "inventory_variant_branches"),
    (131, 150, "inventory_variant_restock"),
    (151, 170, "inventory_variant_preorder"),
    (171, 185, "inventory_variant_hold"),
    (186, 200, "inventory_variant_display_open_box"),
    (201, 215, "inventory_variant_discontinued"),
    (216, 230, "inventory_variant_codes"),
    (231, 250, "inventory_variant_combined"),
    (251, 270, "inventory_variant_replacement"),
    (271, 285, "inventory_variant_sync"),
    (286, 300, "inventory_variant_mismatch"),
    (301, 315, "inventory_variant_ambiguous"),
    (316, 335, "inventory_variant_advanced"),
)

# 1, 36, 52, 61 và 251 đã có nguyên văn trong các fixture trước.
# Nhóm 71–90 và các câu size/quần áo/giày rải rác nằm ngoài catalog điện tử.
EXCLUDED_QUESTIONS = {
    1,
    36,
    52,
    61,
    251,
    *range(71, 91),
    116,
    142,
    222,
    232,
    234,
    241,
    255,
    304,
}

LIVE_QUESTIONS = {231, 233, 236, 240, 243, 245}

PLANNED_RANGES = (
    range(151, 186),
    range(271, 301),
    range(316, 336),
)


def category_for(source_number: int) -> str:
    for start, end, category in CATEGORY_RANGES:
        if start <= source_number <= end:
            return category
    raise ValueError(f"Câu hỏi ngoài phạm vi đánh số: {source_number}")


def expected_for(category: str) -> tuple[list[str], str | None]:
    if category in {"inventory_variant_basic_stock", "inventory_variant_quantity"}:
        return ["STOCK_AVAILABILITY", "PRODUCT_SEARCH"], None
    if category in {"inventory_variant_versions", "inventory_variant_colors", "inventory_variant_configuration"}:
        return [
            "PRODUCT_SEARCH",
            "STOCK_AVAILABILITY",
            "STORE_POLICY",
            "PRICE_AND_PROMOTION",
            "PRODUCT_COMPARISON",
            "PRODUCT_RECOMMENDATION",
        ], None
    if category == "inventory_variant_branches":
        return ["STOCK_AVAILABILITY", "STORE_POLICY", "PRODUCT_SEARCH"], None
    if category == "inventory_variant_restock":
        return ["STORE_POLICY", "STOCK_AVAILABILITY", "PRODUCT_RECOMMENDATION", "PRICE_AND_PROMOTION"], None
    if category in {"inventory_variant_preorder", "inventory_variant_hold"}:
        return ["STORE_POLICY", "PRICE_AND_PROMOTION", "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"], None
    if category == "inventory_variant_display_open_box":
        return [
            "PRODUCT_SEARCH",
            "STOCK_AVAILABILITY",
            "USED_PRODUCT_ADVICE",
            "STORE_POLICY",
            "WARRANTY_POLICY",
            "PRICE_AND_PROMOTION",
            "PRODUCT_RECOMMENDATION",
        ], None
    if category == "inventory_variant_discontinued":
        return [
            "PRODUCT_SEARCH",
            "STOCK_AVAILABILITY",
            "PRODUCT_RECOMMENDATION",
            "WARRANTY_POLICY",
            "STORE_POLICY",
            "PRICE_AND_PROMOTION",
        ], None
    if category == "inventory_variant_codes":
        return ["PRODUCT_SEARCH", "STOCK_AVAILABILITY", "STORE_POLICY", "PRODUCT_COMPARISON"], None
    if category == "inventory_variant_combined":
        return [
            "STOCK_AVAILABILITY",
            "PRODUCT_SEARCH",
            "PRICE_AND_PROMOTION",
            "STORE_POLICY",
            "PRODUCT_RECOMMENDATION",
            "PRODUCT_COMPARISON",
        ], None
    if category == "inventory_variant_replacement":
        return [
            "PRODUCT_RECOMMENDATION",
            "STOCK_AVAILABILITY",
            "PRODUCT_SEARCH",
            "PRICE_AND_PROMOTION",
            "STORE_POLICY",
        ], None
    if category in {"inventory_variant_sync", "inventory_variant_mismatch"}:
        return [
            "STOCK_AVAILABILITY",
            "STORE_POLICY",
            "ORDER_LOOKUP",
            "PRICE_AND_PROMOTION",
            "LOYALTY",
            "PRODUCT_RECOMMENDATION",
        ], None
    if category == "inventory_variant_ambiguous":
        return ["STOCK_AVAILABILITY", "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "STORE_POLICY"], None
    if category == "inventory_variant_advanced":
        return [
            "STOCK_AVAILABILITY",
            "STORE_POLICY",
            "SHIPPING_LOOKUP",
            "PRODUCT_SEARCH",
            "PRODUCT_RECOMMENDATION",
            "PRODUCT_COMPARISON",
        ], None
    raise ValueError(f"Chưa khai báo intent cho nhóm {category}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nhập nhóm câu hỏi tồn kho và phiên bản vào fixture AI.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    questions: list[tuple[int, str]] = []
    for line in args.source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if match:
            questions.append((int(match.group(1)), match.group(2)))

    if [number for number, _ in questions] != list(range(1, 336)):
        raise ValueError("Nguồn phải có đủ và đúng thứ tự 335 câu đánh số.")

    rows = []
    for source_number, message in questions:
        if source_number in EXCLUDED_QUESTIONS:
            continue
        category = category_for(source_number)
        expected_intents, expected_route = expected_for(category)
        support_level = (
            "LIVE"
            if source_number in LIVE_QUESTIONS
            else "PLANNED"
            if any(source_number in planned_range for planned_range in PLANNED_RANGES)
            else "CLARIFY"
        )
        row = {
            "id": f"inventory_variant_domain_{source_number:03d}",
            "category": category,
            "message": message,
            "expected_intents": expected_intents,
            "required_tools": ["search_products"],
            "notes": f"source_question={source_number}; support_level={support_level}",
        }
        if expected_route is not None:
            row["expected_route"] = expected_route
        if 301 <= source_number <= 315:
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
