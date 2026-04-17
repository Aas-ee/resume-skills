import json
import re
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


def load_typora_entry():
    return next(
        entry
        for entry in load_template_catalog(
            examples_root=EXAMPLES,
            generated_at="2026-04-16T12:00:00Z",
        )
        if entry.templateId == "typora-classic"
    )


class TemplateRendererTests(unittest.TestCase):
    def test_render_template_bundle_renders_builtin_assets_without_placeholders(self):
        entry = load_typora_entry()
        profile = load_json(PROFILE_PATH)

        bundle = render_template_bundle(
            manifest=entry.manifest,
            manifest_path=entry.manifestPath,
            profile=profile,
        )

        self.assertNotIn("{{", bundle["markdown"])
        self.assertNotIn("}}", bundle["markdown"])
        self.assertNotIn("{{", bundle["html"])
        self.assertNotIn("}}", bundle["html"])
        self.assertIn('<div class="resume-page">', bundle["markdown"])
        self.assertIn('<table class="resume-header">', bundle["markdown"])
        self.assertIn("Software Engineer", bundle["markdown"])
        self.assertIn("Engineering: Python / TypeScript / CLI tooling", bundle["markdown"])
        self.assertIn("## 个人总结", bundle["markdown"])
        self.assertIn("## 专业技能", bundle["markdown"])
        self.assertIn("## 项目经历", bundle["markdown"])
        self.assertIn("邮箱", bundle["markdown"])
        self.assertIn('<table class="entry-table work-table">', bundle["markdown"])
        self.assertIn("Example Labs", bundle["markdown"])
        self.assertIn('<table class="entry-table project-table">', bundle["markdown"])
        self.assertIn("Example Stream", bundle["markdown"])
        self.assertIn("TypeScript, Node.js, Express, CLI, Automation", bundle["markdown"])
        self.assertIn('<table class="resume-header">', bundle["html"])
        self.assertIn('<table class="entry-table project-table">', bundle["html"])
        self.assertIn("<!DOCTYPE html>", bundle["html"])
        self.assertIn("<style>", bundle["html"])
        self.assertIn(bundle["css"].strip().splitlines()[0], bundle["html"])
        self.assertIn("个人总结", bundle["html"])
        self.assertIn("教育经历", bundle["html"])
        self.assertIn("font-family", bundle["css"])

    def test_typora_markdown_does_not_insert_blank_lines_inside_header_table(self):
        entry = load_typora_entry()
        profile = load_json(PROFILE_PATH)

        bundle = render_template_bundle(
            manifest=entry.manifest,
            manifest_path=entry.manifestPath,
            profile=profile,
        )

        header_table_match = re.search(
            r'<table class="resume-header">(.*?)</table>',
            bundle["markdown"],
            re.DOTALL,
        )
        self.assertIsNotNone(header_table_match)
        header_table = header_table_match.group(1)
        self.assertNotRegex(header_table, r"</tr>\s*\n\s*\n\s*<tr")

    def test_typora_markdown_does_not_insert_blank_lines_inside_project_table(self):
        entry = load_typora_entry()
        profile = load_json(PROFILE_PATH)

        bundle = render_template_bundle(
            manifest=entry.manifest,
            manifest_path=entry.manifestPath,
            profile=profile,
        )

        project_table_match = re.search(
            r'<table class="entry-table project-table">(.*?)</table>',
            bundle["markdown"],
            re.DOTALL,
        )
        self.assertIsNotNone(project_table_match)
        project_table = project_table_match.group(1)
        self.assertNotRegex(project_table, r"</tr>\s*\n\s*\n\s*<tr")

    def test_build_template_context_groups_expanded_profile_fields(self):
        profile = load_json(PROFILE_PATH)

        context = build_template_context(profile)

        self.assertEqual(context["basic.name"], "Alex Example")
        self.assertEqual(context["basic.nameEn"], "Alex Example")
        self.assertEqual(context["basic.phone"], "+1 555-0100")
        self.assertEqual(context["basic.email"], "alex@example.com")
        self.assertEqual(context["required.role"], "Software Engineer")
        self.assertEqual(
            context["skills.items"],
            [
                "Engineering: Python / TypeScript / CLI tooling",
                "Platforms: Resume workflows / template packaging / render pipelines",
            ],
        )
        self.assertEqual(len(context["work"]), 1)
        self.assertEqual(context["work"][0]["date"], "2024.01 - Present")
        self.assertEqual(context["work"][0]["company"], "Example Labs")
        self.assertEqual(context["work"][0]["role"], "Software Engineer")
        self.assertEqual(
            context["work"][0]["bullets"],
            [
                "Built shared runtime flows for multiple hosts.",
                "Improved validation coverage for synthetic public fixtures.",
            ],
        )
        self.assertEqual(len(context["education"]), 1)
        self.assertEqual(context["education"][0]["date"], "2018.09 - 2022.06")
        self.assertEqual(context["education"][0]["school"], "Example University")
        self.assertEqual(len(context["project"]), 1)
        self.assertEqual(context["project"][0]["date"], "2025.01 - Present")
        self.assertEqual(context["project"][0]["name"], "Example Stream")
        self.assertEqual(context["project"][0]["role"], "Open Source Maintainer")
        self.assertEqual(
            context["project"][0]["techStack"],
            ["TypeScript", "Node.js", "Express", "CLI", "Automation"],
        )

    def test_build_template_context_omits_empty_optional_sections(self):
        profile = {
            "profileId": "minimal-profile",
            "fieldValues": {
                "basic.name": "Alex Example",
                "basic.nameEn": "Alex Example",
                "basic.phone": "+1 555-0100",
                "required.role": "Software Engineer",
                "links.github": "https://github.com/alex-example",
            },
        }

        context = build_template_context(profile)

        self.assertEqual(context["basic.email"], "")
        self.assertEqual(context["summary.items"], [])
        self.assertEqual(context["skills.items"], [])
        self.assertEqual(context["work"], [])
        self.assertEqual(context["education"], [])
        self.assertEqual(context["project"], [])

    def test_typora_classic_manifest_and_assets_match_profession_neutral_table_layout(self):
        entry = load_typora_entry()

        self.assertEqual(entry.templateId, "typora-classic")
        self.assertEqual(entry.manifest["target"], "typora")
        self.assertEqual(
            entry.manifest["sectionOrder"],
            ["header", "summary", "skills", "work", "projects", "education"],
        )

        markdown_template = entry.manifestPath.parent.joinpath(entry.manifest["assetRefs"]["markdown"]).resolve().read_text(encoding="utf-8")
        html_template = entry.manifestPath.parent.joinpath(entry.manifest["assetRefs"]["html"]).resolve().read_text(encoding="utf-8")
        css_text = entry.manifestPath.parent.joinpath(entry.manifest["assetRefs"]["css"]).resolve().read_text(encoding="utf-8")

        self.assertIn('<table class="resume-header">', markdown_template)
        self.assertIn('{{basic.nameEn}}', markdown_template)
        self.assertIn('{{required.role}}', markdown_template)
        self.assertIn('{{#skills.items}}', markdown_template)
        self.assertIn('{{#work}}', markdown_template)
        self.assertIn('{{date}}', markdown_template)
        self.assertIn('{{#project}}', markdown_template)
        self.assertIn('## 个人总结', markdown_template)
        self.assertIn('求职方向', markdown_template)
        self.assertIn('class="entry-table project-table"', html_template)
        self.assertIn('个人总结', html_template)
        self.assertIn('技术栈：', html_template)
        self.assertIn('--accent', css_text)
        self.assertIn('.entry-table .date', css_text)

    def test_render_template_bundle_raises_for_inconsistent_repeatable_field_lengths(self):
        entry = load_typora_entry()
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
        entry = load_typora_entry()
        profile = load_json(PROFILE_PATH)
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
            html_text = (Path(temp_dir) / "resume.html").read_text(encoding="utf-8")
            self.assertIn("<style>", html_text)
