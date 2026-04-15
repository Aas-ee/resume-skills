import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "template-layer.schema.json"
EXAMPLES = ROOT / "examples"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(def_name: str):
    schema = load_json(SCHEMA_PATH)
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{def_name}",
        }
    )


class ResumeCoreTemplateLayerTests(unittest.TestCase):
    ORIGIN_TO_SOURCE = {
        "builtin": "builtin",
        "user-promoted": "user",
        "imported": "imported",
    }

    @classmethod
    def setUpClass(cls):
        cls.catalog = load_json(EXAMPLES / "shared-field-catalog.v1.json")
        cls.registry = load_json(EXAMPLES / "template-registry.v1.json")
        cls.manifest_paths = sorted((EXAMPLES / "templates").glob("*.json"))
        cls.manifests = [load_json(path) for path in cls.manifest_paths]
        cls.catalog_validator = validator_for("SharedFieldCatalog")
        cls.manifest_validator = validator_for("TemplateManifest")
        cls.registry_validator = validator_for("TemplateRegistry")
        cls.catalog_fields = {item["fieldId"] for item in cls.catalog["fields"]}

    def test_shared_field_catalog_example_is_valid(self):
        self.catalog_validator.validate(self.catalog)

    def test_template_manifest_examples_are_valid(self):
        for manifest in self.manifests:
            with self.subTest(templateId=manifest["templateId"]):
                self.manifest_validator.validate(manifest)

    def test_template_registry_example_is_valid(self):
        self.registry_validator.validate(self.registry)

    def test_registry_declares_default_template_id(self):
        entry_template_ids = {entry["templateId"] for entry in self.registry["entries"]}
        self.assertIn("defaultTemplateId", self.registry)
        self.assertIn(self.registry["defaultTemplateId"], entry_template_ids)

    def test_all_manifest_fields_exist_in_catalog(self):
        for manifest in self.manifests:
            for requirement in manifest["fieldRequirements"]:
                with self.subTest(templateId=manifest["templateId"], fieldId=requirement["fieldId"]):
                    self.assertIn(requirement["fieldId"], self.catalog_fields)

    def test_registry_entries_match_manifest_versions(self):
        manifest_index = {(manifest["templateId"], manifest["version"]) for manifest in self.manifests}
        registry_index = {(entry["templateId"], entry["version"]) for entry in self.registry["entries"]}
        self.assertEqual(registry_index, manifest_index)

    def test_registry_source_matches_manifest_origin_mapping(self):
        registry_sources = {
            (entry["templateId"], entry["version"]): entry["source"] for entry in self.registry["entries"]
        }
        for manifest in self.manifests:
            manifest_key = (manifest["templateId"], manifest["version"])
            with self.subTest(templateId=manifest["templateId"], version=manifest["version"]):
                self.assertIn(manifest["origin"], self.ORIGIN_TO_SOURCE)
                self.assertEqual(registry_sources[manifest_key], self.ORIGIN_TO_SOURCE[manifest["origin"]])
