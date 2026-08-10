from datetime import (
    datetime,
    timezone,
)

from app.evaluation.candidate_export import (
    build_approved_case_drafts,
    build_case_draft,
)
from app.evaluation.candidate_schemas import (
    EvaluationCandidate,
)
from app.schemas import (
    PredictionRequest,
)


def _candidate(
    *,
    status: str,
) -> EvaluationCandidate:
    return EvaluationCandidate(
        candidate_id="feedback-F-1",
        feedback_id="F-1",
        trace_id="T-1",
        created_at=datetime.now(
            timezone.utc
        ),
        status=status,
        source_request=PredictionRequest(
            request_id="REQ-1",
            location="district_07",
            area=8500,
            road_frontage=0,
            is_landlocked=False,
            predicted_price=12000,
            model_version=(
                "district_07_v3"
            ),
        ),
        actual_issue_codes=[
            "road_access_conflict"
        ],
        expected_issue_codes=[
            "road_access_conflict"
        ],
        affected_issue_code=(
            "road_access_conflict"
        ),
        actual_explanation=(
            "Actual explanation."
        ),
        corrected_explanation=(
            "Corrected explanation."
        ),
        feedback_verdict=(
            "partially_correct"
        ),
        feedback_comment=(
            "Needs improvement."
        ),
        prompt_version=(
            "grounded-explanation-v1"
        ),
        provider_names=[
            "ollama"
        ],
        model_names=[
            "phi4-mini:latest"
        ],
    )




def test_approved_candidate_builds_draft():
    candidate = _candidate(
        status="approved"
    )

    draft = build_case_draft(
        candidate
    )

    assert (
        draft["source_candidate_id"]
        == "feedback-F-1"
    )

    assert (
        draft["request"]["request_id"]
        == "REQ-1"
    )

    assert (
        draft[
            "suggested_expected_issue_codes"
        ]
        == [
            "road_access_conflict"
        ]
    )




def test_rejected_candidate_is_not_exported():
    drafts = (
        build_approved_case_drafts(
            [
                _candidate(
                    status="rejected"
                )
            ]
        )
    )

    assert drafts == []


