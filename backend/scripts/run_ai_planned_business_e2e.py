import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from redis.asyncio import Redis

from app.config import settings


GROUPS = (8, 14, 16, 18, 20)
GENERIC_ANSWERS = (
    "Mình chưa tìm thấy dữ liệu phù hợp",
    "Bạn có thể hỏi mình về giao hàng, thanh toán, hóa đơn",
)


def post_json(url: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload, ensure_ascii=True).encode("ascii")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def create_conversation(base_url: str) -> dict:
    return post_json(f"{base_url.rstrip('/')}/api/ai-assistant/conversations", {})


def post_chat(base_url: str, payload: dict) -> dict:
    return post_json(f"{base_url.rstrip('/')}/api/ai-assistant/chat", payload)


async def clear_anonymous_rate_limit() -> None:
    client = Redis.from_url(settings.redis_url)
    try:
        await client.delete("rate-limit:ai:anonymous")
    except Exception:
        pass
    finally:
        await client.aclose()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm thử end-to-end 266 câu PLANNED đã triển khai.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--fixtures-dir", type=Path, default=Path("tests/fixtures"))
    args = parser.parse_args()

    cases = []
    for group in GROUPS:
        path = args.fixtures_dir / f"ai_business_{group:02d}_cases.jsonl"
        cases.extend((group, json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line)
    if len(cases) != 266:
        raise RuntimeError(f"Cần đúng 266 câu, thực tế {len(cases)}.")

    conversations = {
        group: await asyncio.to_thread(create_conversation, args.base_url)
        for group in GROUPS
    }
    failures = []
    intents = Counter()
    for index, (group, case) in enumerate(cases, start=1):
        if index == 1 or index % 15 == 0:
            await clear_anonymous_rate_limit()
        payload = {
            "conversation_id": conversations[group]["conversation_id"],
            "conversation_token": conversations[group]["conversation_token"],
            "message": case["message"],
            "dynamic_context": {
                "cart_items": [
                    {
                        "product_id": "00000000-0000-0000-0000-000000000001",
                        "name": "Sản phẩm kiểm thử trong giỏ",
                        "quantity": 2,
                        "price": 3_000_000,
                    }
                ],
                "viewed_products": [],
                "loyalty": None,
            },
            "client_capabilities": [
                "response_v2",
                "feedback",
                "planned_business_v1",
                "synthetic_evaluation_v1",
            ],
            "model_provider": "GEMINI",
            "model_name": "gemini-3.5-flash",
        }
        if group == 16:
            payload["page_context"] = {"product_id": "iphone-17-pro", "cart_item_ids": []}
        try:
            response = await asyncio.to_thread(post_chat, args.base_url, payload)
        except HTTPError as error:
            failures.append({"id": case["id"], "error": f"HTTP_{error.code}"})
            continue
        except Exception as error:
            failures.append({"id": case["id"], "error": type(error).__name__})
            continue

        answer = str(response.get("answer") or "").strip()
        intent = str(response.get("intent") or "")
        intents[intent] += 1
        reasons = []
        if intent not in case["expected_intents"]:
            reasons.append(f"intent={intent}")
        if len(answer) < 40:
            reasons.append("answer_too_short")
        if any(generic in answer for generic in GENERIC_ANSWERS):
            reasons.append("generic_answer")
        if response.get("verification_passed") is not True:
            reasons.append("verification_failed")
        if response.get("needs_clarification"):
            reasons.append("unexpected_clarification")
        if reasons:
            failures.append({"id": case["id"], "message": case["message"], "reasons": reasons, "answer": answer})

    report = {
        "total": len(cases),
        "passed": len(cases) - len(failures),
        "failed": len(failures),
        "intents": dict(intents),
        "failures": failures[:30],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
