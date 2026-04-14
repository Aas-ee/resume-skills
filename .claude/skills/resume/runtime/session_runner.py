from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Literal

from resume.runtime.artifact_builders import (
    assemble_follow_up_response_set,
    assemble_guided_intake_response_set,
    derive_follow_up_question_set,
    derive_gap_report,
    derive_guided_intake_question_set,
    project_follow_up_profile,
    project_guided_intake_profile,
)
from resume.runtime.follow_up_agent_adapter import BatchAnswerResult, AskedQuestion
from resume.runtime.follow_up_loop import FollowUpLoop, FollowUpLoopDependencies, FollowUpLoopResult
from resume.runtime.follow_up_state import FollowUpLoopState, new_follow_up_loop_state

GuidedQuestionSetFn = Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]]
GuidedResponseSetFn = Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]]
GuidedProjectionFn = Callable[[dict[str, Any]], dict[str, Any]]
GapReportFn = Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]]
FollowUpQuestionSetFn = Callable[[dict[str, Any], str], dict[str, Any]]
FollowUpResponseSetFn = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], str], dict[str, Any]]
FollowUpProjectionFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
NextActionKind = Literal["ask_batch", "await_recommended_decision", "completed"]


@dataclass(frozen=True)
class SessionRunnerDependencies:
    derive_guided_intake_question_set: GuidedQuestionSetFn
    assemble_guided_intake_response_set: GuidedResponseSetFn
    project_guided_intake_profile: GuidedProjectionFn
    derive_gap_report: GapReportFn
    derive_follow_up_question_set: FollowUpQuestionSetFn
    assemble_follow_up_response_set: FollowUpResponseSetFn
    project_follow_up_profile: FollowUpProjectionFn


@dataclass
class SessionRunnerResult:
    currentProjection: dict[str, Any]
    followUpState: FollowUpLoopState
    nextActionKind: NextActionKind
    templateManifest: dict[str, Any] | None = None
    guidedIntakeQuestionSet: dict[str, Any] | None = None
    guidedIntakeResponseSet: dict[str, Any] | None = None
    guidedIntakeProjection: dict[str, Any] | None = None
    gapReport: dict[str, Any] | None = None
    questionSet: dict[str, Any] | None = None
    followUpResponseSet: dict[str, Any] | None = None
    projection: dict[str, Any] | None = None
    nextBatch: list[AskedQuestion] | None = None


class SessionRunner:
    def __init__(
        self,
        *,
        guided_question_set_generated_at: str,
        guided_response_set_updated_at: str,
        follow_up_generated_at: str,
        follow_up_response_updated_at: str,
        batch_size_policy: int = 2,
        dependencies: SessionRunnerDependencies | None = None,
    ):
        self.guided_question_set_generated_at = guided_question_set_generated_at
        self.guided_response_set_updated_at = guided_response_set_updated_at
        self.follow_up_generated_at = follow_up_generated_at
        self.follow_up_response_updated_at = follow_up_response_updated_at
        self.batch_size_policy = batch_size_policy
        self.dependencies = dependencies or SessionRunnerDependencies(
            derive_guided_intake_question_set=lambda manifest, checklist, generated_at: (
                derive_guided_intake_question_set(
                    manifest,
                    checklist,
                    generated_at=generated_at,
                )
            ),
            assemble_guided_intake_response_set=lambda question_set, responses, updated_at: (
                assemble_guided_intake_response_set(
                    question_set,
                    responses,
                    updated_at=updated_at,
                )
            ),
            project_guided_intake_profile=project_guided_intake_profile,
            derive_gap_report=lambda manifest, projection, generated_at: derive_gap_report(
                manifest,
                projection,
                generated_at=generated_at,
            ),
            derive_follow_up_question_set=lambda gap_report, generated_at: (
                derive_follow_up_question_set(
                    gap_report,
                    generated_at=generated_at,
                )
            ),
            assemble_follow_up_response_set=(
                lambda question_set, responses, current_profile, updated_at: (
                    assemble_follow_up_response_set(
                        question_set,
                        responses,
                        current_profile,
                        updated_at=updated_at,
                    )
                )
            ),
            project_follow_up_profile=project_follow_up_profile,
        )

    def start_after_guided_intake(
        self,
        manifest: dict[str, Any],
        checklist: dict[str, Any],
        guided_answers: dict[str, Any],
    ) -> SessionRunnerResult:
        self._validate_template_identity(
            manifest,
            checklist["templateId"],
            checklist["templateVersion"],
        )
        guided_question_set = self.dependencies.derive_guided_intake_question_set(
            manifest,
            checklist,
            self.guided_question_set_generated_at,
        )
        guided_response_set = self.dependencies.assemble_guided_intake_response_set(
            guided_question_set,
            guided_answers,
            self.guided_response_set_updated_at,
        )
        guided_projection = self.dependencies.project_guided_intake_profile(
            guided_response_set
        )
        follow_up_state = new_follow_up_loop_state(
            template_id=manifest["templateId"],
            template_version=manifest["version"],
            projection=guided_projection,
            projection_kind="guided-intake",
            batch_size_policy=self.batch_size_policy,
        )
        continued_follow_up_state = self._clone_follow_up_state(follow_up_state)
        loop_result = self._loop_for_manifest(manifest).start_or_resume(
            continued_follow_up_state,
            guided_projection,
        )
        return self._build_runner_result(
            current_projection=guided_projection,
            follow_up_state=loop_result.state,
            loop_result=loop_result,
            template_manifest=manifest,
            guided_intake_question_set=guided_question_set,
            guided_intake_response_set=guided_response_set,
            guided_intake_projection=guided_projection,
        )

    def submit_follow_up_batch(
        self,
        session: SessionRunnerResult,
        batch_result: BatchAnswerResult,
        *,
        manifest: dict[str, Any] | None = None,
    ) -> SessionRunnerResult:
        if session.nextActionKind != "ask_batch":
            raise ValueError("follow-up batch answers can only be submitted while asking_batch")
        if session.gapReport is None or session.questionSet is None:
            raise ValueError("gapReport and questionSet are required while asking_batch")

        effective_manifest = self._resolve_manifest(
            manifest,
            session.templateManifest,
            session.followUpState,
        )
        continued_follow_up_state = self._clone_follow_up_state(session.followUpState)
        loop_result = self._loop_for_manifest(effective_manifest).submit_batch_result(
            continued_follow_up_state,
            session.currentProjection,
            session.gapReport,
            session.questionSet,
            batch_result,
        )
        return self._build_runner_result(
            current_projection=session.currentProjection,
            follow_up_state=loop_result.state,
            loop_result=loop_result,
            template_manifest=session.templateManifest,
            guided_intake_question_set=session.guidedIntakeQuestionSet,
            guided_intake_response_set=session.guidedIntakeResponseSet,
            guided_intake_projection=session.guidedIntakeProjection,
        )

    def apply_recommended_decision(
        self,
        session: SessionRunnerResult,
        continue_for_recommended: str,
        *,
        manifest: dict[str, Any] | None = None,
    ) -> SessionRunnerResult:
        if session.nextActionKind != "await_recommended_decision":
            raise ValueError(
                "recommended decision can only be applied while awaiting_recommended_decision"
            )
        if session.gapReport is None:
            raise ValueError("gapReport is required while awaiting_recommended_decision")

        effective_manifest = self._resolve_manifest(
            manifest,
            session.templateManifest,
            session.followUpState,
        )
        continued_follow_up_state = self._clone_follow_up_state(session.followUpState)
        loop_result = self._loop_for_manifest(effective_manifest).apply_recommended_decision(
            continued_follow_up_state,
            session.gapReport,
            continue_for_recommended,
        )
        return self._build_runner_result(
            current_projection=session.currentProjection,
            follow_up_state=loop_result.state,
            loop_result=loop_result,
            template_manifest=session.templateManifest,
            guided_intake_question_set=session.guidedIntakeQuestionSet,
            guided_intake_response_set=session.guidedIntakeResponseSet,
            guided_intake_projection=session.guidedIntakeProjection,
        )

    def resume(
        self,
        *,
        manifest: dict[str, Any],
        current_projection: dict[str, Any],
        follow_up_state: FollowUpLoopState,
        gap_report: dict[str, Any] | None = None,
        question_set: dict[str, Any] | None = None,
        guided_intake_question_set: dict[str, Any] | None = None,
        guided_intake_response_set: dict[str, Any] | None = None,
        guided_intake_projection: dict[str, Any] | None = None,
    ) -> SessionRunnerResult:
        self._validate_template_identity(
            manifest,
            follow_up_state.templateId,
            follow_up_state.templateVersion,
        )
        self._validate_projection_identity(current_projection, follow_up_state)
        resolved_gap_report = self._resolve_gap_report(
            manifest,
            current_projection,
            follow_up_state,
            gap_report,
        )
        resolved_question_set = self._resolve_question_set(
            resolved_gap_report,
            follow_up_state,
            question_set,
        )
        continued_follow_up_state = self._clone_follow_up_state(follow_up_state)
        loop_result = self._loop_for_manifest(manifest).start_or_resume(
            continued_follow_up_state,
            current_projection,
            question_set=resolved_question_set,
        )
        return self._build_runner_result(
            current_projection=current_projection,
            follow_up_state=loop_result.state,
            loop_result=loop_result,
            template_manifest=manifest,
            guided_intake_question_set=guided_intake_question_set,
            guided_intake_response_set=guided_intake_response_set,
            guided_intake_projection=guided_intake_projection,
            fallback_gap_report=resolved_gap_report,
            fallback_question_set=resolved_question_set,
        )

    def _loop_for_manifest(self, manifest: dict[str, Any]) -> FollowUpLoop:
        return FollowUpLoop(
            FollowUpLoopDependencies(
                derive_gap_report=lambda projection: self.dependencies.derive_gap_report(
                    manifest,
                    projection,
                    self.follow_up_generated_at,
                ),
                derive_follow_up_question_set=lambda gap_report: (
                    self.dependencies.derive_follow_up_question_set(
                        gap_report,
                        self.follow_up_generated_at,
                    )
                ),
                assemble_follow_up_response_set=(
                    lambda question_set, responses, current_profile: (
                        self.dependencies.assemble_follow_up_response_set(
                            question_set,
                            responses,
                            current_profile,
                            self.follow_up_response_updated_at,
                        )
                    )
                ),
                project_follow_up_profile=self.dependencies.project_follow_up_profile,
            )
        )

    @staticmethod
    def _clone_follow_up_state(follow_up_state: FollowUpLoopState) -> FollowUpLoopState:
        return deepcopy(follow_up_state)

    def _build_runner_result(
        self,
        *,
        current_projection: dict[str, Any],
        follow_up_state: FollowUpLoopState,
        loop_result: FollowUpLoopResult,
        template_manifest: dict[str, Any] | None,
        guided_intake_question_set: dict[str, Any] | None,
        guided_intake_response_set: dict[str, Any] | None,
        guided_intake_projection: dict[str, Any] | None,
        fallback_gap_report: dict[str, Any] | None = None,
        fallback_question_set: dict[str, Any] | None = None,
    ) -> SessionRunnerResult:
        effective_projection = loop_result.projection or current_projection
        next_action_kind = self._next_action_kind(loop_result.state)
        gap_report = loop_result.gapReport or fallback_gap_report
        question_set = loop_result.questionSet or fallback_question_set

        if next_action_kind != "ask_batch":
            question_set = None if loop_result.questionSet is None else loop_result.questionSet
        if next_action_kind == "completed" and loop_result.questionSet is None:
            question_set = None

        return SessionRunnerResult(
            currentProjection=effective_projection,
            followUpState=follow_up_state,
            nextActionKind=next_action_kind,
            templateManifest=template_manifest,
            guidedIntakeQuestionSet=guided_intake_question_set,
            guidedIntakeResponseSet=guided_intake_response_set,
            guidedIntakeProjection=guided_intake_projection,
            gapReport=gap_report,
            questionSet=question_set,
            followUpResponseSet=loop_result.followUpResponseSet,
            projection=loop_result.projection,
            nextBatch=loop_result.nextBatch,
        )

    def _resolve_gap_report(
        self,
        manifest: dict[str, Any],
        current_projection: dict[str, Any],
        follow_up_state: FollowUpLoopState,
        gap_report: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if gap_report is not None:
            if (
                follow_up_state.currentGapReportId is not None
                and gap_report["reportId"] != follow_up_state.currentGapReportId
            ):
                raise ValueError("gapReport does not match follow-up state")
            return gap_report

        needs_gap_report = follow_up_state.loopPhase in {
            "asking_batch",
            "awaiting_recommended_decision",
            "completed",
        } or follow_up_state.currentGapReportId is not None
        if not needs_gap_report:
            return None

        derived_gap_report = self.dependencies.derive_gap_report(
            manifest,
            current_projection,
            self.follow_up_generated_at,
        )
        if (
            follow_up_state.currentGapReportId is not None
            and derived_gap_report["reportId"] != follow_up_state.currentGapReportId
        ):
            raise ValueError("current projection does not match follow-up state gap report")
        return derived_gap_report

    def _resolve_question_set(
        self,
        gap_report: dict[str, Any] | None,
        follow_up_state: FollowUpLoopState,
        question_set: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if question_set is not None:
            if (
                follow_up_state.currentFollowUpQuestionSetId is not None
                and question_set["followUpQuestionSetId"]
                != follow_up_state.currentFollowUpQuestionSetId
            ):
                raise ValueError("questionSet does not match follow-up state")
            return question_set

        if follow_up_state.currentFollowUpQuestionSetId is None:
            return None
        if gap_report is None:
            raise ValueError("gapReport is required to derive questionSet")

        derived_question_set = self.dependencies.derive_follow_up_question_set(
            gap_report,
            self.follow_up_generated_at,
        )
        if (
            derived_question_set["followUpQuestionSetId"]
            != follow_up_state.currentFollowUpQuestionSetId
        ):
            raise ValueError("gapReport does not match follow-up state question set")
        return derived_question_set

    def _resolve_manifest(
        self,
        manifest: dict[str, Any] | None,
        session_manifest: dict[str, Any] | None,
        follow_up_state: FollowUpLoopState,
    ) -> dict[str, Any]:
        if manifest is None:
            if session_manifest is not None:
                self._validate_template_identity(
                    session_manifest,
                    follow_up_state.templateId,
                    follow_up_state.templateVersion,
                )
                return session_manifest
            raise ValueError("template manifest is required for follow-up continuation")
        self._validate_template_identity(
            manifest,
            follow_up_state.templateId,
            follow_up_state.templateVersion,
        )
        return manifest

    @staticmethod
    def _next_action_kind(state: FollowUpLoopState) -> NextActionKind:
        if state.loopPhase == "asking_batch":
            return "ask_batch"
        if state.loopPhase == "awaiting_recommended_decision":
            return "await_recommended_decision"
        if state.loopPhase == "completed":
            return "completed"
        raise ValueError(f"unexpected loop phase for stable next action: {state.loopPhase}")

    @staticmethod
    def _validate_template_identity(
        manifest: dict[str, Any],
        template_id: str,
        template_version: str,
    ) -> None:
        if manifest["templateId"] != template_id or manifest["version"] != template_version:
            raise ValueError("template identity does not match expected session state")

    @staticmethod
    def _validate_projection_identity(
        current_projection: dict[str, Any],
        follow_up_state: FollowUpLoopState,
    ) -> None:
        projection_ref = follow_up_state.currentProjectionRef
        if current_projection["projectionId"] != projection_ref.projectionId:
            raise ValueError("current projection does not match follow-up state")
        if current_projection["profile"]["profileId"] != projection_ref.profileId:
            raise ValueError("current projection profile does not match follow-up state")
