import argparse
import asyncio
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy import text

from app.api.routers.auth_utils import make_token
from app.infrastructure.database.session import AsyncSessionFactory, engine


CASES = (
    {
        "id": "shipping_loyalty",
        "message": "Đơn hàng của tôi giao tới đâu và tôi còn bao nhiêu điểm tích lũy?",
        "expected_intents": {"SHIPPING_LOOKUP", "LOYALTY"},
    },
    {
        "id": "after_sales_warranty_policy",
        "message": "Hồ sơ bảo hành của tôi đang xử lý tới đâu và chính sách bảo hành thế nào?",
        "expected_intents": {"AFTER_SALES_LOOKUP", "WARRANTY_POLICY"},
    },
    {
        "id": "loyalty_voucher",
        "message": "Tôi có bao nhiêu điểm và có voucher nào dùng được?",
        "expected_intents": {"LOYALTY", "VOUCHER_SUPPORT"},
    },
    {
        "id": "order_after_sales",
        "message": "Đơn hàng của tôi thế nào và hồ sơ hậu mãi gần nhất đang ở đâu?",
        "expected_intents": {"ORDER_LOOKUP", "AFTER_SALES_LOOKUP"},
    },
)


def post_json(url: str, payload: dict, *, access_token: str) -> dict:
    body = json.dumps(payload, ensure_ascii=True).encode("ascii")
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


async def find_test_user_id() -> UUID:
    async with AsyncSessionFactory() as session:
        user_id = (
            await session.execute(
                text(
                    """
                    SELECT u.id
                    FROM users u
                    WHERE u.status = 'ACTIVE'
                      AND u.deleted_at IS NULL
                      AND EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id)
                      AND (
                          EXISTS (SELECT 1 FROM warranty_requests wr WHERE wr.user_id = u.id)
                          OR EXISTS (SELECT 1 FROM return_requests rr WHERE rr.user_id = u.id)
                      )
                    ORDER BY u.loyalty_points_balance DESC
                    LIMIT 1
                    """
                )
            )
        ).scalar_one_or_none()
    if user_id is None:
        raise RuntimeError("Không có tài khoản active đủ đơn hàng và hồ sơ hậu mãi để kiểm thử.")
    return user_id


async def latest_log_context(conversation_id: str) -> dict:
    async with AsyncSessionFactory() as session:
        context = (
            await session.execute(
                text(
                    """
                    SELECT dynamic_context
                    FROM ai_context_logs
                    WHERE conversation_id = CAST(:conversation_id AS uuid)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"conversation_id": conversation_id},
            )
        ).scalar_one_or_none()
    return dict(context or {})


async def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm thử câu hỏi ghép AI bằng tài khoản có dữ liệu thật.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    user_id = await find_test_user_id()
    access_token = make_token(user_id)
    failures = []
    results = []

    for case in CASES:
        try:
            conversation = await asyncio.to_thread(
                post_json,
                f"{args.base_url.rstrip('/')}/api/ai-assistant/conversations",
                {},
                access_token=access_token,
            )
            payload = {
                "conversation_id": conversation["conversation_id"],
                "conversation_token": conversation["conversation_token"],
                "message": case["message"],
                "dynamic_context": {"cart_items": [], "viewed_products": [], "loyalty": None},
                "client_capabilities": [
                    "response_v2",
                    "authenticated_compound_v1",
                    "synthetic_evaluation_v1",
                ],
                "model_provider": "GEMINI",
                "model_name": "gemini-3.5-flash",
            }
            response = await asyncio.to_thread(
                post_json,
                f"{args.base_url.rstrip('/')}/api/ai-assistant/chat",
                payload,
                access_token=access_token,
            )
            log_context = await latest_log_context(conversation["conversation_id"])
        except HTTPError as error:
            failures.append(
                {
                    "id": case["id"],
                    "error": f"HTTP_{error.code}",
                    "detail": error.read().decode("utf-8", errors="replace"),
                }
            )
            continue
        except Exception as error:
            failures.append({"id": case["id"], "error": type(error).__name__, "detail": str(error)})
            continue

        planned_intents = set(log_context.get("service_planner_intents") or [])
        reasons = []
        if not case["expected_intents"].issubset(planned_intents):
            reasons.append(f"planner_intents={sorted(planned_intents)}")
        if log_context.get("traffic_origin") != "SYNTHETIC":
            reasons.append(f"traffic_origin={log_context.get('traffic_origin')}")
        if response.get("verification_passed") is not True:
            reasons.append("verification_failed")
        if len(str(response.get("answer") or "").strip()) < 50:
            reasons.append("answer_too_short")

        result = {
            "id": case["id"],
            "intent": response.get("intent"),
            "planner_intents": sorted(planned_intents),
            "answer_mode": response.get("answer_mode"),
            "verification_passed": response.get("verification_passed"),
        }
        results.append(result)
        if reasons:
            failures.append({**result, "reasons": reasons})

    report = {
        "total": len(CASES),
        "passed": len(CASES) - len(failures),
        "failed": len(failures),
        "results": results,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    await engine.dispose()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
