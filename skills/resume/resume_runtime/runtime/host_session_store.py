from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

from resume_runtime.runtime.host_session_state import HostSessionState, SCHEMA_VERSION


class HostSessionStoreError(Exception):
    """Raised when persisted host session state cannot be read or updated."""


class HostSessionStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)

    def save(self, session_state: HostSessionState) -> Path:
        session_state.validate()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._session_file(session_state.sessionId)
        temp_path = file_path.with_name(f".{file_path.name}.tmp")
        temp_path.write_text(
            json.dumps(session_state.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temp_path, file_path)
        return file_path

    def load(self, session_id: str) -> HostSessionState:
        file_path = self._session_file(session_id)
        payload = self._read_payload(file_path, session_id=session_id)
        return self._state_from_payload(payload, session_id=session_id)

    def find_active_session(self) -> HostSessionState | None:
        if not self._base_dir.exists():
            return None

        newest_session: HostSessionState | None = None
        newest_key: tuple[str, str] | None = None
        first_error: HostSessionStoreError | None = None

        for file_path in sorted(self._base_dir.glob("*.json")):
            try:
                payload = self._read_payload(file_path, session_id=file_path.stem)
                session_state = self._state_from_payload(payload, session_id=file_path.stem)
            except HostSessionStoreError as exc:
                if first_error is None:
                    first_error = exc
                continue
            if session_state.nextActionKind == "completed":
                continue
            if session_state.intakeSession.get("status") in {"completed", "abandoned"}:
                continue

            candidate_key = (session_state.lastInteractedAt, session_state.sessionId)
            if newest_key is None or candidate_key > newest_key:
                newest_session = session_state
                newest_key = candidate_key

        if newest_session is not None:
            return newest_session
        if first_error is not None:
            raise first_error
        return None

    def mark_completed(self, session_id: str, completed_at: str) -> HostSessionState:
        session_state = self.load(session_id)
        completed_follow_up_state = replace(
            session_state.followUpState,
            currentFollowUpQuestionSetId=None,
            pendingQuestionBatch=[],
            pendingRoundAnswers={},
            loopPhase="completed",
            lastDecisionReason="session completed",
        )
        completed_state = replace(
            session_state,
            intakeSession={
                **session_state.intakeSession,
                "status": "completed",
                "updatedAt": completed_at,
            },
            followUpState=completed_follow_up_state,
            questionSet=None,
            nextActionKind="completed",
            updatedAt=completed_at,
            lastInteractedAt=completed_at,
        )
        self.save(completed_state)
        return completed_state

    def _state_from_payload(
        self,
        payload: dict[str, object],
        *,
        session_id: str,
    ) -> HostSessionState:
        schema_version = payload.get("schemaVersion")
        if schema_version != SCHEMA_VERSION:
            raise HostSessionStoreError(
                f"unsupported schema version for session '{session_id}': {schema_version}"
            )
        try:
            return HostSessionState.from_dict(payload)
        except ValueError as exc:
            raise HostSessionStoreError(
                f"invalid session payload for session '{session_id}': {exc}"
            ) from exc

    def _read_payload(self, file_path: Path, *, session_id: str) -> dict[str, object]:
        if not file_path.exists():
            raise HostSessionStoreError(f"missing session file for session '{session_id}'")
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HostSessionStoreError(
                f"corrupted JSON for session '{session_id}'"
            ) from exc
        if not isinstance(payload, dict):
            raise HostSessionStoreError(
                f"invalid session payload for session '{session_id}': root must be an object"
            )
        return payload

    def _session_file(self, session_id: str) -> Path:
        return self._base_dir / f"{session_id}.json"
