import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SKILLS_ROOT = Path(__file__).resolve().parents[2]
if str(SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILLS_ROOT))

from resume_runtime.runtime.agent_intake_core import AgentIntakeCoreOutcome
from resume.runtime.agent_intake_entrypoint import AgentIntakeEntrypoint
from resume.runtime.agent_prompt_adapter import render_agent_outcome_prompt
from resume.runtime.follow_up_agent_adapter import AskedQuestion
from resume.runtime.host_conversation_adapter import HostConversationOutcome
from resume.runtime.material_intake_adapter import MaterialIntakeResult


class _StoreStub:
    def __init__(self, active_session=object(), error: Exception | None = None):
        self._active_session = active_session
        self._error = error

    def find_active_session(self):
        if self._error is not None:
            raise self._error
        return self._active_session


class AgentPromptAdapterTests(unittest.TestCase):
    def test_ask_existing_material_outcome_uses_renderer_prompt(self):
        outcome = AgentIntakeCoreOutcome(
            mode="freeform_discovery",
            promptDirective="ask_existing_material",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertIn("现成简历", prompt)

    def test_parsing_failed_outcome_uses_renderer_prompt(self):
        outcome = AgentIntakeCoreOutcome(
            mode="freeform_discovery",
            promptDirective="parsing_failed",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertIn("没能可靠解析", prompt)

    def test_session_recovery_failed_outcome_uses_renderer_prompt(self):
        outcome = AgentIntakeCoreOutcome(
            mode="freeform_discovery",
            promptDirective="session_recovery_failed",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertIn("没法安全恢复", prompt)

    def test_stay_freeform_outcome_returns_none(self):
        outcome = AgentIntakeCoreOutcome(
            mode="freeform_discovery",
            promptDirective="stay_freeform",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertIsNone(prompt)

    def test_unknown_directive_raises_value_error(self):
        outcome = AgentIntakeCoreOutcome(
            mode="freeform_discovery",
            promptDirective="unexpected_directive",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        with self.assertRaisesRegex(ValueError, "Unsupported agent prompt directive"):
            render_agent_outcome_prompt(outcome)

    def test_start_drafting_without_parsed_answers_uses_generic_prompt(self):
        outcome = AgentIntakeCoreOutcome(
            mode="drafting",
            promptDirective="start_drafting",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertEqual(prompt, "核心信息已经齐了，我开始起草简历。")

    def test_continue_drafting_with_parsed_answers_mentions_existing_material(self):
        outcome = AgentIntakeCoreOutcome(
            mode="drafting",
            promptDirective="continue_drafting",
            prompt=None,
            structuredOutcome=None,
            materialResult=self._material_result({"basic.name": "Ada Lovelace"}),
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertEqual(prompt, "现有材料里的关键信息已经够用了，我开始基于这些内容起草简历。")

    def test_ask_current_batch_with_parsed_answers_uses_structured_prompt_preamble(self):
        outcome = AgentIntakeCoreOutcome(
            mode="structured_intake",
            promptDirective="ask_current_batch",
            prompt=None,
            structuredOutcome=HostConversationOutcome(
                mode="structured",
                promptDirective="ask_current_batch",
                currentBatch=[
                    AskedQuestion(fieldId="required.role", question="你目前的目标岗位是什么？"),
                    AskedQuestion(fieldId="required.project", question="你最想突出的项目是什么？"),
                ],
            ),
            materialResult=self._material_result({"basic.name": "Ada Lovelace"}),
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertEqual(
            prompt,
            "我先读取了你发来的材料，已经先提取出一部分信息。\n"
            "我先补几个关键信息：\n"
            "1. 你目前的目标岗位是什么？\n"
            "2. 你最想突出的项目是什么？",
        )

    def test_ask_yes_no_only_with_parsed_answers_uses_structured_prompt_preamble(self):
        outcome = AgentIntakeCoreOutcome(
            mode="structured_intake",
            promptDirective="ask_yes_no_only",
            prompt=None,
            structuredOutcome=HostConversationOutcome(
                mode="structured",
                promptDirective="ask_yes_no_only",
            ),
            materialResult=self._material_result({"basic.name": "Ada Lovelace"}),
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertEqual(
            prompt,
            "我先读取了你发来的材料，已经先提取出一部分信息。\n"
            "目前核心必填信息已经够了。要不要继续补充推荐项，比如 GitHub、额外亮点或更多项目细节？"
            "请直接回答“要”或“不要”。",
        )

    def test_handoff_to_drafting_with_parsed_answers_uses_structured_prompt_preamble(self):
        outcome = AgentIntakeCoreOutcome(
            mode="drafting",
            promptDirective="handoff_to_drafting",
            prompt=None,
            structuredOutcome=HostConversationOutcome(
                mode="structured",
                promptDirective="handoff_to_drafting",
            ),
            materialResult=self._material_result({"basic.name": "Ada Lovelace"}),
        )

        prompt = render_agent_outcome_prompt(outcome)

        self.assertEqual(
            prompt,
            "我先读取了你发来的材料，已经先提取出一部分信息。\n"
            "信息已经够了，我现在开始基于现有内容起草简历。",
        )

    def test_structured_directive_without_structured_outcome_raises_value_error(self):
        outcome = AgentIntakeCoreOutcome(
            mode="structured_intake",
            promptDirective="ask_yes_no_only",
            prompt=None,
            structuredOutcome=None,
            materialResult=None,
        )

        with self.assertRaisesRegex(
            ValueError,
            "Structured prompt directive requires structuredOutcome",
        ):
            render_agent_outcome_prompt(outcome)

    def test_legacy_entrypoint_delegates_to_public_core_and_preserves_payload(self):
        structured_outcome = HostConversationOutcome(
            mode="structured",
            promptDirective="ask_yes_no_only",
        )
        material_result = self._material_result({"basic.name": "Ada Lovelace"})
        core_outcome = AgentIntakeCoreOutcome(
            mode="structured_intake",
            promptDirective="ask_yes_no_only",
            prompt=None,
            structuredOutcome=structured_outcome,
            materialResult=material_result,
        )
        entrypoint = AgentIntakeEntrypoint(_StoreStub(active_session=None), _adapter_stub(structured_outcome))

        with patch(
            "resume.runtime.agent_intake_entrypoint.AgentIntakeCore.handle_turn",
            return_value=core_outcome,
        ) as handle_turn, patch(
            "resume.runtime.agent_intake_entrypoint.render_agent_outcome_prompt",
            return_value="adapter prompt",
        ) as render_prompt:
            outcome = entrypoint.handle_turn(
                turn_kind="reply",
                timestamp="2026-04-15T10:00:00Z",
                user_message="yes",
            )

        handle_turn.assert_called_once_with(
            turn_kind="reply",
            timestamp="2026-04-15T10:00:00Z",
            user_message="yes",
            manifest=None,
            checklist=None,
            materials=None,
            drafting_started=False,
        )
        render_prompt.assert_called_once_with(core_outcome)
        self.assertEqual(outcome.mode, "structured_intake")
        self.assertEqual(outcome.promptDirective, "ask_yes_no_only")
        self.assertEqual(outcome.prompt, "adapter prompt")
        self.assertIs(outcome.structuredOutcome, structured_outcome)
        self.assertIs(outcome.materialResult, material_result)

    @staticmethod
    def _material_result(guided_answers):
        return MaterialIntakeResult(
            parseStatus="parsed",
            guidedAnswers=guided_answers,
            bootstrapChecklist={"requiredFields": [], "optionalFields": []},
            missingRequiredFields=[],
            missingOptionalFields=[],
            documentIds=["doc-1"],
        )


def _adapter_stub(outcome: HostConversationOutcome):
    class _AdapterStub:
        def handle_turn(self, **kwargs):
            return outcome

    return _AdapterStub()


if __name__ == "__main__":
    unittest.main()
