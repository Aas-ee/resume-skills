import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "follow-up-question-layer.schema.json"
EXAMPLES = ROOT / "examples"
GAP_REPORTS_DIR = EXAMPLES / "gap-reports"
FOLLOW_UP_QUESTION_SETS_DIR = EXAMPLES / "follow-up-question-sets"


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


class ResumeCoreFollowUpQuestionSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gap_reports = {
            gap_report["reportId"]: gap_report
            for gap_report in (
                load_json(path) for path in sorted(GAP_REPORTS_DIR.glob("*.json"))
            )
        }
        cls.follow_up_question_sets = [
            load_json(path)
            for path in sorted(FOLLOW_UP_QUESTION_SETS_DIR.glob("*.json"))
        ]
        cls.follow_up_question_set_validator = validator_for("FollowUpQuestionSet")

    def test_follow_up_question_set_examples_are_present(self):
        self.assertGreater(
            len(self.follow_up_question_sets),
            0,
            "Expected at least one follow-up question-set example.",
        )

    def test_follow_up_question_set_examples_are_valid(self):
        for question_set in self.follow_up_question_sets:
            with self.subTest(reportId=question_set["reportId"]):
                self.follow_up_question_set_validator.validate(question_set)

    def test_follow_up_question_set_references_known_gap_report(self):
        for question_set in self.follow_up_question_sets:
            with self.subTest(reportId=question_set["reportId"]):
                self.assertIn(question_set["reportId"], self.gap_reports)

    def test_follow_up_question_set_inherits_gap_report_binding(self):
        for question_set in self.follow_up_question_sets:
            gap_report = self.gap_reports[question_set["reportId"]]
            with self.subTest(reportId=question_set["reportId"]):
                self.assertEqual(question_set["templateId"], gap_report["templateId"])
                self.assertEqual(question_set["profileId"], gap_report["profileId"])

    def test_follow_up_question_set_questions_exactly_match_gap_report_questions(self):
        for question_set in self.follow_up_question_sets:
            gap_report = self.gap_reports[question_set["reportId"]]
            with self.subTest(reportId=question_set["reportId"]):
                self.assertEqual(question_set["questions"], gap_report["questions"])

    def test_follow_up_question_set_id_is_deterministic(self):
        for question_set in self.follow_up_question_sets:
            expected_id = f"follow-up-for-{question_set['reportId']}"
            with self.subTest(reportId=question_set["reportId"]):
                self.assertEqual(question_set["followUpQuestionSetId"], expected_id)

    def test_follow_up_question_set_report_binding_is_unique(self):
        report_ids = [item["reportId"] for item in self.follow_up_question_sets]
        self.assertEqual(len(report_ids), len(set(report_ids)))
