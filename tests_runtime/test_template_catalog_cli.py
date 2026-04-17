import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from resume_runtime.runtime.template_catalog import TemplateCard, load_template_catalog

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "resume_core" / "examples"
CATALOG_CLI = ROOT / "resume_runtime" / "template_catalog_cli.py"


def make_stored_manifest(
    *,
    template_id: str = "stored-template",
    version: str = "1.0.0",
    storage_scope: str = "user",
) -> dict:
    return {
        "templateId": template_id,
        "version": version,
        "target": "markdown",
        "storageScope": storage_scope,
        "previewCard": {
            "title": "Stored Template",
            "styleLabel": "Clean",
            "useCases": ["general"],
            "requiredContentSummary": ["basic info"],
        },
        "fieldRequirements": [
            {
                "fieldId": "basic.name",
                "required": True,
                "repeatable": False,
                "order": 10,
                "promptHint": "Candidate name",
            }
        ],
    }


class TemplateCatalogTests(unittest.TestCase):
    def test_load_template_catalog_returns_cards_and_template_context(self):
        entries = load_template_catalog(
            examples_root=EXAMPLES,
            generated_at="2026-04-16T12:00:00Z",
        )

        self.assertEqual(
            [entry.templateId for entry in entries],
            ["typora-classic", "markdown-basic"],
        )
        self.assertIsInstance(entries[0].card, TemplateCard)
        self.assertEqual(entries[0].card.title, "Typora Classic Resume")
        self.assertEqual(entries[0].checklist["requiredFields"][0], "basic.name")

    def test_load_template_catalog_discovers_expected_stored_template_manifest_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_root = Path(temp_dir)
            manifests_by_path = {
                store_root / "user" / "alpha" / "manifest.json": make_stored_manifest(
                    template_id="stored-template-alpha",
                    version="1.0.0",
                    storage_scope="user",
                ),
                store_root / "candidate" / "beta" / "manifest.json": make_stored_manifest(
                    template_id="stored-template-beta",
                    version="2.0.0",
                    storage_scope="candidate",
                ),
                store_root / "team" / "gamma" / "manifest.json": make_stored_manifest(
                    template_id="ignored-team-template",
                ),
                store_root / "user" / "nested" / "deeper" / "manifest.json": make_stored_manifest(
                    template_id="ignored-nested-template",
                ),
            }
            discovered_paths = list(manifests_by_path.keys())[:2]

            for path, manifest in manifests_by_path.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(manifest), encoding="utf-8")

            entries = load_template_catalog(
                examples_root=EXAMPLES,
                generated_at="2026-04-16T12:00:00Z",
                template_store_root=store_root,
            )

        stored_entries = [
            entry for entry in entries if entry.templateId in {"stored-template-alpha", "stored-template-beta"}
        ]
        self.assertEqual(
            [entry.manifestPath for entry in stored_entries],
            discovered_paths,
        )

    def test_load_template_catalog_rejects_duplicate_template_id_and_version_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store_root = Path(temp_dir)
            duplicate_manifest = make_stored_manifest(
                template_id="typora-classic",
                version="1.0.0",
            )
            duplicate_path = store_root / "user" / "typora-classic" / "manifest.json"
            duplicate_path.parent.mkdir(parents=True, exist_ok=True)
            duplicate_path.write_text(json.dumps(duplicate_manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate template catalog entry"):
                load_template_catalog(
                    examples_root=EXAMPLES,
                    generated_at="2026-04-16T12:00:00Z",
                    template_store_root=store_root,
                )

    def test_load_template_catalog_rejects_duplicate_example_manifest_keys_before_registry_loading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            examples_root = Path(temp_dir)
            templates_dir = examples_root / "templates"
            templates_dir.mkdir(parents=True, exist_ok=True)

            duplicate_manifest = make_stored_manifest(
                template_id="duplicate-example",
                version="1.0.0",
                storage_scope="builtin",
            )
            for name in ("duplicate-a.json", "duplicate-b.json"):
                (templates_dir / name).write_text(json.dumps(duplicate_manifest), encoding="utf-8")

            registry = {
                "entries": [
                    {
                        "templateId": "duplicate-example",
                        "version": "1.0.0",
                    }
                ]
            }
            (examples_root / "template-registry.v1.json").write_text(
                json.dumps(registry),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Duplicate example template manifest"):
                load_template_catalog(
                    examples_root=examples_root,
                    generated_at="2026-04-16T12:00:00Z",
                )

    def test_template_catalog_cli_lists_cards_and_template_context(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(CATALOG_CLI),
                "--examples-root",
                str(EXAMPLES),
                "--generated-at",
                "2026-04-16T12:00:00Z",
            ],
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "resume-template-catalog-cli/v1")
        self.assertEqual(payload["entries"][0]["card"]["template_id"], "typora-classic")
        self.assertIn("manifest", payload["entries"][0]["template_context"])
        self.assertIn("checklist", payload["entries"][0]["template_context"])
