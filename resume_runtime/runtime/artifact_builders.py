from __future__ import annotations

from copy import deepcopy
from typing import Any


def question_text(prompt_hint: str) -> str:
    return f"Please provide {prompt_hint}."


def _requirements_by_field(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        requirement["fieldId"]: requirement
        for requirement in manifest["fieldRequirements"]
    }


def _question_field_ids(question_set: dict[str, Any]) -> set[str]:
    return {item["fieldId"] for item in question_set["questions"]}


def _validate_response_fields(responses: dict[str, Any], allowed_field_ids: set[str]) -> None:
    unknown_field_ids = sorted(set(responses.keys()) - allowed_field_ids)
    if unknown_field_ids:
        raise ValueError("unknown response field: " + ", ".join(unknown_field_ids))


def derive_guided_intake_checklist(
    manifest: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    requirements = sorted(
        manifest["fieldRequirements"],
        key=lambda requirement: requirement["order"],
    )
    return {
        "checklistId": f"guided-intake-{manifest['templateId']}",
        "templateId": manifest["templateId"],
        "templateVersion": manifest["version"],
        "requiredFields": [item["fieldId"] for item in requirements if item["required"]],
        "optionalFields": [item["fieldId"] for item in requirements if not item["required"]],
        "repeatableFields": [item["fieldId"] for item in requirements if item["repeatable"]],
        "generatedAt": generated_at,
    }


def derive_guided_intake_question_set(
    manifest: dict[str, Any],
    checklist: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    requirements_by_field = _requirements_by_field(manifest)
    ordered_field_ids = checklist["requiredFields"] + checklist["optionalFields"]

    return {
        "questionSetId": f"guided-intake-question-set-{manifest['templateId']}",
        "templateId": manifest["templateId"],
        "templateVersion": manifest["version"],
        "questions": [
            {
                "fieldId": field_id,
                "question": question_text(requirements_by_field[field_id]["promptHint"]),
            }
            for field_id in ordered_field_ids
        ],
        "generatedAt": generated_at,
    }


def assemble_guided_intake_response_set(
    question_set: dict[str, Any],
    responses: dict[str, Any],
    *,
    updated_at: str,
) -> dict[str, Any]:
    allowed_field_ids = _question_field_ids(question_set)
    _validate_response_fields(responses, allowed_field_ids)

    return {
        "responseSetId": f"guided-intake-response-set-{question_set['templateId']}",
        "templateId": question_set["templateId"],
        "templateVersion": question_set["templateVersion"],
        "questionSetId": question_set["questionSetId"],
        "responses": deepcopy(responses),
        "updatedAt": updated_at,
    }


def project_guided_intake_profile(response_set: dict[str, Any]) -> dict[str, Any]:
    profile_id = f"profile-from-{response_set['responseSetId']}"
    return {
        "projectionId": f"guided-intake-profile-projection-{response_set['templateId']}",
        "responseSetId": response_set["responseSetId"],
        "questionSetId": response_set["questionSetId"],
        "templateId": response_set["templateId"],
        "templateVersion": response_set["templateVersion"],
        "profile": {
            "profileId": profile_id,
            "fieldValues": deepcopy(response_set["responses"]),
            "provenance": {
                field_id: [response_set["responseSetId"]]
                for field_id in response_set["responses"].keys()
            },
            "profileStatus": "partial",
            "updatedAt": response_set["updatedAt"],
        },
    }


def derive_gap_report(
    manifest: dict[str, Any],
    projection: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    profile = projection["profile"]
    profile_field_values = profile["fieldValues"]
    missing_required: list[str] = []
    missing_recommended: list[str] = []

    for requirement in manifest["fieldRequirements"]:
        field_id = requirement["fieldId"]
        if field_id in profile_field_values:
            continue
        if requirement["required"]:
            missing_required.append(field_id)
        else:
            missing_recommended.append(field_id)

    missing_field_ids = set(missing_required + missing_recommended)
    questions = [
        {
            "fieldId": requirement["fieldId"],
            "question": question_text(requirement["promptHint"]),
        }
        for requirement in manifest["fieldRequirements"]
        if requirement["fieldId"] in missing_field_ids
    ]

    return {
        "reportId": f"gap-for-{profile['profileId']}-{manifest['templateId']}",
        "templateId": manifest["templateId"],
        "profileId": profile["profileId"],
        "missingRequired": missing_required,
        "missingRecommended": missing_recommended,
        "conflicts": [],
        "questions": questions,
        "generatedAt": generated_at,
    }


def derive_follow_up_question_set(
    gap_report: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "followUpQuestionSetId": f"follow-up-for-{gap_report['reportId']}",
        "reportId": gap_report["reportId"],
        "templateId": gap_report["templateId"],
        "profileId": gap_report["profileId"],
        "questions": deepcopy(gap_report["questions"]),
        "generatedAt": generated_at,
    }


def assemble_follow_up_response_set(
    question_set: dict[str, Any],
    responses: dict[str, Any],
    current_profile: dict[str, Any],
    *,
    updated_at: str,
) -> dict[str, Any]:
    allowed_field_ids = _question_field_ids(question_set)
    _validate_response_fields(responses, allowed_field_ids)

    if current_profile["profileId"] != question_set["profileId"]:
        raise ValueError("follow-up response set profileId does not match follow-up question set")

    return {
        "followUpResponseSetId": (
            f"follow-up-response-for-{question_set['followUpQuestionSetId']}"
        ),
        "followUpQuestionSetId": question_set["followUpQuestionSetId"],
        "reportId": question_set["reportId"],
        "templateId": question_set["templateId"],
        "profileId": question_set["profileId"],
        "responses": deepcopy(responses),
        "updatedAt": updated_at,
    }


def project_follow_up_profile(
    response_set: dict[str, Any],
    base_projection: dict[str, Any],
) -> dict[str, Any]:
    base_profile = base_projection["profile"]

    if response_set["profileId"] != base_profile["profileId"]:
        raise ValueError("follow-up response set profileId does not match base projection profileId")
    if response_set["templateId"] != base_projection["templateId"]:
        raise ValueError("follow-up response set templateId does not match base projection templateId")

    field_values = deepcopy(base_profile["fieldValues"])
    field_values.update(deepcopy(response_set["responses"]))

    provenance = deepcopy(base_profile["provenance"])
    provenance.update(
        {
            field_id: [response_set["followUpResponseSetId"]]
            for field_id in response_set["responses"].keys()
        }
    )

    return {
        "projectionId": (
            "follow-up-profile-projection-for-"
            + response_set["followUpResponseSetId"]
        ),
        "followUpResponseSetId": response_set["followUpResponseSetId"],
        "followUpQuestionSetId": response_set["followUpQuestionSetId"],
        "reportId": response_set["reportId"],
        "templateId": base_projection["templateId"],
        "templateVersion": base_projection["templateVersion"],
        "baseProfileId": base_profile["profileId"],
        "profile": {
            "profileId": f"profile-from-{response_set['followUpResponseSetId']}",
            "fieldValues": field_values,
            "provenance": provenance,
            "profileStatus": "partial",
            "updatedAt": response_set["updatedAt"],
        },
    }
