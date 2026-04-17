from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from resume_runtime.runtime.follow_up_agent_adapter import AskedQuestion
from resume_runtime.runtime.host_session_runner import (
    HostSessionAction,
    HostSessionRunner,
    HostSessionRunnerError,
)
from resume_runtime.runtime.host_session_state import HostSessionState
from resume_runtime.runtime.host_session_store import HostSessionStore, HostSessionStoreError
from resume_runtime.runtime.session_runner import SessionRunner

HostConversationTurnKind = Literal["resume", "reply"]
HostConversationMode = Literal["structured", "freeform"]
HostPromptDirective = Literal[
    "ask_current_batch",
    "ask_yes_no_only",
    "handoff_to_drafting",
    "stay_freeform",
]

_RUNTIME_TO_PROMPT_DIRECTIVE: dict[str, HostPromptDirective] = {
    "ask_batch": "ask_current_batch",
    "await_recommended_decision": "ask_yes_no_only",
    "completed": "handoff_to_drafting",
}


class HostConversationAdapterError(Exception):
    """Raised when host conversation routing cannot safely use structured runtime."""


@dataclass(frozen=True)
class HostConversationOutcome:
    mode: HostConversationMode
    promptDirective: HostPromptDirective
    sessionId: str | None = None
    sessionState: HostSessionState | None = None
    nextActionKind: str | None = None
    currentProjection: dict[str, Any] | None = None
    currentBatch: list[AskedQuestion] | None = None


class HostConversationAdapter:
    def __init__(
        self,
        store: HostSessionStore,
        session_runner: SessionRunner,
    ) -> None:
        self._store = store
        self._runner = HostSessionRunner(store, session_runner)

    def handle_turn(
        self,
        *,
        turn_kind: HostConversationTurnKind,
        timestamp: str,
        user_reply: str | None = None,
        manifest: dict[str, Any] | None = None,
        checklist: dict[str, Any] | None = None,
        guided_answers: dict[str, Any] | None = None,
        intake_session: dict[str, Any] | None = None,
    ) -> HostConversationOutcome:
        try:
            active_session = self._store.find_active_session()
            if active_session is not None:
                if turn_kind == "resume":
                    action = self._runner.resume_session(
                        active_session.sessionId,
                        timestamp=timestamp,
                    )
                elif turn_kind == "reply":
                    action = self._runner.continue_session(
                        session_id=active_session.sessionId,
                        user_reply=user_reply,
                        timestamp=timestamp,
                    )
                else:
                    raise HostConversationAdapterError(f"Unsupported turn kind: {turn_kind}")
                return self._structured_outcome(action)

            if self._has_structured_start_inputs(
                manifest=manifest,
                checklist=checklist,
                guided_answers=guided_answers,
            ):
                action = self._runner.start_structured_guided_intake_session(
                    session_id=self._new_session_id(),
                    manifest=manifest,
                    checklist=checklist,
                    guided_answers=guided_answers,
                    timestamp=timestamp,
                    intake_session=intake_session,
                )
                return self._structured_outcome(action)

            return HostConversationOutcome(
                mode="freeform",
                promptDirective="stay_freeform",
            )
        except HostConversationAdapterError:
            raise
        except (HostSessionStoreError, HostSessionRunnerError, ValueError, KeyError, TypeError) as exc:
            raise HostConversationAdapterError(str(exc)) from exc

    @staticmethod
    def _has_structured_start_inputs(
        *,
        manifest: dict[str, Any] | None,
        checklist: dict[str, Any] | None,
        guided_answers: dict[str, Any] | None,
    ) -> bool:
        provided = [manifest is not None, checklist is not None, guided_answers is not None]
        if any(provided) and not all(provided):
            raise HostConversationAdapterError(
                "Structured start requires manifest, checklist, and guided_answers"
            )
        return all(provided)

    @staticmethod
    def _new_session_id() -> str:
        return f"host-session-{uuid4()}"

    @staticmethod
    def _structured_outcome(action: HostSessionAction) -> HostConversationOutcome:
        next_action_kind = action.nextActionKind
        try:
            prompt_directive = _RUNTIME_TO_PROMPT_DIRECTIVE[next_action_kind]
        except KeyError as exc:
            raise HostConversationAdapterError(
                f"Unsupported runtime next action kind: {next_action_kind}"
            ) from exc
        return HostConversationOutcome(
            mode="structured",
            promptDirective=prompt_directive,
            sessionId=action.sessionState.sessionId,
            sessionState=action.sessionState,
            nextActionKind=next_action_kind,
            currentProjection=action.currentProjection,
            currentBatch=action.currentBatch,
        )


def default_host_session_store_path(skill_root: Path | None = None) -> Path:
    base_root = skill_root or Path(__file__).resolve().parents[1]
    return Path(base_root) / ".runtime" / "host_sessions"


__all__ = [
    "HostConversationAdapter",
    "HostConversationAdapterError",
    "HostConversationMode",
    "HostConversationOutcome",
    "HostConversationTurnKind",
    "HostPromptDirective",
    "default_host_session_store_path",
]
