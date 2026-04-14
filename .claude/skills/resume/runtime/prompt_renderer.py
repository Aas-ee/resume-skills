from __future__ import annotations

from typing import Any

from resume.runtime.host_conversation_adapter import HostConversationOutcome


def render_ask_existing_material_prompt() -> str:
    return (
        "你现在有现成简历吗？可以直接发 PDF、Markdown、纯文本，或者项目笔记也行。"
        "我先帮你解析已有内容，再只补问缺的部分。"
    )


def render_material_parse_failure_prompt() -> str:
    return (
        "我这次没能可靠解析你发来的材料。你可以直接粘贴文本，"
        "或者我改成一步步引导你补信息。"
    )


def render_active_session_recovery_failure_prompt() -> str:
    return (
        "我找到你上一次的结构化收集记录了，但这次没法安全恢复。"
        "你可以重新发简历给我解析，或者我从头带你重新收集。"
    )


def render_drafting_prompt(*, parsed_answers: dict[str, Any]) -> str:
    if parsed_answers:
        return "现有材料里的关键信息已经够用了，我开始基于这些内容起草简历。"
    return "核心信息已经齐了，我开始起草简历。"


def render_structured_prompt(
    outcome: HostConversationOutcome,
    *,
    parsed_answers: dict[str, Any],
) -> str:
    preamble = ""
    if parsed_answers:
        preamble = "我先读取了你发来的材料，已经先提取出一部分信息。\n"

    if outcome.promptDirective == "ask_current_batch":
        if not outcome.currentBatch:
            raise ValueError("ask_current_batch requires currentBatch")
        question_lines = [
            f"{index}. {item.question}"
            for index, item in enumerate(outcome.currentBatch, start=1)
        ]
        return preamble + "我先补几个关键信息：\n" + "\n".join(question_lines)

    if outcome.promptDirective == "ask_yes_no_only":
        return (
            preamble
            + "目前核心必填信息已经够了。要不要继续补充推荐项，比如 GitHub、额外亮点或更多项目细节？"
            "请直接回答“要”或“不要”。"
        )

    if outcome.promptDirective == "handoff_to_drafting":
        return preamble + "信息已经够了，我现在开始基于现有内容起草简历。"

    raise ValueError(f"Unsupported prompt directive: {outcome.promptDirective}")
