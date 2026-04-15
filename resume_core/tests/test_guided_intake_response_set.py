import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "response-layer.schema.json"
EXAMPLES = ROOT / "examples"
QUESTION_SETS_DIR = EXAMPLES / "guided-intake-question-sets"
RESPONSE_SETS_DIR = EXAMPLES / "guided-intake-response-sets"


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


class ResumeCoreGuidedIntakeResponseSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.question_sets = {
            question_set["questionSetId"]: question_set
            for question_set in (
                load_json(path) for path in sorted(QUESTION_SETS_DIR.glob("*.json"))
            )
        }
        cls.response_sets = [
            load_json(path) for path in sorted(RESPONSE_SETS_DIR.glob("*.json"))
        ]
        cls.validator = validator_for("GuidedIntakeResponseSet")

    def test_response_set_examples_are_valid(self):
        for response_set in self.response_sets:
            with self.subTest(responseSetId=response_set["responseSetId"]):
                self.validator.validate(response_set)

    def test_response_sets_reference_known_question_sets(self):
        for response_set in self.response_sets:
            with self.subTest(responseSetId=response_set["responseSetId"]):
                self.assertIn(response_set["questionSetId"], self.question_sets)

    def test_template_binding_matches_question_set(self):
        for response_set in self.response_sets:
            question_set = self.question_sets[response_set["questionSetId"]]
            with self.subTest(responseSetId=response_set["responseSetId"]):
                self.assertEqual(response_set["templateId"], question_set["templateId"])
                self.assertEqual(
                    response_set["templateVersion"],
                    question_set["templateVersion"],
                )

    def test_response_keys_belong_to_referenced_question_set(self):
        for response_set in self.response_sets:
            question_set = self.question_sets[response_set["questionSetId"]]
            allowed_field_ids = {
                item["fieldId"] for item in question_set["questions"]
            }
            response_field_ids = set(response_set["responses"].keys())
            with self.subTest(responseSetId=response_set["responseSetId"]):
                self.assertTrue(response_field_ids.issubset(allowed_field_ids))

    def test_examples_show_partial_answers(self):
        for response_set in self.response_sets:
            question_set = self.question_sets[response_set["questionSetId"]]
            total_question_fields = len(question_set["questions"])
            answered_fields = len(response_set["responses"])
            with self.subTest(responseSetId=response_set["responseSetId"]):
                self.assertLess(answered_fields, total_question_fields)

    def test_response_values_allow_multiple_json_types(self):
        response_set = next(
            item
            for item in self.response_sets
            if item["responseSetId"] == "guided-intake-response-set-typora-classic"
        )
        self.assertIsInstance(response_set["responses"]["basic.email"], str)
        self.assertIsInstance(response_set["responses"]["project[].bullets"], list)
        self.assertIsInstance(response_set["responses"]["summary.items"], list)
