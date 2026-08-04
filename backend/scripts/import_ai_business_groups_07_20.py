import argparse
import json
import re
from pathlib import Path

from app.application.ai.intent_router import normalize_text


GROUP_TITLES = {
    7: "Phụ kiện và dịch vụ đi kèm",
    8: "Giỏ hàng và đặt hàng",
    9: "Theo dõi đơn hàng",
    10: "Thanh toán và trả góp",
    11: "Giao hàng và nhận tại cửa hàng",
    12: "Đổi trả, bảo hành và hậu mãi",
    13: "Sản phẩm đã qua sử dụng",
    14: "Voucher và mã giảm giá",
    15: "Điểm thưởng và khách hàng thân thiết",
    16: "Đánh giá và trải nghiệm sản phẩm",
    17: "Thông tin cửa hàng",
    18: "Tài khoản khách hàng",
    19: "Chính sách và điều khoản",
    20: "Khiếu nại và hỗ trợ nhân viên",
}

EXPECTED_INTENTS = {
    7: ["PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON", "STORE_POLICY", "WARRANTY_POLICY", "PRICE_AND_PROMOTION", "STOCK_AVAILABILITY", "COMPLAINT"],
    8: ["CART_SUPPORT", "ACCOUNT_SUPPORT", "ORDER_LOOKUP", "SHIPPING_LOOKUP", "VOUCHER_SUPPORT", "PRICE_AND_PROMOTION", "LOYALTY", "STOCK_AVAILABILITY", "COMPLAINT", "STORE_POLICY"],
    9: ["ORDER_LOOKUP", "SHIPPING_LOOKUP", "COMPLAINT", "STORE_POLICY"],
    10: ["STORE_POLICY", "ACCOUNT_SUPPORT", "PRICE_AND_PROMOTION", "ORDER_LOOKUP", "LOYALTY", "COMPLAINT", "UNSUPPORTED_REQUEST"],
    11: ["STORE_POLICY", "SHIPPING_LOOKUP", "ORDER_LOOKUP", "PRODUCT_SEARCH", "COMPLAINT", "STOCK_AVAILABILITY"],
    12: ["WARRANTY_POLICY", "AFTER_SALES_LOOKUP", "STORE_POLICY", "PRODUCT_SEARCH", "PRODUCT_COMPARISON", "PRICE_AND_PROMOTION", "COMPLAINT", "ORDER_LOOKUP"],
    13: ["USED_PRODUCT_ADVICE", "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "PRODUCT_COMPARISON", "PRICE_AND_PROMOTION", "WARRANTY_POLICY", "STORE_POLICY", "LOYALTY", "STOCK_AVAILABILITY"],
    14: ["VOUCHER_SUPPORT", "PRICE_AND_PROMOTION", "LOYALTY", "COMPLAINT"],
    15: ["LOYALTY", "ACCOUNT_SUPPORT", "STORE_POLICY", "PRICE_AND_PROMOTION", "WARRANTY_POLICY", "COMPLAINT"],
    16: ["PRODUCT_REVIEW"],
    17: ["STORE_POLICY", "STOCK_AVAILABILITY", "SHIPPING_LOOKUP", "WARRANTY_POLICY", "PRODUCT_SEARCH", "PRODUCT_RECOMMENDATION", "COMPLAINT"],
    18: ["ACCOUNT_SUPPORT", "COMPLAINT", "ORDER_LOOKUP", "SHIPPING_LOOKUP", "WARRANTY_POLICY", "LOYALTY"],
    19: ["STORE_POLICY", "WARRANTY_POLICY", "SHIPPING_LOOKUP", "ORDER_LOOKUP", "USED_PRODUCT_ADVICE", "PRICE_AND_PROMOTION", "UNSUPPORTED_REQUEST"],
    20: ["COMPLAINT", "UNSUPPORTED_REQUEST", "STORE_POLICY", "AFTER_SALES_LOOKUP", "ORDER_LOOKUP"],
}

REQUIRED_TOOLS = {
    7: ["search_products"],
    8: ["cart_context", "get_my_latest_order"],
    9: ["get_my_order", "get_shipping_timeline"],
    10: ["store_policy", "get_my_order"],
    11: ["store_policy", "get_shipping_timeline"],
    12: ["store_policy", "get_after_sales_status"],
    13: ["search_used_products"],
    14: ["list_public_vouchers", "get_my_vouchers"],
    15: ["get_my_loyalty"],
    16: ["get_product_review_insights", "get_my_review_eligibility"],
    17: ["store_policy"],
    18: ["get_my_account"],
    19: ["store_policy"],
    20: ["create_support_request", "get_my_latest_support_request"],
}

# Các câu đã có nguyên văn trong fixture trước hoặc lặp lại ở nhóm xuất hiện sớm hơn.
EXCLUDED = {
    (10, 15), (10, 31), (10, 51),
    (12, 6), (12, 20), (12, 21),
    (13, 42),
    (14, 15), (14, 16),
    (15, 11), (15, 28),
    (16, 23), (16, 27), (16, 28), (16, 29), (16, 30),
    (18, 4), (18, 26),
    (19, 31),
}

PLANNED_GROUPS: set[int] = set()
IMPLEMENTED_GROUPS = {8, 14, 16, 18, 20}
LIVE_SECTIONS = {
    "9.1", "9.2", "10.1", "10.3", "11.1", "11.3", "11.4",
    "12.1", "12.2", "12.3", "13.1", "13.3", "13.4", "15.1",
    "15.2", "17.1", "17.2", "19.1", "19.2", "19.3",
}


def support_level(group: int, section_code: str) -> str:
    if group in IMPLEMENTED_GROUPS:
        return "LIVE"
    if group in PLANNED_GROUPS:
        return "PLANNED"
    if section_code in LIVE_SECTIONS:
        return "LIVE"
    return "CLARIFY"


def parse_source(source: Path) -> tuple[dict[int, list[dict]], list[dict]]:
    groups = {group: [] for group in GROUP_TITLES}
    dialogues: list[dict] = []
    group: int | None = None
    section_code: str | None = None
    section_title: str | None = None
    dialogue_turns: list[dict] | None = None

    for line in source.read_text(encoding="utf-8").splitlines():
        group_match = re.match(r"^# (\d+)\.\s+(.+?)\s*$", line)
        if group_match:
            candidate = int(group_match.group(1))
            group = candidate if candidate in GROUP_TITLES else None
            section_code = None
            section_title = None
            dialogue_turns = None
            continue
        if group is None:
            continue
        if line.startswith("## H"):
            dialogue_turns = []
            dialogues.append(
                {
                    "id": f"business_{group:02d}_dialogue",
                    "group": group,
                    "title": GROUP_TITLES[group],
                    "turns": dialogue_turns,
                }
            )
            section_code = None
            continue
        section_match = re.match(r"^## (\d+\.\d+)\.\s+(.+?)\s*$", line)
        if section_match:
            section_code = section_match.group(1)
            section_title = section_match.group(2)
            dialogue_turns = None
            continue
        if line.startswith("## "):
            section_code = None
            dialogue_turns = None
            continue
        if dialogue_turns is not None and line.startswith("* ") and ":" in line:
            dialogue_turns.append(
                {
                    "message": line.split(":", 1)[1].strip(),
                    "expected_intents": EXPECTED_INTENTS[group],
                }
            )
            continue
        question_match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if question_match and section_code and section_title:
            groups[group].append(
                {
                    "source_number": int(question_match.group(1)),
                    "section_code": section_code,
                    "section_title": section_title,
                    "message": question_match.group(2),
                }
            )
    return groups, dialogues


def main() -> None:
    parser = argparse.ArgumentParser(description="Nhập bộ câu hỏi chatbot nghiệp vụ 7–20.")
    parser.add_argument("source", type=Path)
    parser.add_argument("fixtures_dir", type=Path)
    args = parser.parse_args()

    groups, dialogues = parse_source(args.source)
    if sum(len(rows) for rows in groups.values()) != 740:
        raise ValueError("Nguồn phải có đúng 740 câu nghiệp vụ trong nhóm 7–20.")
    if sum(len(item["turns"]) for item in dialogues) != 70:
        raise ValueError("Nguồn phải có đúng 70 lượt hội thoại kiểm thử.")

    args.fixtures_dir.mkdir(parents=True, exist_ok=True)
    kept_messages: set[str] = set()
    total = 0
    for group, questions in groups.items():
        rows = []
        for question in questions:
            source_number = question["source_number"]
            if (group, source_number) in EXCLUDED:
                continue
            normalized = normalize_text(question["message"])
            if normalized in kept_messages:
                raise ValueError(f"Câu trùng chưa được khai báo loại: nhóm {group}, câu {source_number}.")
            kept_messages.add(normalized)
            rows.append(
                {
                    "id": f"business_{group:02d}_{source_number:03d}",
                    "category": f"business_{question['section_code'].replace('.', '_')}",
                    "message": question["message"],
                    "expected_intents": EXPECTED_INTENTS[group],
                    "required_tools": REQUIRED_TOOLS[group],
                    "notes": (
                        f"group={group}; section={question['section_code']}; "
                        f"support_level={support_level(group, question['section_code'])}"
                    ),
                }
            )
        output = args.fixtures_dir / f"ai_business_{group:02d}_cases.jsonl"
        output.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
            encoding="utf-8",
        )
        total += len(rows)
        print(f"Nhóm {group}: {len(rows)} câu")

    (args.fixtures_dir / "ai_business_07_20_dialogues.json").write_text(
        json.dumps(dialogues, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Tổng cộng: {total} câu, {sum(len(item['turns']) for item in dialogues)} lượt hội thoại")


if __name__ == "__main__":
    main()
