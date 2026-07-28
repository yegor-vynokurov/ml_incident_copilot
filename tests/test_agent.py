from datetime import date

from app.agent import (
    AgentDependencies,
    MLIncidentAgent,
)
from app.schemas import (
    KnownIssue,
    LLMResponse,
    LocationStats,
    ModelMetadata,
    PredictionRequest,
)

class FakeLLMProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )

        return LLMResponse(
            text=(
                "The request requires engineering "
                "review."
            ),
            provider="fake",
            model="fake-model",
            request_id="fake-request",
            input_tokens=100,
            output_tokens=20,
        )

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

def test_agent_runs_required_tools():
    provider = FakeLLMProvider()

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
    provider = FakeLLMProvider()

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
    provider = FakeLLMProvider()

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
    provider = FakeLLMProvider()

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
        if (
            step.tool_name
            == "search_known_issues"
        )
    )

    assert issue_search_step.status == "skipped"
