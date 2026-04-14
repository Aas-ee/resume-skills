from __future__ import annotations

import re

from resume.runtime.follow_up_agent_adapter import AskedQuestion, BatchAnswerResult

_DECLINE_PATTERNS = (
    re.compile(r"\b(?:prefer not to answer|prefer not to say|rather not answer|rather not say)\b", re.IGNORECASE),
    re.compile(r"\b(?:decline to answer|won't answer|will not answer|skip these|skip all|pass on these)\b", re.IGNORECASE),
    re.compile(r"(?:暂时不想回答|先不回答|不回答这些|跳过这些|都不回答|不方便回答)") ,
)

_LABEL_PATTERN = re.compile(r"^([A-Za-z0-9_.\[\]-]+)\s*[:：]\s*(.*?)\s*$")
_NUMBERED_PATTERN = re.compile(r"^\s*(\d+)[\.)]\s+(.*?)\s*$")
_BULLET_PATTERN = re.compile(r"^\s*(?:[-*•]|[–—])\s+(.*?)\s*$")

_YES_TOKENS = {
    "yes",
    "y",
    "ok",
    "okay",
    "sure",
    "continue",
    "go on",
    "proceed",
    "继续",
    "继续吧",
    "要",
    "好的",
    "好",
    "可以",
    "是",
    "是的",
    "行",
}
_NO_TOKENS = {
    "no",
    "n",
    "nope",
    "stop",
    "done",
    "enough",
    "不用",
    "不用了",
    "不需要",
    "不要",
    "先这样",
    "就这样",
    "否",
    "不是",
    "不",
}


def normalize_batch_answer(
    batch: list[AskedQuestion],
    answer_text: str | None,
) -> BatchAnswerResult:
    asked_field_ids = [item.fieldId for item in batch]
    if not asked_field_ids:
        return BatchAnswerResult(answers={})

    normalized_text = _normalize_text(answer_text)
    if not normalized_text:
        return BatchAnswerResult(answers={})

    if _is_full_batch_decline(normalized_text):
        return BatchAnswerResult(answers={}, userDeclined=True)

    label_answers = _parse_label_answers(asked_field_ids, normalized_text)
    if label_answers:
        return BatchAnswerResult(answers=label_answers)

    if len(asked_field_ids) == 1:
        return BatchAnswerResult(answers={asked_field_ids[0]: normalized_text})

    numbered_answers = _parse_numbered_answers(asked_field_ids, normalized_text)
    if numbered_answers:
        return BatchAnswerResult(answers=numbered_answers)

    bullet_answers = _parse_bullet_answers(asked_field_ids, normalized_text)
    if bullet_answers:
        return BatchAnswerResult(answers=bullet_answers)

    return BatchAnswerResult(answers={})


def parse_recommended_yes_no(answer_text: str | None) -> str | None:
    normalized = _normalize_decision_text(answer_text)
    if not normalized:
        return None

    if _contains_both_yes_and_no(normalized):
        return None

    tokens = tuple(normalized.split())
    if _all_tokens_are(tokens, _YES_TOKENS):
        return "yes"
    if _all_tokens_are(tokens, _NO_TOKENS):
        return "no"
    return None


def _normalize_text(answer_text: str | None) -> str:
    if answer_text is None:
        return ""
    lines = [line.strip() for line in answer_text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines).strip()


def _is_full_batch_decline(answer_text: str) -> bool:
    return any(pattern.search(answer_text) for pattern in _DECLINE_PATTERNS)


def _parse_label_answers(
    asked_field_ids: list[str],
    answer_text: str,
) -> dict[str, str]:
    asked = set(asked_field_ids)
    parsed: dict[str, str] = {}
    matched_any_label = False

    for line in answer_text.splitlines():
        match = _LABEL_PATTERN.match(line)
        if not match:
            continue
        matched_any_label = True
        field_id, value = match.groups()
        value = value.strip()
        if field_id in asked and value:
            parsed[field_id] = value

    if matched_any_label:
        return parsed
    return {}


def _parse_numbered_answers(
    asked_field_ids: list[str],
    answer_text: str,
) -> dict[str, str]:
    entries: list[tuple[int, str]] = []
    for line in answer_text.splitlines():
        match = _NUMBERED_PATTERN.match(line)
        if not match:
            return {}
        index = int(match.group(1))
        value = match.group(2).strip()
        if value:
            entries.append((index, value))

    if not entries:
        return {}

    if [index for index, _ in entries] != list(range(1, len(entries) + 1)):
        return {}

    return {
        asked_field_ids[position]: value
        for position, (_, value) in enumerate(entries[: len(asked_field_ids)])
    }


def _parse_bullet_answers(
    asked_field_ids: list[str],
    answer_text: str,
) -> dict[str, str]:
    entries: list[str] = []
    for line in answer_text.splitlines():
        match = _BULLET_PATTERN.match(line)
        if not match:
            return {}
        value = match.group(1).strip()
        if value:
            entries.append(value)

    if not entries:
        return {}

    return {
        asked_field_ids[position]: value
        for position, value in enumerate(entries[: len(asked_field_ids)])
    }


def _normalize_decision_text(answer_text: str | None) -> str:
    if answer_text is None:
        return ""
    lowered = answer_text.strip().lower()
    lowered = re.sub(r"[.!?。,，；;：:\s]+", " ", lowered)
    return lowered.strip()


def _contains_both_yes_and_no(normalized: str) -> bool:
    tokens = tuple(normalized.split())
    yes_present = any(token in _YES_TOKENS for token in tokens)
    no_present = any(token in _NO_TOKENS for token in tokens)
    if yes_present and no_present:
        return True
    if "yes or no" in normalized:
        return True
    return False


def _all_tokens_are(tokens: tuple[str, ...], allowed_tokens: set[str]) -> bool:
    return bool(tokens) and all(token in allowed_tokens for token in tokens)
