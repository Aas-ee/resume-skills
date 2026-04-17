"""Claude adapter helpers for the resume skill."""

from resume_runtime.runtime import (
    HostConversationAdapter,
    HostConversationAdapterError,
    HostConversationOutcome,
    HostSessionAction,
    HostSessionRunner,
    HostSessionRunnerError,
    HostSessionState,
    HostSessionStore,
    HostSessionStoreError,
    MaterialIntakeResult,
    ResumeMaterial,
    default_host_session_store_path,
)
from resume.runtime.agent_intake_entrypoint import (
    AgentIntakeEntrypoint,
    AgentIntakeEntrypointError,
    AgentIntakeOutcome,
)
from resume.runtime.agent_prompt_adapter import render_agent_outcome_prompt, render_template_selection_prompt

__all__ = [
    "AgentIntakeEntrypoint",
    "AgentIntakeEntrypointError",
    "AgentIntakeOutcome",
    "HostConversationAdapter",
    "HostConversationAdapterError",
    "HostConversationOutcome",
    "HostSessionAction",
    "HostSessionRunner",
    "HostSessionRunnerError",
    "HostSessionState",
    "HostSessionStore",
    "HostSessionStoreError",
    "MaterialIntakeResult",
    "ResumeMaterial",
    "default_host_session_store_path",
    "render_agent_outcome_prompt",
    "render_template_selection_prompt",
]
