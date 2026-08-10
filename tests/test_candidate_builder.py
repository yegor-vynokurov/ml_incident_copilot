from datetime import (
    datetime,
    timezone,
)

from app.evaluation.candidate_builder import (
    CandidateBuildError,
    build_candidates,
)
from app.observability.schemas import (
    IncidentFeedbackRecord,
    IncidentRunRecord,
)
from app.schemas import (
    AgentRun,
    EvidenceReference,
    IncidentFinding,
    IncidentReport,
    PredictionRequest,
)


def _make_request() -> PredictionRequest:
    return PredictionRequest(
        request_id="REQ-CANDIDATE-1",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )



def _make_run_record() -> IncidentRunRecord:
    request = _make_request()

    agent_run = AgentRun(
        request_id=(
            request.request_id
        ),
        status=(
            "completed_with_issues"
        ),
        issue_codes=[
            "road_access_conflict",
        ],
        steps=[],
        report=IncidentReport(
            request_id=(
                request.request_id
            ),
            status="needs_review",
            summary=(
                "Detected 1 configured issue "
                "requiring review: "
                "road_access_conflict."
            ),
            findings=[
                IncidentFinding(
                    issue_code=(
                        "road_access_conflict"
                    ),
                    explanation=(
                        "The request contains "
                        "inconsistent road-access "
                        "fields."
                    ),
                    evidence_ref=(
                        EvidenceReference(
                            tool_name=(
                                "validate_input"
                            )
                        )
                    ),
                    possible_causes=[],
                    recommended_checks=[],
                )
            ],
        ),
        analysis_traces=[],
    )

    return IncidentRunRecord(
        trace_id="TRACE-CANDIDATE-1",
        created_at=datetime.now(
            timezone.utc
        ),
        duration_ms=25.0,
        outcome="success",
        request=request,
        agent_run=agent_run,
        prompt_version=(
            "grounded-explanation-v1"
        ),
        providers=[
            "ollama"
        ],
        models=[
            "phi4-mini:latest"
        ],
    )




def _make_feedback(
    *,
    verdict: str = (
        "partially_correct"
    ),
) -> IncidentFeedbackRecord:
    return IncidentFeedbackRecord(
        feedback_id="FEEDBACK-1",
        trace_id=(
            "TRACE-CANDIDATE-1"
        ),
        created_at=datetime.now(
            timezone.utc
        ),
        verdict=verdict,
        issue_code=(
            "road_access_conflict"
        ),
        expected_issue_codes=[
            "road_access_conflict"
        ],
        comment=(
            "Explanation needs review."
        ),
        corrected_explanation=(
            "The two road-access fields "
            "contradict each other."
        ),
    )




def test_partially_correct_feedback_creates_candidate():
    candidates = build_candidates(
        runs=[
            _make_run_record()
        ],
        feedback_records=[
            _make_feedback()
        ],
    )

    assert len(candidates) == 1

    candidate = candidates[0]

    assert (
        candidate.feedback_id
        == "FEEDBACK-1"
    )

    assert (
        candidate.trace_id
        == "TRACE-CANDIDATE-1"
    )

    assert (
        candidate.status
        == "pending"
    )

    assert (
        candidate.affected_issue_code
        == "road_access_conflict"
    )

    assert (
        candidate.actual_explanation
        == (
            "The request contains "
            "inconsistent road-access "
            "fields."
        )
    )

    assert candidate.provider_names == [
        "ollama"
    ]

    assert candidate.model_names == [
        "phi4-mini:latest"
    ]




def test_correct_feedback_is_ignored():
    feedback = IncidentFeedbackRecord(
        feedback_id="FEEDBACK-CORRECT",
        trace_id=(
            "TRACE-CANDIDATE-1"
        ),
        created_at=datetime.now(
            timezone.utc
        ),
        verdict="correct",
        issue_code=None,
        expected_issue_codes=None,
        comment=None,
        corrected_explanation=None,
    )

    candidates = build_candidates(
        runs=[
            _make_run_record()
        ],
        feedback_records=[
            feedback
        ],
    )

    assert candidates == []






def test_existing_feedback_is_not_duplicated():
    first = build_candidates(
        runs=[
            _make_run_record()
        ],
        feedback_records=[
            _make_feedback()
        ],
    )

    second = build_candidates(
        runs=[
            _make_run_record()
        ],
        feedback_records=[
            _make_feedback()
        ],
        existing_candidates=first,
    )

    assert second == []




def test_unknown_trace_raises_clear_error():
    feedback = IncidentFeedbackRecord(
        feedback_id="FEEDBACK-MISSING",
        trace_id="TRACE-DOES-NOT-EXIST",
        created_at=datetime.now(
            timezone.utc
        ),
        verdict="incorrect",
        issue_code=None,
        expected_issue_codes=None,
        comment=(
            "Wrong result."
        ),
        corrected_explanation=None,
    )

    try:
        build_candidates(
            runs=[],
            feedback_records=[
                feedback
            ],
        )

    except CandidateBuildError as exc:
        assert (
            "unknown runtime trace"
            in str(exc)
        )

    else:
        raise AssertionError(
            "CandidateBuildError "
            "was not raised."
        )