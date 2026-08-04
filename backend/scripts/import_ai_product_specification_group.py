import argparse
import json
import re
from pathlib import Path


CATEGORY_RANGES = (
    (1, 15, "product_specification_basic"),
    (16, 30, "product_specification_size_weight"),
    (31, 45, "product_specification_material"),
    (46, 60, "product_specification_power"),
    (61, 80, "product_specification_battery"),
    (81, 95, "product_specification_performance"),
    (96, 115, "product_specification_memory"),
    (116, 135, "product_specification_display"),
    (136, 155, "product_specification_camera"),
    (156, 170, "product_specification_audio"),
    (171, 190, "product_specification_connectivity"),
    (191, 205, "product_specification_durability"),
    (206, 220, "product_specification_software"),
    (221, 235, "product_specification_compatibility"),
    (266, 285, "product_specification_explanation"),
    (286, 300, "product_specification_reconciliation"),
    (301, 315, "product_specification_ambiguous"),
    (316, 335, "product_specification_advanced"),
)

EXCLUDED_QUESTIONS = {
    39,
    53,
    *range(236, 266),
    271,
    279,
    281,
    282,
    283,
    284,
    309,
}

COMPARISON_QUESTIONS = {30, 54, 115, 273, 274, 276, 277, 278, 290, 291}

PLANNED_QUESTIONS = {
    9,
    10,
    12,
    13,
    15,
    17,
    18,
    19,
    27,
    28,
    29,
    *range(32, 46),
    *range(49, 61),
    63,
    73,
    74,
    77,
    78,
    79,
    *range(82, 96),
    98,
    100,
    101,
    102,
    107,
    108,
    112,
    113,
    120,
    122,
    129,
    131,
    134,
    139,
    143,
    146,
    *range(151, 156),
    157,
    *range(161, 171),
    175,
    *range(178, 191),
    *range(193, 206),
    *range(207, 221),
    *range(226, 236),
    *range(286, 301),
    *range(316, 336),
}


def category_for(source_number: int) -> str:
    for start, end, category in CATEGORY_RANGES:
        if start <= source_number <= end:
            return category
    raise ValueError(f"Câu hỏi ngoài phạm vi giữ lại: {source_number}")


def expected_for(source_number: int) -> tuple[list[str], str | None]:
    if source_number in COMPARISON_QUESTIONS:
        return ["PRODUCT_COMPARISON", "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"], "MODEL"
    if source_number == 202:
        return ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "WARRANTY_POLICY"], None
    if source_number == 296:
        return ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "STORE_POLICY"], None
    return ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION"], "MODEL"


def main() -> None:
    parser = argparse.ArgumentParser(description="Nhập nhóm câu hỏi thông số kỹ thuật vào fixture AI.")
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
        expected_intents, expected_route = expected_for(source_number)
        support_level = "PLANNED" if source_number in PLANNED_QUESTIONS else "CLARIFY"
        row = {
            "id": f"product_specification_domain_{source_number:03d}",
            "category": category_for(source_number),
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
