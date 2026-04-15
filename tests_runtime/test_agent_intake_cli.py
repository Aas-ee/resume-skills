import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_INTAKE_CLI = ROOT / "resume_runtime" / "agent_intake_cli.py"


class ResumeRuntimeAgentIntakeCliTests(unittest.TestCase):
    def test_freeform_resume_intent_requests_existing_material(self):
        request = {
            "version": "resume-agent-intake-cli/v1",
            "turn": {
                "kind": "reply",
                "timestamp": "2026-04-15T10:00:00Z",
                "user_message": "Please help improve my resume for a backend role.",
            },
        }
        completed = self._run_cli(request)

        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "resume-agent-intake-cli/v1")
        self.assertEqual(payload["outcome"]["mode"], "freeform_discovery")
        self.assertEqual(payload["outcome"]["prompt_directive"], "ask_existing_material")
        self.assertNotIn("structured_outcome", payload["outcome"])
        self.assertNotIn("material_result", payload["outcome"])

    def test_structured_material_cli_output_preserves_contract_shape(self):
        request = {
            "version": "resume-agent-intake-cli/v1",
            "turn": {
                "kind": "resume",
                "timestamp": "2026-04-15T10:00:00Z",
            },
            "template_context": {
                "manifest": {
                    "templateId": "markdown-basic",
                    "version": "1.0.0",
                    "fieldRequirements": [
                        {
                            "fieldId": "basic.name",
                            "required": True,
                            "promptHint": "Candidate name in the Markdown title",
                        },
                        {
                            "fieldId": "basic.email",
                            "required": True,
                            "promptHint": "Primary email below the title",
                        },
                    ],
                },
                "checklist": {
                    "templateId": "markdown-basic",
                    "templateVersion": "1.0.0",
                    "requiredFields": ["basic.name", "basic.email"],
                    "optionalFields": [],
                },
            },
            "materials": [
                {
                    "document_id": "doc-1",
                    "source_label": "existing-resume.md",
                    "media_type": "text/markdown",
                    "text": "# Ada Lovelace",
                }
            ],
        }

        completed = self._run_cli(request)

        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "resume-agent-intake-cli/v1")
        self.assertEqual(payload["outcome"]["mode"], "structured_intake")
        self.assertEqual(payload["outcome"]["prompt_directive"], "ask_current_batch")
        self.assertEqual(payload["structured_outcome"]["mode"], "structured")
        self.assertEqual(payload["structured_outcome"]["prompt_directive"], "ask_current_batch")
        self.assertTrue(payload["structured_outcome"]["session_id"])
        self.assertEqual(payload["structured_outcome"]["next_action_kind"], "ask_batch")
        self.assertEqual(payload["material_result"]["parse_status"], "parsed")
        self.assertIn("required_fields", payload["material_result"]["bootstrap_checklist"])
        self.assertEqual(payload["material_result"]["missing_required_fields"], ["basic.email"])
        self.assertEqual(payload["material_result"]["document_ids"], ["doc-1"])

    def test_missing_template_checklist_returns_invalid_request_shape(self):
        request = {
            "version": "resume-agent-intake-cli/v1",
            "turn": {
                "kind": "resume",
                "timestamp": "2026-04-15T10:00:00Z",
            },
            "template_context": {
                "manifest": {
                    "templateId": "markdown-basic",
                    "version": "1.0.0",
                    "fieldRequirements": [],
                }
            },
        }

        completed = self._run_cli(request)

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["version"], "resume-agent-intake-cli/v1")
        self.assertEqual(payload["error"]["code"], "invalid_request_shape")

    def test_invalid_json_returns_machine_readable_error(self):
        completed = subprocess.run(
            [sys.executable, str(AGENT_INTAKE_CLI)],
            input="{not-json}",
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["version"], "resume-agent-intake-cli/v1")
        self.assertEqual(payload["error"]["code"], "invalid_request_json")

    def _run_cli(self, request: dict[str, object]) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            return subprocess.run(
                [
                    sys.executable,
                    str(AGENT_INTAKE_CLI),
                    "--session-store",
                    temp_dir,
                ],
                input=json.dumps(request),
                text=True,
                capture_output=True,
            )


if __name__ == "__main__":
    unittest.main()
