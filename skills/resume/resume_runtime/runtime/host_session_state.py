from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from resume_runtime.runtime.follow_up_state import (
    CurrentProjectionRef,
    FollowUpLoopHistory,
    FollowUpLoopState,
)

NextActionKind = Literal["ask_batch", "await_recommended_decision", "completed"]
SCHEMA_VERSION = "1"
_REQUIRED_FIELDS = (
    "schemaVersion",
    "sessionId",
    "templateManifest",
    "intakeSession",
    "currentProjection",
    "followUpState",
    "nextActionKind",
    "createdAt",
    "updatedAt",
    "lastInteractedAt",
)
_VALID_NEXT_ACTION_KINDS = {
    "ask_batch",
    "await_recommended_decision",
    "completed",
}


@dataclass(frozen=True)
class HostSessionState:
    schemaVersion: str
    sessionId: str
    templateManifest: dict[str, Any]
    intakeSession: dict[str, Any]
    currentProjection: dict[str, Any]
    followUpState: FollowUpLoopState
    nextActionKind: NextActionKind
    createdAt: str
    updatedAt: str
    lastInteractedAt: str
    gapReport: dict[str, Any] | None = None
    questionSet: dict[str, Any] | None = None
    guidedIntakeQuestionSet: dict[str, Any] | None = None
    guidedIntakeResponseSet: dict[str, Any] | None = None
    guidedIntakeProjection: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload: dict[str, Any] = {
            "schemaVersion": self.schemaVersion,
            "sessionId": self.sessionId,
            "templateManifest": self.templateManifest,
            "intakeSession": self.intakeSession,
            "currentProjection": self.currentProjection,
            "followUpState": follow_up_loop_state_to_dict(self.followUpState),
            "nextActionKind": self.nextActionKind,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "lastInteractedAt": self.lastInteractedAt,
        }
        if self.gapReport is not None:
            payload["gapReport"] = self.gapReport
        if self.questionSet is not None:
            payload["questionSet"] = self.questionSet
        if self.guidedIntakeQuestionSet is not None:
            payload["guidedIntakeQuestionSet"] = self.guidedIntakeQuestionSet
        if self.guidedIntakeResponseSet is not None:
            payload["guidedIntakeResponseSet"] = self.guidedIntakeResponseSet
        if self.guidedIntakeProjection is not None:
            payload["guidedIntakeProjection"] = self.guidedIntakeProjection
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> HostSessionState:
        _validate_required_fields(payload)
        state = cls(
            schemaVersion=payload["schemaVersion"],
            sessionId=payload["sessionId"],
            templateManifest=payload["templateManifest"],
            intakeSession=payload["intakeSession"],
            currentProjection=payload["currentProjection"],
            followUpState=follow_up_loop_state_from_dict(payload["followUpState"]),
            nextActionKind=payload["nextActionKind"],
            createdAt=payload["createdAt"],
            updatedAt=payload["updatedAt"],
            lastInteractedAt=payload["lastInteractedAt"],
            gapReport=payload.get("gapReport"),
            questionSet=payload.get("questionSet"),
            guidedIntakeQuestionSet=payload.get("guidedIntakeQuestionSet"),
            guidedIntakeResponseSet=payload.get("guidedIntakeResponseSet"),
            guidedIntakeProjection=payload.get("guidedIntakeProjection"),
        )
        state.validate()
        return state

    def validate(self) -> None:
        if self.nextActionKind not in _VALID_NEXT_ACTION_KINDS:
            raise ValueError(f"invalid nextActionKind: {self.nextActionKind}")
        intake_session_id = _require_dict_value(self.intakeSession, "sessionId", "intakeSession")
        if self.sessionId != intake_session_id:
            raise ValueError("sessionId does not match intakeSession.sessionId")
        _validate_template_identity(
            manifest=self.templateManifest,
            intake_session=self.intakeSession,
            follow_up_state=self.followUpState,
        )
        _validate_current_projection_alignment(
            current_projection=self.currentProjection,
            current_projection_ref=self.followUpState.currentProjectionRef,
        )


def follow_up_loop_state_to_dict(state: FollowUpLoopState) -> dict[str, Any]:
    return {
        "templateId": state.templateId,
        "templateVersion": state.templateVersion,
        "currentProjectionRef": {
            "projectionKind": state.currentProjectionRef.projectionKind,
            "projectionId": state.currentProjectionRef.projectionId,
            "profileId": state.currentProjectionRef.profileId,
        },
        "currentGapReportId": state.currentGapReportId,
        "currentFollowUpQuestionSetId": state.currentFollowUpQuestionSetId,
        "pendingQuestionBatch": list(state.pendingQuestionBatch),
        "pendingRoundAnswers": dict(state.pendingRoundAnswers),
        "loopPhase": state.loopPhase,
        "continueForRecommended": state.continueForRecommended,
        "batchSizePolicy": state.batchSizePolicy,
        "lastDecisionReason": state.lastDecisionReason,
        "history": {
            "gapReportIds": list(state.history.gapReportIds),
            "followUpQuestionSetIds": list(state.history.followUpQuestionSetIds),
            "followUpResponseSetIds": list(state.history.followUpResponseSetIds),
            "followUpProfileProjectionIds": list(state.history.followUpProfileProjectionIds),
        },
    }


def follow_up_loop_state_from_dict(payload: dict[str, Any]) -> FollowUpLoopState:
    history = payload.get("history") or {}
    projection_ref = _require_dict_value(payload, "currentProjectionRef", "followUpState")
    return FollowUpLoopState(
        templateId=_require_dict_value(payload, "templateId", "followUpState"),
        templateVersion=_require_dict_value(payload, "templateVersion", "followUpState"),
        currentProjectionRef=CurrentProjectionRef(
            projectionKind=_require_dict_value(
                projection_ref,
                "projectionKind",
                "followUpState.currentProjectionRef",
            ),
            projectionId=_require_dict_value(
                projection_ref,
                "projectionId",
                "followUpState.currentProjectionRef",
            ),
            profileId=_require_dict_value(
                projection_ref,
                "profileId",
                "followUpState.currentProjectionRef",
            ),
        ),
        currentGapReportId=payload.get("currentGapReportId"),
        currentFollowUpQuestionSetId=payload.get("currentFollowUpQuestionSetId"),
        pendingQuestionBatch=list(payload.get("pendingQuestionBatch", [])),
        pendingRoundAnswers=dict(payload.get("pendingRoundAnswers", {})),
        loopPhase=payload.get("loopPhase", "analyzing_gaps"),
        continueForRecommended=payload.get("continueForRecommended", "unset"),
        batchSizePolicy=payload.get("batchSizePolicy", 2),
        lastDecisionReason=payload.get("lastDecisionReason", "loop initialized"),
        history=FollowUpLoopHistory(
            gapReportIds=list(history.get("gapReportIds", [])),
            followUpQuestionSetIds=list(history.get("followUpQuestionSetIds", [])),
            followUpResponseSetIds=list(history.get("followUpResponseSetIds", [])),
            followUpProfileProjectionIds=list(history.get("followUpProfileProjectionIds", [])),
        ),
    )


def _validate_required_fields(payload: dict[str, Any]) -> None:
    for field_name in _REQUIRED_FIELDS:
        if field_name not in payload:
            raise ValueError(f"missing required field: {field_name}")


def _validate_template_identity(
    *,
    manifest: dict[str, Any],
    intake_session: dict[str, Any],
    follow_up_state: FollowUpLoopState,
) -> None:
    manifest_template_id = _require_dict_value(manifest, "templateId", "templateManifest")
    manifest_template_version = _require_dict_value(manifest, "version", "templateManifest")
    intake_template_id = _require_dict_value(intake_session, "templateId", "intakeSession")
    intake_template_version = _require_dict_value(
        intake_session,
        "templateVersion",
        "intakeSession",
    )
    if (
        manifest_template_id != intake_template_id
        or manifest_template_id != follow_up_state.templateId
        or manifest_template_version != intake_template_version
        or manifest_template_version != follow_up_state.templateVersion
    ):
        raise ValueError("template identity does not match session state")



def _validate_current_projection_alignment(
    *,
    current_projection: dict[str, Any],
    current_projection_ref: CurrentProjectionRef,
) -> None:
    projection_id = _require_dict_value(
        current_projection,
        "projectionId",
        "currentProjection",
    )
    profile = _require_dict_value(current_projection, "profile", "currentProjection")
    profile_id = _require_dict_value(profile, "profileId", "currentProjection.profile")
    if (
        projection_id != current_projection_ref.projectionId
        or profile_id != current_projection_ref.profileId
    ):
        raise ValueError("currentProjection does not match followUpState.currentProjectionRef")



def _require_dict_value(payload: dict[str, Any], key: str, path: str) -> Any:
    try:
        return payload[key]
    except KeyError as exc:
        raise ValueError(f"missing required field: {path}.{key}") from exc
    except TypeError as exc:
        raise ValueError(f"invalid object at {path}") from exc
