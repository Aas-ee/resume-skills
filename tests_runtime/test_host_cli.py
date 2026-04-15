import json
import subprocess
import sys
import unittest
from pathlib import Path

from resume_runtime.runtime.follow_up_agent_adapter import AskedQuestion
from resume_runtime.runtime.follow_up_state import CurrentProjectionRef, FollowUpLoopHistory, FollowUpLoopState
from resume_runtime.runtime.host_conversation_adapter import HostConversationOutcome
from resume_runtime.runtime.host_session_state import HostSessionState
from resume_runtime.runtime.serialization import host_conversation_outcome_to_dict

ROOT = Path(__file__).resolve().parents[1]
HOST_CLI = ROOT / "resume_runtime" / "host_cli.py"


class HostSerializationTests(unittest.TestCase):
    def test_host_conversation_outcome_to_dict_serializes_batch_and_state(self):
        state = HostSessionState(
            schemaVersion="1",
            sessionId="host-session-1",
            templateManifest={"templateId": "markdown-basic", "version": "1.0.0"},
            intakeSession={
                "sessionId": "host-session-1",
                "templateId": "markdown-basic",
                "templateVersion": "1.0.0",
                "hasExistingMaterial": False,
                "documentIds": [],
                "phase": "handed-off",
                "route": "guided-intake",
                "status": "active",
            },
            currentProjection={
                "projectionId": "projection-1",
                "profile": {"profileId": "profile-1"},
            },
            followUpState=FollowUpLoopState(
                templateId="markdown-basic",
                templateVersion="1.0.0",
                currentProjectionRef=CurrentProjectionRef(
                    projectionKind="guided-intake",
                    projectionId="projection-1",
                    profileId="profile-1",
                ),
                currentGapReportId=None,
                currentFollowUpQuestionSetId=None,
                pendingQuestionBatch=[],
                pendingRoundAnswers={},
                loopPhase="asking_batch",
                continueForRecommended="unset",
                batchSizePolicy=2,
                lastDecisionReason="initialized",
                history=FollowUpLoopHistory([], [], [], []),
            ),
            nextActionKind="ask_batch",
            createdAt="2026-04-15T10:00:00Z",
            updatedAt="2026-04-15T10:00:00Z",
            lastInteractedAt="2026-04-15T10:00:00Z",
        )
        outcome = HostConversationOutcome(
            mode="structured",
            promptDirective="ask_current_batch",
            sessionId="host-session-1",
            sessionState=state,
            nextActionKind="ask_batch",
            currentProjection={"projectionId": "projection-1"},
            currentBatch=[AskedQuestion(fieldId="required.role", question="What role?")],
        )

        payload = host_conversation_outcome_to_dict(outcome)

        self.assertEqual(payload["prompt_directive"], "ask_current_batch")
        self.assertEqual(payload["session_id"], "host-session-1")
        self.assertEqual(payload["current_batch"], [{"field_id": "required.role", "question": "What role?"}])
        self.assertEqual(payload["session_state"]["sessionId"], "host-session-1")


class ResumeRuntimeHostCliTests(unittest.TestCase):
    def test_freeform_turn_stays_freeform(self):
        request = {
            "version": "resume-host-cli/v1",
            "turn": {
                "kind": "reply",
                "timestamp": "2026-04-15T10:00:00Z",
                "user_reply": "just chat normally",
            },
        }
        completed = subprocess.run(
            [sys.executable, str(HOST_CLI)],
            input=json.dumps(request),
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["version"], "resume-host-cli/v1")
        self.assertEqual(payload["mode"], "freeform")
        self.assertEqual(payload["outcome"]["prompt_directive"], "stay_freeform")

    def test_invalid_json_returns_request_error(self):
        completed = subprocess.run(
            [sys.executable, str(HOST_CLI)],
            input="{not-json}",
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["version"], "resume-host-cli/v1")
        self.assertEqual(payload["error"]["code"], "invalid_request_json")
