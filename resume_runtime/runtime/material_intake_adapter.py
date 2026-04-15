from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

ParseStatus = Literal["parsed", "needs_fallback"]
_GITHUB_RE = re.compile(r"https?://github\.com/[^\s)\\]+")
_ROLE_RE = re.compile(r"(?:role|职位|岗位)\s*[:：]\s*(.+)", re.IGNORECASE)
_PROJECT_RE = re.compile(r"(?:project|项目)\s*[:：]\s*(.+)", re.IGNORECASE)


@dataclass(frozen=True)
class ResumeMaterial:
    documentId: str
    sourceLabel: str
    mediaType: str
    text: str | None


@dataclass(frozen=True)
class MaterialIntakeResult:
    parseStatus: ParseStatus
    guidedAnswers: dict[str, Any]
    bootstrapChecklist: dict[str, Any]
    missingRequiredFields: list[str]
    missingOptionalFields: list[str]
    documentIds: list[str]


def build_material_intake_artifacts(
    *,
    manifest: dict[str, Any],
    checklist: dict[str, Any],
    materials: list[ResumeMaterial],
) -> MaterialIntakeResult:
    document_ids = [item.documentId for item in materials]
    parsed_answers = _extract_guided_answers(materials)
    if not parsed_answers:
        return MaterialIntakeResult(
            parseStatus="needs_fallback",
            guidedAnswers={},
            bootstrapChecklist=deepcopy(checklist),
            missingRequiredFields=_missing_fields(manifest, {}, required=True),
            missingOptionalFields=_missing_fields(manifest, {}, required=False),
            documentIds=document_ids,
        )

    bootstrap_checklist = _extend_checklist_for_bootstrap_answers(
        checklist,
        manifest,
        parsed_answers.keys(),
    )
    return MaterialIntakeResult(
        parseStatus="parsed",
        guidedAnswers=parsed_answers,
        bootstrapChecklist=bootstrap_checklist,
        missingRequiredFields=_missing_fields(manifest, parsed_answers, required=True),
        missingOptionalFields=_missing_fields(manifest, parsed_answers, required=False),
        documentIds=document_ids,
    )


def _extract_guided_answers(materials: list[ResumeMaterial]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    for material in materials:
        text = (material.text or "").strip()
        if not text:
            continue
        extracted = {
            "basic.name": _extract_name(text),
            "optional.github": _extract_github(text),
            "required.role": _extract_labeled_value(text, _ROLE_RE),
            "required.project": _extract_labeled_value(text, _PROJECT_RE),
        }
        for key, value in extracted.items():
            if key in answers or value in (None, ""):
                continue
            answers[key] = value
    return answers


def _extract_name(text: str) -> str | None:
    for line in text.splitlines():
        candidate = line.strip().lstrip("#").strip()
        if candidate and not any(token in candidate for token in ("邮箱", "GitHub", "http://", "https://")):
            return candidate
    return None


def _extract_github(text: str) -> str | None:
    match = _GITHUB_RE.search(text)
    return match.group(0) if match else None


def _extract_labeled_value(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _extend_checklist_for_bootstrap_answers(
    checklist: dict[str, Any],
    manifest: dict[str, Any],
    parsed_field_ids: Any,
) -> dict[str, Any]:
    allowed_field_ids = {item["fieldId"] for item in manifest["fieldRequirements"]}
    extended = deepcopy(checklist)
    optional_fields = list(extended.get("optionalFields", []))
    required_fields = set(extended.get("requiredFields", []))
    for field_id in parsed_field_ids:
        if field_id not in allowed_field_ids:
            continue
        if field_id in required_fields or field_id in optional_fields:
            continue
        optional_fields.append(field_id)
    extended["optionalFields"] = optional_fields
    return extended


def _missing_fields(
    manifest: dict[str, Any],
    guided_answers: dict[str, Any],
    *,
    required: bool,
) -> list[str]:
    return [
        item["fieldId"]
        for item in manifest["fieldRequirements"]
        if item["required"] is required and item["fieldId"] not in guided_answers
    ]
