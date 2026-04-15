import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "checklist-layer.schema.json"
EXAMPLES = ROOT / "examples"
TEMPLATES_DIR = EXAMPLES / "templates"
CHECKLISTS_DIR = EXAMPLES / "guided-intake-checklists"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(def_name: str):
    schema = load_json(SCHEMA_PATH)
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{def_name}",
        }
    )


def split_fields(manifest: dict) -> tuple[list[str], list[str], list[str]]:
    requirements = sorted(
        manifest["fieldRequirements"], key=lambda requirement: requirement["order"]
    )
    required_fields = [
        item["fieldId"] for item in requirements if item["required"]
    ]
    optional_fields = [
        item["fieldId"] for item in requirements if not item["required"]
    ]
    repeatable_fields = [
        item["fieldId"] for item in requirements if item["repeatable"]
    ]
    return required_fields, optional_fields, repeatable_fields


class ResumeCoreGuidedIntakeChecklistTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifests = {
            path.stem.replace(".v1", ""): load_json(path)
            for path in sorted(TEMPLATES_DIR.glob("*.json"))
        }
        cls.checklists = [
            load_json(path) for path in sorted(CHECKLISTS_DIR.glob("*.json"))
        ]
        cls.validator = validator_for("GuidedIntakeChecklist")

    def test_checklist_examples_are_valid(self):
        for checklist in self.checklists:
            with self.subTest(checklistId=checklist["checklistId"]):
                self.validator.validate(checklist)

    def test_checklists_reference_known_template_versions(self):
        manifest_index = {
            (manifest["templateId"], manifest["version"])
            for manifest in self.manifests.values()
        }
        for checklist in self.checklists:
            checklist_key = (checklist["templateId"], checklist["templateVersion"])
            with self.subTest(checklistId=checklist["checklistId"]):
                self.assertIn(checklist_key, manifest_index)

    def test_required_fields_match_template_requirements(self):
        for checklist in self.checklists:
            manifest = self.manifests[checklist["templateId"]]
            required_fields, _, _ = split_fields(manifest)
            with self.subTest(checklistId=checklist["checklistId"]):
                self.assertEqual(checklist["requiredFields"], required_fields)

    def test_optional_fields_match_template_requirements(self):
        for checklist in self.checklists:
            manifest = self.manifests[checklist["templateId"]]
            _, optional_fields, _ = split_fields(manifest)
            with self.subTest(checklistId=checklist["checklistId"]):
                self.assertEqual(checklist["optionalFields"], optional_fields)

    def test_repeatable_fields_match_template_requirements(self):
        for checklist in self.checklists:
            manifest = self.manifests[checklist["templateId"]]
            _, _, repeatable_fields = split_fields(manifest)
            with self.subTest(checklistId=checklist["checklistId"]):
                self.assertEqual(checklist["repeatableFields"], repeatable_fields)

    def test_required_and_optional_fields_do_not_overlap(self):
        for checklist in self.checklists:
            overlap = set(checklist["requiredFields"]) & set(checklist["optionalFields"])
            with self.subTest(checklistId=checklist["checklistId"]):
                self.assertEqual(overlap, set())

    def test_repeatable_fields_are_subset_of_declared_fields(self):
        for checklist in self.checklists:
            declared = set(checklist["requiredFields"]) | set(checklist["optionalFields"])
            repeatable = set(checklist["repeatableFields"])
            with self.subTest(checklistId=checklist["checklistId"]):
                self.assertTrue(repeatable.issubset(declared))
