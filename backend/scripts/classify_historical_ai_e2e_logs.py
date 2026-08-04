import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app.infrastructure.database.session import AsyncSessionFactory, engine


GROUPS = (8, 14, 16, 18, 20)


def load_fixture_messages(fixtures_dir: Path) -> set[str]:
    messages: set[str] = set()
    for group in GROUPS:
        path = fixtures_dir / f"ai_business_{group:02d}_cases.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                messages.add(str(json.loads(line)["message"]))
    return messages


def candidate_log_ids(
    rows: list[dict],
    *,
    fixture_messages: set[str],
    conversations_with_feedback: set[UUID],
    min_matches: int,
    min_ratio: float,
) -> tuple[list[UUID], list[dict]]:
    grouped: dict[UUID, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["conversation_id"]].append(row)

    selected_ids: list[UUID] = []
    summaries: list[dict] = []
    for conversation_id, logs in grouped.items():
        matched = [row for row in logs if row["user_message"] in fixture_messages]
        ratio = len(matched) / len(logs) if logs else 0
        if (
            conversation_id not in conversations_with_feedback
            and len(matched) >= min_matches
            and ratio >= min_ratio
        ):
            selected_ids.extend(row["id"] for row in matched)
            summaries.append(
                {
                    "conversation_id": str(conversation_id),
                    "matched_logs": len(matched),
                    "legacy_logs": len(logs),
                    "match_ratio": round(ratio, 4),
                }
            )
    return selected_ids, summaries


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phân loại log E2E cũ bằng dấu hiệu phiên fixture mật độ cao; mặc định chỉ dry-run."
    )
    parser.add_argument("--apply", action="store_true", help="Ghi nhãn SYNTHETIC cho các log đủ tiêu chí.")
    parser.add_argument("--min-matches", type=int, default=20)
    parser.add_argument("--min-ratio", type=float, default=0.9)
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "tests" / "fixtures",
    )
    args = parser.parse_args()
    if args.min_matches < 20:
        raise ValueError("min-matches không được nhỏ hơn 20 để tránh nhận nhầm hội thoại khách.")
    if not 0.9 <= args.min_ratio <= 1:
        raise ValueError("min-ratio phải nằm trong khoảng 0.9 đến 1.")

    fixture_messages = load_fixture_messages(args.fixtures_dir)
    async with AsyncSessionFactory() as session:
        rows = [
            dict(row)
            for row in (
                await session.execute(
                    text(
                        """
                        SELECT id, conversation_id, user_message
                        FROM ai_context_logs
                        WHERE user_id IS NULL
                          AND dynamic_context->>'traffic_origin' IS NULL
                        ORDER BY conversation_id, created_at
                        """
                    )
                )
            ).mappings().all()
        ]
        feedback_conversations = set(
            (
                await session.execute(
                    text(
                        """
                        SELECT DISTINCT logs.conversation_id
                        FROM ai_response_feedback feedback
                        JOIN ai_context_logs logs ON logs.id = feedback.response_id
                        """
                    )
                )
            ).scalars().all()
        )
        selected_ids, summaries = candidate_log_ids(
            rows,
            fixture_messages=fixture_messages,
            conversations_with_feedback=feedback_conversations,
            min_matches=args.min_matches,
            min_ratio=args.min_ratio,
        )

        updated = 0
        if args.apply and selected_ids:
            result = await session.execute(
                text(
                    """
                    UPDATE ai_context_logs
                    SET dynamic_context = jsonb_set(
                        jsonb_set(
                            COALESCE(dynamic_context, '{}'::jsonb),
                            '{traffic_origin}',
                            '"SYNTHETIC"'::jsonb,
                            true
                        ),
                        '{synthetic_classifier}',
                        '"fixture_session_v1"'::jsonb,
                        true
                    )
                    WHERE id = ANY(CAST(:log_ids AS uuid[]))
                      AND user_id IS NULL
                      AND dynamic_context->>'traffic_origin' IS NULL
                    """
                ),
                {"log_ids": [str(log_id) for log_id in selected_ids]},
            )
            updated = int(result.rowcount or 0)
            await session.commit()

    report = {
        "mode": "apply" if args.apply else "dry-run",
        "fixture_messages": len(fixture_messages),
        "candidate_conversations": len(summaries),
        "candidate_logs": len(selected_ids),
        "updated_logs": updated,
        "conversations": summaries,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
