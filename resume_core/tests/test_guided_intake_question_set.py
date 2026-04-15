import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "question-layer.schema.json"
EXAMPLES = ROOT / "examples"
TEMPLATES_DIR = EXAMPLES / "templates"
CHECKLISTS_DIR = EXAMPLES / "guided-intake-checklists"
QUESTION_SETS_DIR = EXAMPLES / "guided-intake-question-sets"


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


def question_text(prompt_hint: str) -> str:
    return f"Please provide {prompt_hint}."


def requirements_by_field(manifest: dict) -> dict[str, dict]:
    return {
        requirement["fieldId"]: requirement
        for requirement in manifest["fieldRequirements"]
    }


class ResumeCoreGuidedIntakeQuestionSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifests = {
            path.stem.replace(".v1", ""): load_json(path)
            for path in sorted(TEMPLATES_DIR.glob("*.json"))
        }
        cls.checklists = {
            (checklist["templateId"], checklist["templateVersion"]): checklist
            for checklist in (
                load_json(path) for path in sorted(CHECKLISTS_DIR.glob("*.json"))
            )
        }
        cls.question_sets = [
            load_json(path) for path in sorted(QUESTION_SETS_DIR.glob("*.json"))
        ]
        cls.validator = validator_for("GuidedIntakeQuestionSet")

    def test_question_set_examples_are_valid(self):
        for question_set in self.question_sets:
            with self.subTest(questionSetId=question_set["questionSetId"]):
                self.validator.validate(question_set)

    def test_question_sets_reference_known_template_versions(self):
        manifest_index = {
            (manifest["templateId"], manifest["version"])
            for manifest in self.manifests.values()
        }
        for question_set in self.question_sets:
            question_set_key = (
                question_set["templateId"],
                question_set["templateVersion"],
            )
            with self.subTest(questionSetId=question_set["questionSetId"]):
                self.assertIn(question_set_key, manifest_index)

    def test_question_sets_reference_known_checklists(self):
        for question_set in self.question_sets:
            checklist_key = (
                question_set["templateId"],
                question_set["templateVersion"],
            )
            with self.subTest(questionSetId=question_set["questionSetId"]):
                self.assertIn(checklist_key, self.checklists)

    def test_question_field_ids_match_checklist_order(self):
        for question_set in self.question_sets:
            checklist = self.checklists[
                (question_set["templateId"], question_set["templateVersion"])
            ]
            expected_field_ids = (
                checklist["requiredFields"] + checklist["optionalFields"]
            )
            actual_field_ids = [
                item["fieldId"] for item in question_set["questions"]
            ]
            with self.subTest(questionSetId=question_set["questionSetId"]):
                self.assertEqual(actual_field_ids, expected_field_ids)

    def test_question_text_matches_template_prompt_hints(self):
        for question_set in self.question_sets:
            manifest = self.manifests[question_set["templateId"]]
            field_requirements = requirements_by_field(manifest)
            expected_questions = []
            for item in question_set["questions"]:
                prompt_hint = field_requirements[item["fieldId"]]["promptHint"]
                expected_questions.append(
                    {
                        "fieldId": item["fieldId"],
                        "question": question_text(prompt_hint),
                    }
                )
            with self.subTest(questionSetId=question_set["questionSetId"]):
                self.assertEqual(question_set["questions"], expected_questions)

    def test_question_field_ids_do_not_repeat(self):
        for question_set in self.question_sets:
            field_ids = [item["fieldId"] for item in question_set["questions"]]
            with self.subTest(questionSetId=question_set["questionSetId"]):
                self.assertEqual(len(field_ids), len(set(field_ids)))

    def test_every_included_field_has_non_empty_prompt_hint(self):
        for question_set in self.question_sets:
            manifest = self.manifests[question_set["templateId"]]
            field_requirements = requirements_by_field(manifest)
            for item in question_set["questions"]:
                prompt_hint = field_requirements[item["fieldId"]].get("promptHint")
                with self.subTest(
                    questionSetId=question_set["questionSetId"],
                    fieldId=item["fieldId"],
                ):
                    self.assertTrue(isinstance(prompt_hint, str) and prompt_hint.strip())
