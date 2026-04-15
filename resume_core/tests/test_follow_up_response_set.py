import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "follow-up-response-layer.schema.json"
EXAMPLES = ROOT / "examples"
FOLLOW_UP_QUESTION_SETS_DIR = EXAMPLES / "follow-up-question-sets"
FOLLOW_UP_RESPONSE_SETS_DIR = EXAMPLES / "follow-up-response-sets"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(def_name: str):
    schema = load_json(SCHEMA_PATH)
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{def_name}",
        },
        format_checker=FormatChecker(),
    )


class ResumeCoreFollowUpResponseSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(SCHEMA_PATH)
        cls.follow_up_question_sets = {
            question_set["followUpQuestionSetId"]: question_set
            for question_set in (
                load_json(path)
                for path in sorted(FOLLOW_UP_QUESTION_SETS_DIR.glob("*.json"))
            )
        }
        cls.follow_up_response_sets = [
            load_json(path)
            for path in sorted(FOLLOW_UP_RESPONSE_SETS_DIR.glob("*.json"))
        ]
        cls.follow_up_response_set_validator = validator_for("FollowUpResponseSet")

    def test_follow_up_response_set_examples_are_present(self):
        self.assertGreater(
            len(self.follow_up_response_sets),
            0,
            "Expected at least one follow-up response-set example.",
        )

    def test_follow_up_response_set_examples_are_valid(self):
        for response_set in self.follow_up_response_sets:
            with self.subTest(
                followUpResponseSetId=response_set["followUpResponseSetId"]
            ):
                self.follow_up_response_set_validator.validate(response_set)

    def test_follow_up_response_set_references_known_follow_up_question_set(self):
        for response_set in self.follow_up_response_sets:
            with self.subTest(
                followUpResponseSetId=response_set["followUpResponseSetId"]
            ):
                self.assertIn(
                    response_set["followUpQuestionSetId"],
                    self.follow_up_question_sets,
                )

    def test_follow_up_response_set_inherits_question_set_binding(self):
        for response_set in self.follow_up_response_sets:
            question_set = self.follow_up_question_sets[
                response_set["followUpQuestionSetId"]
            ]
            with self.subTest(
                followUpResponseSetId=response_set["followUpResponseSetId"]
            ):
                self.assertEqual(response_set["reportId"], question_set["reportId"])
                self.assertEqual(response_set["templateId"], question_set["templateId"])
                self.assertEqual(response_set["profileId"], question_set["profileId"])

    def test_response_keys_belong_to_referenced_follow_up_question_set(self):
        for response_set in self.follow_up_response_sets:
            question_set = self.follow_up_question_sets[
                response_set["followUpQuestionSetId"]
            ]
            allowed_field_ids = {
                item["fieldId"] for item in question_set["questions"]
            }
            response_field_ids = set(response_set["responses"].keys())
            with self.subTest(
                followUpResponseSetId=response_set["followUpResponseSetId"]
            ):
                self.assertTrue(response_field_ids.issubset(allowed_field_ids))

    def test_examples_show_partial_answers(self):
        for response_set in self.follow_up_response_sets:
            question_set = self.follow_up_question_sets[
                response_set["followUpQuestionSetId"]
            ]
            total_question_fields = len(question_set["questions"])
            answered_fields = len(response_set["responses"])
            with self.subTest(
                followUpResponseSetId=response_set["followUpResponseSetId"]
            ):
                self.assertLess(answered_fields, total_question_fields)

    def test_follow_up_response_set_id_is_deterministic(self):
        for response_set in self.follow_up_response_sets:
            expected_id = (
                "follow-up-response-for-"
                + response_set["followUpQuestionSetId"]
            )
            with self.subTest(
                followUpResponseSetId=response_set["followUpResponseSetId"]
            ):
                self.assertEqual(response_set["followUpResponseSetId"], expected_id)

    def test_follow_up_question_set_binding_is_unique(self):
        question_set_ids = [
            item["followUpQuestionSetId"] for item in self.follow_up_response_sets
        ]
        self.assertEqual(len(question_set_ids), len(set(question_set_ids)))

    def test_typora_classic_example_matches_planned_content(self):
        response_set = next(
            item
            for item in self.follow_up_response_sets
            if item["templateId"] == "typora-classic"
        )
        self.assertEqual(response_set["templateId"], "typora-classic")
        self.assertEqual(
            response_set["followUpResponseSetId"],
            "follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-typora-classic-typora-classic",
        )
        self.assertEqual(
            response_set["responses"],
            {
                "basic.name": "Alex Example",
                "education[].major": "Software Engineering",
                "project[].techStack": "Java, Spring Boot, MySQL, Redis",
            },
        )
        self.assertEqual(response_set["updatedAt"], "2026-04-12T10:00:00Z")

    def test_markdown_basic_example_matches_planned_content(self):
        response_set = next(
            item
            for item in self.follow_up_response_sets
            if item["templateId"] == "markdown-basic"
        )
        self.assertEqual(response_set["templateId"], "markdown-basic")
        self.assertEqual(
            response_set["followUpResponseSetId"],
            "follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-markdown-basic-markdown-basic",
        )
        self.assertEqual(
            response_set["responses"],
            {
                "links.github": "https://github.com/alex-example",
                "education[].school": "Example University",
                "project[].role": "Backend Engineer",
            },
        )
        self.assertEqual(response_set["updatedAt"], "2026-04-12T10:05:00Z")

    def test_follow_up_response_values_reject_non_json_like_types(self):
        response_set = self.follow_up_response_sets[0]
        invalid_values = (
            {"invalid"},
            {"nested": {"invalid"}},
            ["valid", {"nested": {"invalid"}}],
        )

        for invalid_value in invalid_values:
            invalid_response_set = {
                **response_set,
                "responses": {
                    **response_set["responses"],
                    "basic.name": invalid_value,
                },
            }

            with self.subTest(invalid_value=repr(invalid_value)):
                with self.assertRaises(ValidationError):
                    self.follow_up_response_set_validator.validate(invalid_response_set)

    def test_json_like_value_schema_does_not_duplicate_integer_type(self):
        self.assertEqual(
            self.schema["$defs"]["JsonLikeValue"]["type"].count("integer"),
            0,
        )
