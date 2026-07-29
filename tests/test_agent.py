from datetime import date
from typing import TypeVar

import pytest
from pydantic import BaseModel

from app.agent import (
    AgentDependencies,
    MLIncidentAgent,
)
from app.report_validation import (
    ReportGroundingError,
)
from app.schemas import (
    IncidentReport,
    KnownIssue,
    LLMResponse,
    LocationStats,
    ModelMetadata,
    PredictionRequest,
    StructuredLLMResponse,
)

StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)



class FakeLLMProvider:
    def __init__(
        self,
        structured_data: dict | None = None,
    ) -> None:
        self.calls: list[dict] = []

        self.structured_data = (
            structured_data
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        return LLMResponse(
            text="Fake text response.",
            provider="fake",
            model="fake-model",
        )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[
            StructuredModelT
        ],
    ) -> StructuredLLMResponse[
        StructuredModelT
    ]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": (
                    response_model
                ),
            }
        )

        if self.structured_data is None:
            raise RuntimeError(
                "Fake structured data "
                "was not configured."
            )

        parsed = response_model.model_validate(
            self.structured_data
        )

        return StructuredLLMResponse(
            raw_text=parsed.model_dump_json(),
            parsed=parsed,
            provider="fake",
            model="fake-model",
            request_id="fake-request",
            input_tokens=100,
            output_tokens=40,
        )


def create_valid_incident_report_data(
    request_id: str,
) -> dict:
    return {
        "request_id": request_id,
        "status": "needs_review",
        "summary": (
            "Two configured issues "
            "require review."
        ),
        "findings": [
            {
                "issue_code": (
                    "road_access_conflict"
                ),
                "explanation": (
                    "The configured road access "
                    "fields are inconsistent."
                ),
                "evidence_ref": {
                    "tool_name": "validate_input",
                },
                "possible_causes": [
                    "Incorrect source data",
                ],
                "recommended_checks": [
                    "Verify the source record",
                ],
            },
            {
                "issue_code": (
                    "prediction_below_reference_range"
                ),
                "explanation": (
                    "The predicted price per area "
                    "is below the configured range."
                ),
                "evidence_ref": {
                    "tool_name": (
                        "analyze_prediction"
                    ),
                },
                "possible_causes": [
                    "Unusual property characteristics",
                ],
                "recommended_checks": [
                    "Compare with regional examples",
                ],
            },
        ],
    }






def create_test_dependencies(
    provider: FakeLLMProvider,
) -> AgentDependencies:
    registry = {
        "district_07_v3": ModelMetadata(
            model_version="district_07_v3",
            location="district_07",
            training_date=date(
                2026,
                6,
                15,
            ),
            validation_smape=18.4,
            supported_area_range=(
                300,
                12000,
            ),
            is_active=True,
        )
    }

    stats_by_location = {
        "district_07": LocationStats(
            location="district_07",
            median_price_per_area=4.2,
            p10_price_per_area=2.3,
            p90_price_per_area=7.8,
            sample_size=184,
        )
    }

    known_issues = [
        KnownIssue(
            issue_id=(
                "input_data_contradiction"
            ),
            title=(
                "Contradictory access fields"
            ),
            trigger_codes=[
                "road_access_conflict"
            ],
            possible_causes=[
                "Incorrect source data"
            ],
            recommended_checks=[
                "Verify the source record"
            ],
        ),
        KnownIssue(
            issue_id="prediction_outlier",
            title=(
                "Prediction outside reference range"
            ),
            trigger_codes=[
                "prediction_below_reference_range"
            ],
            possible_causes=[
                "Unusual property characteristics"
            ],
            recommended_checks=[
                "Compare with regional examples"
            ],
        ),
    ]

    return AgentDependencies(
        registry=registry,
        stats_by_location=stats_by_location,
        known_issues=known_issues,
        llm_provider=provider,
    )


def create_unknown_location_report_data(
    request_id: str,
) -> dict:
    return {
        "request_id": request_id,
        "status": "needs_review",
        "summary": (
            "The request location and model routing "
            "require review."
        ),
        "findings": [
            {
                "issue_code": "unsupported_location",
                "explanation": (
                    "The request location is not "
                    "supported."
                ),
                "evidence_ref": {
                    "tool_name": "validate_input",
                },
                "possible_causes": [],
                "recommended_checks": [],
            },
            {
                "issue_code": (
                    "model_location_mismatch"
                ),
                "explanation": (
                    "The selected model does not "
                    "match the request location."
                ),
                "evidence_ref": {
                    "tool_name": (
                        "get_model_metadata"
                    ),
                },
                "possible_causes": [],
                "recommended_checks": [],
            },
        ],
    }






def test_agent_runs_required_tools():
    provider = FakeLLMProvider(
        structured_data=(
            create_valid_incident_report_data(
                "REQ-TEST-1"
            )
        )
    )

    dependencies = create_test_dependencies(
        provider
    )

    agent = MLIncidentAgent(
        dependencies
    )

    request = PredictionRequest(
        request_id="REQ-TEST-1",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    assert result.status == (
        "completed_with_issues"
    )

    assert result.issue_codes == [
        "prediction_below_reference_range",
        "road_access_conflict",
    ]

    step_names = [
        step.tool_name
        for step in result.steps
    ]

    assert step_names == [
        "validate_input",
        "get_model_metadata",
        "analyze_prediction",
        "search_known_issues",
    ]

    assert all(
        step.status == "executed"
        for step in result.steps
    )

    assert len(provider.calls) == 1

def test_agent_passes_verified_facts_to_llm():
    provider = FakeLLMProvider(
        structured_data=(
            create_valid_incident_report_data(
                "REQ-TEST-2"
            )
        )
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TEST-2",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    agent.run(request)

    assert len(provider.calls) == 1

    user_prompt = (
        provider.calls[0]["user_prompt"]
    )

    assert "road_access_conflict" in user_prompt

    assert (
        "prediction_below_reference_range"
        in user_prompt
    )

    assert '"road_frontage": 0.0' in (
        user_prompt
    ) or '"road_frontage": 0' in (
        user_prompt
    )

    assert '"is_landlocked": false' in (
        user_prompt
    )


def test_agent_skips_prediction_analysis_for_unknown_location():
    provider = FakeLLMProvider(
        structured_data=(
            create_unknown_location_report_data(
                "REQ-TEST-3"
            )
        )
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TEST-3",
        location="unknown_district",
        area=8500,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    prediction_step = next(
        step
        for step in result.steps
        if (
            step.tool_name
            == "analyze_prediction"
        )
    )

    assert prediction_step.status == "skipped"

    assert (
        "no regional reference data"
        in prediction_step.reason.lower()
    )

def test_agent_skips_issue_search_when_no_issues():
    provider = FakeLLMProvider(
        structured_data=(
            create_ok_report_data(
                "REQ-TEST-4"
            )
        )
    )

    dependencies = create_test_dependencies(
        provider
    )

    agent = MLIncidentAgent(
        dependencies
    )

    request = PredictionRequest(
        request_id="REQ-TEST-4",
        location="district_07",
        area=5000,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=21000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    assert result.status == "completed"
    assert result.issue_codes == []

    issue_search_step = next(
        step
        for step in result.steps
        if step.tool_name == "search_known_issues"
    )

    assert issue_search_step.status == "skipped"


def test_agent_returns_structured_report():
    provider = FakeLLMProvider(
        structured_data=(
            create_valid_incident_report_data(
                "REQ-TEST-1"
            )
        )
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TEST-1",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    report = result.llm_response.parsed

    assert isinstance(
        report,
        IncidentReport,
    )

    assert report.request_id == (
        "REQ-TEST-1"
    )

    assert report.status == (
        "needs_review"
    )

    assert {
        finding.issue_code
        for finding in report.findings
    } == {
        "road_access_conflict",
        "prediction_below_reference_range",
    }




def test_agent_rejects_invented_issue_code():
    '''unresolved issue code'''
    invalid_data = (
        create_valid_incident_report_data(
            "REQ-TEST-2"
        )
    )

    invalid_data["findings"].append(
        {
            "issue_code": "invented_issue",
            "explanation": (
                "An invented issue."
            ),
            "evidence_ref": {
                "tool_name": "validate_input",
            },
            "possible_causes": [],
            "recommended_checks": [],
        }
    )

    provider = FakeLLMProvider(
        structured_data=invalid_data
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TEST-2",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    with pytest.raises(
        ReportGroundingError
    ):
        agent.run(request)



def test_agent_rejects_unsupported_check():
    '''unresolved recomendation'''
    invalid_data = (
        create_valid_incident_report_data(
            "REQ-TEST-3"
        )
    )

    invalid_data["findings"][0][
        "recommended_checks"
    ].append(
        "Check OpenStreetMap"
    )

    provider = FakeLLMProvider(
        structured_data=invalid_data
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TEST-3",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    with pytest.raises(
        ReportGroundingError,
        match="Unsupported recommended check",
    ):
        agent.run(request)



def create_ok_report_data(
    request_id: str,
) -> dict:
    '''no problem report'''
    return {
        "request_id": request_id,
        "status": "ok",
        "summary": (
            "No configured issue was detected."
        ),
        "findings": [],
    }

def test_agent_accepts_empty_report_when_no_issues():
    '''test for no problem report'''
    provider = FakeLLMProvider(
        structured_data=(
            create_ok_report_data(
                "REQ-TEST-4"
            )
        )
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TEST-4",
        location="district_07",
        area=5000,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=21000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    assert result.status == "completed"

    assert (
        result.llm_response.parsed.status
        == "ok"
    )

    assert (
        result.llm_response
        .parsed
        .findings
        == []
    )


def test_agent_rejects_wrong_evidence_tool():
    request_id = "REQ-TEST-WRONG-TOOL"

    invalid_data = (
        create_valid_incident_report_data(
            request_id
        )
    )

    invalid_data["findings"][0][
        "evidence_ref"
    ] = {
        "tool_name": "analyze_prediction",
    }

    provider = FakeLLMProvider(
        structured_data=invalid_data
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id=request_id,
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    with pytest.raises(
        ReportGroundingError,
        match="did not produce issue",
    ):
        agent.run(request)