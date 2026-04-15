import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_SCHEMA_PATH = ROOT / "schema" / "projection-layer.schema.json"
CONTENT_SCHEMA_PATH = ROOT / "schema" / "content-layer.schema.json"
EXAMPLES = ROOT / "examples"
TEMPLATES_DIR = EXAMPLES / "templates"
QUESTION_SETS_DIR = EXAMPLES / "guided-intake-question-sets"
RESPONSE_SETS_DIR = EXAMPLES / "guided-intake-response-sets"
PROJECTIONS_DIR = EXAMPLES / "guided-intake-profile-projections"


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


class ResumeCoreGuidedIntakeProfileProjectionTests(unittest.TestCase):
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
        cls.manifests = {
            (manifest["templateId"], manifest["version"]): manifest
            for manifest in (
                load_json(path) for path in sorted(TEMPLATES_DIR.glob("*.json"))
            )
        }
        cls.question_sets = {
            question_set["questionSetId"]: question_set
            for question_set in (
                load_json(path) for path in sorted(QUESTION_SETS_DIR.glob("*.json"))
            )
        }
        cls.response_sets = {
            response_set["responseSetId"]: response_set
            for response_set in (
                load_json(path) for path in sorted(RESPONSE_SETS_DIR.glob("*.json"))
            )
        }
        cls.projections = [
            load_json(path) for path in sorted(PROJECTIONS_DIR.glob("*.json"))
        ]
        cls.projection_validator = validator_for(
            PROJECTION_SCHEMA_PATH,
            "GuidedIntakeProfileProjection",
            resolver=cls.projection_resolver,
        )
        cls.profile_validator = validator_for(CONTENT_SCHEMA_PATH, "ResumeProfile")

    def test_projection_examples_are_valid(self):
        for projection in self.projections:
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.projection_validator.validate(projection)

    def test_projected_profiles_are_valid_resume_profiles(self):
        for projection in self.projections:
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.profile_validator.validate(projection["profile"])

    def test_projection_rejects_non_partial_profile_status(self):
        invalid_projection = load_json(
            PROJECTIONS_DIR / "markdown-basic.partial.v1.json"
        )
        invalid_projection["profile"]["profileStatus"] = "ready"

        with self.assertRaisesRegex(Exception, "partial"):
            self.projection_validator.validate(invalid_projection)

    def test_projection_references_known_response_sets(self):
        for projection in self.projections:
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertIn(projection["responseSetId"], self.response_sets)

    def test_projection_template_binding_matches_response_set(self):
        for projection in self.projections:
            response_set = self.response_sets[projection["responseSetId"]]
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertEqual(projection["templateId"], response_set["templateId"])
                self.assertEqual(
                    projection["templateVersion"],
                    response_set["templateVersion"],
                )
                self.assertEqual(
                    projection["questionSetId"],
                    response_set["questionSetId"],
                )

    def test_projection_template_binding_references_known_manifest(self):
        for projection in self.projections:
            projection_key = (
                projection["templateId"],
                projection["templateVersion"],
            )
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertIn(projection_key, self.manifests)

    def test_projected_field_values_match_response_set_answers(self):
        for projection in self.projections:
            response_set = self.response_sets[projection["responseSetId"]]
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertEqual(
                    projection["profile"]["fieldValues"],
                    response_set["responses"],
                )

    def test_projected_provenance_uses_response_set_id(self):
        for projection in self.projections:
            expected_provenance = {
                field_id: [projection["responseSetId"]]
                for field_id in projection["profile"]["fieldValues"].keys()
            }
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertEqual(projection["profile"]["provenance"], expected_provenance)

    def test_projected_profile_metadata_is_deterministic(self):
        for projection in self.projections:
            response_set = self.response_sets[projection["responseSetId"]]
            expected_profile_id = f"profile-from-{projection['responseSetId']}"
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertEqual(projection["profile"]["profileId"], expected_profile_id)
                self.assertEqual(projection["profile"]["profileStatus"], "partial")
                self.assertEqual(
                    projection["profile"]["updatedAt"],
                    response_set["updatedAt"],
                )

    def test_projected_fields_remain_within_question_set(self):
        for projection in self.projections:
            question_set = self.question_sets[projection["questionSetId"]]
            allowed_field_ids = {
                item["fieldId"] for item in question_set["questions"]
            }
            projected_field_ids = set(projection["profile"]["fieldValues"].keys())
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertTrue(projected_field_ids.issubset(allowed_field_ids))

    def test_examples_show_partial_profiles(self):
        for projection in self.projections:
            question_set = self.question_sets[projection["questionSetId"]]
            answered_fields = len(projection["profile"]["fieldValues"])
            total_question_fields = len(question_set["questions"])
            with self.subTest(responseSetId=projection["responseSetId"]):
                self.assertLess(answered_fields, total_question_fields)
