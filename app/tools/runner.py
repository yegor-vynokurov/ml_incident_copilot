from app.schemas import (
    KnownIssue,
    LocationStats,
    ModelMetadata,
    PredictionRequest,
    ToolResult,
)
from app.tools.input_validator import validate_input
from app.tools.issue_search import search_known_issues
from app.tools.model_registry import get_model_metadata
from app.tools.prediction_analyzer import (
    analyze_prediction,
)


def extract_issue_codes(
    result: ToolResult,
) -> set[str]:
    raw_codes = result.data.get(
        "issue_codes",
        [],
    )

    return set(raw_codes)


def run_domain_tools(
    request: PredictionRequest,
    registry: dict[str, ModelMetadata],
    stats_by_location: dict[str, LocationStats],
    known_issues: list[KnownIssue],
) -> list[ToolResult]:
    """
    Run all tools without llm.
    """

    supported_locations = set(
        stats_by_location.keys()
    )

    validation_result = validate_input(
        request=request,
        supported_locations=supported_locations,
    )

    model_result = get_model_metadata(
        request=request,
        registry=registry,
    )

    prediction_result = analyze_prediction(
        request=request,
        stats_by_location=stats_by_location,
    )

    observed_issue_codes = set()

    for result in (
        validation_result,
        model_result,
        prediction_result,
    ):
        observed_issue_codes.update(
            extract_issue_codes(result)
        )

    issue_search_result = search_known_issues(
        observed_issue_codes=observed_issue_codes,
        known_issues=known_issues,
    )

    return [
        validation_result,
        model_result,
        prediction_result,
        issue_search_result,
    ]