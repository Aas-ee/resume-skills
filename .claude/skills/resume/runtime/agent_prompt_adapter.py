from __future__ import annotations

from resume_runtime.runtime.agent_intake_core import AgentIntakeCoreOutcome

from resume.runtime.prompt_renderer import (
    render_active_session_recovery_failure_prompt,
    render_ask_existing_material_prompt,
    render_drafting_prompt,
    render_material_parse_failure_prompt,
    render_structured_prompt,
)


def render_agent_outcome_prompt(outcome: AgentIntakeCoreOutcome) -> str | None:
    parsed_answers = outcome.materialResult.guidedAnswers if outcome.materialResult is not None else {}

    if outcome.promptDirective == "ask_existing_material":
        return render_ask_existing_material_prompt()
    if outcome.promptDirective == "parsing_failed":
        return render_material_parse_failure_prompt()
    if outcome.promptDirective == "session_recovery_failed":
        return render_active_session_recovery_failure_prompt()
    if outcome.promptDirective in {"ask_current_batch", "ask_yes_no_only", "handoff_to_drafting"}:
        if outcome.structuredOutcome is None:
            raise ValueError("Structured prompt directive requires structuredOutcome")
        return render_structured_prompt(outcome.structuredOutcome, parsed_answers=parsed_answers)
    if outcome.promptDirective in {"start_drafting", "continue_drafting"}:
        return render_drafting_prompt(parsed_answers=parsed_answers)
    if outcome.promptDirective == "stay_freeform":
        return None
    raise ValueError(f"Unsupported agent prompt directive: {outcome.promptDirective}")
