from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

import pytest

from app.evaluation.candidate_schemas import (
    EvaluationCandidate,
)
from app.evaluation.candidate_store import (
    CandidateStoreError,
    append_candidate,
    load_candidates,
)
from app.schemas import (
    PredictionRequest,
)




def _make_candidate() -> EvaluationCandidate:
    request = PredictionRequest(
        request_id="REQ-STORE-1",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    return EvaluationCandidate(
        candidate_id=(
            "feedback-FEEDBACK-STORE-1"
        ),
        feedback_id=(
            "FEEDBACK-STORE-1"
        ),
        trace_id="TRACE-STORE-1",
        created_at=datetime.now(
            timezone.utc
        ),
        status="pending",
        source_request=request,
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
            "Example actual explanation."
        ),
        corrected_explanation=(
            "Example corrected explanation."
        ),
        feedback_verdict=(
            "partially_correct"
        ),
        feedback_comment=(
            "Needs review."
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



def test_candidate_is_written_and_loaded(
    tmp_path: Path,
):
    path = (
        tmp_path
        / "candidates.jsonl"
    )

    candidate = (
        _make_candidate()
    )

    append_candidate(
        path=path,
        candidate=candidate,
    )

    loaded = load_candidates(
        path
    )

    assert len(loaded) == 1

    assert (
        loaded[0].candidate_id
        == candidate.candidate_id
    )

    assert (
        loaded[0].feedback_id
        == "FEEDBACK-STORE-1"
    )





def test_missing_candidate_file_is_empty(
    tmp_path: Path,
):
    loaded = load_candidates(
        tmp_path
        / "does-not-exist.jsonl"
    )

    assert loaded == []



def test_invalid_candidate_jsonl_has_line_number(
    tmp_path: Path,
):
    path = (
        tmp_path
        / "candidates.jsonl"
    )

    path.write_text(
        '{"broken": true}\n'
        'not-json\n',
        encoding="utf-8",
    )

    with pytest.raises(
        CandidateStoreError,
    ) as exc_info:
        load_candidates(
            path
        )

    assert (
        "line 1"
        in str(exc_info.value)
    )



