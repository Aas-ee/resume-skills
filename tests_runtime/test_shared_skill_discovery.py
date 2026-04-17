import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED_SKILL = ROOT / "skills" / "resume" / "SKILL.md"
SHARED_SKILL_DIR = ROOT / "skills" / "resume"
SHARED_TEMPLATE_CATALOG_CLI = SHARED_SKILL_DIR / "template_catalog_cli.py"
CLAUDE_SKILL = ROOT / ".claude" / "skills" / "resume" / "SKILL.md"
SKILLS_INDEX = ROOT / "skills" / "README.md"


class SharedSkillDiscoveryTests(unittest.TestCase):
    def test_shared_skill_exists_and_is_indexed(self):
        self.assertTrue(SHARED_SKILL.is_file())
        self.assertTrue((SHARED_SKILL_DIR / "template_catalog_cli.py").is_file())
        self.assertTrue((SHARED_SKILL_DIR / "template_store_cli.py").is_file())
        self.assertTrue((SHARED_SKILL_DIR / "agent_intake_cli.py").is_file())
        self.assertTrue((SHARED_SKILL_DIR / "host_cli.py").is_file())
        self.assertTrue((SHARED_SKILL_DIR / "render_cli.py").is_file())
        self.assertTrue((SHARED_SKILL_DIR / "resume_runtime" / "__init__.py").is_file())
        self.assertTrue((SHARED_SKILL_DIR / "resume_core" / "examples" / "template-registry.v1.json").is_file())
        self.assertTrue(SKILLS_INDEX.is_file())
        index_text = SKILLS_INDEX.read_text(encoding="utf-8")
        self.assertIn("skills/resume/SKILL.md", index_text)

    def test_shared_skill_points_to_public_runtime_entrypoints(self):
        shared_text = SHARED_SKILL.read_text(encoding="utf-8")
        self.assertIn("resume_runtime/template_catalog_cli.py", shared_text)
        self.assertIn("resume_runtime/template_store_cli.py", shared_text)
        self.assertIn("resume_runtime/agent_intake_cli.py", shared_text)
        self.assertIn("resume_runtime/host_cli.py", shared_text)
        self.assertIn("resume_runtime/render_cli.py", shared_text)

    def test_shared_skill_describes_claude_as_adapter_not_primary_contract(self):
        shared_text = SHARED_SKILL.read_text(encoding="utf-8")
        self.assertIn("compatibility adapters", shared_text)
        self.assertIn("not the primary shared contract", shared_text)
        self.assertNotIn("`.claude/skills/resume/SKILL.md`", shared_text)

    def test_shared_skill_points_to_builtin_template_manifests_and_assets(self):
        shared_text = SHARED_SKILL.read_text(encoding="utf-8")
        self.assertIn("resume_core/examples/templates/", shared_text)
        self.assertIn("resume_core/examples/template-assets/", shared_text)
        self.assertIn("typora-classic", shared_text)
        self.assertIn("markdown-basic", shared_text)
        self.assertIn("resume_core/examples/template-assets/typora-classic/style.css", shared_text)
        self.assertIn("resume_core/examples/template-assets/markdown-basic/style.css", shared_text)
        self.assertIn("self-contained", shared_text)
        self.assertIn("/path/to/installed/skill/template_catalog_cli.py", shared_text)

    def test_shared_template_catalog_cli_runs_from_unrelated_cwd(self):
        import json
        import subprocess
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SHARED_TEMPLATE_CATALOG_CLI),
                ],
                cwd=temp_dir,
                text=True,
                capture_output=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertGreater(len(payload["entries"]), 0)
        self.assertIn("asset_paths", payload["entries"][0])

    def test_claude_skill_points_back_to_shared_skill(self):
        claude_text = CLAUDE_SKILL.read_text(encoding="utf-8")
        self.assertIn("skills/resume/SKILL.md", claude_text)
        self.assertIn("adapter layer", claude_text)
        self.assertIn(".claude/skills/resume/template_catalog_cli.py", claude_text)
        self.assertIn("entries[].asset_paths", claude_text)
        self.assertIn("entries[].template_context", claude_text)
        self.assertIn("absolute path", claude_text)


if __name__ == "__main__":
    unittest.main()
