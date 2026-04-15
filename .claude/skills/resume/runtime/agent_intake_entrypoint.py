from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from resume_runtime.runtime.agent_intake_core import AgentIntakeCore, AgentIntakeCoreError

from resume.runtime.agent_prompt_adapter import render_agent_outcome_prompt
from resume.runtime.host_conversation_adapter import HostConversationAdapter, HostConversationOutcome
from resume.runtime.host_session_store import HostSessionStore
from resume.runtime.material_intake_adapter import MaterialIntakeResult, ResumeMaterial

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


class AgentIntakeEntrypointError(Exception):
    pass


@dataclass(frozen=True)
class AgentIntakeOutcome:
    mode: EntrypointMode
    promptDirective: PromptDirective
    prompt: str | None
    structuredOutcome: HostConversationOutcome | None = None
    materialResult: MaterialIntakeResult | None = None


class AgentIntakeEntrypoint:
    def __init__(self, store: HostSessionStore, adapter: HostConversationAdapter) -> None:
        self._core = AgentIntakeCore(store, adapter)

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
    ) -> AgentIntakeOutcome:
        try:
            core_outcome = self._core.handle_turn(
                turn_kind=turn_kind,
                timestamp=timestamp,
                user_message=user_message,
                manifest=manifest,
                checklist=checklist,
                materials=materials,
                drafting_started=drafting_started,
            )
        except AgentIntakeCoreError as exc:
            raise AgentIntakeEntrypointError(str(exc)) from exc

        return AgentIntakeOutcome(
            mode=core_outcome.mode,
            promptDirective=core_outcome.promptDirective,
            prompt=render_agent_outcome_prompt(core_outcome),
            structuredOutcome=core_outcome.structuredOutcome,
            materialResult=core_outcome.materialResult,
        )
