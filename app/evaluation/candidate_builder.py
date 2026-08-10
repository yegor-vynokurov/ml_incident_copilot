from datetime import (
    datetime,
    timezone,
)

from app.evaluation.candidate_schemas import (
    EvaluationCandidate,
)
from app.observability.schemas import (
    IncidentFeedbackRecord,
    IncidentRunRecord,
)


class CandidateBuildError(
    ValueError
):
    """
    Runtime records and feedback cannot be
    converted into a valid evaluation candidate.
    """


def _find_actual_explanation(
    *,
    run_record: IncidentRunRecord,
    issue_code: str | None,
) -> str | None:
    """
    Find the explanation for the issue mentioned
    in feedback.

    Returning None is valid:
    the feedback may concern an issue that the
    system failed to detect at all.
    """

    if issue_code is None:
        return None

    agent_run = run_record.agent_run

    if agent_run is None:
        return None

    for finding in agent_run.report.findings:
        if finding.issue_code == issue_code:
            return finding.explanation

    return None


def build_candidates(
    *,
    runs: list[IncidentRunRecord],
    feedback_records: list[
        IncidentFeedbackRecord
    ],
    existing_candidates: list[
        EvaluationCandidate
    ] | None = None,
) -> list[EvaluationCandidate]:
    """
    Build NEW evaluation candidates.

    Rules:
    - feedback='correct' is ignored;
    - partially_correct / incorrect may become
      candidates;
    - feedback must reference a known run;
    - only successful agent runs are currently
      eligible;
    - one feedback_id can create at most one
      candidate.
    """

    if existing_candidates is None:
        existing_candidates = []

    runs_by_trace_id = {
        record.trace_id: record
        for record in runs
    }

    processed_feedback_ids = {
        candidate.feedback_id
        for candidate
        in existing_candidates
    }

    new_candidates: list[
        EvaluationCandidate
    ] = []

    for feedback in feedback_records:
        # Correct runs do not need to become
        # regression examples.
        if feedback.verdict == "correct":
            continue

        # Idempotency:
        # don't create the same candidate again.
        if (
            feedback.feedback_id
            in processed_feedback_ids
        ):
            continue

        run_record = runs_by_trace_id.get(
            feedback.trace_id
        )

        if run_record is None:
            raise CandidateBuildError(
                "Feedback references an unknown "
                "runtime trace: "
                f"{feedback.trace_id!r}."
            )

        if run_record.outcome != "success":
            raise CandidateBuildError(
                "Evaluation candidates currently "
                "require a successful agent run. "
                f"trace_id={feedback.trace_id!r}, "
                f"outcome={run_record.outcome!r}."
            )

        if run_record.agent_run is None:
            raise CandidateBuildError(
                "Successful runtime record does "
                "not contain agent_run. "
                f"trace_id={feedback.trace_id!r}."
            )

        actual_explanation = (
            _find_actual_explanation(
                run_record=run_record,
                issue_code=(
                    feedback.issue_code
                ),
            )
        )

        candidate = EvaluationCandidate(
            candidate_id=(
                "feedback-"
                f"{feedback.feedback_id}"
            ),
            feedback_id=(
                feedback.feedback_id
            ),
            trace_id=(
                feedback.trace_id
            ),
            created_at=datetime.now(
                timezone.utc
            ),
            status="pending",
            source_request=(
                run_record.request
            ),
            actual_issue_codes=list(
                run_record
                .agent_run
                .issue_codes
            ),
            expected_issue_codes=(
                list(
                    feedback
                    .expected_issue_codes
                )
                if (
                    feedback
                    .expected_issue_codes
                    is not None
                )
                else None
            ),
            affected_issue_code=(
                feedback.issue_code
            ),
            actual_explanation=(
                actual_explanation
            ),
            corrected_explanation=(
                feedback
                .corrected_explanation
            ),
            feedback_verdict=(
                feedback.verdict
            ),
            feedback_comment=(
                feedback.comment
            ),
            prompt_version=(
                run_record.prompt_version
            ),
            provider_names=list(
                run_record.providers
            ),
            model_names=list(
                run_record.models
            ),
        )

        new_candidates.append(
            candidate
        )

        # Important if the same feedback_id
        # appears twice in one input file.
        processed_feedback_ids.add(
            feedback.feedback_id
        )

    return new_candidates