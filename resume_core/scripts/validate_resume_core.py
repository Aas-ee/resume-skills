import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schema"
EXAMPLES = ROOT / "examples"
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time")
def is_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    if "T" not in value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(schema_name: str, def_name: str) -> Draft202012Validator:
    schema = load_json(SCHEMA_DIR / schema_name)
    resolver = None
    if schema_name == "projection-layer.schema.json":
        content_schema = load_json(SCHEMA_DIR / "content-layer.schema.json")
        resolver = RefResolver.from_schema(
            schema,
            store={
                content_schema["$id"]: content_schema,
                (SCHEMA_DIR / "content-layer.schema.json").as_uri(): content_schema,
                schema["$id"]: schema,
                (SCHEMA_DIR / schema_name).as_uri(): schema,
            },
        )
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{def_name}",
        },
        resolver=resolver,
        format_checker=FORMAT_CHECKER,
    )


def load_required_json_collection(directory: Path, label: str) -> list[Any]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError(f"no example JSON files found for {label}: {directory}")
    return [load_json(path) for path in paths]


def load_example_artifacts() -> dict[str, Any]:
    return {
        "catalog": load_json(EXAMPLES / "shared-field-catalog.v1.json"),
        "manifests": load_required_json_collection(
            EXAMPLES / "templates", "template manifests"
        ),
        "registry": load_json(EXAMPLES / "template-registry.v1.json"),
        "source_document": load_json(
            EXAMPLES / "source-documents" / "existing-resume-markdown.v1.json"
        ),
        "intake_sessions": load_required_json_collection(
            EXAMPLES / "intake-sessions", "intake sessions"
        ),
        "guided_intake_checklists": load_required_json_collection(
            EXAMPLES / "guided-intake-checklists", "guided-intake checklists"
        ),
        "guided_intake_question_sets": load_required_json_collection(
            EXAMPLES / "guided-intake-question-sets", "guided-intake question sets"
        ),
        "guided_intake_response_sets": load_required_json_collection(
            EXAMPLES / "guided-intake-response-sets", "guided-intake response sets"
        ),
        "guided_intake_profile_projections": load_required_json_collection(
            EXAMPLES / "guided-intake-profile-projections",
            "guided-intake profile projections",
        ),
        "extractions": load_required_json_collection(
            EXAMPLES / "source-extractions", "source extractions"
        ),
        "profile": load_json(
            EXAMPLES / "resume-profiles" / "sample-ai-agent-profile.v1.json"
        ),
        "gap_reports": load_required_json_collection(
            EXAMPLES / "gap-reports", "gap reports"
        ),
        "follow_up_question_sets": load_required_json_collection(
            EXAMPLES / "follow-up-question-sets", "follow-up question sets"
        ),
        "follow_up_response_sets": load_required_json_collection(
            EXAMPLES / "follow-up-response-sets", "follow-up response sets"
        ),
        "follow_up_profile_projections": load_required_json_collection(
            EXAMPLES / "follow-up-profile-projections",
            "follow-up profile projections",
        ),
    }


def validate_schemas(artifacts: dict[str, Any]) -> None:
    catalog_validator = validator_for("template-layer.schema.json", "SharedFieldCatalog")
    manifest_validator = validator_for("template-layer.schema.json", "TemplateManifest")
    registry_validator = validator_for("template-layer.schema.json", "TemplateRegistry")
    document_validator = validator_for("content-layer.schema.json", "SourceDocument")
    session_validator = validator_for("intake-layer.schema.json", "IntakeSession")
    checklist_validator = validator_for(
        "checklist-layer.schema.json", "GuidedIntakeChecklist"
    )
    question_set_validator = validator_for(
        "question-layer.schema.json", "GuidedIntakeQuestionSet"
    )
    response_set_validator = validator_for(
        "response-layer.schema.json", "GuidedIntakeResponseSet"
    )
    projection_validator = validator_for(
        "projection-layer.schema.json", "GuidedIntakeProfileProjection"
    )
    follow_up_question_set_validator = validator_for(
        "follow-up-question-layer.schema.json", "FollowUpQuestionSet"
    )
    follow_up_response_set_validator = validator_for(
        "follow-up-response-layer.schema.json", "FollowUpResponseSet"
    )
    follow_up_projection_validator = validator_for(
        "projection-layer.schema.json", "FollowUpProfileProjection"
    )
    extraction_validator = validator_for("content-layer.schema.json", "SourceExtraction")
    profile_validator = validator_for("content-layer.schema.json", "ResumeProfile")
    gap_validator = validator_for("content-layer.schema.json", "GapReport")

    catalog_validator.validate(artifacts["catalog"])
    print("validated: shared-field-catalog")

    for manifest in artifacts["manifests"]:
        manifest_validator.validate(manifest)
    print(f"validated: {len(artifacts['manifests'])} template manifests")

    registry_validator.validate(artifacts["registry"])
    print("validated: template-registry")

    document_validator.validate(artifacts["source_document"])
    print("validated: source-document")

    for session in artifacts["intake_sessions"]:
        session_validator.validate(session)
    print(f"validated: {len(artifacts['intake_sessions'])} intake sessions")

    for checklist in artifacts["guided_intake_checklists"]:
        checklist_validator.validate(checklist)
    print(
        "validated: "
        f"{len(artifacts['guided_intake_checklists'])} guided-intake checklists"
    )

    for question_set in artifacts["guided_intake_question_sets"]:
        question_set_validator.validate(question_set)
    print(
        "validated: "
        f"{len(artifacts['guided_intake_question_sets'])} guided-intake question sets"
    )

    for response_set in artifacts["guided_intake_response_sets"]:
        response_set_validator.validate(response_set)
    print(
        "validated: "
        f"{len(artifacts['guided_intake_response_sets'])} guided-intake response sets"
    )

    for projection in artifacts["guided_intake_profile_projections"]:
        projection_validator.validate(projection)
    print(
        "validated: "
        f"{len(artifacts['guided_intake_profile_projections'])} guided-intake profile projections"
    )

    for extraction in artifacts["extractions"]:
        extraction_validator.validate(extraction)
    print(f"validated: {len(artifacts['extractions'])} source extractions")

    profile_validator.validate(artifacts["profile"])
    print("validated: resume profile")

    for gap_report in artifacts["gap_reports"]:
        gap_validator.validate(gap_report)
    print(f"validated: {len(artifacts['gap_reports'])} gap reports")

    for question_set in artifacts["follow_up_question_sets"]:
        follow_up_question_set_validator.validate(question_set)
    print(
        "validated: "
        f"{len(artifacts['follow_up_question_sets'])} follow-up question sets"
    )

    for response_set in artifacts["follow_up_response_sets"]:
        follow_up_response_set_validator.validate(response_set)
    print(
        "validated: "
        f"{len(artifacts['follow_up_response_sets'])} follow-up response sets"
    )

    for projection in artifacts["follow_up_profile_projections"]:
        follow_up_projection_validator.validate(projection)
    print(
        "validated: "
        f"{len(artifacts['follow_up_profile_projections'])} follow-up profile projections"
    )


def build_integrity_indexes(artifacts: dict[str, Any]) -> dict[str, Any]:
    manifest_by_key = {}
    manifest_requirements_by_key = {}
    for manifest in artifacts["manifests"]:
        manifest_key = (manifest["templateId"], manifest["version"])
        if manifest_key in manifest_by_key:
            raise ValueError(
                "duplicate template manifest key: "
                f"{manifest['templateId']}@{manifest['version']}"
            )
        manifest_by_key[manifest_key] = manifest
        requirements_by_field = {}
        for requirement in manifest["fieldRequirements"]:
            field_id = requirement["fieldId"]
            if field_id in requirements_by_field:
                raise ValueError(
                    "template manifest contains duplicate fieldRequirements fieldId: "
                    f"{manifest['templateId']}@{manifest['version']}:{field_id}"
                )
            requirements_by_field[field_id] = requirement
        manifest_requirements_by_key[manifest_key] = requirements_by_field

    registry_index = set()
    for entry in artifacts["registry"]["entries"]:
        registry_key = (entry["templateId"], entry["version"])
        if registry_key in registry_index:
            raise ValueError(
                "duplicate template registry key: "
                f"{entry['templateId']}@{entry['version']}"
            )
        registry_index.add(registry_key)

    checklist_index = {}
    for checklist in artifacts["guided_intake_checklists"]:
        checklist_key = (checklist["templateId"], checklist["templateVersion"])
        if checklist_key in checklist_index:
            raise ValueError(
                "duplicate guided-intake checklist key: "
                f"{checklist['templateId']}@{checklist['templateVersion']}"
            )
        checklist_index[checklist_key] = checklist

    question_set_index = {}
    guided_intake_question_set_by_id = {}
    for question_set in artifacts["guided_intake_question_sets"]:
        question_set_key = (question_set["templateId"], question_set["templateVersion"])
        if question_set_key in question_set_index:
            raise ValueError(
                "duplicate guided-intake question set key: "
                f"{question_set['templateId']}@{question_set['templateVersion']}"
            )
        question_set_index[question_set_key] = question_set
        question_set_id = question_set["questionSetId"]
        if question_set_id in guided_intake_question_set_by_id:
            raise ValueError(
                "duplicate guided-intake question set questionSetId: "
                f"{question_set['questionSetId']}"
            )
        guided_intake_question_set_by_id[question_set_id] = question_set

    response_set_by_question_set_id = {}
    response_set_by_id = {}
    for response_set in artifacts["guided_intake_response_sets"]:
        response_set_key = response_set["questionSetId"]
        if response_set_key in response_set_by_question_set_id:
            raise ValueError(
                "duplicate guided-intake response set key: "
                f"{response_set['questionSetId']}"
            )
        response_set_id = response_set["responseSetId"]
        if response_set_id in response_set_by_id:
            raise ValueError(
                "duplicate guided-intake response set responseSetId: "
                f"{response_set['responseSetId']}"
            )
        response_set_by_question_set_id[response_set_key] = response_set
        response_set_by_id[response_set_id] = response_set

    projection_by_response_set_id = {}
    projection_by_template_and_profile_id = {}
    for projection in artifacts["guided_intake_profile_projections"]:
        projection_key = projection["responseSetId"]
        if projection_key in projection_by_response_set_id:
            raise ValueError(
                "duplicate guided-intake profile projection responseSetId: "
                f"{projection['responseSetId']}"
            )
        projection_by_response_set_id[projection_key] = projection
        profile_binding_key = (
            projection["templateId"],
            projection["profile"]["profileId"],
        )
        if profile_binding_key in projection_by_template_and_profile_id:
            raise ValueError(
                "duplicate guided-intake profile projection template/profile binding: "
                f"{projection['templateId']}:{projection['profile']['profileId']}"
            )
        projection_by_template_and_profile_id[profile_binding_key] = projection

    gap_report_by_id = {}
    for gap_report in artifacts["gap_reports"]:
        report_id = gap_report["reportId"]
        if report_id in gap_report_by_id:
            raise ValueError(f"duplicate gap report id: {report_id}")
        gap_report_by_id[report_id] = gap_report

    follow_up_question_set_by_report_id = {}
    follow_up_question_set_by_id = {}
    for question_set in artifacts["follow_up_question_sets"]:
        report_id = question_set["reportId"]
        if report_id in follow_up_question_set_by_report_id:
            raise ValueError(
                "duplicate follow-up question set reportId: "
                f"{question_set['reportId']}"
            )
        follow_up_question_set_by_report_id[report_id] = question_set
        question_set_id = question_set["followUpQuestionSetId"]
        if question_set_id in follow_up_question_set_by_id:
            raise ValueError(
                "duplicate follow-up question set followUpQuestionSetId: "
                f"{question_set['followUpQuestionSetId']}"
            )
        follow_up_question_set_by_id[question_set_id] = question_set

    follow_up_response_set_by_question_set_id = {}
    follow_up_response_set_by_id = {}
    for response_set in artifacts["follow_up_response_sets"]:
        question_set_id = response_set["followUpQuestionSetId"]
        if question_set_id in follow_up_response_set_by_question_set_id:
            raise ValueError(
                "duplicate follow-up response set followUpQuestionSetId: "
                f"{response_set['followUpQuestionSetId']}"
            )
        response_set_id = response_set["followUpResponseSetId"]
        if response_set_id in follow_up_response_set_by_id:
            raise ValueError(
                "duplicate follow-up response set followUpResponseSetId: "
                f"{response_set['followUpResponseSetId']}"
            )
        follow_up_response_set_by_question_set_id[question_set_id] = response_set
        follow_up_response_set_by_id[response_set_id] = response_set

    follow_up_projection_by_response_set_id = {}
    follow_up_projection_by_template_and_profile_id = {}
    for projection in artifacts["follow_up_profile_projections"]:
        response_set_id = projection["followUpResponseSetId"]
        if response_set_id in follow_up_projection_by_response_set_id:
            raise ValueError(
                "duplicate follow-up profile projection followUpResponseSetId: "
                f"{projection['followUpResponseSetId']}"
            )
        follow_up_projection_by_response_set_id[response_set_id] = projection
        profile_binding_key = (
            projection["templateId"],
            projection["profile"]["profileId"],
        )
        if profile_binding_key in follow_up_projection_by_template_and_profile_id:
            raise ValueError(
                "duplicate follow-up profile projection template/profile binding: "
                f"{projection['templateId']}:{projection['profile']['profileId']}"
            )
        follow_up_projection_by_template_and_profile_id[profile_binding_key] = projection

    ambiguous_gap_report_source_bindings = sorted(
        set(projection_by_template_and_profile_id.keys())
        & set(follow_up_projection_by_template_and_profile_id.keys())
    )
    if ambiguous_gap_report_source_bindings:
        template_id, profile_id = ambiguous_gap_report_source_bindings[0]
        raise ValueError(
            "ambiguous gap report profile binding across guided-intake and follow-up projections: "
            f"{template_id}:{profile_id}"
        )

    return {
        "manifest_by_key": manifest_by_key,
        "manifest_requirements_by_key": manifest_requirements_by_key,
        "manifest_index": set(manifest_by_key.keys()),
        "registry_index": registry_index,
        "checklist_index": checklist_index,
        "question_set_index": question_set_index,
        "guided_intake_question_set_by_id": guided_intake_question_set_by_id,
        "response_set_by_question_set_id": response_set_by_question_set_id,
        "response_set_by_id": response_set_by_id,
        "projection_by_response_set_id": projection_by_response_set_id,
        "projection_by_template_and_profile_id": projection_by_template_and_profile_id,
        "gap_report_by_id": gap_report_by_id,
        "follow_up_question_set_by_report_id": follow_up_question_set_by_report_id,
        "follow_up_question_set_by_id": follow_up_question_set_by_id,
        "follow_up_response_set_by_question_set_id": follow_up_response_set_by_question_set_id,
        "follow_up_response_set_by_id": follow_up_response_set_by_id,
        "follow_up_projection_by_response_set_id": follow_up_projection_by_response_set_id,
        "follow_up_projection_by_template_and_profile_id": follow_up_projection_by_template_and_profile_id,
    }


def validate_template_artifact_integrity(
    artifacts: dict[str, Any],
    indexes: dict[str, Any],
    catalog_fields: set[str],
    document_ids: set[str],
) -> None:
    manifest_index = indexes["manifest_index"]
    registry_index = indexes["registry_index"]
    checklist_index = indexes["checklist_index"]
    manifest_requirements_by_key = indexes["manifest_requirements_by_key"]
    guided_intake_question_set_by_id = indexes["guided_intake_question_set_by_id"]

    if manifest_index != registry_index:
        raise ValueError("template registry entries do not match manifest ids and versions")

    for manifest in artifacts["manifests"]:
        for requirement in manifest["fieldRequirements"]:
            field_id = requirement["fieldId"]
            if field_id not in catalog_fields:
                raise ValueError(f"unknown template field: {field_id}")

    for session in artifacts["intake_sessions"]:
        session_key = (session["templateId"], session["templateVersion"])
        if session_key not in registry_index:
            raise ValueError(
                "unknown intake session template reference: "
                f"{session['templateId']}@{session['templateVersion']}"
            )
        for document_id in session["documentIds"]:
            if document_id not in document_ids:
                raise ValueError(f"unknown intake session document id: {document_id}")

    for checklist in artifacts["guided_intake_checklists"]:
        checklist_key = (checklist["templateId"], checklist["templateVersion"])
        if checklist_key not in manifest_index:
            raise ValueError(
                "unknown guided-intake checklist template reference: "
                f"{checklist['templateId']}@{checklist['templateVersion']}"
            )
        declared_fields = set(checklist["requiredFields"]) | set(checklist["optionalFields"])
        repeatable_fields = set(checklist["repeatableFields"])
        if set(checklist["requiredFields"]) & set(checklist["optionalFields"]):
            raise ValueError(
                "guided-intake checklist required and optional fields overlap: "
                f"{checklist['checklistId']}"
            )
        if not repeatable_fields.issubset(declared_fields):
            raise ValueError(
                "guided-intake checklist repeatable fields must be declared: "
                f"{checklist['checklistId']}"
            )
        for field_id in declared_fields | repeatable_fields:
            if field_id not in catalog_fields:
                raise ValueError(f"unknown guided-intake checklist field: {field_id}")

    for question_set in artifacts["guided_intake_question_sets"]:
        question_set_key = (question_set["templateId"], question_set["templateVersion"])
        if question_set_key not in manifest_index:
            raise ValueError(
                "unknown guided-intake question set template reference: "
                f"{question_set['templateId']}@{question_set['templateVersion']}"
            )
        if question_set_key not in checklist_index:
            raise ValueError(
                "missing guided-intake checklist for question set: "
                f"{question_set['questionSetId']}"
            )

        checklist = checklist_index[question_set_key]
        requirements_by_field = manifest_requirements_by_key[question_set_key]
        expected_field_ids = checklist["requiredFields"] + checklist["optionalFields"]
        actual_field_ids = [item["fieldId"] for item in question_set["questions"]]
        if actual_field_ids != expected_field_ids:
            raise ValueError(
                "guided-intake question set fields do not match checklist order: "
                f"{question_set['questionSetId']}"
            )
        if len(actual_field_ids) != len(set(actual_field_ids)):
            raise ValueError(
                "guided-intake question set contains duplicate fields: "
                f"{question_set['questionSetId']}"
            )

        for item in question_set["questions"]:
            field_id = item["fieldId"]
            requirement = requirements_by_field.get(field_id)
            if requirement is None:
                raise ValueError(f"unknown guided-intake question set field: {field_id}")
            prompt_hint = requirement.get("promptHint", "")
            if not isinstance(prompt_hint, str) or not prompt_hint.strip():
                raise ValueError(
                    "guided-intake question set field is missing promptHint: "
                    f"{question_set['questionSetId']}:{field_id}"
                )
            expected_question = f"Please provide {prompt_hint}."
            if item["question"] != expected_question:
                raise ValueError(
                    "guided-intake question text does not match template promptHint: "
                    f"{question_set['questionSetId']}:{field_id}"
                )

    for response_set in artifacts["guided_intake_response_sets"]:
        question_set = guided_intake_question_set_by_id.get(response_set["questionSetId"])
        if question_set is None:
            raise ValueError(
                "unknown guided-intake response set questionSetId: "
                f"{response_set['questionSetId']}"
            )
        if response_set["templateId"] != question_set["templateId"]:
            raise ValueError(
                "guided-intake response set templateId does not match question set: "
                f"{response_set['responseSetId']}"
            )
        if response_set["templateVersion"] != question_set["templateVersion"]:
            raise ValueError(
                "guided-intake response set templateVersion does not match question set: "
                f"{response_set['responseSetId']}"
            )

        allowed_field_ids = {item["fieldId"] for item in question_set["questions"]}
        for field_id in response_set["responses"].keys():
            if field_id not in allowed_field_ids:
                raise ValueError(
                    "guided-intake response set contains unknown response field: "
                    f"{response_set['responseSetId']}:{field_id}"
                )


def validate_projection_and_profile_integrity(
    artifacts: dict[str, Any],
    indexes: dict[str, Any],
    catalog_fields: set[str],
    extraction_ids: set[str],
) -> None:
    manifest_index = indexes["manifest_index"]
    response_set_by_id = indexes["response_set_by_id"]

    for projection in artifacts["guided_intake_profile_projections"]:
        response_set = response_set_by_id.get(projection["responseSetId"])
        if response_set is None:
            raise ValueError(
                "unknown guided-intake profile projection responseSetId: "
                f"{projection['responseSetId']}"
            )
        if projection["questionSetId"] != response_set["questionSetId"]:
            raise ValueError(
                "guided-intake profile projection questionSetId does not match response set: "
                f"{projection['projectionId']}"
            )
        if projection["templateId"] != response_set["templateId"]:
            raise ValueError(
                "guided-intake profile projection templateId does not match response set: "
                f"{projection['projectionId']}"
            )
        if projection["templateVersion"] != response_set["templateVersion"]:
            raise ValueError(
                "guided-intake profile projection templateVersion does not match response set: "
                f"{projection['projectionId']}"
            )
        projection_key = (projection["templateId"], projection["templateVersion"])
        if projection_key not in manifest_index:
            raise ValueError(
                "unknown guided-intake profile projection template reference: "
                f"{projection['projectionId']}"
            )
        if projection["profile"]["fieldValues"] != response_set["responses"]:
            raise ValueError(
                "guided-intake profile projection fieldValues must match response set responses: "
                f"{projection['projectionId']}"
            )
        if projection["profile"]["profileId"] != f"profile-from-{projection['responseSetId']}":
            raise ValueError(
                "guided-intake profile projection profileId must derive from responseSetId: "
                f"{projection['projectionId']}"
            )
        if projection["profile"]["profileStatus"] != "partial":
            raise ValueError(
                "guided-intake profile projection must set profileStatus to partial: "
                f"{projection['projectionId']}"
            )
        if projection["profile"]["updatedAt"] != response_set["updatedAt"]:
            raise ValueError(
                "guided-intake profile projection updatedAt must match response set: "
                f"{projection['projectionId']}"
            )
        if set(projection["profile"]["provenance"].keys()) != set(
            projection["profile"]["fieldValues"].keys()
        ):
            raise ValueError(
                "guided-intake profile projection provenance keys must match fieldValues: "
                f"{projection['projectionId']}"
            )
        for field_id, provenance_ids in projection["profile"]["provenance"].items():
            if provenance_ids != [projection["responseSetId"]]:
                raise ValueError(
                    "guided-intake profile projection provenance must equal responseSetId: "
                    f"{projection['projectionId']}:{field_id}"
                )
            if field_id not in catalog_fields:
                raise ValueError(f"unknown guided-intake profile projection field: {field_id}")

    for extraction in artifacts["extractions"]:
        for field_id in extraction["candidateFieldIds"]:
            if field_id not in catalog_fields:
                raise ValueError(f"unknown extraction candidate field: {field_id}")

    for field_id in artifacts["profile"]["fieldValues"].keys():
        if field_id not in catalog_fields:
            raise ValueError(f"unknown profile field: {field_id}")

    for field_id, referenced_ids in artifacts["profile"]["provenance"].items():
        if field_id not in catalog_fields:
            raise ValueError(f"unknown provenance field: {field_id}")
        for extraction_id in referenced_ids:
            if extraction_id not in extraction_ids:
                raise ValueError(f"unknown provenance extraction id: {extraction_id}")


def validate_gap_report_integrity(
    artifacts: dict[str, Any],
    indexes: dict[str, Any],
    catalog_fields: set[str],
) -> None:
    manifest_by_key = indexes["manifest_by_key"]
    guided_projection_by_template_and_profile_id = indexes[
        "projection_by_template_and_profile_id"
    ]
    follow_up_projection_by_template_and_profile_id = indexes[
        "follow_up_projection_by_template_and_profile_id"
    ]

    for gap_report in artifacts["gap_reports"]:
        gap_fields = []
        gap_fields.extend(gap_report["missingRequired"])
        gap_fields.extend(gap_report["missingRecommended"])
        gap_fields.extend(item["fieldId"] for item in gap_report["questions"])
        for field_id in gap_fields:
            if field_id not in catalog_fields:
                raise ValueError(f"unknown gap report field: {field_id}")

        projection = guided_projection_by_template_and_profile_id.get(
            (gap_report["templateId"], gap_report["profileId"])
        )
        if projection is None:
            projection = follow_up_projection_by_template_and_profile_id.get(
                (gap_report["templateId"], gap_report["profileId"])
            )
        if projection is None:
            raise ValueError(
                "unknown gap report profile binding: "
                f"{gap_report['templateId']}:{gap_report['profileId']}"
            )

        manifest_key = (projection["templateId"], projection["templateVersion"])
        manifest = manifest_by_key.get(manifest_key)
        if manifest is None:
            raise ValueError(
                "unknown gap report template binding: "
                f"{gap_report['templateId']}"
            )

        expected_report_id = f"gap-for-{gap_report['profileId']}-{gap_report['templateId']}"
        if gap_report["reportId"] != expected_report_id:
            raise ValueError(
                "gap report reportId must derive from profileId and templateId: "
                f"{gap_report['reportId']}"
            )

        if gap_report["conflicts"] != []:
            raise ValueError(
                "gap report conflicts must be empty: "
                f"{gap_report['reportId']}"
            )

        missing_required = set(gap_report["missingRequired"])
        missing_recommended = set(gap_report["missingRecommended"])
        if missing_required & missing_recommended:
            raise ValueError(
                "gap report missingRequired and missingRecommended must not overlap: "
                f"{gap_report['reportId']}"
            )

        profile_field_values = projection["profile"]["fieldValues"]
        expected_missing_required = []
        expected_missing_recommended = []
        for requirement in manifest["fieldRequirements"]:
            field_id = requirement["fieldId"]
            if field_id in profile_field_values:
                continue
            if requirement["required"]:
                expected_missing_required.append(field_id)
            else:
                expected_missing_recommended.append(field_id)

        if gap_report["missingRequired"] != expected_missing_required:
            raise ValueError(
                "gap report missingRequired must equal absent required manifest fields: "
                f"{gap_report['reportId']}"
            )
        if gap_report["missingRecommended"] != expected_missing_recommended:
            raise ValueError(
                "gap report missingRecommended must equal absent optional manifest fields: "
                f"{gap_report['reportId']}"
            )

        missing_field_ids = set(
            gap_report["missingRequired"] + gap_report["missingRecommended"]
        )
        expected_questions = [
            {
                "fieldId": requirement["fieldId"],
                "question": f"Please provide {requirement['promptHint']}.",
            }
            for requirement in manifest["fieldRequirements"]
            if requirement["fieldId"] in missing_field_ids
        ]
        if len(gap_report["questions"]) != len(expected_questions):
            raise ValueError(
                "gap report questions must cover all and only missing fields in manifest order: "
                f"{gap_report['reportId']}"
            )
        for actual_question, expected_question in zip(
            gap_report["questions"], expected_questions
        ):
            if actual_question["fieldId"] != expected_question["fieldId"]:
                raise ValueError(
                    "gap report questions must follow manifest order for missing fields: "
                    f"{gap_report['reportId']}"
                )
            if actual_question["question"] != expected_question["question"]:
                raise ValueError(
                    "gap report question text does not match template promptHint: "
                    f"{gap_report['reportId']}:{actual_question['fieldId']}"
                )


def validate_follow_up_artifact_integrity(
    artifacts: dict[str, Any],
    indexes: dict[str, Any],
    catalog_fields: set[str],
) -> None:
    gap_report_by_id = indexes["gap_report_by_id"]
    follow_up_question_set_by_id = indexes["follow_up_question_set_by_id"]
    follow_up_response_set_by_id = indexes["follow_up_response_set_by_id"]
    guided_projection_by_template_and_profile_id = indexes[
        "projection_by_template_and_profile_id"
    ]
    follow_up_projection_by_template_and_profile_id = indexes[
        "follow_up_projection_by_template_and_profile_id"
    ]

    for question_set in artifacts["follow_up_question_sets"]:
        for item in question_set["questions"]:
            if item["fieldId"] not in catalog_fields:
                raise ValueError(f"unknown follow-up question set field: {item['fieldId']}")

        gap_report = gap_report_by_id.get(question_set["reportId"])
        if gap_report is None:
            raise ValueError(
                "unknown follow-up question set reportId: "
                f"{question_set['reportId']}"
            )
        if question_set["templateId"] != gap_report["templateId"]:
            raise ValueError(
                "follow-up question set templateId does not match gap report: "
                f"{question_set['followUpQuestionSetId']}"
            )
        if question_set["profileId"] != gap_report["profileId"]:
            raise ValueError(
                "follow-up question set profileId does not match gap report: "
                f"{question_set['followUpQuestionSetId']}"
            )
        expected_question_set_id = f"follow-up-for-{question_set['reportId']}"
        if question_set["followUpQuestionSetId"] != expected_question_set_id:
            raise ValueError(
                "follow-up question set id must derive from reportId: "
                f"{question_set['followUpQuestionSetId']}"
            )
        if question_set["questions"] != gap_report["questions"]:
            raise ValueError(
                "follow-up question set questions must exactly match gap report questions: "
                f"{question_set['followUpQuestionSetId']}"
            )

    for response_set in artifacts["follow_up_response_sets"]:
        follow_up_question_set = follow_up_question_set_by_id.get(
            response_set["followUpQuestionSetId"]
        )
        if follow_up_question_set is None:
            raise ValueError(
                "unknown follow-up response set followUpQuestionSetId: "
                f"{response_set['followUpQuestionSetId']}"
            )
        if response_set["reportId"] != follow_up_question_set["reportId"]:
            raise ValueError(
                "follow-up response set reportId does not match follow-up question set: "
                f"{response_set['followUpResponseSetId']}"
            )
        if response_set["templateId"] != follow_up_question_set["templateId"]:
            raise ValueError(
                "follow-up response set templateId does not match follow-up question set: "
                f"{response_set['followUpResponseSetId']}"
            )
        if response_set["profileId"] != follow_up_question_set["profileId"]:
            raise ValueError(
                "follow-up response set profileId does not match follow-up question set: "
                f"{response_set['followUpResponseSetId']}"
            )
        expected_response_set_id = (
            f"follow-up-response-for-{response_set['followUpQuestionSetId']}"
        )
        if response_set["followUpResponseSetId"] != expected_response_set_id:
            raise ValueError(
                "follow-up response set id must derive from followUpQuestionSetId: "
                f"{response_set['followUpResponseSetId']}"
            )

        allowed_field_ids = {
            item["fieldId"] for item in follow_up_question_set["questions"]
        }
        for field_id in response_set["responses"].keys():
            if field_id not in allowed_field_ids:
                raise ValueError(
                    "follow-up response set contains unknown response field: "
                    f"{response_set['followUpResponseSetId']}:{field_id}"
                )

    for projection in artifacts["follow_up_profile_projections"]:
        response_set = follow_up_response_set_by_id.get(projection["followUpResponseSetId"])
        if response_set is None:
            raise ValueError(
                "unknown follow-up profile projection followUpResponseSetId: "
                f"{projection['followUpResponseSetId']}"
            )
        if projection["followUpQuestionSetId"] != response_set["followUpQuestionSetId"]:
            raise ValueError(
                "follow-up profile projection followUpQuestionSetId does not match response set: "
                f"{projection['projectionId']}"
            )
        if projection["reportId"] != response_set["reportId"]:
            raise ValueError(
                "follow-up profile projection reportId does not match response set: "
                f"{projection['projectionId']}"
            )
        if projection["templateId"] != response_set["templateId"]:
            raise ValueError(
                "follow-up profile projection templateId does not match response set: "
                f"{projection['projectionId']}"
            )

        expected_projection_id = (
            f"follow-up-profile-projection-for-{projection['followUpResponseSetId']}"
        )
        if projection["projectionId"] != expected_projection_id:
            raise ValueError(
                "follow-up profile projection projectionId must derive from followUpResponseSetId: "
                f"{projection['projectionId']}"
            )
        expected_profile_id = f"profile-from-{projection['followUpResponseSetId']}"
        if projection["profile"]["profileId"] != expected_profile_id:
            raise ValueError(
                "follow-up profile projection profileId must derive from followUpResponseSetId: "
                f"{projection['projectionId']}"
            )
        if projection["profile"]["updatedAt"] != response_set["updatedAt"]:
            raise ValueError(
                "follow-up profile projection updatedAt must match response set: "
                f"{projection['projectionId']}"
            )

        base_projection = guided_projection_by_template_and_profile_id.get(
            (projection["templateId"], projection["baseProfileId"])
        )
        if base_projection is None:
            base_projection = follow_up_projection_by_template_and_profile_id.get(
                (projection["templateId"], projection["baseProfileId"])
            )
        if base_projection is None:
            raise ValueError(
                "unknown follow-up profile projection baseProfileId: "
                f"{projection['baseProfileId']}"
            )
        if projection["baseProfileId"] != response_set["profileId"]:
            raise ValueError(
                "follow-up profile projection baseProfileId does not match response set profileId: "
                f"{projection['projectionId']}"
            )
        if projection["templateVersion"] != base_projection["templateVersion"]:
            raise ValueError(
                "follow-up profile projection templateVersion does not match base profile projection: "
                f"{projection['projectionId']}"
            )
        if response_set["templateId"] != base_projection["templateId"]:
            raise ValueError(
                "follow-up profile projection templateId does not match base profile projection: "
                f"{projection['projectionId']}"
            )

        expected_field_values = {
            **base_projection["profile"]["fieldValues"],
            **response_set["responses"],
        }
        if projection["profile"]["fieldValues"] != expected_field_values:
            raise ValueError(
                "follow-up profile projection fieldValues must equal cumulative base fieldValues merged with response set responses: "
                f"{projection['projectionId']}"
            )

        expected_provenance = dict(base_projection["profile"]["provenance"])
        expected_provenance.update(
            {
                field_id: [projection["followUpResponseSetId"]]
                for field_id in response_set["responses"].keys()
            }
        )
        if projection["profile"]["provenance"] != expected_provenance:
            raise ValueError(
                "follow-up profile projection provenance must equal cumulative base provenance with follow-up response set ids for answered fields: "
                f"{projection['projectionId']}"
            )
        for field_id in projection["profile"]["fieldValues"].keys():
            if field_id not in catalog_fields:
                raise ValueError(f"unknown follow-up profile projection field: {field_id}")


def validate_integrity(artifacts: dict[str, Any]) -> None:
    catalog_fields = {item["fieldId"] for item in artifacts["catalog"]["fields"]}
    document_ids = {artifacts["source_document"]["documentId"]}
    extraction_ids = {item["extractionId"] for item in artifacts["extractions"]}
    indexes = build_integrity_indexes(artifacts)
    validate_template_artifact_integrity(
        artifacts, indexes, catalog_fields, document_ids
    )
    validate_projection_and_profile_integrity(
        artifacts, indexes, catalog_fields, extraction_ids
    )
    validate_follow_up_artifact_integrity(artifacts, indexes, catalog_fields)
    validate_gap_report_integrity(artifacts, indexes, catalog_fields)


def main() -> int:
    artifacts = load_example_artifacts()
    validate_schemas(artifacts)
    validate_integrity(artifacts)
    print("resume-core validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
