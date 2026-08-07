from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from app.observability.schemas import (
    IncidentRunRecord,
)
from app.observability.store import (
    JsonlRunStore,
)
from app.schemas import (
    AgentRun,
    IncidentReport,
    PredictionRequest,
)


def test_jsonl_store_appends_and_reads_run(
    tmp_path: Path,
):
    store = JsonlRunStore(
        runs_path=(
            tmp_path / "runs.jsonl"
        ),
        feedback_path=(
            tmp_path / "feedback.jsonl"
        ),
    )

    request = PredictionRequest(
        request_id="STORE-TEST-1",
        location="district_07",
        area=5000,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=21000,
        model_version="district_07_v3",
    )

    agent_run = AgentRun(
        request_id=request.request_id,
        status="completed",
        issue_codes=[],
        steps=[],
        report=IncidentReport(
            request_id=request.request_id,
            status="ok",
            summary=(
                "No configured issue "
                "was detected."
            ),
            findings=[],
        ),
        analysis_traces=[],
    )

    record = IncidentRunRecord(
        trace_id="TRACE-1",
        created_at=datetime.now(
            timezone.utc
        ),
        duration_ms=1.25,
        outcome="success",
        request=request,
        agent_run=agent_run,
        prompt_version=(
            "grounded-explanation-v1"
        ),
        providers=[],
        models=[],
    )

    store.append_run(
        record
    )

    loaded = store.get_run(
        "TRACE-1"
    )

    assert loaded is not None
    assert loaded.trace_id == "TRACE-1"
    assert loaded.outcome == "success"

    assert (
        loaded.request.request_id
        == "STORE-TEST-1"
    )