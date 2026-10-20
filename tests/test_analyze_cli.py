import json

from fastapi.testclient import TestClient

from app.api import create_app
from app.bootstrap import build_agent
from app.evaluation.fake_provider import DeterministicEvaluationLLMProvider
from app.observability.store import JsonlRunStore
from scripts.analyze import main


def test_cli_accepts_custom_json_from_stdin(monkeypatch, capsys):
    payload = {
        "request_id": "OWN-001",
        "location": "district_07",
        "area": 5000,
        "road_frontage": 10,
        "is_landlocked": False,
        "predicted_price": 21000,
        "model_version": "district_07_v3",
    }
    monkeypatch.setattr("sys.stdin.read", lambda: json.dumps(payload))

    assert main(["--input", "-"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["request_id"] == "OWN-001"
    assert report["status"] == "ok"


def test_offline_agent_loads_data_outside_project_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    agent = build_agent(llm_provider=DeterministicEvaluationLLMProvider())
    assert agent is not None


def test_api_runs_real_pipeline_with_offline_provider(tmp_path):
    store = JsonlRunStore(
        runs_path=tmp_path / "runs.jsonl",
        feedback_path=tmp_path / "feedback.jsonl",
    )
    app = create_app(
        agent=build_agent(llm_provider=DeterministicEvaluationLLMProvider()),
        run_store=store,
    )
    payload = {
        "request_id": "API-PIPELINE-001",
        "location": "district_07",
        "area": 8500,
        "road_frontage": 0,
        "is_landlocked": False,
        "predicted_price": 12000,
        "model_version": "district_07_v3",
    }

    with TestClient(app) as client:
        response = client.post("/v1/incidents/analyze", json=payload)
        trace_id = response.headers["X-Trace-ID"]
        feedback = client.post(
            f"/v1/incidents/{trace_id}/feedback",
            json={"verdict": "correct"},
        )

    assert response.status_code == 200
    assert set(response.json()["issue_codes"]) == {
        "road_access_conflict",
        "prediction_below_reference_range",
    }
    assert store.get_run(trace_id) is not None
    assert feedback.status_code == 200
    assert feedback.json()["status"] == "recorded"
