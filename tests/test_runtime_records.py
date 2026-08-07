from app.observability.records import (
    build_success_run_record,
)
from app.schemas import (
    AgentRun,
    IncidentReport,
    PredictionRequest,
)


def test_success_record_has_no_model_when_llm_was_not_called():
    request = PredictionRequest(
        request_id="RUNTIME-1",
        location="district_07",
        area=5000,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=21000,
        model_version="district_07_v3",
    )

    run = AgentRun(
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

    record = build_success_run_record(
        trace_id="TRACE-NORMAL",
        request=request,
        agent_run=run,
        duration_ms=1.5,
    )

    assert record.outcome == "success"
    assert record.providers == []
    assert record.models == []

    assert (
        record.prompt_version
        == "grounded-explanation-v1"
    )