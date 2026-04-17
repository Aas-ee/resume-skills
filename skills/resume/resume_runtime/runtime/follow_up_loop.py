from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from resume_runtime.runtime.follow_up_agent_adapter import (
    AskedQuestion,
    BatchAnswerResult,
    materialize_batch,
    validate_batch_result,
)
from resume_runtime.runtime.follow_up_policy import (
    StopDecision,
    decide_stop_or_continue,
    select_question_batch,
    should_close_round,
)
from resume_runtime.runtime.follow_up_state import (
    FollowUpLoopState,
    projection_ref_from_projection,
)

GapReportFn = Callable[[dict[str, Any]], dict[str, Any]]
QuestionSetFn = Callable[[dict[str, Any]], dict[str, Any]]
AssembleResponseSetFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]]
ProjectProfileFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class FollowUpLoopDependencies:
    derive_gap_report: GapReportFn
    derive_follow_up_question_set: QuestionSetFn
    assemble_follow_up_response_set: AssembleResponseSetFn
    project_follow_up_profile: ProjectProfileFn


@dataclass
class FollowUpLoopResult:
    state: FollowUpLoopState
    gapReport: dict[str, Any] | None = None
    questionSet: dict[str, Any] | None = None
    nextBatch: list[AskedQuestion] | None = None
    followUpResponseSet: dict[str, Any] | None = None
    projection: dict[str, Any] | None = None


class FollowUpLoop:
    def __init__(self, dependencies: FollowUpLoopDependencies):
        self.dependencies = dependencies

    def start_or_resume(
        self,
        state: FollowUpLoopState,
        current_projection: dict[str, Any],
        *,
        question_set: dict[str, Any] | None = None,
    ) -> FollowUpLoopResult:
        if state.loopPhase in {"completed", "awaiting_recommended_decision"}:
            return FollowUpLoopResult(state=state)

        if state.loopPhase == "asking_batch":
            if question_set is None:
                raise ValueError("question_set is required when resuming asking_batch")
            return FollowUpLoopResult(
                state=state,
                questionSet=question_set,
                nextBatch=materialize_batch(question_set, state.pendingQuestionBatch),
            )

        if state.loopPhase == "assembling_response_set":
            if question_set is None:
                raise ValueError(
                    "question_set is required when resuming assembly or projection"
                )
            return self._assemble_and_project(state, current_projection, question_set)

        if state.loopPhase == "projecting_profile":
            if question_set is None:
                raise ValueError(
                    "question_set is required when resuming assembly or projection"
                )
            return self._project_from_existing_response_set(
                state,
                current_projection,
                question_set,
            )

        return self._analyze_and_prepare_batch(state, current_projection)

    def apply_recommended_decision(
        self,
        state: FollowUpLoopState,
        gap_report: dict[str, Any],
        continue_for_recommended: str,
    ) -> FollowUpLoopResult:
        if state.loopPhase != "awaiting_recommended_decision":
            raise ValueError(
                "recommended decision can only be applied while awaiting_recommended_decision"
            )
        if continue_for_recommended not in {"yes", "no"}:
            raise ValueError(
                "continue_for_recommended must be 'yes' or 'no'"
            )

        state.continueForRecommended = continue_for_recommended
        decision = decide_stop_or_continue(gap_report, state.continueForRecommended)

        if decision.action == "complete":
            state.pendingQuestionBatch = []
            state.pendingRoundAnswers = {}
            state.currentFollowUpQuestionSetId = None
            state.loopPhase = "completed"
            state.lastDecisionReason = decision.reason
            return FollowUpLoopResult(state=state, gapReport=gap_report)

        return self._prepare_question_set(state, gap_report, decision)

    def submit_batch_result(
        self,
        state: FollowUpLoopState,
        current_projection: dict[str, Any],
        gap_report: dict[str, Any],
        question_set: dict[str, Any],
        batch_result: BatchAnswerResult,
    ) -> FollowUpLoopResult:
        validate_batch_result(state.pendingQuestionBatch, batch_result)
        state.pendingRoundAnswers.update(batch_result.answers)

        if should_close_round(
            gap_report,
            state.pendingRoundAnswers,
            user_declined=batch_result.userDeclined,
        ):
            state.pendingQuestionBatch = []
            state.loopPhase = "assembling_response_set"
            state.lastDecisionReason = "closing current round"
            return self._assemble_and_project(state, current_projection, question_set)

        state.pendingQuestionBatch = select_question_batch(
            question_set,
            state.pendingRoundAnswers,
            state.batchSizePolicy,
        )
        if not state.pendingQuestionBatch:
            state.loopPhase = "assembling_response_set"
            state.lastDecisionReason = "no unanswered questions remain in current round"
            return self._assemble_and_project(state, current_projection, question_set)

        state.loopPhase = "asking_batch"
        state.lastDecisionReason = "continuing current round with another small batch"
        return FollowUpLoopResult(
            state=state,
            gapReport=gap_report,
            questionSet=question_set,
            nextBatch=materialize_batch(question_set, state.pendingQuestionBatch),
        )

    def _analyze_and_prepare_batch(
        self,
        state: FollowUpLoopState,
        current_projection: dict[str, Any],
    ) -> FollowUpLoopResult:
        state.loopPhase = "analyzing_gaps"
        gap_report = self.dependencies.derive_gap_report(current_projection)
        state.currentGapReportId = gap_report["reportId"]
        state.history.gapReportIds.append(gap_report["reportId"])

        decision = decide_stop_or_continue(
            gap_report,
            state.continueForRecommended,
        )
        if decision.action == "complete":
            state.pendingQuestionBatch = []
            state.pendingRoundAnswers = {}
            state.currentFollowUpQuestionSetId = None
            state.loopPhase = "completed"
            state.lastDecisionReason = decision.reason
            return FollowUpLoopResult(state=state, gapReport=gap_report)

        if decision.action == "await_recommended_decision":
            state.pendingQuestionBatch = []
            state.pendingRoundAnswers = {}
            state.currentFollowUpQuestionSetId = None
            state.loopPhase = "awaiting_recommended_decision"
            state.lastDecisionReason = decision.reason
            return FollowUpLoopResult(state=state, gapReport=gap_report)

        return self._prepare_question_set(state, gap_report, decision)

    def _prepare_question_set(
        self,
        state: FollowUpLoopState,
        gap_report: dict[str, Any],
        decision: StopDecision,
    ) -> FollowUpLoopResult:
        question_set = self.dependencies.derive_follow_up_question_set(gap_report)
        state.currentFollowUpQuestionSetId = question_set["followUpQuestionSetId"]
        state.history.followUpQuestionSetIds.append(question_set["followUpQuestionSetId"])
        state.pendingRoundAnswers = {}
        state.pendingQuestionBatch = select_question_batch(
            question_set,
            state.pendingRoundAnswers,
            state.batchSizePolicy,
        )
        if not state.pendingQuestionBatch:
            raise ValueError("follow-up question set produced no pending question batch")

        state.loopPhase = "asking_batch"
        state.lastDecisionReason = decision.reason
        return FollowUpLoopResult(
            state=state,
            gapReport=gap_report,
            questionSet=question_set,
            nextBatch=materialize_batch(question_set, state.pendingQuestionBatch),
        )

    def _assemble_and_project(
        self,
        state: FollowUpLoopState,
        current_projection: dict[str, Any],
        question_set: dict[str, Any],
    ) -> FollowUpLoopResult:
        state.loopPhase = "assembling_response_set"
        response_set = self.dependencies.assemble_follow_up_response_set(
            question_set,
            dict(state.pendingRoundAnswers),
            current_projection["profile"],
        )
        state.history.followUpResponseSetIds.append(
            response_set["followUpResponseSetId"]
        )
        return self._project_from_response_set(state, current_projection, response_set)

    def _project_from_existing_response_set(
        self,
        state: FollowUpLoopState,
        current_projection: dict[str, Any],
        question_set: dict[str, Any],
    ) -> FollowUpLoopResult:
        response_set = self.dependencies.assemble_follow_up_response_set(
            question_set,
            dict(state.pendingRoundAnswers),
            current_projection["profile"],
        )
        return self._project_from_response_set(state, current_projection, response_set)

    def _project_from_response_set(
        self,
        state: FollowUpLoopState,
        current_projection: dict[str, Any],
        response_set: dict[str, Any],
    ) -> FollowUpLoopResult:
        state.loopPhase = "projecting_profile"
        projection = self.dependencies.project_follow_up_profile(
            response_set,
            current_projection,
        )
        state.history.followUpProfileProjectionIds.append(projection["projectionId"])
        state.currentProjectionRef = projection_ref_from_projection(
            projection,
            "follow-up",
        )
        state.pendingQuestionBatch = []
        state.pendingRoundAnswers = {}
        state.currentGapReportId = None
        state.currentFollowUpQuestionSetId = None
        state.lastDecisionReason = "projected follow-up round and re-entered gap analysis"

        next_result = self._analyze_and_prepare_batch(state, projection)
        next_result.followUpResponseSet = response_set
        next_result.projection = projection
        return next_result
