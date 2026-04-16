import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from resume_runtime.runtime.host_conversation_adapter import default_host_session_store_path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = ROOT / "resume_core" / "examples"
CLAUDE_SKILL_TESTS = ROOT / ".claude" / "skills" / "resume" / "tests"
LEGACY_AGENT_CLI = ROOT / ".claude" / "skills" / "resume" / "agent_intake_cli.py"
LEGACY_HOST_CLI = ROOT / ".claude" / "skills" / "resume" / "host_cli.py"
LEGACY_TEMPLATE_CATALOG_CLI = ROOT / ".claude" / "skills" / "resume" / "template_catalog_cli.py"
LEGACY_TEMPLATE_STORE_CLI = ROOT / ".claude" / "skills" / "resume" / "template_store_cli.py"
PUBLIC_RUNTIME_DIR = ROOT / "resume_runtime"
PUBLIC_RUNTIME_RUNTIME_DIR = PUBLIC_RUNTIME_DIR / "runtime"


class ResumeRuntimeImportTests(unittest.TestCase):
    def test_public_package_imports_without_claude_path_injection(self):
        package = importlib.import_module("resume_runtime")
        runtime = importlib.import_module("resume_runtime.runtime")

        self.assertIsNotNone(package)
        self.assertIsNotNone(runtime)

    def test_public_package_re_exports_runtime_surface(self):
        package = importlib.import_module("resume_runtime")
        runtime = importlib.import_module("resume_runtime.runtime")

        expected_symbol_names = [
            "AgentIntakeCore",
            "AgentIntakeCoreError",
            "AgentIntakeCoreOutcome",
            "AskedQuestion",
            "BatchAnswerResult",
            "ConversationRoute",
            "EntrypointMode",
            "HostConversationAdapter",
            "HostConversationAdapterError",
            "HostConversationOutcome",
            "HostSessionAction",
            "HostSessionRunner",
            "HostSessionRunnerError",
            "HostSessionState",
            "HostSessionStore",
            "HostSessionStoreError",
            "MaterialIntakeResult",
            "PromptDirective",
            "ResumeMaterial",
            "SessionRunner",
            "SessionRunnerResult",
            "TemplateCatalogEntry",
            "TemplateCard",
            "TemplateStore",
            "default_host_session_store_path",
            "derive_guided_intake_checklist",
            "host_conversation_outcome_to_dict",
            "load_template_catalog",
            "render_template_bundle",
            "route_conversation_turn",
            "serialize_question_batch",
            "write_rendered_bundle",
        ]

        for symbol_name in expected_symbol_names:
            with self.subTest(symbol_name=symbol_name):
                self.assertTrue(hasattr(runtime, symbol_name))
                self.assertTrue(hasattr(package, symbol_name))
                self.assertIs(getattr(package, symbol_name), getattr(runtime, symbol_name))

    def test_runtime_submodules_import_from_public_package(self):
        module_names = [
            "resume_runtime.runtime.follow_up_agent_adapter",
            "resume_runtime.runtime.follow_up_policy",
            "resume_runtime.runtime.follow_up_state",
            "resume_runtime.runtime.follow_up_loop",
            "resume_runtime.runtime.artifact_builders",
            "resume_runtime.runtime.nl_batch_normalizer",
            "resume_runtime.runtime.conversation_router",
            "resume_runtime.runtime.material_intake_adapter",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_session_modules_import_from_public_package(self):
        module_names = [
            "resume_runtime.runtime.session_runner",
            "resume_runtime.runtime.host_session_state",
            "resume_runtime.runtime.host_session_store",
            "resume_runtime.runtime.host_session_runner",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_public_runtime_sources_do_not_import_claude_adapter_modules(self):
        python_files = list(PUBLIC_RUNTIME_DIR.glob("*.py")) + list(PUBLIC_RUNTIME_RUNTIME_DIR.glob("*.py"))
        for file_path in python_files:
            with self.subTest(file_path=file_path):
                source = file_path.read_text(encoding="utf-8")
                self.assertNotIn(".claude", source)
                self.assertNotIn("resume.runtime", source)

    def test_default_host_session_store_path_stays_inside_public_runtime_dir(self):
        expected = ROOT / "resume_runtime" / ".runtime" / "host_sessions"
        self.assertEqual(default_host_session_store_path(), expected)

    def test_claude_skill_tests_discover_from_repo_root(self):
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(CLAUDE_SKILL_TESTS)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )

    def test_legacy_agent_cli_wrapper_runs_directly(self):
        completed = subprocess.run(
            [sys.executable, str(LEGACY_AGENT_CLI)],
            cwd=ROOT,
            input='{"version":"resume-agent-intake-cli/v1","turn":{"kind":"reply","timestamp":"2026-04-15T10:00:00Z","user_message":"Please help improve my resume for a backend role."}}\n',
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )

    def test_legacy_host_cli_wrapper_runs_directly(self):
        completed = subprocess.run(
            [sys.executable, str(LEGACY_HOST_CLI)],
            cwd=ROOT,
            input='{"version":"resume-host-cli/v1","turn":{"kind":"reply","timestamp":"2026-04-15T10:00:00Z","user_reply":"just chat normally"}}\n',
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )

    def test_legacy_template_catalog_cli_wrapper_runs_directly(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(LEGACY_TEMPLATE_CATALOG_CLI),
                "--examples-root",
                str(EXAMPLES_ROOT),
                "--generated-at",
                "2026-04-16T12:00:00Z",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
        )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "resume-template-catalog-cli/v1")
        self.assertGreater(len(payload["entries"]), 0)

    def test_legacy_template_store_cli_wrapper_runs_directly(self):
        request = {
            "version": "resume-template-store-cli/v1",
            "action": "save",
            "scope": "user",
            "manifest": {
                "templateId": "wrapper-template",
                "name": "Wrapper Template",
                "version": "1.0.0",
                "description": "Wrapper smoke test template",
                "target": "typora",
                "sectionOrder": ["header", "projects"],
                "fieldRequirements": [
                    {
                        "fieldId": "basic.name",
                        "required": True,
                        "repeatable": False,
                        "order": 10,
                        "promptHint": "Candidate name",
                    }
                ],
                "renderSpecRef": "renderers/wrapper-template@1.0.0",
                "origin": "imported",
                "assetRefs": {
                    "markdown": "template.md",
                    "html": "template.html",
                    "css": "style.css",
                },
                "previewCard": {
                    "title": "Wrapper Template",
                    "styleLabel": "Compact",
                    "useCases": ["测试"],
                    "requiredContentSummary": ["姓名"],
                },
                "storageScope": "user",
            },
            "assets": {
                "markdown": "# {{basic.name}}",
                "html": "<h1>{{basic.name}}</h1>",
                "css": "body { color: #222; }",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(LEGACY_TEMPLATE_STORE_CLI),
                    "--store-root",
                    temp_dir,
                ],
                cwd=ROOT,
                input=json.dumps(request),
                text=True,
                capture_output=True,
            )

            self.assertEqual(
                completed.returncode,
                0,
                msg=f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}",
            )
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["version"], "resume-template-store-cli/v1")
            self.assertTrue(Path(payload["manifest_path"]).is_file())
