import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, RefResolver
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_SCHEMA_PATH = ROOT / "schema" / "projection-layer.schema.json"
CONTENT_SCHEMA_PATH = ROOT / "schema" / "content-layer.schema.json"
EXAMPLES = ROOT / "examples"
FOLLOW_UP_QUESTION_SETS_DIR = EXAMPLES / "follow-up-question-sets"
FOLLOW_UP_RESPONSE_SETS_DIR = EXAMPLES / "follow-up-response-sets"
GUIDED_INTAKE_PROJECTIONS_DIR = EXAMPLES / "guided-intake-profile-projections"
FOLLOW_UP_PROJECTIONS_DIR = EXAMPLES / "follow-up-profile-projections"


REQUIRED_EXAMPLE_FILES = {
    "markdown-basic.partial.v1.json",
    "typora-classic.partial.v1.json",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(schema_path: Path, def_name: str, resolver: RefResolver | None = None):
    schema = load_json(schema_path)
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{def_name}",
        },
        format_checker=FormatChecker(),
        resolver=resolver,
    )


class ResumeCoreFollowUpProfileProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content_schema = load_json(CONTENT_SCHEMA_PATH)
        cls.projection_schema = load_json(PROJECTION_SCHEMA_PATH)
        cls.projection_resolver = RefResolver.from_schema(
            cls.projection_schema,
            store={
                cls.content_schema["$id"]: cls.content_schema,
                CONTENT_SCHEMA_PATH.as_uri(): cls.content_schema,
                cls.projection_schema["$id"]: cls.projection_schema,
                PROJECTION_SCHEMA_PATH.as_uri(): cls.projection_schema,
            },
        )
        cls.follow_up_question_sets = {
            question_set["followUpQuestionSetId"]: question_set
            for question_set in (
                load_json(path)
                for path in sorted(FOLLOW_UP_QUESTION_SETS_DIR.glob("*.json"))
            )
        }
        cls.follow_up_response_sets = {
            response_set["followUpResponseSetId"]: response_set
            for response_set in (
                load_json(path)
                for path in sorted(FOLLOW_UP_RESPONSE_SETS_DIR.glob("*.json"))
            )
        }
        cls.guided_intake_projections = {
            (projection["templateId"], projection["profile"]["profileId"]): projection
            for projection in (
                load_json(path)
                for path in sorted(GUIDED_INTAKE_PROJECTIONS_DIR.glob("*.json"))
            )
        }
        cls.follow_up_projection_paths = sorted(FOLLOW_UP_PROJECTIONS_DIR.glob("*.json"))
        cls.follow_up_projections = [
            load_json(path) for path in cls.follow_up_projection_paths
        ]
        cls.follow_up_projections_by_template_and_profile_id = {
            (projection["templateId"], projection["profile"]["profileId"]): projection
            for projection in cls.follow_up_projections
        }
        cls.projected_profiles_by_template_and_profile_id = {
            **cls.guided_intake_projections,
            **cls.follow_up_projections_by_template_and_profile_id,
        }
        cls.follow_up_projection_validator = validator_for(
            PROJECTION_SCHEMA_PATH,
            "FollowUpProfileProjection",
            resolver=cls.projection_resolver,
        )
        cls.profile_validator = validator_for(CONTENT_SCHEMA_PATH, "ResumeProfile")

    def test_follow_up_profile_projection_examples_are_present(self):
        actual_example_files = {path.name for path in self.follow_up_projection_paths}
        self.assertTrue(
            REQUIRED_EXAMPLE_FILES.issubset(actual_example_files),
            "Missing required follow-up projection fixtures: "
            f"{sorted(REQUIRED_EXAMPLE_FILES - actual_example_files)}",
        )

    def test_follow_up_profile_projection_examples_are_valid(self):
        for projection in self.follow_up_projections:
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.follow_up_projection_validator.validate(projection)

    def test_projected_profiles_are_valid_resume_profiles(self):
        for projection in self.follow_up_projections:
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.profile_validator.validate(projection["profile"])

    def test_projection_references_known_follow_up_response_set(self):
        for projection in self.follow_up_projections:
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.assertIn(
                    projection["followUpResponseSetId"],
                    self.follow_up_response_sets,
                )

    def test_projection_references_known_follow_up_question_set(self):
        for projection in self.follow_up_projections:
            with self.subTest(
                followUpQuestionSetId=projection["followUpQuestionSetId"]
            ):
                self.assertIn(
                    projection["followUpQuestionSetId"],
                    self.follow_up_question_sets,
                )

    def test_projection_references_known_base_profile(self):
        for projection in self.follow_up_projections:
            with self.subTest(baseProfileId=projection["baseProfileId"]):
                self.assertIn(
                    (projection["templateId"], projection["baseProfileId"]),
                    self.projected_profiles_by_template_and_profile_id,
                )

    def test_projection_inherits_follow_up_and_base_projection_binding(self):
        for projection in self.follow_up_projections:
            response_set = self.follow_up_response_sets[projection["followUpResponseSetId"]]
            base_projection = self.projected_profiles_by_template_and_profile_id[
                (projection["templateId"], projection["baseProfileId"])
            ]
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.assertEqual(
                    projection["followUpQuestionSetId"],
                    response_set["followUpQuestionSetId"],
                )
                self.assertEqual(projection["reportId"], response_set["reportId"])
                self.assertEqual(projection["templateId"], response_set["templateId"])
                self.assertEqual(projection["baseProfileId"], response_set["profileId"])
                self.assertEqual(
                    projection["templateVersion"],
                    base_projection["templateVersion"],
                )
                self.assertEqual(
                    projection["templateId"],
                    base_projection["templateId"],
                )

    def test_projection_field_values_are_cumulative_merge(self):
        for projection in self.follow_up_projections:
            response_set = self.follow_up_response_sets[projection["followUpResponseSetId"]]
            base_projection = self.projected_profiles_by_template_and_profile_id[
                (projection["templateId"], projection["baseProfileId"])
            ]
            expected_field_values = {
                **base_projection["profile"]["fieldValues"],
                **response_set["responses"],
            }
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.assertEqual(
                    projection["profile"]["fieldValues"], expected_field_values
                )

    def test_projection_provenance_is_cumulative_merge(self):
        for projection in self.follow_up_projections:
            response_set = self.follow_up_response_sets[projection["followUpResponseSetId"]]
            base_projection = self.projected_profiles_by_template_and_profile_id[
                (projection["templateId"], projection["baseProfileId"])
            ]
            expected_provenance = dict(base_projection["profile"]["provenance"])
            expected_provenance.update(
                {
                    field_id: [projection["followUpResponseSetId"]]
                    for field_id in response_set["responses"].keys()
                }
            )
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.assertEqual(projection["profile"]["provenance"], expected_provenance)

    def test_projection_profile_metadata_is_deterministic(self):
        for projection in self.follow_up_projections:
            response_set = self.follow_up_response_sets[projection["followUpResponseSetId"]]
            expected_profile_id = (
                "profile-from-" + projection["followUpResponseSetId"]
            )
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.assertEqual(projection["profile"]["profileId"], expected_profile_id)
                self.assertEqual(projection["profile"]["profileStatus"], "partial")
                self.assertEqual(
                    projection["profile"]["updatedAt"], response_set["updatedAt"]
                )

    def test_projection_id_is_deterministic(self):
        for projection in self.follow_up_projections:
            expected_projection_id = (
                "follow-up-profile-projection-for-"
                + projection["followUpResponseSetId"]
            )
            with self.subTest(
                followUpResponseSetId=projection["followUpResponseSetId"]
            ):
                self.assertEqual(projection["projectionId"], expected_projection_id)

    def test_projection_rejects_non_partial_profile_status(self):
        invalid_projection = load_json(
            FOLLOW_UP_PROJECTIONS_DIR / "markdown-basic.partial.v1.json"
        )
        invalid_projection["profile"]["profileStatus"] = "ready"

        with self.assertRaises(ValidationError):
            self.follow_up_projection_validator.validate(invalid_projection)
