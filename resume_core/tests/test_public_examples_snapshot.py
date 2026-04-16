import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
EXAMPLES = ROOT / "examples"


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class PublicExamplesSnapshotTests(unittest.TestCase):
    def assert_relative_paths_exist(self, relative_paths: list[str]) -> None:
        missing = [path for path in relative_paths if not (ROOT / path).exists()]
        self.assertEqual(missing, [])

    def test_examples_index_exists_and_names_baseline_templates(self):
        path = EXAMPLES / "README.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("synthetic", text.lower())
        self.assertIn("typora-classic", text)
        self.assertIn("markdown-basic", text)

    def test_root_source_material_chain_is_synthetic(self):
        document = load_json("examples/source-documents/existing-resume-markdown.v1.json")
        self.assertEqual(document["sourceRef"], "public://examples/existing-resume.md")
        self.assertEqual(document["metadata"]["title"], "Synthetic existing resume draft")
        self.assertEqual(document["metadata"]["language"], "en")
        self.assertIn("Alex Example", document["rawText"])
        self.assertIn("alex@example.com", document["rawText"])
        self.assertIn("https://github.com/alex-example", document["rawText"])
        self.assertIn("Example Stream", document["rawText"])

        profile = load_json("examples/resume-profiles/sample-ai-agent-profile.v1.json")
        self.assertEqual(profile["fieldValues"]["basic.name"], "Alex Example")
        self.assertEqual(
            profile["fieldValues"]["links.github"],
            "https://github.com/alex-example",
        )
        self.assertEqual(profile["fieldValues"]["project[].name"], ["Example Stream"])
        self.assertEqual(
            profile["fieldValues"]["project[].role"],
            ["Open Source Maintainer"],
        )
        self.assertEqual(
            profile["fieldValues"]["project[].techStack"],
            [["TypeScript", "Node.js", "Express", "CLI", "Automation"]],
        )

    def test_source_extractions_match_synthetic_source_document(self):
        expected_fragments = {
            "examples/source-extractions/extract-basic-name.v1.json": "# Alex Example",
            "examples/source-extractions/extract-github-link.v1.json": "GitHub: https://github.com/alex-example",
            "examples/source-extractions/extract-project-name.v1.json": "Example Stream",
            "examples/source-extractions/extract-project-role.v1.json": "Open Source Maintainer",
            "examples/source-extractions/extract-project-tech-stack.v1.json": "TypeScript / Node.js / Express / CLI / Automation",
        }
        for relative_path, expected_fragment in expected_fragments.items():
            extraction = load_json(relative_path)
            self.assertEqual(extraction["documentId"], "source-existing-resume-md")
            self.assertEqual(extraction["fragmentText"], expected_fragment)

    def test_typora_baseline_fixture_chain_exists(self):
        self.assert_relative_paths_exist(
            [
                "examples/templates/typora-classic.v1.json",
                "examples/template-assets/typora-classic/template.md",
                "examples/template-assets/typora-classic/template.html",
                "examples/template-assets/typora-classic/style.css",
                "examples/intake-sessions/typora-import-existing.v1.json",
                "examples/intake-sessions/typora-guided-empty.v1.json",
                "examples/guided-intake-checklists/typora-classic.v1.json",
                "examples/guided-intake-question-sets/typora-classic.v1.json",
                "examples/guided-intake-response-sets/typora-classic.partial.v1.json",
                "examples/guided-intake-profile-projections/typora-classic.partial.v1.json",
                "examples/gap-reports/typora-classic-gap.v1.json",
                "examples/follow-up-question-sets/typora-classic.v1.json",
                "examples/follow-up-response-sets/typora-classic.partial.v1.json",
                "examples/follow-up-profile-projections/typora-classic.partial.v1.json",
                "examples/gap-reports/typora-classic-follow-up-gap.v1.json",
            ]
        )

    def test_typora_partial_fixtures_use_synthetic_values(self):
        guided_response = load_json(
            "examples/guided-intake-response-sets/typora-classic.partial.v1.json"
        )
        guided_projection = load_json(
            "examples/guided-intake-profile-projections/typora-classic.partial.v1.json"
        )
        follow_up_response = load_json(
            "examples/follow-up-response-sets/typora-classic.partial.v1.json"
        )
        follow_up_projection = load_json(
            "examples/follow-up-profile-projections/typora-classic.partial.v1.json"
        )

        self.assertEqual(guided_response["responses"]["basic.email"], "alex@example.com")
        self.assertEqual(
            guided_response["responses"]["summary.items"],
            [
                "Backend engineer focused on developer tools and structured content pipelines.",
                "Maintains synthetic public fixtures that explain the resume workflow end to end.",
            ],
        )
        self.assertEqual(
            guided_projection["profile"]["fieldValues"]["basic.email"],
            "alex@example.com",
        )
        self.assertEqual(follow_up_response["responses"]["basic.name"], "Alex Example")
        self.assertEqual(
            follow_up_projection["profile"]["fieldValues"]["basic.name"],
            "Alex Example",
        )
        self.assertEqual(
            follow_up_projection["profile"]["fieldValues"]["project[].techStack"],
            "Java, Spring Boot, MySQL, Redis",
        )

    def test_markdown_baseline_fixture_chain_exists(self):
        self.assert_relative_paths_exist(
            [
                "examples/templates/markdown-basic.v1.json",
                "examples/template-assets/markdown-basic/template.md",
                "examples/template-assets/markdown-basic/template.html",
                "examples/template-assets/markdown-basic/style.css",
                "examples/intake-sessions/markdown-manual-override.v1.json",
                "examples/guided-intake-checklists/markdown-basic.v1.json",
                "examples/guided-intake-question-sets/markdown-basic.v1.json",
                "examples/guided-intake-response-sets/markdown-basic.partial.v1.json",
                "examples/guided-intake-profile-projections/markdown-basic.partial.v1.json",
                "examples/gap-reports/markdown-basic-gap.v1.json",
                "examples/follow-up-question-sets/markdown-basic.v1.json",
                "examples/follow-up-response-sets/markdown-basic.partial.v1.json",
                "examples/follow-up-profile-projections/markdown-basic.partial.v1.json",
                "examples/gap-reports/markdown-basic-follow-up-gap.v1.json",
            ]
        )

    def test_markdown_partial_fixtures_use_synthetic_values(self):
        guided_response = load_json(
            "examples/guided-intake-response-sets/markdown-basic.partial.v1.json"
        )
        guided_projection = load_json(
            "examples/guided-intake-profile-projections/markdown-basic.partial.v1.json"
        )
        follow_up_response = load_json(
            "examples/follow-up-response-sets/markdown-basic.partial.v1.json"
        )
        follow_up_projection = load_json(
            "examples/follow-up-profile-projections/markdown-basic.partial.v1.json"
        )

        self.assertEqual(guided_response["responses"]["basic.name"], "Alex Example")
        self.assertEqual(guided_response["responses"]["basic.email"], "alex@example.com")
        self.assertEqual(
            guided_projection["profile"]["fieldValues"]["basic.name"],
            "Alex Example",
        )
        self.assertEqual(
            follow_up_response["responses"]["links.github"],
            "https://github.com/alex-example",
        )
        self.assertEqual(
            follow_up_projection["profile"]["fieldValues"]["education[].school"],
            "Example University",
        )
        self.assertEqual(
            follow_up_projection["profile"]["fieldValues"]["project[].role"],
            "Backend Engineer",
        )

    def test_top_level_readmes_point_to_public_examples_index(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_zh = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        self.assertIn("resume_core/examples/README.md", readme)
        self.assertIn("synthetic public examples", readme.lower())
        self.assertIn("resume_core/examples/README.md", readme_zh)
        self.assertIn("纯虚构", readme_zh)
