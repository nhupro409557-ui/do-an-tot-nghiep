from collections import defaultdict
from uuid import UUID


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
