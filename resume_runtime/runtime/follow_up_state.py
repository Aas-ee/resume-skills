from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

LoopPhase = Literal[
    "analyzing_gaps",
    "asking_batch",
    "assembling_response_set",
    "projecting_profile",
    "awaiting_recommended_decision",
    "completed",
]
ProjectionKind = Literal["guided-intake", "follow-up"]
RecommendedDecision = Literal["unset", "yes", "no"]


@dataclass(frozen=True)
class CurrentProjectionRef:
    projectionKind: ProjectionKind
    projectionId: str
    profileId: str


@dataclass
class FollowUpLoopHistory:
    gapReportIds: list[str] = field(default_factory=list)
    followUpQuestionSetIds: list[str] = field(default_factory=list)
    followUpResponseSetIds: list[str] = field(default_factory=list)
    followUpProfileProjectionIds: list[str] = field(default_factory=list)


@dataclass
class FollowUpLoopState:
    templateId: str
    templateVersion: str
    currentProjectionRef: CurrentProjectionRef
    currentGapReportId: str | None = None
    currentFollowUpQuestionSetId: str | None = None
    pendingQuestionBatch: list[str] = field(default_factory=list)
    pendingRoundAnswers: dict[str, Any] = field(default_factory=dict)
    loopPhase: LoopPhase = "analyzing_gaps"
    continueForRecommended: RecommendedDecision = "unset"
    batchSizePolicy: int = 2
    lastDecisionReason: str = "loop initialized"
    history: FollowUpLoopHistory = field(default_factory=FollowUpLoopHistory)


def projection_ref_from_projection(
    projection: dict[str, Any],
    projection_kind: ProjectionKind,
) -> CurrentProjectionRef:
    return CurrentProjectionRef(
        projectionKind=projection_kind,
        projectionId=projection["projectionId"],
        profileId=projection["profile"]["profileId"],
    )


def new_follow_up_loop_state(
    *,
    template_id: str,
    template_version: str,
    projection: dict[str, Any],
    projection_kind: ProjectionKind,
    batch_size_policy: int = 2,
) -> FollowUpLoopState:
    return FollowUpLoopState(
        templateId=template_id,
        templateVersion=template_version,
        currentProjectionRef=projection_ref_from_projection(
            projection,
            projection_kind,
        ),
        batchSizePolicy=batch_size_policy,
    )
