import logging

from fastapi.testclient import (
    TestClient,
)

from app.api import create_app
from app.llm.base import (
    LLMProviderError,
    LLMRepairExhaustedError,
)
from app.observability.store import JsonlRunStore
from app.report_validation import (
    ReportGroundingError,
)
from app.schemas import (
    AgentRun,
    IncidentReport,
    PredictionRequest,
)


class FakeAgent:
    """
    min agent for API-tests.
    """

    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self.error = error

        self.calls: list[
            PredictionRequest
        ] = []

    def run(
        self,
        request: PredictionRequest,
    ) -> AgentRun:
        self.calls.append(
            request
        )

        if self.error is not None:
            raise self.error

        return AgentRun(
            request_id=request.request_id,
            status="completed",
            issue_codes=[],
            steps=[],
            report=IncidentReport(
                request_id=(
                    request.request_id
                ),
                status="ok",
                summary=(
                    "No configured issue "
                    "was detected."
                ),
                findings=[],
            ),
            analysis_traces=[],
        )


def valid_payload() -> dict:
    return {
        "request_id": "REQ-API-1",
        "location": "district_07",
        "area": 5000,
        "road_frontage": 10,
        "is_landlocked": False,
        "predicted_price": 21000,
        "model_version": (
            "district_07_v3"
        ),
    }




def test_health_endpoint():
    app = create_app(
        agent=FakeAgent()
    )

    with TestClient(app) as client:
        response = client.get(
            "/v1/health"
        )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": (
            "ml-incident-copilot"
        ),
        "version": "0.1.0",
    }

    assert (
        response.headers.get(
            "X-Trace-ID"
        )
        is not None
    )




def test_analyze_incident_success():
    fake_agent = FakeAgent()

    app = create_app(
        agent=fake_agent
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/incidents/analyze",
            json=valid_payload(),
        )

    assert response.status_code == 200

    body = response.json()

    assert body["request_id"] == (
        "REQ-API-1"
    )

    assert body["status"] == (
        "completed"
    )

    assert body["report"]["status"] == (
        "ok"
    )

    assert len(fake_agent.calls) == 1

    assert (
        fake_agent.calls[0].request_id
        == "REQ-API-1"
    )




def test_invalid_request_returns_contract():
    app = create_app(
        agent=FakeAgent()
    )

    payload = valid_payload()

    payload["area"] = 0

    with TestClient(app) as client:
        response = client.post(
            "/v1/incidents/analyze",
            json=payload,
        )

    assert response.status_code == 422

    body = response.json()

    assert body["error"]["code"] == (
        "request_validation_error"
    )

    assert (
        body["error"]["retryable"]
        is False
    )

    assert body["error"]["trace_id"]

    assert (
        isinstance(
            body["error"]["details"],
            list,
        )
    )




def test_llm_provider_error_returns_503():
    fake_agent = FakeAgent(
        error=LLMProviderError(
            "Ollama is unavailable."
        )
    )

    app = create_app(
        agent=fake_agent
    )

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/v1/incidents/analyze",
            json=valid_payload(),
        )

    assert response.status_code == 503

    body = response.json()

    assert body["error"]["code"] == (
        "llm_provider_unavailable"
    )

    assert (
        body["error"]["retryable"]
        is True
    )

    assert body["error"]["request_id"] == (
        "REQ-API-1"
    )





def test_repair_exhausted_returns_502():
    fake_agent = FakeAgent(
        error=LLMRepairExhaustedError(
            "Repair attempts exhausted."
        )
    )

    app = create_app(
        agent=fake_agent
    )

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/v1/incidents/analyze",
            json=valid_payload(),
        )

    assert response.status_code == 502

    body = response.json()

    assert body["error"]["code"] == (
        "llm_output_invalid"
    )

    assert (
        body["error"]["retryable"]
        is True
    )





def test_grounding_error_returns_500():
    fake_agent = FakeAgent(
        error=ReportGroundingError(
            "Wrong evidence tool."
        )
    )

    app = create_app(
        agent=fake_agent
    )

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/v1/incidents/analyze",
            json=valid_payload(),
        )

    assert response.status_code == 500

    body = response.json()

    assert body["error"]["code"] == (
        "internal_consistency_error"
    )

    assert (
        body["error"]["retryable"]
        is False
    )

    # Inner test of exception does not allow to go outside
    assert "Wrong evidence tool" not in (
        response.text
    )


def test_operational_events_are_logged_without_request_body(caplog, tmp_path):
    store = JsonlRunStore(
        runs_path=tmp_path / "runs.jsonl",
        feedback_path=tmp_path / "feedback.jsonl",
    )
    app = create_app(agent=FakeAgent(), run_store=store)
    payload = valid_payload()

    with caplog.at_level(logging.INFO, logger="app"):
        with TestClient(app) as client:
            response = client.post("/v1/incidents/analyze", json=payload)
            trace_id = response.headers["X-Trace-ID"]
            feedback = client.post(
                f"/v1/incidents/{trace_id}/feedback",
                json={"verdict": "correct", "comment": "private note"},
            )
            invalid = client.post(
                "/v1/incidents/analyze",
                json={**payload, "area": 0},
            )

        failing_app = create_app(
            agent=FakeAgent(error=LLMProviderError("Ollama is unavailable.")),
            run_store=store,
        )
        with TestClient(failing_app, raise_server_exceptions=False) as client:
            failure = client.post("/v1/incidents/analyze", json=payload)

    assert response.status_code == 200
    assert feedback.status_code == 200
    assert invalid.status_code == 422
    assert failure.status_code == 503
    messages = [record.getMessage() for record in caplog.records]
    assert any("analysis_started" in message and trace_id in message for message in messages)
    assert any("analysis_completed" in message and "duration_ms=" in message for message in messages)
    assert any("feedback_recorded" in message and trace_id in message for message in messages)
    assert any("request_rejected" in message for message in messages)
    assert any("analysis_failed" in message and "LLMProviderError" in message for message in messages)
    assert all("private note" not in message for message in messages)





