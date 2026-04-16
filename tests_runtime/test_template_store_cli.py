import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from resume_runtime.runtime.template_store import TemplateStore

ROOT = Path(__file__).resolve().parents[1]
STORE_CLI = ROOT / "resume_runtime" / "template_store_cli.py"


def make_manifest(template_id: str = "custom-typora") -> dict:
    return {
        "templateId": template_id,
        "name": "Custom Typora",
        "version": "1.0.0",
        "description": "User refined Typora template",
        "target": "typora",
        "sectionOrder": ["header", "projects"],
        "fieldRequirements": [
            {
                "fieldId": "basic.name",
                "required": True,
                "repeatable": False,
                "order": 10,
                "promptHint": "Candidate name",
            },
            {
                "fieldId": "project[].name",
                "required": True,
                "repeatable": True,
                "order": 20,
                "promptHint": "Project title",
            },
        ],
        "renderSpecRef": "renderers/custom-typora@1.0.0",
        "origin": "imported",
        "assetRefs": {"markdown": "template.md", "html": "template.html", "css": "style.css"},
        "previewCard": {
            "title": "Custom Typora",
            "styleLabel": "Compact personal theme",
            "useCases": ["个人复用"],
            "requiredContentSummary": ["姓名", "项目标题"],
        },
        "storageScope": "user",
    }


class TemplateStoreCliTests(unittest.TestCase):
    def run_store_cli(self, store_root: str, request: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(STORE_CLI), "--store-root", store_root],
            input=json.dumps(request),
            text=True,
            capture_output=True,
        )

    def test_save_action_writes_user_template_package(self):
        request = {
            "version": "resume-template-store-cli/v1",
            "action": "save",
            "scope": "user",
            "manifest": make_manifest(),
            "assets": {
                "markdown": "# {{basic.name}}",
                "html": "<h1>{{basic.name}}</h1>",
                "css": "body { color: #222; }",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_store_cli(temp_dir, request)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            manifest_path = Path(payload["manifest_path"])
            self.assertTrue(manifest_path.is_file())
            self.assertTrue((manifest_path.parent / "template.md").is_file())
            self.assertTrue((manifest_path.parent / "template.html").is_file())
            self.assertTrue((manifest_path.parent / "style.css").is_file())

    def test_save_action_rejects_invalid_scope(self):
        request = {
            "version": "resume-template-store-cli/v1",
            "action": "save",
            "scope": "team",
            "manifest": make_manifest(),
            "assets": {
                "markdown": "# {{basic.name}}",
                "html": "<h1>{{basic.name}}</h1>",
                "css": "body { color: #222; }",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_store_cli(temp_dir, request)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Unsupported template scope", completed.stderr)

    def test_save_action_rejects_unsafe_template_id(self):
        request = {
            "version": "resume-template-store-cli/v1",
            "action": "save",
            "scope": "user",
            "manifest": make_manifest("../escape"),
            "assets": {
                "markdown": "# {{basic.name}}",
                "html": "<h1>{{basic.name}}</h1>",
                "css": "body { color: #222; }",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = self.run_store_cli(temp_dir, request)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Unsafe templateId", completed.stderr)

    def test_save_action_overwrites_existing_package_for_same_template_id(self):
        first_request = {
            "version": "resume-template-store-cli/v1",
            "action": "save",
            "scope": "user",
            "manifest": make_manifest(),
            "assets": {
                "markdown": "# First version",
                "html": "<h1>First version</h1>",
                "css": "body { color: #111; }",
            },
        }
        second_request = {
            "version": "resume-template-store-cli/v1",
            "action": "save",
            "scope": "user",
            "manifest": make_manifest(),
            "assets": {
                "markdown": "# Second version",
                "html": "<h1>Second version</h1>",
                "css": "body { color: #222; }",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            first_completed = self.run_store_cli(temp_dir, first_request)
            self.assertEqual(first_completed.returncode, 0, first_completed.stderr)
            second_completed = self.run_store_cli(temp_dir, second_request)
            self.assertEqual(second_completed.returncode, 0, second_completed.stderr)

            manifest_path = Path(json.loads(second_completed.stdout)["manifest_path"])
            self.assertEqual((manifest_path.parent / "template.md").read_text(encoding="utf-8"), "# Second version")
            self.assertEqual((manifest_path.parent / "template.html").read_text(encoding="utf-8"), "<h1>Second version</h1>")
            self.assertEqual((manifest_path.parent / "style.css").read_text(encoding="utf-8"), "body { color: #222; }")

    def test_save_preserves_existing_live_directory_when_install_fails(self):
        store = TemplateStore(Path(self.enterContext(tempfile.TemporaryDirectory())))
        store.save(
            scope="user",
            manifest=make_manifest(),
            markdown="# First version",
            html="<h1>First version</h1>",
            css="body { color: #111; }",
        )

        live_dir = store.root / "user" / "custom-typora"
        original_files = {
            path.name: path.read_text(encoding="utf-8")
            for path in live_dir.iterdir()
            if path.is_file()
        }
        original_manifest = json.loads((live_dir / "manifest.json").read_text(encoding="utf-8"))

        real_move = shutil.move

        def fail_install_once(src: str, dst: str, *args, **kwargs):
            src_path = Path(src)
            if Path(dst) == live_dir and src_path.name == live_dir.name:
                raise RuntimeError("install failed")
            return real_move(src, dst, *args, **kwargs)

        with patch("resume_runtime.runtime.template_store.shutil.move", side_effect=fail_install_once):
            with self.assertRaisesRegex(RuntimeError, "install failed"):
                store.save(
                    scope="user",
                    manifest=make_manifest(),
                    markdown="# Second version",
                    html="<h1>Second version</h1>",
                    css="body { color: #222; }",
                )

        self.assertTrue(live_dir.is_dir())
        self.assertEqual(
            {
                path.name: path.read_text(encoding="utf-8")
                for path in live_dir.iterdir()
                if path.is_file()
            },
            original_files,
        )
        self.assertEqual(
            json.loads((live_dir / "manifest.json").read_text(encoding="utf-8")),
            original_manifest,
        )

    def test_promote_action_moves_template_to_candidate_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_request = {
                "version": "resume-template-store-cli/v1",
                "action": "save",
                "scope": "user",
                "manifest": make_manifest(),
                "assets": {
                    "markdown": "# {{basic.name}}",
                    "html": "<h1>{{basic.name}}</h1>",
                    "css": "body { color: #222; }",
                },
            }
            save_completed = self.run_store_cli(temp_dir, save_request)
            self.assertEqual(save_completed.returncode, 0, save_completed.stderr)

            promote_request = {
                "version": "resume-template-store-cli/v1",
                "action": "promote",
                "template_id": "custom-typora",
            }
            completed = self.run_store_cli(temp_dir, promote_request)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            promoted_manifest_path = Path(payload["manifest_path"])
            promoted_manifest = json.loads(promoted_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted_manifest["storageScope"], "candidate")
            self.assertFalse((Path(temp_dir) / "user" / "custom-typora").exists())
            self.assertTrue((Path(temp_dir) / "candidate" / "custom-typora").exists())

    def test_promote_action_replaces_existing_candidate_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            user_save = {
                "version": "resume-template-store-cli/v1",
                "action": "save",
                "scope": "user",
                "manifest": make_manifest(),
                "assets": {
                    "markdown": "# User version",
                    "html": "<h1>User version</h1>",
                    "css": "body { color: #333; }",
                },
            }
            candidate_save = {
                "version": "resume-template-store-cli/v1",
                "action": "save",
                "scope": "candidate",
                "manifest": make_manifest(),
                "assets": {
                    "markdown": "# Older candidate version",
                    "html": "<h1>Older candidate version</h1>",
                    "css": "body { color: #111; }",
                },
            }
            self.assertEqual(self.run_store_cli(temp_dir, user_save).returncode, 0)
            self.assertEqual(self.run_store_cli(temp_dir, candidate_save).returncode, 0)

            promote_request = {
                "version": "resume-template-store-cli/v1",
                "action": "promote",
                "template_id": "custom-typora",
            }
            completed = self.run_store_cli(temp_dir, promote_request)
            self.assertEqual(completed.returncode, 0, completed.stderr)

            candidate_dir = Path(temp_dir) / "candidate" / "custom-typora"
            self.assertEqual((candidate_dir / "template.md").read_text(encoding="utf-8"), "# User version")
            self.assertEqual((candidate_dir / "template.html").read_text(encoding="utf-8"), "<h1>User version</h1>")
            self.assertEqual((candidate_dir / "style.css").read_text(encoding="utf-8"), "body { color: #333; }")
            self.assertFalse((Path(temp_dir) / "user" / "custom-typora").exists())

    def test_promote_preserves_candidate_and_user_package_when_install_fails(self):
        store = TemplateStore(Path(self.enterContext(tempfile.TemporaryDirectory())))
        store.save(
            scope="user",
            manifest=make_manifest(),
            markdown="# User version",
            html="<h1>User version</h1>",
            css="body { color: #333; }",
        )
        store.save(
            scope="candidate",
            manifest=make_manifest(),
            markdown="# Older candidate version",
            html="<h1>Older candidate version</h1>",
            css="body { color: #111; }",
        )

        candidate_dir = store.root / "candidate" / "custom-typora"
        user_dir = store.root / "user" / "custom-typora"
        original_candidate_files = {
            path.name: path.read_text(encoding="utf-8")
            for path in candidate_dir.iterdir()
            if path.is_file()
        }
        original_user_files = {
            path.name: path.read_text(encoding="utf-8")
            for path in user_dir.iterdir()
            if path.is_file()
        }

        real_move = shutil.move

        def fail_install_once(src: str, dst: str, *args, **kwargs):
            src_path = Path(src)
            if Path(dst) == candidate_dir and src_path.name == candidate_dir.name:
                raise RuntimeError("install failed")
            return real_move(src, dst, *args, **kwargs)

        with patch("resume_runtime.runtime.template_store.shutil.move", side_effect=fail_install_once):
            with self.assertRaisesRegex(RuntimeError, "install failed"):
                store.promote("custom-typora")

        self.assertTrue(candidate_dir.is_dir())
        self.assertTrue(user_dir.is_dir())
        self.assertEqual(
            {
                path.name: path.read_text(encoding="utf-8")
                for path in candidate_dir.iterdir()
                if path.is_file()
            },
            original_candidate_files,
        )
        self.assertEqual(
            {
                path.name: path.read_text(encoding="utf-8")
                for path in user_dir.iterdir()
                if path.is_file()
            },
            original_user_files,
        )
