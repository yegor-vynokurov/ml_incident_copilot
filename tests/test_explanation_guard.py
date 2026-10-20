from app.incident_builder import IssueContext, build_grounded_issue_data
from app.issue_analysis_prompts import validate_issue_explanation
from app.llm.repair import generate_structured_with_repair
from app.schemas import IssueAnalysis, PredictionRequest, StructuredLLMResponse


class SequencedProvider:
    def __init__(self, explanations):
        self.explanations = iter(explanations)
        self.calls = 0

    def generate_structured(self, **kwargs):
        self.calls += 1
        parsed = IssueAnalysis(explanation=next(self.explanations))
        return StructuredLLMResponse(
            raw_text=parsed.model_dump_json(),
            parsed=parsed,
            provider="fake",
            model="fake-model",
        )


def test_sparse_context_and_semantic_repair():
    request = PredictionRequest(
        request_id="SPARSE-TEST",
        location="district_08",
        area=5000,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=25500,
        model_version="district_08_v2",
    )
    grounded = build_grounded_issue_data(
        issue_code="sparse_location_data",
        request=request,
        source_data={
            "reference_sample_size": 26,
            "sparse_sample_threshold": 30,
        },
    )
    assert grounded.relevant_evidence == {
        "request_location": "district_08",
        "reference_sample_size": 26,
        "sparse_sample_threshold": 30,
    }
    context = IssueContext(
        issue_code="sparse_location_data",
        evidence_tool="analyze_prediction",
        evidence=[],
        relevant_evidence=grounded.relevant_evidence,
        grounded_statement=grounded.grounded_statement,
        possible_causes=[],
        recommended_checks=[],
    )
    provider = SequencedProvider(
        [
            "The model location does not match the request location.",
            "The regional reference has 26 samples, below the threshold of 30.",
        ]
    )

    result = generate_structured_with_repair(
        provider=provider,
        system_prompt="Use only verified facts.",
        user_prompt="Explain the sparse reference data.",
        response_model=IssueAnalysis,
        validate_parsed=lambda analysis: validate_issue_explanation(context, analysis),
    )

    assert provider.calls == 2
    assert result.attempt_count == 2
    assert "26 samples" in result.parsed.explanation
