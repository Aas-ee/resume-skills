import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "content-layer.schema.json"
EXAMPLES = ROOT / "examples"
TEMPLATES_DIR = EXAMPLES / "templates"
GUIDED_INTAKE_PROJECTIONS_DIR = EXAMPLES / "guided-intake-profile-projections"
FOLLOW_UP_PROJECTIONS_DIR = EXAMPLES / "follow-up-profile-projections"
GAP_REPORTS_DIR = EXAMPLES / "gap-reports"

TARGETED_FOLLOW_UP_GAP_REPORTS = {
    "typora-classic": {
        "profileId": "profile-from-follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-typora-classic-typora-classic",
        "reportId": "gap-for-profile-from-follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-typora-classic-typora-classic-typora-classic",
        "missingRequired": [
            "education[].school",
            "education[].degree",
            "project[].name",
            "project[].role",
        ],
        "missingRecommended": ["links.github"],
        "questions": [
            {
                "fieldId": "links.github",
                "question": "Please provide GitHub link if it strengthens the profile.",
            },
            {
                "fieldId": "education[].school",
                "question": "Please provide School name for each education entry.",
            },
            {
                "fieldId": "education[].degree",
                "question": "Please provide Degree label for each education entry.",
            },
            {
                "fieldId": "project[].name",
                "question": "Please provide Project title.",
            },
            {
                "fieldId": "project[].role",
                "question": "Please provide Role label shown on the project row.",
            },
        ],
        "generatedAt": "2026-04-12T10:10:00Z",
    },
    "markdown-basic": {
        "profileId": "profile-from-follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-markdown-basic-markdown-basic",
        "reportId": "gap-for-profile-from-follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-markdown-basic-markdown-basic-markdown-basic",
        "missingRequired": [
            "education[].major",
            "education[].degree",
            "project[].name",
        ],
        "missingRecommended": ["summary.items"],
        "questions": [
            {
                "fieldId": "summary.items",
                "question": "Please provide Short summary bullets.",
            },
            {
                "fieldId": "education[].major",
                "question": "Please provide Major name.",
            },
            {
                "fieldId": "education[].degree",
                "question": "Please provide Degree label.",
            },
            {
                "fieldId": "project[].name",
                "question": "Please provide Project title.",
            },
        ],
        "generatedAt": "2026-04-12T10:15:00Z",
    },
}


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


class ResumeCoreGapReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifests = {
            (manifest["templateId"], manifest["version"]): manifest
            for manifest in (
                load_json(path) for path in sorted(TEMPLATES_DIR.glob("*.json"))
            )
        }
        projection_paths = sorted(GUIDED_INTAKE_PROJECTIONS_DIR.glob("*.json")) + sorted(
            FOLLOW_UP_PROJECTIONS_DIR.glob("*.json")
        )
        cls.projections_by_template_and_profile = {
            (projection["templateId"], projection["profile"]["profileId"]): projection
            for projection in (load_json(path) for path in projection_paths)
        }
        cls.gap_reports = [
            load_json(path) for path in sorted(GAP_REPORTS_DIR.glob("*.json"))
        ]
        cls.gap_reports_by_template_and_profile = {
            (gap_report["templateId"], gap_report["profileId"]): gap_report
            for gap_report in cls.gap_reports
        }
        cls.gap_validator = validator_for("GapReport")

    def projection_for_gap_report(self, gap_report):
        return self.projections_by_template_and_profile[
            (gap_report["templateId"], gap_report["profileId"])
        ]

    def gap_report_for_template_and_profile(self, template_id, profile_id):
        return self.gap_reports_by_template_and_profile[(template_id, profile_id)]

    def test_gap_report_examples_are_present(self):
        self.assertGreater(
            len(self.gap_reports),
            0,
            "Expected at least one gap-report example.",
        )

    def test_gap_report_examples_are_valid(self):
        for gap_report in self.gap_reports:
            with self.subTest(reportId=gap_report["reportId"]):
                self.gap_validator.validate(gap_report)

    def test_gap_report_template_and_profile_binding_is_known(self):
        for gap_report in self.gap_reports:
            projection = self.projection_for_gap_report(gap_report)
            template_key = (
                projection["templateId"],
                projection["templateVersion"],
            )
            with self.subTest(reportId=gap_report["reportId"]):
                self.assertIn(template_key, self.manifests)
                self.assertEqual(
                    gap_report["profileId"],
                    projection["profile"]["profileId"],
                )

    def test_gap_report_missing_fields_match_absent_profile_keys(self):
        for gap_report in self.gap_reports:
            projection = self.projection_for_gap_report(gap_report)
            template_key = (
                projection["templateId"],
                projection["templateVersion"],
            )
            manifest = self.manifests[template_key]
            profile = projection["profile"]
            expected_missing_required = []
            expected_missing_recommended = []
            for requirement in manifest["fieldRequirements"]:
                field_id = requirement["fieldId"]
                if field_id in profile["fieldValues"]:
                    continue
                if requirement["required"]:
                    expected_missing_required.append(field_id)
                else:
                    expected_missing_recommended.append(field_id)
            with self.subTest(reportId=gap_report["reportId"]):
                self.assertEqual(gap_report["missingRequired"], expected_missing_required)
                self.assertEqual(
                    gap_report["missingRecommended"], expected_missing_recommended
                )

    def test_gap_report_questions_follow_manifest_field_order_for_missing_fields(self):
        for gap_report in self.gap_reports:
            projection = self.projection_for_gap_report(gap_report)
            template_key = (
                projection["templateId"],
                projection["templateVersion"],
            )
            manifest = self.manifests[template_key]
            missing_field_ids = (
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
            with self.subTest(reportId=gap_report["reportId"]):
                self.assertEqual(gap_report["questions"], expected_questions)

    def test_gap_report_metadata_is_deterministic(self):
        for gap_report in self.gap_reports:
            expected_report_id = f"gap-for-{gap_report['profileId']}-{gap_report['templateId']}"
            with self.subTest(reportId=gap_report["reportId"]):
                self.assertEqual(gap_report["reportId"], expected_report_id)
                self.assertEqual(gap_report["conflicts"], [])

    def test_gap_report_required_and_recommended_fields_do_not_overlap(self):
        for gap_report in self.gap_reports:
            with self.subTest(reportId=gap_report["reportId"]):
                self.assertEqual(
                    set(gap_report["missingRequired"])
                    & set(gap_report["missingRecommended"]),
                    set(),
                )

    def test_targeted_follow_up_gap_examples_match_planned_content(self):
        for template_id, expected_gap_report in TARGETED_FOLLOW_UP_GAP_REPORTS.items():
            with self.subTest(templateId=template_id):
                gap_report = self.gap_report_for_template_and_profile(
                    template_id,
                    expected_gap_report["profileId"],
                )
                self.assertEqual(gap_report["reportId"], expected_gap_report["reportId"])
                self.assertEqual(
                    gap_report["missingRequired"],
                    expected_gap_report["missingRequired"],
                )
                self.assertEqual(
                    gap_report["missingRecommended"],
                    expected_gap_report["missingRecommended"],
                )
                self.assertEqual(gap_report["questions"], expected_gap_report["questions"])
                self.assertEqual(
                    gap_report["generatedAt"], expected_gap_report["generatedAt"]
                )
