from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AskedQuestion:
    fieldId: str
    question: str


@dataclass
class BatchAnswerResult:
    answers: dict[str, Any]
    userDeclined: bool = False


class FollowUpBatchAgent(Protocol):
    def ask_question_batch(self, batch: list[AskedQuestion]) -> BatchAnswerResult:
        ...


def materialize_batch(
    question_set: dict[str, Any],
    field_ids: list[str],
) -> list[AskedQuestion]:
    questions_by_field_id = {
        item["fieldId"]: item["question"]
        for item in question_set["questions"]
    }

    batch: list[AskedQuestion] = []
    for field_id in field_ids:
        if field_id not in questions_by_field_id:
            raise ValueError(f"unknown fieldId in pending question batch: {field_id}")
        batch.append(
            AskedQuestion(
                fieldId=field_id,
                question=questions_by_field_id[field_id],
            )
        )
    return batch


def validate_batch_result(
    asked_field_ids: list[str],
    batch_result: BatchAnswerResult,
) -> None:
    unexpected_field_ids = sorted(
        set(batch_result.answers.keys()) - set(asked_field_ids)
    )
    if unexpected_field_ids:
        raise ValueError(
            "batch answers contain unasked fields: "
            + ", ".join(unexpected_field_ids)
        )
