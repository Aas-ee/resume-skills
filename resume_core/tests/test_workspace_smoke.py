import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResumeCoreWorkspaceSmokeTests(unittest.TestCase):
    def test_expected_workspace_structure_exists(self):
        required_directories = [
            ROOT / "schema",
            ROOT / "examples" / "templates",
            ROOT / "examples" / "template-assets" / "typora-classic",
            ROOT / "examples" / "template-assets" / "markdown-basic",
            ROOT / "examples" / "source-documents",
            ROOT / "examples" / "source-extractions",
            ROOT / "examples" / "resume-profiles",
            ROOT / "examples" / "gap-reports",
            ROOT / "examples" / "intake-sessions",
            ROOT / "examples" / "guided-intake-checklists",
            ROOT / "examples" / "guided-intake-question-sets",
            ROOT / "examples" / "guided-intake-response-sets",
            ROOT / "examples" / "guided-intake-profile-projections",
            ROOT / "examples" / "follow-up-question-sets",
            ROOT / "examples" / "follow-up-response-sets",
            ROOT / "examples" / "follow-up-profile-projections",
            ROOT / "scripts",
            ROOT / "tests",
        ]
        required_files = [
            ROOT / "requirements-dev.txt",
        ]

        missing_directories = [
            str(path.relative_to(ROOT)) for path in required_directories if not path.is_dir()
        ]
        missing_files = [
            str(path.relative_to(ROOT)) for path in required_files if not path.is_file()
        ]

        self.assertEqual(missing_directories, [])
        self.assertEqual(missing_files, [])
