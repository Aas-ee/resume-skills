import json
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "intake-layer.schema.json"
EXAMPLES = ROOT / "examples"
REGISTRY_PATH = EXAMPLES / "template-registry.v1.json"
SOURCE_DOCUMENTS_DIR = EXAMPLES / "source-documents"
SESSIONS_DIR = EXAMPLES / "intake-sessions"


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


class ResumeCoreIntakeLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_json(REGISTRY_PATH)
        cls.registry_index = {
            (entry["templateId"], entry["version"])
            for entry in cls.registry["entries"]
        }
        cls.documents = [
            load_json(path) for path in sorted(SOURCE_DOCUMENTS_DIR.glob("*.json"))
        ]
        cls.document_ids = {item["documentId"] for item in cls.documents}
        cls.sessions = [
            load_json(path) for path in sorted(SESSIONS_DIR.glob("*.json"))
        ]
        cls.session_validator = validator_for("IntakeSession")

    def test_intake_session_examples_are_valid(self):
        for session in self.sessions:
            with self.subTest(sessionId=session["sessionId"]):
                self.session_validator.validate(session)

    def test_session_template_references_exist_in_registry(self):
        for session in self.sessions:
            session_key = (session["templateId"], session["templateVersion"])
            with self.subTest(sessionId=session["sessionId"]):
                self.assertIn(session_key, self.registry_index)

    def test_session_document_ids_reference_known_source_documents(self):
        for session in self.sessions:
            for document_id in session["documentIds"]:
                with self.subTest(
                    sessionId=session["sessionId"], documentId=document_id
                ):
                    self.assertIn(document_id, self.document_ids)

    def test_import_existing_example_is_handed_off_with_documents(self):
        import_session = next(
            session
            for session in self.sessions
            if session["sessionId"] == "intake-typora-import-existing"
        )
        self.assertEqual(import_session["route"], "import-existing")
        self.assertTrue(import_session["hasExistingMaterial"])
        self.assertGreaterEqual(len(import_session["documentIds"]), 1)
        self.assertEqual(import_session["phase"], "handed-off")

    def test_guided_intake_can_start_without_existing_material(self):
        guided_session = next(
            session
            for session in self.sessions
            if session["sessionId"] == "intake-typora-guided-empty"
        )
        self.assertEqual(guided_session["route"], "guided-intake")
        self.assertFalse(guided_session["hasExistingMaterial"])
        self.assertEqual(guided_session["documentIds"], [])

    def test_guided_intake_can_override_existing_material(self):
        override_session = next(
            session
            for session in self.sessions
            if session["sessionId"] == "intake-markdown-manual-override"
        )
        self.assertEqual(override_session["route"], "guided-intake")
        self.assertTrue(override_session["hasExistingMaterial"])
        self.assertGreaterEqual(len(override_session["documentIds"]), 1)

    def test_handed_off_session_requires_decided_route(self):
        invalid_session = deepcopy(self.sessions[0])
        invalid_session["route"] = "undecided"
        with self.assertRaises(ValidationError):
            self.session_validator.validate(invalid_session)

    def test_session_without_existing_material_cannot_reference_documents(self):
        invalid_session = deepcopy(self.sessions[1])
        invalid_session["documentIds"] = ["source-existing-resume-md"]
        with self.assertRaises(ValidationError):
            self.session_validator.validate(invalid_session)

    def test_completed_session_must_be_handed_off(self):
        invalid_session = deepcopy(self.sessions[0])
        invalid_session["phase"] = "routing"
        with self.assertRaises(ValidationError):
            self.session_validator.validate(invalid_session)

    def test_examples_do_not_include_host_specific_fields(self):
        disallowed_keys = {"promptBuffer", "toolState", "uiState", "memoryRef"}
        for session in self.sessions:
            with self.subTest(sessionId=session["sessionId"]):
                self.assertTrue(disallowed_keys.isdisjoint(session.keys()))
