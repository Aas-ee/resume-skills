from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RecommendedDecision = Literal["unset", "yes", "no"]
DecisionAction = Literal[
    "continue",
    "await_recommended_decision",
    "complete",
]


@dataclass(frozen=True)
class StopDecision:
    action: DecisionAction
    reason: str


def select_question_batch(
    question_set: dict[str, Any],
    pending_round_answers: dict[str, Any],
    batch_size: int,
) -> list[str]:
    normalized_batch_size = max(1, batch_size)
    unanswered_field_ids = [
        item["fieldId"]
        for item in question_set["questions"]
        if item["fieldId"] not in pending_round_answers
    ]
    return unanswered_field_ids[:normalized_batch_size]


def should_close_round(
    gap_report: dict[str, Any],
    pending_round_answers: dict[str, Any],
    *,
    user_declined: bool = False,
) -> bool:
    if user_declined:
        return True

    missing_required_fields = set(gap_report["missingRequired"])
    answered_fields = set(pending_round_answers.keys())
    return missing_required_fields.issubset(answered_fields)


def decide_stop_or_continue(
    gap_report: dict[str, Any],
    continue_for_recommended: RecommendedDecision,
) -> StopDecision:
    if gap_report["missingRequired"]:
        return StopDecision(
            action="continue",
            reason="required fields remain",
        )

    if not gap_report["missingRecommended"]:
        return StopDecision(
            action="complete",
            reason="required and recommended fields are complete",
        )

    if continue_for_recommended == "yes":
        return StopDecision(
            action="continue",
            reason="user chose to continue for recommended fields",
        )

    if continue_for_recommended == "no":
        return StopDecision(
            action="complete",
            reason="user chose to stop after required fields",
        )

    return StopDecision(
        action="await_recommended_decision",
        reason="only recommended fields remain",
    )
