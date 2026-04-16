import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
TEMPLATES_DIR = EXAMPLES / "templates"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ResumeCoreTemplateAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifests = [load_json(path) for path in sorted(TEMPLATES_DIR.glob("*.json"))]

    def test_every_manifest_declares_asset_refs_preview_card_and_storage_scope(self):
        for manifest in self.manifests:
            with self.subTest(templateId=manifest["templateId"]):
                self.assertIn("assetRefs", manifest)
                self.assertIn("previewCard", manifest)
                self.assertIn("storageScope", manifest)

    def test_every_manifest_asset_ref_resolves(self):
        for manifest in self.manifests:
            refs = manifest["assetRefs"]
            for key in ("markdown", "html", "css"):
                with self.subTest(templateId=manifest["templateId"], asset=key):
                    self.assertTrue((TEMPLATES_DIR / refs[key]).resolve().is_file())
