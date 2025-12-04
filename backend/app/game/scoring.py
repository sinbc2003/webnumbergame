from dataclasses import dataclass
from typing import Optional


DEFAULT_COSTS = {"1": 1, "+": 1, "*": 1, "(": 1, ")": 1}


@dataclass
class SubmissionScore:
    value: Optional[float]
    cost: int
    distance: Optional[float]
    is_optimal: bool
    score: int
    message: str


def compute_score(
    *,
    target_number: int,
    result_value: Optional[float],
    total_cost: int,
    optimal_cost: int,
    remaining_seconds: int = 0,
) -> SubmissionScore:
    if result_value is None:
        return SubmissionScore(
            value=None,
            cost=total_cost,
            distance=None,
            is_optimal=False,
            score=0,
            message="결과 값을 계산할 수 없습니다.",
        )

    distance = abs(target_number - result_value)
    cost_gap = max(0, total_cost - optimal_cost)

    base_score = 1000
    penalty = (distance * 50) + (cost_gap * 25)
    time_bonus = max(0, remaining_seconds // 5)
    raw_score = max(0, int(base_score - penalty + time_bonus))
    is_optimal = distance == 0 and total_cost <= optimal_cost
    if is_optimal:
        raw_score += 150

    message = "성공" if distance == 0 else "근사 해답"
    return SubmissionScore(
        value=result_value,
        cost=total_cost,
        distance=distance,
        is_optimal=is_optimal,
        score=raw_score,
        message=message,
    )

