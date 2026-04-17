from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from resume_runtime.runtime.conversation_router import route_conversation_turn
from resume_runtime.runtime.host_conversation_adapter import (
    HostConversationAdapter,
    HostConversationAdapterError,
    HostConversationOutcome,
)
from resume_runtime.runtime.host_session_store import HostSessionStore, HostSessionStoreError
from resume_runtime.runtime.material_intake_adapter import (
    MaterialIntakeResult,
    ResumeMaterial,
    build_material_intake_artifacts,
)

EntrypointMode = Literal["freeform_discovery", "material_parsing", "structured_intake", "drafting"]
PromptDirective = Literal[
    "stay_freeform",
    "ask_existing_material",
    "parsing_failed",
    "session_recovery_failed",
    "ask_current_batch",
    "ask_yes_no_only",
    "handoff_to_drafting",
    "start_drafting",
    "continue_drafting",
]


class AgentIntakeCoreError(Exception):
    """Raised when public intake orchestration inputs are incomplete."""


@dataclass(frozen=True)
class AgentIntakeCoreOutcome:
    mode: EntrypointMode
    promptDirective: PromptDirective
    prompt: str | None
    structuredOutcome: HostConversationOutcome | None = None
    materialResult: MaterialIntakeResult | None = None


class AgentIntakeCore:
    def __init__(self, store: HostSessionStore, adapter: HostConversationAdapter) -> None:
        self._store = store
        self._adapter = adapter

    def handle_turn(
        self,
        *,
        turn_kind: Literal["reply", "resume"],
        timestamp: str,
        user_message: str | None = None,
        manifest: dict[str, Any] | None = None,
        checklist: dict[str, Any] | None = None,
        materials: list[ResumeMaterial] | None = None,
        drafting_started: bool = False,
    ) -> AgentIntakeCoreOutcome:
        materials = materials or []
        try:
            has_active_session = self._store.find_active_session() is not None
        except HostSessionStoreError:
            return AgentIntakeCoreOutcome(
                mode="freeform_discovery",
                promptDirective="session_recovery_failed",
                prompt=None,
            )

        route = route_conversation_turn(
            user_message=user_message,
            has_material=bool(materials),
            has_active_session=has_active_session,
            drafting_started=drafting_started,
        )

        if route.mode == "resume_active_session":
            try:
                structured_outcome = self._adapter.handle_turn(
                    turn_kind=turn_kind,
                    timestamp=timestamp,
                    user_reply=user_message,
                )
            except HostConversationAdapterError:
                return AgentIntakeCoreOutcome(
                    mode="freeform_discovery",
                    promptDirective="session_recovery_failed",
                    prompt=None,
                )
            if structured_outcome.promptDirective == "handoff_to_drafting":
                return AgentIntakeCoreOutcome(
                    mode="drafting",
                    promptDirective=structured_outcome.promptDirective,
                    prompt=None,
                    structuredOutcome=structured_outcome,
                )
            return AgentIntakeCoreOutcome(
                mode="structured_intake",
                promptDirective=structured_outcome.promptDirective,
                prompt=None,
                structuredOutcome=structured_outcome,
            )

        if route.mode == "parse_material":
            if manifest is None or checklist is None:
                raise AgentIntakeCoreError("manifest and checklist are required for material parsing")
            material_result = build_material_intake_artifacts(
                manifest=manifest,
                checklist=checklist,
                materials=materials,
            )
            if material_result.parseStatus == "needs_fallback":
                return AgentIntakeCoreOutcome(
                    mode="freeform_discovery",
                    promptDirective="parsing_failed",
                    prompt=None,
                    materialResult=material_result,
                )
            if not material_result.missingRequiredFields:
                return AgentIntakeCoreOutcome(
                    mode="drafting",
                    promptDirective="start_drafting",
                    prompt=None,
                    materialResult=material_result,
                )
            try:
                structured_outcome = self._adapter.handle_turn(
                    turn_kind="reply",
                    timestamp=timestamp,
                    manifest=manifest,
                    checklist=material_result.bootstrapChecklist,
                    guided_answers=material_result.guidedAnswers,
                    intake_session={
                        "hasExistingMaterial": True,
                        "documentIds": material_result.documentIds,
                        "phase": "handed-off",
                        "route": "guided-intake",
                        "status": "active",
                    },
                )
            except HostConversationAdapterError:
                return AgentIntakeCoreOutcome(
                    mode="freeform_discovery",
                    promptDirective="parsing_failed",
                    prompt=None,
                    materialResult=material_result,
                )
            return AgentIntakeCoreOutcome(
                mode="structured_intake",
                promptDirective=structured_outcome.promptDirective,
                prompt=None,
                structuredOutcome=structured_outcome,
                materialResult=material_result,
            )

        if route.mode == "continue_drafting":
            return AgentIntakeCoreOutcome(
                mode="drafting",
                promptDirective="continue_drafting",
                prompt=None,
            )

        if route.mode == "ask_existing_material":
            return AgentIntakeCoreOutcome(
                mode="freeform_discovery",
                promptDirective="ask_existing_material",
                prompt=None,
            )

        return AgentIntakeCoreOutcome(
            mode="freeform_discovery",
            promptDirective="stay_freeform",
            prompt=None,
        )


__all__ = [
    "AgentIntakeCore",
    "AgentIntakeCoreError",
    "AgentIntakeCoreOutcome",
    "EntrypointMode",
    "PromptDirective",
]
