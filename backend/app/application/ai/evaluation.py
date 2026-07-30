import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.ai.intent_router import route_intent


class AIEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    category: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=2000)
    expected_intents: list[str] = Field(min_length=1)
    expected_route: Literal["POLICY", "DETERMINISTIC", "MODEL"] | None = None
    expected_needs_clarification: bool | None = None
    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    requires_auth: bool = False
    simulated_condition: str | None = None
    facts_must_include: list[str] = Field(default_factory=list)
    facts_must_not_include: list[str] = Field(default_factory=list)
    notes: str | None = None


class AIEvaluationResult(BaseModel):
    total: int
    passed: int
    intent_accuracy: float
    route_accuracy: float
    category_accuracy: dict[str, float]
    failures: list[dict]


def load_evaluation_cases(path: str | Path) -> list[AIEvaluationCase]:
    cases: list[AIEvaluationCase] = []
    seen_ids: set[str] = set()
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            case = AIEvaluationCase.model_validate(payload)
            if case.id in seen_ids:
                raise ValueError(f"Trùng mã evaluation case tại dòng {line_number}: {case.id}")
            seen_ids.add(case.id)
            cases.append(case)
    return cases


def evaluate_router(cases: list[AIEvaluationCase]) -> AIEvaluationResult:
    category_totals: Counter[str] = Counter()
    category_passed: Counter[str] = Counter()
    failures: list[dict] = []
    route_matches = 0
    intent_matches_count = 0

    for case in cases:
        decision = route_intent(case.message)
        intent_matches = decision.intent in case.expected_intents
        route_matches_case = case.expected_route is None or decision.route == case.expected_route
        clarification_matches = (
            case.expected_needs_clarification is None
            or decision.needs_clarification == case.expected_needs_clarification
        )
        category_totals[case.category] += 1
        if route_matches_case:
            route_matches += 1
        if intent_matches:
            intent_matches_count += 1
        if intent_matches and route_matches_case and clarification_matches:
            category_passed[case.category] += 1
        else:
            failures.append(
                {
                    "id": case.id,
                    "category": case.category,
                    "message": case.message,
                    "expected_intents": case.expected_intents,
                    "actual_intent": decision.intent,
                    "expected_route": case.expected_route,
                    "actual_route": decision.route,
                    "expected_needs_clarification": case.expected_needs_clarification,
                    "actual_needs_clarification": decision.needs_clarification,
                }
            )

    total = len(cases)
    passed = total - len(failures)
    return AIEvaluationResult(
        total=total,
        passed=passed,
        intent_accuracy=intent_matches_count / total if total else 0,
        route_accuracy=route_matches / total if total else 0,
        category_accuracy={
            category: category_passed[category] / count
            for category, count in sorted(category_totals.items())
        },
        failures=failures,
    )
