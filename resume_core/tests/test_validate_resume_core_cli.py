import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKTREE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKTREE_ROOT))

from resume_core.scripts import validate_resume_core

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_resume_core.py"
EXAMPLES = ROOT / "examples"


class ResumeCoreValidationScriptTests(unittest.TestCase):
    def assert_dynamic_collection_loading(
        self,
        examples_dir: str,
        expected_values: list[object],
        actual_values: list[object],
    ) -> None:
        expected_paths = sorted((ROOT / "examples" / examples_dir).glob("*.json"))

        self.assertGreater(len(expected_paths), 0)
        self.assertEqual(len(actual_values), len(expected_paths))
        self.assertEqual(expected_values, actual_values)

    def assert_integrity_validation_error(self, mutator, expected_message: str) -> None:
        artifacts = validate_resume_core.load_example_artifacts()
        mutator(artifacts)

        with self.assertRaisesRegex(ValueError, expected_message):
            validate_resume_core.validate_integrity(artifacts)

    def test_dynamic_manifest_loading_picks_up_all_template_json_files(self):
        artifacts = validate_resume_core.load_example_artifacts()

        self.assert_dynamic_collection_loading(
            examples_dir="templates",
            expected_values=[
                (
                    validate_resume_core.load_json(path)["templateId"],
                    validate_resume_core.load_json(path)["version"],
                )
                for path in sorted((ROOT / "examples" / "templates").glob("*.json"))
            ],
            actual_values=[
                (item["templateId"], item["version"]) for item in artifacts["manifests"]
            ],
        )

    def test_load_manifest_records_keeps_template_paths(self):
        records = validate_resume_core.load_manifest_records()
        expected_paths = sorted((validate_resume_core.ROOT / "examples" / "templates").glob("*.json"))

        self.assertEqual([record["path"] for record in records], expected_paths)
        self.assertEqual(
            [(record["manifest"]["templateId"], record["manifest"]["version"]) for record in records],
            [
                (
                    validate_resume_core.load_json(path)["templateId"],
                    validate_resume_core.load_json(path)["version"],
                )
                for path in expected_paths
            ],
        )

    def test_dynamic_gap_report_loading_picks_up_all_gap_report_json_files(self):
        artifacts = validate_resume_core.load_example_artifacts()

        self.assert_dynamic_collection_loading(
            examples_dir="gap-reports",
            expected_values=[
                validate_resume_core.load_json(path)["reportId"]
                for path in sorted((ROOT / "examples" / "gap-reports").glob("*.json"))
            ],
            actual_values=[item["reportId"] for item in artifacts["gap_reports"]],
        )

    def test_dynamic_follow_up_question_set_loading_picks_up_all_json_files(self):
        artifacts = validate_resume_core.load_example_artifacts()

        self.assert_dynamic_collection_loading(
            examples_dir="follow-up-question-sets",
            expected_values=[
                validate_resume_core.load_json(path)["followUpQuestionSetId"]
                for path in sorted(
                    (ROOT / "examples" / "follow-up-question-sets").glob("*.json")
                )
            ],
            actual_values=[
                item["followUpQuestionSetId"]
                for item in artifacts["follow_up_question_sets"]
            ],
        )

    def test_dynamic_follow_up_response_set_loading_picks_up_all_json_files(self):
        artifacts = validate_resume_core.load_example_artifacts()

        self.assert_dynamic_collection_loading(
            examples_dir="follow-up-response-sets",
            expected_values=[
                validate_resume_core.load_json(path)["followUpResponseSetId"]
                for path in sorted(
                    (ROOT / "examples" / "follow-up-response-sets").glob("*.json")
                )
            ],
            actual_values=[
                item["followUpResponseSetId"]
                for item in artifacts["follow_up_response_sets"]
            ],
        )

    def test_dynamic_follow_up_profile_projection_loading_picks_up_all_json_files(self):
        artifacts = validate_resume_core.load_example_artifacts()

        self.assert_dynamic_collection_loading(
            examples_dir="follow-up-profile-projections",
            expected_values=[
                validate_resume_core.load_json(path)["followUpResponseSetId"]
                for path in sorted(
                    (ROOT / "examples" / "follow-up-profile-projections").glob("*.json")
                )
            ],
            actual_values=[
                item["followUpResponseSetId"]
                for item in artifacts["follow_up_profile_projections"]
            ],
        )

    def run_validation_script(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(root / "scripts" / "validate_resume_core.py")],
            cwd=root.parent,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_validation_script_reports_success(self):
        result = self.run_validation_script(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("follow-up response sets", result.stdout)
        self.assertIn("follow-up profile projections", result.stdout)
        self.assertIn("resume-core validation ok", result.stdout)

    def test_validation_script_rejects_ambiguous_gap_report_profile_binding_across_projection_collections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir) / "resume_core"
            shutil.copytree(ROOT, temp_root)

            guided_projection_path = (
                temp_root
                / "examples"
                / "guided-intake-profile-projections"
                / "markdown-basic.partial.v1.json"
            )
            follow_up_projection_path = (
                temp_root
                / "examples"
                / "follow-up-profile-projections"
                / "markdown-basic.partial.v1.json"
            )
            guided_projection = validate_resume_core.load_json(guided_projection_path)
            follow_up_projection = validate_resume_core.load_json(follow_up_projection_path)

            follow_up_projection["profile"]["profileId"] = guided_projection["profile"][
                "profileId"
            ]
            follow_up_projection_path.write_text(
                validate_resume_core.json.dumps(follow_up_projection, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_validation_script(temp_root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "ambiguous gap report profile binding across guided-intake and follow-up projections",
            result.stderr,
        )

    def test_validation_script_rejects_missing_template_asset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir) / "resume_core"
            shutil.copytree(ROOT, temp_root)
            missing_asset = (
                temp_root
                / "examples"
                / "template-assets"
                / "typora-classic"
                / "template.md"
            )
            missing_asset.unlink()

            result = self.run_validation_script(temp_root)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing template asset for typora-classic:markdown", result.stderr)

    def test_load_required_json_collection_rejects_empty_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "no example JSON files found for",
            ):
                validate_resume_core.load_required_json_collection(
                    Path(temp_dir), "template manifests"
                )

    def test_validate_template_asset_refs_rejects_missing_asset_file(self):
        artifacts = validate_resume_core.load_example_artifacts()
        artifacts["manifest_records"][0] = deepcopy(artifacts["manifest_records"][0])
        artifacts["manifest_records"][0]["manifest"] = deepcopy(
            artifacts["manifest_records"][0]["manifest"]
        )
        artifacts["manifest_records"][0]["manifest"]["assetRefs"]["markdown"] = "../template-assets/missing/template.md"

        with self.assertRaisesRegex(ValueError, "missing template asset for"):
            validate_resume_core.validate_template_asset_refs(artifacts)

    def test_validate_template_asset_refs_rejects_out_of_tree_asset_path(self):
        artifacts = validate_resume_core.load_example_artifacts()
        artifacts["manifest_records"][0] = deepcopy(artifacts["manifest_records"][0])
        artifacts["manifest_records"][0]["manifest"] = deepcopy(
            artifacts["manifest_records"][0]["manifest"]
        )
        artifacts["manifest_records"][0]["manifest"]["assetRefs"]["markdown"] = "../../../README.md"

        with self.assertRaisesRegex(
            ValueError, "template asset ref must stay within template-assets"
        ):
            validate_resume_core.validate_template_asset_refs(artifacts)

    def test_validate_integrity_rejects_duplicate_manifest_field_requirements(self):
        def mutate(artifacts):
            duplicate_manifest = deepcopy(artifacts["manifests"][0])
            duplicate_requirement = deepcopy(duplicate_manifest["fieldRequirements"][0])
            duplicate_manifest["fieldRequirements"].append(duplicate_requirement)
            artifacts["manifests"][0] = duplicate_manifest

        self.assert_integrity_validation_error(
            mutate,
            "template manifest contains duplicate fieldRequirements fieldId",
        )

    def test_validate_integrity_rejects_duplicate_follow_up_question_set_report_ids(self):
        self.assert_integrity_validation_error(
            lambda artifacts: artifacts["follow_up_question_sets"].append(
                deepcopy(artifacts["follow_up_question_sets"][0])
            ),
            "duplicate follow-up question set reportId",
        )

    def test_validate_integrity_rejects_follow_up_question_set_unknown_report_id(self):
        def mutate(artifacts):
            invalid_question_set = deepcopy(artifacts["follow_up_question_sets"][0])
            invalid_question_set["reportId"] = "gap-report-missing"
            artifacts["follow_up_question_sets"][0] = invalid_question_set

        self.assert_integrity_validation_error(
            mutate,
            "unknown follow-up question set reportId",
        )

    def test_validate_integrity_rejects_follow_up_question_set_template_binding_mismatch(self):
        def mutate(artifacts):
            invalid_question_set = deepcopy(artifacts["follow_up_question_sets"][0])
            invalid_question_set["templateId"] = "mismatched.template"
            artifacts["follow_up_question_sets"][0] = invalid_question_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up question set templateId does not match gap report",
        )

    def test_validate_integrity_rejects_follow_up_question_set_profile_binding_mismatch(self):
        def mutate(artifacts):
            invalid_question_set = deepcopy(artifacts["follow_up_question_sets"][0])
            invalid_question_set["profileId"] = "profile-mismatch"
            artifacts["follow_up_question_sets"][0] = invalid_question_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up question set profileId does not match gap report",
        )

    def test_validate_integrity_rejects_follow_up_question_set_id_not_derived_from_report(self):
        def mutate(artifacts):
            invalid_question_set = deepcopy(artifacts["follow_up_question_sets"][0])
            invalid_question_set["followUpQuestionSetId"] = "follow-up-custom"
            artifacts["follow_up_question_sets"][0] = invalid_question_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up question set id must derive from reportId",
        )

    def test_validate_integrity_rejects_follow_up_question_set_questions_not_matching_gap_report(self):
        def mutate(artifacts):
            invalid_question_set = deepcopy(artifacts["follow_up_question_sets"][0])
            invalid_question_set["questions"] = invalid_question_set["questions"][1:]
            artifacts["follow_up_question_sets"][0] = invalid_question_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up question set questions must exactly match gap report questions",
        )

    def test_validate_integrity_rejects_duplicate_follow_up_response_set_question_set_ids(self):
        self.assert_integrity_validation_error(
            lambda artifacts: artifacts["follow_up_response_sets"].append(
                deepcopy(artifacts["follow_up_response_sets"][0])
            ),
            "duplicate follow-up response set followUpQuestionSetId",
        )

    def test_validate_integrity_rejects_follow_up_response_set_unknown_question_set_id(self):
        def mutate(artifacts):
            invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
            invalid_response_set["followUpQuestionSetId"] = "follow-up-for-missing-report"
            artifacts["follow_up_response_sets"][0] = invalid_response_set

        self.assert_integrity_validation_error(
            mutate,
            "unknown follow-up response set followUpQuestionSetId",
        )

    def test_validate_integrity_rejects_follow_up_response_set_report_binding_mismatch(self):
        def mutate(artifacts):
            invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
            invalid_response_set["reportId"] = "gap-report-mismatch"
            artifacts["follow_up_response_sets"][0] = invalid_response_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up response set reportId does not match follow-up question set",
        )

    def test_validate_integrity_rejects_follow_up_response_set_template_binding_mismatch(self):
        def mutate(artifacts):
            invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
            invalid_response_set["templateId"] = "mismatched.template"
            artifacts["follow_up_response_sets"][0] = invalid_response_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up response set templateId does not match follow-up question set",
        )

    def test_validate_integrity_rejects_follow_up_response_set_profile_binding_mismatch(self):
        def mutate(artifacts):
            invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
            invalid_response_set["profileId"] = "profile-mismatch"
            artifacts["follow_up_response_sets"][0] = invalid_response_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up response set profileId does not match follow-up question set",
        )

    def test_validate_integrity_rejects_follow_up_response_set_id_not_derived_from_question_set(self):
        def mutate(artifacts):
            invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
            invalid_response_set["followUpResponseSetId"] = "follow-up-response-custom"
            artifacts["follow_up_response_sets"][0] = invalid_response_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up response set id must derive from followUpQuestionSetId",
        )

    def test_validate_integrity_rejects_follow_up_response_set_unknown_response_field(self):
        def mutate(artifacts):
            invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
            invalid_response_set["responses"]["unknown.field"] = "value"
            artifacts["follow_up_response_sets"][0] = invalid_response_set

        self.assert_integrity_validation_error(
            mutate,
            "follow-up response set contains unknown response field",
        )

    def test_validate_integrity_rejects_duplicate_follow_up_profile_projection_response_set_ids(self):
        self.assert_integrity_validation_error(
            lambda artifacts: artifacts["follow_up_profile_projections"].append(
                deepcopy(artifacts["follow_up_profile_projections"][0])
            ),
            "duplicate follow-up profile projection followUpResponseSetId",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_unknown_response_set_id(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["followUpResponseSetId"] = "follow-up-response-missing"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "unknown follow-up profile projection followUpResponseSetId",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_unknown_base_profile_id(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["baseProfileId"] = "profile-missing"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "unknown follow-up profile projection baseProfileId",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_question_set_mismatch(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["followUpQuestionSetId"] = "follow-up-for-other-report"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection followUpQuestionSetId does not match response set",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_report_mismatch(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["reportId"] = "gap-report-mismatch"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection reportId does not match response set",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_template_mismatch(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["templateId"] = "mismatched.template"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection templateId does not match response set",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_template_version_mismatch(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["templateVersion"] = "9.9.9"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection templateVersion does not match base profile projection",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_profile_id_not_derived_from_response_set(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["profile"]["profileId"] = "profile-custom"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection profileId must derive from followUpResponseSetId",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_projection_id_not_derived_from_response_set(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["projectionId"] = "follow-up-projection-custom"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection projectionId must derive from followUpResponseSetId",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_updated_at_mismatch(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["profile"]["updatedAt"] = "2026-04-12T11:05:00Z"
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection updatedAt must match response set",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_non_cumulative_field_values(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            del invalid_projection["profile"]["fieldValues"]["basic.name"]
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection fieldValues must equal cumulative base fieldValues merged with response set responses",
        )

    def test_validate_integrity_rejects_follow_up_profile_projection_non_cumulative_provenance(self):
        def mutate(artifacts):
            invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
            invalid_projection["profile"]["provenance"]["basic.email"] = [
                "follow-up-response-for-follow-up-for-gap-for-profile-from-guided-intake-response-set-markdown-basic-markdown-basic"
            ]
            artifacts["follow_up_profile_projections"][0] = invalid_projection

        self.assert_integrity_validation_error(
            mutate,
            "follow-up profile projection provenance must equal cumulative base provenance with follow-up response set ids for answered fields",
        )

    def test_validate_schemas_rejects_follow_up_response_set_invalid_updated_at_datetime(self):
        artifacts = validate_resume_core.load_example_artifacts()
        invalid_response_set = deepcopy(artifacts["follow_up_response_sets"][0])
        invalid_response_set["updatedAt"] = "not-a-date-time"
        artifacts["follow_up_response_sets"][0] = invalid_response_set

        with self.assertRaisesRegex(Exception, "not a 'date-time'"):
            validate_resume_core.validate_schemas(artifacts)

    def test_validate_schemas_rejects_follow_up_profile_projection_invalid_updated_at_datetime(self):
        artifacts = validate_resume_core.load_example_artifacts()
        invalid_projection = deepcopy(artifacts["follow_up_profile_projections"][0])
        invalid_projection["profile"]["updatedAt"] = "not-a-date-time"
        artifacts["follow_up_profile_projections"][0] = invalid_projection

        with self.assertRaisesRegex(Exception, "not a 'date-time'"):
            validate_resume_core.validate_schemas(artifacts)
