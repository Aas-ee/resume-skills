from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from resume_runtime.runtime.follow_up_agent_adapter import AskedQuestion, validate_batch_result
from resume_runtime.runtime.host_session_state import HostSessionState, SCHEMA_VERSION
from resume_runtime.runtime.host_session_store import HostSessionStore, HostSessionStoreError
from resume_runtime.runtime.nl_batch_normalizer import normalize_batch_answer, parse_recommended_yes_no
from resume_runtime.runtime.session_runner import SessionRunner, SessionRunnerResult


class HostSessionRunnerError(Exception):
    """Raised when the host-facing session facade cannot continue safely."""


@dataclass(frozen=True)
class HostSessionAction:
    sessionState: HostSessionState
    nextActionKind: str
    currentProjection: dict[str, Any]
    currentBatch: list[AskedQuestion] | None = None


class HostSessionRunner:
    def __init__(self, store: HostSessionStore, session_runner: SessionRunner) -> None:
        self._store = store
        self._session_runner = session_runner

    def start_structured_guided_intake_session(
        self,
        *,
        session_id: str,
        manifest: dict[str, Any],
        checklist: dict[str, Any],
        guided_answers: dict[str, Any],
        timestamp: str,
        intake_session: dict[str, Any] | None = None,
    ) -> HostSessionAction:
        try:
            runner_result = self._session_runner.start_after_guided_intake(
                manifest,
                checklist,
                guided_answers,
            )
            session_state = self._build_host_session_state(
                session_id=session_id,
                manifest=manifest,
                intake_session=intake_session
                or self._default_intake_session(session_id, manifest),
                timestamp=timestamp,
                runner_result=runner_result,
                created_at=timestamp,
            )
            self._save(session_state)
            return self._build_action(session_state, runner_result)
        except HostSessionStoreError as exc:
            raise HostSessionRunnerError(str(exc)) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise HostSessionRunnerError(str(exc)) from exc

    def resume_session(
        self,
        session_id: str,
        *,
        timestamp: str | None = None,
    ) -> HostSessionAction:
        try:
            session_state = self._store.load(session_id)
            if session_state.nextActionKind == "completed":
                raise HostSessionRunnerError("Session is already completed")
            runner_result = self._session_runner.resume(
                manifest=session_state.templateManifest,
                current_projection=session_state.currentProjection,
                follow_up_state=session_state.followUpState,
                gap_report=session_state.gapReport,
                question_set=session_state.questionSet,
                guided_intake_question_set=session_state.guidedIntakeQuestionSet,
                guided_intake_response_set=session_state.guidedIntakeResponseSet,
                guided_intake_projection=session_state.guidedIntakeProjection,
            )
            refreshed_state = self._build_host_session_state(
                session_id=session_state.sessionId,
                manifest=session_state.templateManifest,
                intake_session=session_state.intakeSession,
                timestamp=timestamp or session_state.lastInteractedAt,
                runner_result=runner_result,
                created_at=session_state.createdAt,
            )
            self._save(refreshed_state)
            return self._build_action(refreshed_state, runner_result)
        except HostSessionStoreError as exc:
            raise HostSessionRunnerError(str(exc)) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise HostSessionRunnerError(str(exc)) from exc

    def continue_session(
        self,
        *,
        session_id: str,
        user_reply: str | None,
        timestamp: str,
    ) -> HostSessionAction:
        try:
            persisted_state = self._store.load(session_id)
            if persisted_state.nextActionKind == "completed":
                raise HostSessionRunnerError("Session is already completed")

            session = self._session_runner.resume(
                manifest=persisted_state.templateManifest,
                current_projection=persisted_state.currentProjection,
                follow_up_state=persisted_state.followUpState,
                gap_report=persisted_state.gapReport,
                question_set=persisted_state.questionSet,
                guided_intake_question_set=persisted_state.guidedIntakeQuestionSet,
                guided_intake_response_set=persisted_state.guidedIntakeResponseSet,
                guided_intake_projection=persisted_state.guidedIntakeProjection,
            )

            if session.nextActionKind == "ask_batch":
                batch = session.nextBatch or []
                batch_result = normalize_batch_answer(batch, user_reply)
                validate_batch_result([item.fieldId for item in batch], batch_result)
                continued = self._session_runner.submit_follow_up_batch(session, batch_result)
            elif session.nextActionKind == "await_recommended_decision":
                decision = parse_recommended_yes_no(user_reply)
                if decision is None:
                    raise HostSessionRunnerError("Could not determine a yes/no decision")
                continued = self._session_runner.apply_recommended_decision(session, decision)
            elif session.nextActionKind == "completed":
                raise HostSessionRunnerError("Session is already completed")
            else:
                raise HostSessionRunnerError(
                    f"Unsupported next action kind: {session.nextActionKind}"
                )

            updated_intake_session = dict(persisted_state.intakeSession)
            updated_intake_session["status"] = (
                "completed" if continued.nextActionKind == "completed" else "active"
            )
            next_state = self._build_host_session_state(
                session_id=persisted_state.sessionId,
                manifest=persisted_state.templateManifest,
                intake_session=updated_intake_session,
                timestamp=timestamp,
                runner_result=continued,
                created_at=persisted_state.createdAt,
            )
            self._save(next_state)
            return self._build_action(next_state, continued)
        except HostSessionRunnerError:
            raise
        except HostSessionStoreError as exc:
            raise HostSessionRunnerError(str(exc)) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise HostSessionRunnerError(str(exc)) from exc

    def _save(self, session_state: HostSessionState) -> None:
        self._store.save(session_state)

    def _build_host_session_state(
        self,
        *,
        session_id: str,
        manifest: dict[str, Any],
        intake_session: dict[str, Any],
        timestamp: str,
        runner_result: SessionRunnerResult,
        created_at: str,
    ) -> HostSessionState:
        effective_intake_session = dict(intake_session)
        effective_intake_session.setdefault("sessionId", session_id)
        effective_intake_session.setdefault("templateId", manifest["templateId"])
        effective_intake_session.setdefault("templateVersion", manifest["version"])
        effective_intake_session.setdefault("hasExistingMaterial", False)
        effective_intake_session.setdefault("documentIds", [])
        effective_intake_session["phase"] = "handed-off"
        effective_intake_session["route"] = "guided-intake"
        effective_intake_session.setdefault("createdAt", created_at)
        effective_intake_session["updatedAt"] = timestamp
        effective_intake_session["status"] = (
            "completed" if runner_result.nextActionKind == "completed" else "active"
        )
        return HostSessionState(
            schemaVersion=SCHEMA_VERSION,
            sessionId=session_id,
            templateManifest=manifest,
            intakeSession=effective_intake_session,
            currentProjection=runner_result.currentProjection,
            followUpState=runner_result.followUpState,
            nextActionKind=runner_result.nextActionKind,
            createdAt=created_at,
            updatedAt=timestamp,
            lastInteractedAt=timestamp,
            gapReport=runner_result.gapReport,
            questionSet=runner_result.questionSet,
            guidedIntakeQuestionSet=runner_result.guidedIntakeQuestionSet,
            guidedIntakeResponseSet=runner_result.guidedIntakeResponseSet,
            guidedIntakeProjection=runner_result.guidedIntakeProjection,
        )

    def _build_action(
        self,
        session_state: HostSessionState,
        runner_result: SessionRunnerResult,
    ) -> HostSessionAction:
        current_batch = runner_result.nextBatch if runner_result.nextActionKind == "ask_batch" else None
        return HostSessionAction(
            sessionState=session_state,
            nextActionKind=runner_result.nextActionKind,
            currentProjection=runner_result.currentProjection,
            currentBatch=current_batch,
        )

    @staticmethod
    def _default_intake_session(
        session_id: str,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sessionId": session_id,
            "templateId": manifest["templateId"],
            "templateVersion": manifest["version"],
            "hasExistingMaterial": False,
            "documentIds": [],
            "phase": "handed-off",
            "route": "guided-intake",
            "status": "active",
        }
