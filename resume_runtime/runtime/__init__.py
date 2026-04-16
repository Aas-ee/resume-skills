"""Runtime helpers for the public resume runtime package."""

from resume_runtime.runtime.agent_intake_core import (
    AgentIntakeCore,
    AgentIntakeCoreError,
    AgentIntakeCoreOutcome,
    EntrypointMode,
    PromptDirective,
)
from resume_runtime.runtime.artifact_builders import derive_guided_intake_checklist
from resume_runtime.runtime.conversation_router import ConversationRoute, route_conversation_turn
from resume_runtime.runtime.follow_up_agent_adapter import AskedQuestion, BatchAnswerResult
from resume_runtime.runtime.host_conversation_adapter import (
    HostConversationAdapter,
    HostConversationAdapterError,
    HostConversationOutcome,
    default_host_session_store_path,
)
from resume_runtime.runtime.host_session_runner import HostSessionAction, HostSessionRunner, HostSessionRunnerError
from resume_runtime.runtime.host_session_state import HostSessionState
from resume_runtime.runtime.host_session_store import HostSessionStore, HostSessionStoreError
from resume_runtime.runtime.material_intake_adapter import MaterialIntakeResult, ResumeMaterial
from resume_runtime.runtime.serialization import host_conversation_outcome_to_dict, serialize_question_batch
from resume_runtime.runtime.session_runner import SessionRunner, SessionRunnerResult
from resume_runtime.runtime.template_catalog import TemplateCatalogEntry, TemplateCard, load_template_catalog
from resume_runtime.runtime.template_renderer import render_template_bundle, write_rendered_bundle
from resume_runtime.runtime.template_store import TemplateStore

__all__ = [
    "AgentIntakeCore",
    "AgentIntakeCoreError",
    "AgentIntakeCoreOutcome",
    "AskedQuestion",
    "BatchAnswerResult",
    "ConversationRoute",
    "EntrypointMode",
    "TemplateCatalogEntry",
    "TemplateCard",
    "TemplateStore",
    "HostConversationAdapter",
    "default_host_session_store_path",
    "HostConversationAdapterError",
    "HostConversationOutcome",
    "HostSessionAction",
    "HostSessionRunner",
    "HostSessionRunnerError",
    "HostSessionState",
    "HostSessionStore",
    "HostSessionStoreError",
    "MaterialIntakeResult",
    "PromptDirective",
    "ResumeMaterial",
    "SessionRunner",
    "SessionRunnerResult",
    "derive_guided_intake_checklist",
    "host_conversation_outcome_to_dict",
    "load_template_catalog",
    "render_template_bundle",
    "serialize_question_batch",
    "route_conversation_turn",
    "write_rendered_bundle",
]
