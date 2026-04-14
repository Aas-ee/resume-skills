from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKILLS_ROOT = Path(__file__).resolve().parents[1]
if str(SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILLS_ROOT))

from resume.runtime import (
    HostConversationAdapter,
    HostConversationAdapterError,
    HostSessionStore,
    default_host_session_store_path,
)
from resume.runtime.session_runner import SessionRunner

CLI_VERSION = "resume-host-cli/v1"
_DEFAULT_BATCH_SIZE_POLICY = 2


@dataclass(frozen=True)
class RequestEnvelope:
    turn_kind: str
    timestamp: str
    user_reply: str | None
    manifest: dict[str, Any] | None
    checklist: dict[str, Any] | None
    guided_answers: dict[str, Any] | None
    intake_session: dict[str, Any] | None


class HostCliRequestError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the resume host JSON CLI")
    parser.add_argument(
        "--session-store",
        type=Path,
        default=None,
        help="Override the persisted host session directory",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=None,
        help="Read the JSON request payload from a file instead of stdin",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        raw_request = _read_request_text(args.input_file)
        request = _parse_request(raw_request)
        adapter = _build_adapter(
            session_store_path=args.session_store,
            timestamp=request.timestamp,
        )
        outcome = adapter.handle_turn(
            turn_kind=request.turn_kind,
            timestamp=request.timestamp,
            user_reply=request.user_reply,
            manifest=request.manifest,
            checklist=request.checklist,
            guided_answers=request.guided_answers,
            intake_session=request.intake_session,
        )
        _write_json(
            {
                "ok": True,
                "version": CLI_VERSION,
                "mode": outcome.mode,
                "outcome": _serialize_outcome(outcome),
            }
        )
        return 0
    except HostCliRequestError as exc:
        _write_json(
            {
                "ok": False,
                "version": CLI_VERSION,
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                },
            }
        )
        return 2
    except HostConversationAdapterError as exc:
        _write_json(
            {
                "ok": False,
                "version": CLI_VERSION,
                "error": {
                    "code": "host_conversation_error",
                    "message": str(exc),
                },
            }
        )
        return 1


def _build_adapter(*, session_store_path: Path | None, timestamp: str) -> HostConversationAdapter:
    effective_store_path = session_store_path or default_host_session_store_path(
        Path(__file__).resolve().parent
    )
    session_runner = SessionRunner(
        guided_question_set_generated_at=timestamp,
        guided_response_set_updated_at=timestamp,
        follow_up_generated_at=timestamp,
        follow_up_response_updated_at=timestamp,
        batch_size_policy=_DEFAULT_BATCH_SIZE_POLICY,
    )
    return HostConversationAdapter(HostSessionStore(effective_store_path), session_runner)


def _read_request_text(input_file: Path | None) -> str:
    if input_file is None:
        return sys.stdin.read()
    try:
        return input_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise HostCliRequestError("invalid_request_io", str(exc)) from exc


def _parse_request(raw_request: str) -> RequestEnvelope:
    try:
        payload = json.loads(raw_request)
    except json.JSONDecodeError as exc:
        raise HostCliRequestError("invalid_request_json", "Request body must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HostCliRequestError("invalid_request_shape", "Request root must be a JSON object")

    version = payload.get("version")
    if version != CLI_VERSION:
        raise HostCliRequestError(
            "invalid_request_shape",
            f"Request version must be {CLI_VERSION}",
        )

    turn = payload.get("turn")
    if not isinstance(turn, dict):
        raise HostCliRequestError("invalid_request_shape", "turn must be an object")

    turn_kind = turn.get("kind")
    if turn_kind not in {"reply", "resume"}:
        raise HostCliRequestError(
            "invalid_request_shape",
            "turn.kind must be 'reply' or 'resume'",
        )

    timestamp = turn.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise HostCliRequestError(
            "invalid_request_shape",
            "turn.timestamp must be a non-empty string",
        )

    user_reply = turn.get("user_reply")
    if user_reply is not None and not isinstance(user_reply, str):
        raise HostCliRequestError(
            "invalid_request_shape",
            "turn.user_reply must be a string when provided",
        )

    structured_start = payload.get("structured_start")
    manifest = checklist = guided_answers = intake_session = None
    if structured_start is not None:
        if not isinstance(structured_start, dict):
            raise HostCliRequestError(
                "invalid_request_shape",
                "structured_start must be an object",
            )
        manifest = _optional_object(structured_start, "manifest")
        checklist = _optional_object(structured_start, "checklist")
        guided_answers = _optional_object(structured_start, "guided_answers")
        intake_session = _optional_object(structured_start, "intake_session")
        provided = [manifest is not None, checklist is not None, guided_answers is not None]
        if any(provided) and not all(provided):
            raise HostCliRequestError(
                "invalid_request_shape",
                "structured_start must include manifest, checklist, and guided_answers together",
            )

    return RequestEnvelope(
        turn_kind=turn_kind,
        timestamp=timestamp,
        user_reply=user_reply,
        manifest=manifest,
        checklist=checklist,
        guided_answers=guided_answers,
        intake_session=intake_session,
    )


def _optional_object(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise HostCliRequestError(
            "invalid_request_shape",
            f"structured_start.{key} must be an object",
        )
    return value


def _serialize_outcome(outcome: Any) -> dict[str, Any]:
    return {
        "prompt_directive": outcome.promptDirective,
        "session_id": outcome.sessionId,
        "session_state": outcome.sessionState.to_dict() if outcome.sessionState is not None else None,
        "next_action_kind": outcome.nextActionKind,
        "current_projection": outcome.currentProjection,
        "current_batch": _serialize_batch(outcome.currentBatch),
    }


def _serialize_batch(batch: list[Any] | None) -> list[dict[str, Any]] | None:
    if batch is None:
        return None
    return [
        {
            "field_id": item.fieldId,
            "question": item.question,
        }
        for item in batch
    ]


def _write_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
