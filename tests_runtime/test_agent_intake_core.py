import tempfile
import unittest
from pathlib import Path

from resume_runtime.runtime.agent_intake_core import AgentIntakeCore
from resume_runtime.runtime.host_conversation_adapter import (
    HostConversationAdapter,
    HostConversationAdapterError,
    HostConversationOutcome,
)
from resume_runtime.runtime.host_session_store import HostSessionStore, HostSessionStoreError
from resume_runtime.runtime.material_intake_adapter import ResumeMaterial
from resume_runtime.runtime.session_runner import SessionRunner


class _StoreStub:
    def __init__(self, active_session=object(), error: Exception | None = None):
        self._active_session = active_session
        self._error = error

    def find_active_session(self):
        if self._error is not None:
            raise self._error
        return self._active_session


class _AdapterStub:
    def __init__(
        self,
        outcome: HostConversationOutcome | None = None,
        error: Exception | None = None,
    ) -> None:
        self._outcome = outcome
        self._error = error
        self.calls: list[dict[str, object]] = []

    def handle_turn(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._outcome


class AgentIntakeCoreTests(unittest.TestCase):
    def test_resume_intent_without_material_asks_for_existing_material(self):
        core = self._build_core()

        outcome = core.handle_turn(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="Please help update my resume for a backend role.",
        )

        self.assertEqual(outcome.mode, "freeform_discovery")
        self.assertEqual(outcome.promptDirective, "ask_existing_material")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNone(outcome.materialResult)

    def test_structured_handoff_returns_structured_outcome_without_prompt_text(self):
        core = self._build_core()
        manifest = {
            "templateId": "markdown-basic",
            "version": "1.0.0",
            "fieldRequirements": [
                {
                    "fieldId": "basic.name",
                    "required": True,
                    "promptHint": "Candidate name in the Markdown title",
                },
                {
                    "fieldId": "basic.email",
                    "required": True,
                    "promptHint": "Primary email below the title",
                },
            ],
        }
        checklist = {
            "templateId": "markdown-basic",
            "templateVersion": "1.0.0",
            "requiredFields": ["basic.name", "basic.email"],
            "optionalFields": [],
        }
        materials = [
            ResumeMaterial(
                documentId="doc-1",
                sourceLabel="existing-resume.md",
                mediaType="text/markdown",
                text="# Ada Lovelace",
            )
        ]

        outcome = core.handle_turn(
            turn_kind="resume",
            timestamp="2026-04-15T10:00:00Z",
            manifest=manifest,
            checklist=checklist,
            materials=materials,
        )

        self.assertEqual(outcome.mode, "structured_intake")
        self.assertEqual(outcome.promptDirective, "ask_current_batch")
        self.assertIsNone(outcome.prompt)
        self.assertIsNotNone(outcome.structuredOutcome)
        self.assertIsNotNone(outcome.materialResult)
        self.assertEqual(outcome.structuredOutcome.mode, "structured")
        self.assertEqual(outcome.structuredOutcome.promptDirective, "ask_current_batch")
        self.assertEqual(
            [item.fieldId for item in outcome.structuredOutcome.currentBatch or []],
            ["basic.email"],
        )
        self.assertEqual(outcome.materialResult.parseStatus, "parsed")
        self.assertEqual(outcome.materialResult.guidedAnswers, {"basic.name": "Ada Lovelace"})

    def test_session_store_recovery_failure_returns_session_recovery_failed(self):
        core = AgentIntakeCore(
            _StoreStub(error=HostSessionStoreError("corrupted store")),
            _AdapterStub(),
        )

        outcome = core.handle_turn(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="help with my resume",
        )

        self.assertEqual(outcome.mode, "freeform_discovery")
        self.assertEqual(outcome.promptDirective, "session_recovery_failed")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNone(outcome.materialResult)

    def test_active_session_adapter_failure_returns_session_recovery_failed(self):
        core = AgentIntakeCore(
            _StoreStub(active_session={"sessionId": "session-1"}),
            _AdapterStub(error=HostConversationAdapterError("adapter failed")),
        )

        outcome = core.handle_turn(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="yes",
        )

        self.assertEqual(outcome.mode, "freeform_discovery")
        self.assertEqual(outcome.promptDirective, "session_recovery_failed")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNone(outcome.materialResult)

    def test_parse_fallback_returns_parsing_failed_without_prompt_text(self):
        core = AgentIntakeCore(_StoreStub(active_session=None), _AdapterStub())

        outcome = core.handle_turn(
            turn_kind="resume",
            timestamp="2026-04-15T10:00:00Z",
            manifest=self._full_manifest(),
            checklist=self._full_checklist(),
            materials=[
                ResumeMaterial(
                    documentId="doc-1",
                    sourceLabel="empty.md",
                    mediaType="text/markdown",
                    text="   ",
                )
            ],
        )

        self.assertEqual(outcome.mode, "freeform_discovery")
        self.assertEqual(outcome.promptDirective, "parsing_failed")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNotNone(outcome.materialResult)
        self.assertEqual(outcome.materialResult.parseStatus, "needs_fallback")

    def test_parse_success_without_missing_required_fields_starts_drafting(self):
        core = AgentIntakeCore(_StoreStub(active_session=None), _AdapterStub())

        outcome = core.handle_turn(
            turn_kind="resume",
            timestamp="2026-04-15T10:00:00Z",
            manifest=self._full_manifest(),
            checklist=self._full_checklist(),
            materials=[
                ResumeMaterial(
                    documentId="doc-1",
                    sourceLabel="resume.md",
                    mediaType="text/markdown",
                    text=(
                        "# Ada Lovelace\n"
                        "Role: Backend Engineer\n"
                        "Project: Resume Runtime\n"
                    ),
                )
            ],
        )

        self.assertEqual(outcome.mode, "drafting")
        self.assertEqual(outcome.promptDirective, "start_drafting")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNotNone(outcome.materialResult)
        self.assertEqual(outcome.materialResult.parseStatus, "parsed")
        self.assertEqual(outcome.materialResult.missingRequiredFields, [])
        self.assertEqual(
            outcome.materialResult.guidedAnswers,
            {
                "basic.name": "Ada Lovelace",
                "required.role": "Backend Engineer",
                "required.project": "Resume Runtime",
            },
        )

    def test_active_session_handoff_returns_drafting_mode_without_prompt_text(self):
        structured_outcome = HostConversationOutcome(
            mode="structured",
            promptDirective="handoff_to_drafting",
            sessionId="session-1",
            nextActionKind="completed",
        )
        core = AgentIntakeCore(
            _StoreStub(active_session={"sessionId": "session-1"}),
            _AdapterStub(outcome=structured_outcome),
        )

        outcome = core.handle_turn(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="Yes, draft it now.",
        )

        self.assertEqual(outcome.mode, "drafting")
        self.assertEqual(outcome.promptDirective, "handoff_to_drafting")
        self.assertIsNone(outcome.prompt)
        self.assertIs(outcome.structuredOutcome, structured_outcome)
        self.assertIsNone(outcome.materialResult)

    def test_drafting_started_routes_to_continue_drafting(self):
        core = AgentIntakeCore(_StoreStub(active_session=None), _AdapterStub())

        outcome = core.handle_turn(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="keep refining this summary",
            drafting_started=True,
        )

        self.assertEqual(outcome.mode, "drafting")
        self.assertEqual(outcome.promptDirective, "continue_drafting")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNone(outcome.materialResult)

    def test_non_resume_freeform_path_stays_freeform(self):
        core = AgentIntakeCore(_StoreStub(active_session=None), _AdapterStub())

        outcome = core.handle_turn(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="What is a good way to learn Python generators?",
        )

        self.assertEqual(outcome.mode, "freeform_discovery")
        self.assertEqual(outcome.promptDirective, "stay_freeform")
        self.assertIsNone(outcome.prompt)
        self.assertIsNone(outcome.structuredOutcome)
        self.assertIsNone(outcome.materialResult)

    def _build_core(self) -> AgentIntakeCore:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        store = HostSessionStore(Path(temp_dir.name))
        runner = SessionRunner(
            guided_question_set_generated_at="2026-04-15T10:00:00Z",
            guided_response_set_updated_at="2026-04-15T10:00:00Z",
            follow_up_generated_at="2026-04-15T10:00:00Z",
            follow_up_response_updated_at="2026-04-15T10:00:00Z",
        )
        adapter = HostConversationAdapter(store, runner)
        return AgentIntakeCore(store, adapter)

    @staticmethod
    def _full_manifest() -> dict[str, object]:
        return {
            "templateId": "markdown-basic",
            "version": "1.0.0",
            "fieldRequirements": [
                {
                    "fieldId": "basic.name",
                    "required": True,
                    "promptHint": "Candidate name in the Markdown title",
                },
                {
                    "fieldId": "required.role",
                    "required": True,
                    "promptHint": "Current role label",
                },
                {
                    "fieldId": "required.project",
                    "required": True,
                    "promptHint": "Representative project label",
                },
            ],
        }

    @staticmethod
    def _full_checklist() -> dict[str, object]:
        return {
            "templateId": "markdown-basic",
            "templateVersion": "1.0.0",
            "requiredFields": ["basic.name", "required.role", "required.project"],
            "optionalFields": [],
        }


if __name__ == "__main__":
    unittest.main()
