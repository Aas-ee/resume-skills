import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from resume_runtime.runtime.template_catalog import load_template_catalog
from resume_runtime.runtime.template_renderer import (
    build_template_context,
    render_template_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "resume_core" / "examples"
PROFILE_PATH = EXAMPLES / "resume-profiles" / "sample-ai-agent-profile.v1.json"
RENDER_CLI = ROOT / "resume_runtime" / "render_cli.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TemplateRendererTests(unittest.TestCase):
    def test_render_template_bundle_renders_builtin_assets_without_placeholders(self):
        entry = load_template_catalog(
            examples_root=EXAMPLES,
            generated_at="2026-04-16T12:00:00Z",
        )[0]
        profile = load_json(PROFILE_PATH)
        profile["fieldValues"].update(
            {
                "basic.email": "alex@example.com",
                "summary.items": [
                    "Builds agent workflows",
                    "Ships developer tooling",
                ],
                "education[].school": ["Example University"],
                "education[].degree": ["BSc"],
                "education[].major": ["Computer Science"],
                "project[].bullets": [
                    [
                        "Improved runtime reliability",
                        "Published reusable package",
                    ]
                ],
            }
        )

        bundle = render_template_bundle(
            manifest=entry.manifest,
            manifest_path=entry.manifestPath,
            profile=profile,
        )

        self.assertNotIn("{{", bundle["markdown"])
        self.assertNotIn("}}", bundle["markdown"])
        self.assertNotIn("{{", bundle["html"])
        self.assertNotIn("}}", bundle["html"])
        self.assertIn("- Builds agent workflows", bundle["markdown"])
        self.assertIn("<li>Builds agent workflows</li>", bundle["html"])
        self.assertIn("### Example University", bundle["markdown"])
        self.assertIn("BSc · Computer Science", bundle["markdown"])
        self.assertIn("<li>Published reusable package</li>", bundle["html"])
        self.assertIn("font-family", bundle["css"])

    def test_build_template_context_omits_empty_optional_sections(self):
        profile = load_json(PROFILE_PATH)

        context = build_template_context(profile)

        self.assertEqual(context["basic.email"], "")
        self.assertEqual(context["summary.items"], [])
        self.assertEqual(context["education"], [])
        self.assertEqual(len(context["project"]), 1)
        self.assertEqual(context["project"][0]["name"], "Example Stream")
        self.assertEqual(context["project"][0]["role"], "Open Source Maintainer")
        self.assertEqual(
            context["project"][0]["techStack"],
            ["TypeScript", "Node.js", "Express", "CLI", "Automation"],
        )
        self.assertNotIn("bullets", context["project"][0])

    def test_render_template_bundle_raises_for_inconsistent_repeatable_field_lengths(self):
        entry = load_template_catalog(
            examples_root=EXAMPLES,
            generated_at="2026-04-16T12:00:00Z",
        )[0]
        profile = load_json(PROFILE_PATH)
        profile["fieldValues"].update(
            {
                "basic.email": "alex@example.com",
                "education[].school": ["Example University", "Backup University"],
                "education[].degree": ["BSc"],
                "education[].major": ["Computer Science", "Mathematics"],
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "education repeatable fields have inconsistent populated lengths",
        ):
            render_template_bundle(
                manifest=entry.manifest,
                manifest_path=entry.manifestPath,
                profile=profile,
            )

    def test_render_cli_writes_markdown_html_and_css_files(self):
        entry = load_template_catalog(
            examples_root=EXAMPLES,
            generated_at="2026-04-16T12:00:00Z",
        )[0]
        profile = load_json(PROFILE_PATH)
        profile["fieldValues"]["basic.email"] = "alex@example.com"
        request = {
            "version": "resume-render-cli/v1",
            "manifest_path": str(entry.manifestPath),
            "profile": profile,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_CLI),
                    "--output-dir",
                    temp_dir,
                ],
                input=json.dumps(request),
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue((Path(temp_dir) / "resume.md").is_file())
            self.assertTrue((Path(temp_dir) / "resume.html").is_file())
            self.assertTrue((Path(temp_dir) / "style.css").is_file())
