import importlib
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILL_TESTS = ROOT / ".claude" / "skills" / "resume" / "tests"
LEGACY_AGENT_CLI = ROOT / ".claude" / "skills" / "resume" / "agent_intake_cli.py"
LEGACY_HOST_CLI = ROOT / ".claude" / "skills" / "resume" / "host_cli.py"


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
            "default_host_session_store_path",
            "host_conversation_outcome_to_dict",
            "route_conversation_turn",
            "serialize_question_batch",
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
