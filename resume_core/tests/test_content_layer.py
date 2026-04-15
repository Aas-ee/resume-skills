import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "content-layer.schema.json"
EXAMPLES = ROOT / "examples"
CATALOG_PATH = EXAMPLES / "shared-field-catalog.v1.json"


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


class ResumeCoreContentLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_json(CATALOG_PATH)
        cls.catalog_fields = {item["fieldId"] for item in cls.catalog["fields"]}
        cls.source_document = load_json(
            EXAMPLES / "source-documents" / "existing-resume-markdown.v1.json"
        )
        cls.extractions = [
            load_json(path)
            for path in sorted((EXAMPLES / "source-extractions").glob("*.json"))
        ]
        cls.extraction_ids = {item["extractionId"] for item in cls.extractions}
        cls.profile = load_json(
            EXAMPLES / "resume-profiles" / "sample-ai-agent-profile.v1.json"
        )
        cls.gap_reports = [
            load_json(path) for path in sorted((EXAMPLES / "gap-reports").glob("*.json"))
        ]
        cls.document_validator = validator_for("SourceDocument")
        cls.extraction_validator = validator_for("SourceExtraction")
        cls.profile_validator = validator_for("ResumeProfile")
        cls.gap_validator = validator_for("GapReport")

    def test_source_document_example_is_valid(self):
        self.document_validator.validate(self.source_document)

    def test_source_extraction_examples_are_valid(self):
        for extraction in self.extractions:
            with self.subTest(extractionId=extraction["extractionId"]):
                self.extraction_validator.validate(extraction)

    def test_extraction_candidate_fields_exist_in_catalog(self):
        for extraction in self.extractions:
            for field_id in extraction["candidateFieldIds"]:
                with self.subTest(extractionId=extraction["extractionId"], fieldId=field_id):
                    self.assertIn(field_id, self.catalog_fields)

    def test_resume_profile_example_is_valid(self):
        self.profile_validator.validate(self.profile)

    def test_profile_field_keys_exist_in_catalog(self):
        for field_id in self.profile["fieldValues"].keys():
            with self.subTest(fieldId=field_id):
                self.assertIn(field_id, self.catalog_fields)

    def test_profile_provenance_references_known_extractions(self):
        for field_id, extraction_ids in self.profile["provenance"].items():
            self.assertIn(field_id, self.catalog_fields)
            for extraction_id in extraction_ids:
                with self.subTest(fieldId=field_id, extractionId=extraction_id):
                    self.assertIn(extraction_id, self.extraction_ids)

    def test_gap_report_examples_are_valid(self):
        for gap_report in self.gap_reports:
            with self.subTest(reportId=gap_report["reportId"]):
                self.gap_validator.validate(gap_report)

    def test_gap_report_fields_exist_in_catalog(self):
        for gap_report in self.gap_reports:
            field_ids = []
            field_ids.extend(gap_report["missingRequired"])
            field_ids.extend(gap_report["missingRecommended"])
            field_ids.extend(item["fieldId"] for item in gap_report["questions"])
            for field_id in field_ids:
                with self.subTest(reportId=gap_report["reportId"], fieldId=field_id):
                    self.assertIn(field_id, self.catalog_fields)
