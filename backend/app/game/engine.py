from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .calculator import analyze_input
from .scoring import compute_score, SubmissionScore, DEFAULT_COSTS


@dataclass
class EvaluationOutcome:
    expression: str
    value: Optional[float]
    cost: int
    distance: Optional[float]
    is_optimal: bool
    score: int
    summary: str


class NumberGameEngine:
    def __init__(self, costs: dict[str, int] | None = None) -> None:
        self.costs = costs or DEFAULT_COSTS

    def evaluate(
        self,
        *,
        expression: str,
        target_number: int,
        optimal_cost: int,
        deadline: datetime | None = None,
    ) -> EvaluationOutcome:
        analysis = analyze_input(expression, mode="cost", costs=self.costs)
        if not analysis["results"]:
            raise ValueError("식이 비어있습니다.")

        last_result = analysis["results"][-1]["result"]
        if isinstance(last_result, str):
            raise ValueError(last_result)

        total_cost = analysis["total_cost"]
        remaining_seconds = 0
        if deadline:
            remaining_seconds = max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))

        score_bundle: SubmissionScore = compute_score(
            target_number=target_number,
            result_value=last_result,
            total_cost=total_cost,
            optimal_cost=optimal_cost,
            remaining_seconds=remaining_seconds,
        )

        return EvaluationOutcome(
            expression=expression,
            value=score_bundle.value,
            cost=score_bundle.cost,
            distance=score_bundle.distance,
            is_optimal=score_bundle.is_optimal,
            score=score_bundle.score,
            summary=score_bundle.message,
        )

