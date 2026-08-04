import argparse
import json
import sys
from pathlib import Path

from app.application.ai.evaluation import evaluate_router, load_evaluation_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy bộ đánh giá offline cho AI intent router.")
    parser.add_argument(
        "--dataset",
        default="tests/fixtures/ai_eval_cases.jsonl",
        help="Đường dẫn tới bộ evaluation JSONL.",
    )
    parser.add_argument("--min-accuracy", type=float, default=0.97)
    parser.add_argument("--max-failures", type=int, default=30)
    args = parser.parse_args()

    cases = load_evaluation_cases(Path(args.dataset))
    result = evaluate_router(cases)
    output = result.model_dump(mode="json")
    output["failures"] = output["failures"][: max(args.max_failures, 0)]
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if len(cases) < 300:
        print(f"Bộ evaluation phải có ít nhất 300 case, hiện có {len(cases)}.", file=sys.stderr)
        return 2
    if result.intent_accuracy < args.min_accuracy:
        print(
            f"Intent accuracy {result.intent_accuracy:.2%} thấp hơn ngưỡng {args.min_accuracy:.2%}.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
