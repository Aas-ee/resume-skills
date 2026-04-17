from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

RouteMode = Literal[
    "resume_active_session",
    "parse_material",
    "ask_existing_material",
    "continue_drafting",
    "stay_freeform",
]


@dataclass(frozen=True)
class ConversationRoute:
    mode: RouteMode
    reason: str


_CHINESE_RESUME_INTENT_TOKENS = (
    "简历",
    "改简历",
    "优化简历",
    "修改简历",
    "润色简历",
    "制作简历",
    "写简历",
    "完善简历",
    "整理项目经历",
    "把项目写进简历",
    "生成一版社招后端简历",
)

_ENGLISH_RESUME_INTENT_PATTERNS = (
    re.compile(r"\b(?:update|tailor)\s+my\s+(?:resume|cv)\b"),
    re.compile(r"\b(?:resume|cv)\s+(?:for|to)\b"),
)


def looks_like_resume_intent(message: str | None) -> bool:
    if not message:
        return False
    lowered = message.lower()
    return any(token in message for token in _CHINESE_RESUME_INTENT_TOKENS) or any(
        pattern.search(lowered) for pattern in _ENGLISH_RESUME_INTENT_PATTERNS
    )


def route_conversation_turn(
    *,
    user_message: str | None,
    has_material: bool,
    has_active_session: bool,
    drafting_started: bool,
) -> ConversationRoute:
    if has_active_session:
        return ConversationRoute(
            mode="resume_active_session",
            reason="active structured session wins",
        )
    if has_material:
        return ConversationRoute(
            mode="parse_material",
            reason="new material provided",
        )
    if drafting_started:
        return ConversationRoute(
            mode="continue_drafting",
            reason="drafting already started",
        )
    if looks_like_resume_intent(user_message):
        return ConversationRoute(
            mode="ask_existing_material",
            reason="resume intent without material",
        )
    return ConversationRoute(
        mode="stay_freeform",
        reason="no resume intent detected",
    )
