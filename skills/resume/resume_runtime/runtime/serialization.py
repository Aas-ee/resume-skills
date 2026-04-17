from __future__ import annotations

from typing import Any

from resume_runtime.runtime.host_conversation_adapter import HostConversationOutcome


def serialize_question_batch(batch: list[Any] | None) -> list[dict[str, Any]] | None:
    if batch is None:
        return None
    return [
        {
            "field_id": item.fieldId,
            "question": item.question,
        }
        for item in batch
    ]


def host_conversation_outcome_to_dict(outcome: HostConversationOutcome) -> dict[str, Any]:
    return {
        "prompt_directive": outcome.promptDirective,
        "session_id": outcome.sessionId,
        "session_state": outcome.sessionState.to_dict() if outcome.sessionState is not None else None,
        "next_action_kind": outcome.nextActionKind,
        "current_projection": outcome.currentProjection,
        "current_batch": serialize_question_batch(outcome.currentBatch),
    }
