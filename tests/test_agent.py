from datetime import date
from typing import TypeVar

import json

from pydantic import BaseModel, ValidationError

from app.llm.base import (
    LLMProvider,
    LLMStructuredOutputError,
)
from app.schemas import (
    LLMResponse,
    StructuredLLMResponse,
)

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

import json

from pydantic import (
    BaseModel,
    ValidationError,
)

from app.llm.base import (
    LLMRepairExhaustedError,
    LLMStructuredOutputError,
)

StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)



class MappingFakeLLMProvider:
    """
    Возвращает IssueAnalysis по issue code,
    указанному в user prompt.
    """

    def __init__(
        self,
        outputs_by_issue: dict[str, dict],
    ) -> None:
        self.outputs_by_issue = outputs_by_issue
        self.calls: list[dict] = []

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
        response_model: type[StructuredModelT],
    ) -> StructuredLLMResponse[
        StructuredModelT
    ]:
        issue_code = self._extract_issue_code(
            user_prompt
        )

        self.calls.append(
            {
                "issue_code": issue_code,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )

        try:
            payload = self.outputs_by_issue[
                issue_code
            ]
        except KeyError as exc:
            raise RuntimeError(
                "No fake output configured for "
                f"issue {issue_code!r}."
            ) from exc

        raw_text = json.dumps(
            payload,
            ensure_ascii=False,
        )

        try:
            parsed = response_model.model_validate(
                payload
            )

        except ValidationError as exc:
            # Fake должен вести себя так же,
            # как реальный OllamaProvider.
            raise LLMStructuredOutputError(
                "Fake response does not match "
                "the requested schema.",
                raw_text=raw_text,
                validation_errors=exc.errors(),
            ) from exc

        return StructuredLLMResponse(
            raw_text=raw_text,
            parsed=parsed,
            provider="fake",
            model="fake-model",
            request_id="fake-request",
            input_tokens=100,
            output_tokens=40,
        )

    @staticmethod
    def _extract_issue_code(
        user_prompt: str,
    ) -> str:
        marker = "Issue code for context:"

        if marker not in user_prompt:
            raise RuntimeError(
                "Issue code marker was not found "
                "in the user prompt."
            )

        remainder = user_prompt.split(
            marker,
            maxsplit=1,
        )[1]

        issue_code = (
            remainder
            .strip()
            .splitlines()[0]
            .strip()
        )

        if not issue_code:
            raise RuntimeError(
                "Issue code is empty."
            )

        return issue_code


def create_analysis_outputs() -> dict[str, dict]:
    return {
        "road_access_conflict": {
            "explanation": (
                "The road access fields are "
                "inconsistent and require "
                "source-data review."
            ),
        },
        "prediction_below_reference_range": {
            "explanation": (
                "The predicted price per area is "
                "below the configured regional "
                "reference and requires review."
            ),
        },
        "unsupported_location": {
            "explanation": (
                "The request location is not "
                "supported by the configured "
                "regional data."
            ),
        },
        "model_location_mismatch": {
            "explanation": (
                "The selected model location does "
                "not match the request location."
            ),
        },
    }


def create_analysis_provider(
) -> MappingFakeLLMProvider:
    return MappingFakeLLMProvider(
        outputs_by_issue=(
            create_analysis_outputs()
        )
    )


class SequencedFakeLLMProvider:
    """
    Returns previously added answers by quewe
    """

    def __init__(
        self,
        structured_outputs: list[dict],
    ) -> None:
        self.structured_outputs = list(
            structured_outputs
        )

        self.calls: list[dict] = []

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
                "system_prompt": (
                    system_prompt
                ),
                "user_prompt": user_prompt,
                "response_model": (
                    response_model
                ),
            }
        )

        if not self.structured_outputs:
            raise RuntimeError(
                "No fake structured output "
                "remains."
            )

        payload = (
            self.structured_outputs
            .pop(0)
        )

        raw_text = json.dumps(
            payload,
            ensure_ascii=False,
        )

        try:
            parsed = (
                response_model
                .model_validate(payload)
            )

        except ValidationError as exc:
            raise LLMStructuredOutputError(
                "Fake response does not "
                "match the schema.",
                raw_text=raw_text,
                validation_errors=(
                    exc.errors()
                ),
            ) from exc

        return StructuredLLMResponse(
            raw_text=raw_text,
            parsed=parsed,
            provider="fake",
            model="fake-model",
            request_id="fake-request",
            input_tokens=100,
            output_tokens=40,
        )
    







def create_test_dependencies(
    provider: LLMProvider,
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
    provider = create_analysis_provider()

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

    assert len(provider.calls) == 2

    assert {
        call["issue_code"]
        for call in provider.calls
    } == {
        "road_access_conflict",
        "prediction_below_reference_range",
    }





def test_agent_passes_verified_facts_to_llm():
    provider = create_analysis_provider()

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

    assert len(provider.calls) == 2

    prompts_by_issue = {
        call["issue_code"]: call["user_prompt"]
        for call in provider.calls
    }

    road_prompt = prompts_by_issue[
        "road_access_conflict"
    ]

    prediction_prompt = prompts_by_issue[
        "prediction_below_reference_range"
    ]

    assert '"road_frontage": 0.0' in road_prompt
    assert '"is_landlocked": false' in road_prompt

    assert (
        '"predicted_price_per_area": 1.4118'
        in prediction_prompt
    )

    assert (
        "prediction_below_reference_range"
        not in road_prompt
    )

    assert (
        "road_access_conflict"
        not in prediction_prompt
    )


def test_agent_skips_prediction_analysis_for_unknown_location():
    provider = create_analysis_provider()

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
    assert {
        call["issue_code"]
        for call in provider.calls
    } == {
        "unsupported_location",
        "model_location_mismatch",
    }




def test_agent_skips_issue_search_when_no_issues():
    provider = MappingFakeLLMProvider(
        outputs_by_issue={}
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
    assert result.report.status == "ok"
    assert result.report.findings == []
    assert result.analysis_traces == []
    assert provider.calls == []




def test_agent_returns_structured_report():
    provider = create_analysis_provider()

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

    report = result.report

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

    findings_by_code = {
        finding.issue_code: finding
        for finding in report.findings
    }

    assert (
        findings_by_code[
            "road_access_conflict"
        ].evidence_ref.tool_name
        == "validate_input"
    )

    assert (
        findings_by_code[
            "prediction_below_reference_range"
        ].evidence_ref.tool_name
        == "analyze_prediction"
    )









def test_agent_repairs_old_wrong_evidence_output():
    request_id = "REQ-REPAIR-1"

    # First try reproduces real bug: 
    # Model trys choose the issue code
    # and incorrect evidence tool.
    invalid_first_output = {
        "issue_code": (
            "road_access_conflict"
        ),
        "explanation": (
            "The predicted price per area "
            "is below the regional reference."
        ),
        "evidence_ref": {
            "tool_name": (
                "analyze_prediction"
            )
        },
    }

    valid_repair_output = {
        "explanation": (
            "road_frontage is 0 while "
            "is_landlocked is false, so the "
            "road-access fields are inconsistent "
            "and require source-data review."
        )
    }

    provider = SequencedFakeLLMProvider(
        structured_outputs=[
            invalid_first_output,
            valid_repair_output,
        ]
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    # Price is located exactly on the median:
    # 21000 / 5000 = 4.2.
    # So only problem is the:
    # road_access_conflict.
    request = PredictionRequest(
        request_id=request_id,
        location="district_07",
        area=5000,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=21000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    assert len(provider.calls) == 2

    assert result.issue_codes == [
        "road_access_conflict"
    ]

    assert len(
        result.report.findings
    ) == 1

    finding = result.report.findings[0]

    # This fields marks Python,
    # but not LLM.
    assert finding.issue_code == (
        "road_access_conflict"
    )

    assert (
        finding.evidence_ref.tool_name
        == "validate_input"
    )

    assert finding.possible_causes == [
        "Incorrect source data"
    ]

    assert finding.recommended_checks == [
        "Verify the source record"
    ]

    assert len(
        result.analysis_traces
    ) == 1

    assert (
        result.analysis_traces[0]
        .response
        .attempt_count
        == 2
    )





def test_agent_fails_after_repair_is_exhausted():
    invalid_output = {
        "issue_code": (
            "road_access_conflict"
        ),
        "evidence_ref": {
            "tool_name": (
                "analyze_prediction"
            )
        },
        "explanation": (
            "Incorrect mixed explanation."
        ),
    }

    provider = SequencedFakeLLMProvider(
        structured_outputs=[
            invalid_output,
            invalid_output,
        ]
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-REPAIR-FAIL",
        location="district_07",
        area=5000,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=21000,
        model_version="district_07_v3",
    )

    with pytest.raises(
        LLMRepairExhaustedError
    ):
        agent.run(request)

    assert len(provider.calls) == 2


def test_agent_does_not_call_llm_when_no_issues():
    provider = SequencedFakeLLMProvider(
        structured_outputs=[]
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-NO-ISSUES",
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

    assert result.report.status == "ok"
    assert result.report.findings == []

    assert result.analysis_traces == []

    assert provider.calls == []




def test_agent_analyzes_each_issue_separately():
    provider = SequencedFakeLLMProvider(
        structured_outputs=[
            {
                "explanation": (
                    "The prediction is below the "
                    "configured regional reference."
                )
            },
            {
                "explanation": (
                    "The road-access fields "
                    "are inconsistent."
                )
            },
        ]
    )

    agent = MLIncidentAgent(
        create_test_dependencies(
            provider
        )
    )

    request = PredictionRequest(
        request_id="REQ-TWO-ISSUES",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = agent.run(request)

    assert len(provider.calls) == 2

    prompts = [
        call["user_prompt"]
        for call in provider.calls
    ]

    road_prompts = [
        prompt
        for prompt in prompts
        if (
            "road_access_conflict"
            in prompt
        )
    ]

    prediction_prompts = [
        prompt
        for prompt in prompts
        if (
            "prediction_below_reference_range"
            in prompt
        )
    ]

    assert len(road_prompts) == 1
    assert len(prediction_prompts) == 1

    assert (
        "prediction_below_reference_range"
        not in road_prompts[0]
    )

    assert (
        "road_access_conflict"
        not in prediction_prompts[0]
    )

    assert (
        result.report.status
        == "needs_review"
    )




