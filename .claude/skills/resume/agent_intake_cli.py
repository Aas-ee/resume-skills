from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SKILLS_ROOT = Path(__file__).resolve().parents[1]
if str(SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILLS_ROOT))

from resume.runtime import (
    AgentIntakeEntrypoint,
    AgentIntakeEntrypointError,
    HostConversationAdapter,
    HostSessionStore,
    ResumeMaterial,
    default_host_session_store_path,
)
from resume.runtime.session_runner import SessionRunner

CLI_VERSION = "resume-agent-intake-cli/v1"
_DEFAULT_BATCH_SIZE_POLICY = 2
_CAMEL_BOUNDARY_RE = re.compile(r"(?<!^)(?=[A-Z])")


@dataclass(frozen=True)
class RequestEnvelope:
    turn_kind: str
    timestamp: str
    user_message: str | None
    manifest: dict[str, Any] | None
    checklist: dict[str, Any] | None
    materials: list[ResumeMaterial]
    drafting_started: bool


class AgentIntakeCliRequestError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the resume agent intake JSON CLI")
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
        entrypoint = _build_entrypoint(
            session_store_path=args.session_store,
            timestamp=request.timestamp,
        )
        outcome = entrypoint.handle_turn(
            turn_kind=request.turn_kind,
            timestamp=request.timestamp,
            user_message=request.user_message,
            manifest=request.manifest,
            checklist=request.checklist,
            materials=request.materials,
            drafting_started=request.drafting_started,
        )
        _write_json(
            {
                "ok": True,
                "version": CLI_VERSION,
                "outcome": _serialize_agent_outcome(outcome),
            }
        )
        return 0
    except AgentIntakeCliRequestError as exc:
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
    except AgentIntakeEntrypointError as exc:
        _write_json(
            {
                "ok": False,
                "version": CLI_VERSION,
                "error": {
                    "code": "invalid_request_shape",
                    "message": str(exc),
                },
            }
        )
        return 2


def _build_entrypoint(*, session_store_path: Path | None, timestamp: str) -> AgentIntakeEntrypoint:
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
    store = HostSessionStore(effective_store_path)
    adapter = HostConversationAdapter(store, session_runner)
    return AgentIntakeEntrypoint(store, adapter)


def _read_request_text(input_file: Path | None) -> str:
    if input_file is None:
        return sys.stdin.read()
    try:
        return input_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentIntakeCliRequestError("invalid_request_io", str(exc)) from exc


def _parse_request(raw_request: str) -> RequestEnvelope:
    try:
        payload = json.loads(raw_request)
    except json.JSONDecodeError as exc:
        raise AgentIntakeCliRequestError(
            "invalid_request_json",
            "Request body must be valid JSON",
        ) from exc

    if not isinstance(payload, dict):
        raise AgentIntakeCliRequestError("invalid_request_shape", "Request root must be a JSON object")

    version = payload.get("version")
    if version != CLI_VERSION:
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            f"Request version must be {CLI_VERSION}",
        )

    turn = payload.get("turn")
    if not isinstance(turn, dict):
        raise AgentIntakeCliRequestError("invalid_request_shape", "turn must be an object")

    turn_kind = turn.get("kind")
    if turn_kind not in {"reply", "resume"}:
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            "turn.kind must be 'reply' or 'resume'",
        )

    timestamp = turn.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            "turn.timestamp must be a non-empty string",
        )

    user_message = turn.get("user_message")
    if user_message is not None and not isinstance(user_message, str):
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            "turn.user_message must be a string when provided",
        )

    template_context = payload.get("template_context")
    manifest = checklist = None
    if template_context is not None:
        if not isinstance(template_context, dict):
            raise AgentIntakeCliRequestError(
                "invalid_request_shape",
                "template_context must be an object",
            )
        manifest = _optional_object(template_context, "manifest", "template_context")
        checklist = _optional_object(template_context, "checklist", "template_context")
        provided = [manifest is not None, checklist is not None]
        if not all(provided):
            raise AgentIntakeCliRequestError(
                "invalid_request_shape",
                "template_context must include manifest and checklist together",
            )

    materials_payload = payload.get("materials", [])
    if materials_payload is None:
        materials_payload = []
    if not isinstance(materials_payload, list):
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            "materials must be a list when provided",
        )
    materials = [_parse_material(item, index) for index, item in enumerate(materials_payload)]

    drafting_started = payload.get("drafting_started", False)
    if not isinstance(drafting_started, bool):
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            "drafting_started must be a boolean when provided",
        )

    return RequestEnvelope(
        turn_kind=turn_kind,
        timestamp=timestamp,
        user_message=user_message,
        manifest=manifest,
        checklist=checklist,
        materials=materials,
        drafting_started=drafting_started,
    )


def _optional_object(payload: dict[str, Any], key: str, path: str) -> dict[str, Any] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            f"{path}.{key} must be an object",
        )
    return value


def _parse_material(payload: Any, index: int) -> ResumeMaterial:
    path = f"materials[{index}]"
    if not isinstance(payload, dict):
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            f"{path} must be an object",
        )

    document_id = _required_string(payload, "document_id", path)
    source_label = _required_string(payload, "source_label", path)
    media_type = _required_string(payload, "media_type", path)
    text = payload.get("text")
    if text is not None and not isinstance(text, str):
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            f"{path}.text must be a string when provided",
        )
    return ResumeMaterial(
        documentId=document_id,
        sourceLabel=source_label,
        mediaType=media_type,
        text=text,
    )


def _required_string(payload: dict[str, Any], key: str, path: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AgentIntakeCliRequestError(
            "invalid_request_shape",
            f"{path}.{key} must be a non-empty string",
        )
    return value


def _serialize_agent_outcome(outcome: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": outcome.mode,
        "prompt_directive": outcome.promptDirective,
        "prompt": outcome.prompt,
    }
    if outcome.structuredOutcome is not None:
        payload["structured_outcome"] = _serialize_structured_outcome(outcome.structuredOutcome)
    if outcome.materialResult is not None:
        payload["material_result"] = _snake_case_keys(
            {
                "parseStatus": outcome.materialResult.parseStatus,
                "guidedAnswers": outcome.materialResult.guidedAnswers,
                "bootstrapChecklist": outcome.materialResult.bootstrapChecklist,
                "missingRequiredFields": outcome.materialResult.missingRequiredFields,
                "missingOptionalFields": outcome.materialResult.missingOptionalFields,
                "documentIds": outcome.materialResult.documentIds,
            }
        )
    return payload


def _serialize_structured_outcome(outcome: Any) -> dict[str, Any]:
    return {
        "mode": outcome.mode,
        "prompt_directive": outcome.promptDirective,
        "session_id": outcome.sessionId,
        "next_action_kind": outcome.nextActionKind,
        "current_projection": _snake_case_keys(outcome.currentProjection),
        "current_batch": _serialize_batch(outcome.currentBatch),
        "session_state": _snake_case_keys(
            outcome.sessionState.to_dict() if outcome.sessionState is not None else None
        ),
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


def _snake_case_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {_to_snake_case(key): _snake_case_keys(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_snake_case_keys(item) for item in value]
    return value


def _to_snake_case(key: str) -> str:
    return _CAMEL_BOUNDARY_RE.sub("_", key).lower()


def _write_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True))
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
