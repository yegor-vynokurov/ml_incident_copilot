from dataclasses import dataclass

from app.agent_prompts import (
    build_agent_prompts,
)
from app.llm.base import LLMProvider
from app.schemas import (
    AgentRun,
    AgentStep,
    KnownIssue,
    LocationStats,
    ModelMetadata,
    PredictionRequest,
    ToolResult,
)
from app.tools.input_validator import (
    validate_input,
)
from app.tools.issue_search import (
    search_known_issues,
)
from app.tools.model_registry import (
    get_model_metadata,
)
from app.tools.prediction_analyzer import (
    analyze_prediction,
)


@dataclass(frozen=True)
class AgentDependencies:
    """
    All dependencies needed for agent
    """

    registry: dict[str, ModelMetadata]

    stats_by_location: dict[
        str,
        LocationStats,
    ]

    known_issues: list[KnownIssue]

    llm_provider: LLMProvider



class MLIncidentAgent:
    """
    Policy-based agent for
    ML prediction incidents.
    """

    def __init__(
        self,
        dependencies: AgentDependencies,
    ) -> None:
        self._dependencies = dependencies

    def run(
        self,
        request: PredictionRequest,
    ) -> AgentRun:
        steps: list[AgentStep] = []
        issue_codes: set[str] = set()

        # 1. Check input data
        validation_result = validate_input(
            request=request,
            supported_locations=set(
                self._dependencies
                .stats_by_location
                .keys()
            ),
        )

        steps.append(
            AgentStep(
                tool_name="validate_input",
                status="executed",
                reason=(
                    "Input validation is required "
                    "for every request."
                ),
                result=validation_result,
            )
        )

        issue_codes.update(
            self._extract_issue_codes(
                validation_result
            )
        )

        # 2. Check used model
        model_result = get_model_metadata(
            request=request,
            registry=(
                self._dependencies.registry
            ),
        )

        steps.append(
            AgentStep(
                tool_name="get_model_metadata",
                status="executed",
                reason=(
                    "The model version and routing "
                    "must be checked for every request."
                ),
                result=model_result,
            )
        )

        issue_codes.update(
            self._extract_issue_codes(
                model_result
            )
        )

        # 3. Check correspondance region
        location_supported = bool(
            validation_result.data
            .get("checks", {})
            .get("location_supported", False)
        )

        if location_supported:
            prediction_result = (
                analyze_prediction(
                    request=request,
                    stats_by_location=(
                        self._dependencies
                        .stats_by_location
                    ),
                )
            )

            steps.append(
                AgentStep(
                    tool_name=(
                        "analyze_prediction"
                    ),
                    status="executed",
                    reason=(
                        "The request location has "
                        "regional reference data."
                    ),
                    result=prediction_result,
                )
            )

            issue_codes.update(
                self._extract_issue_codes(
                    prediction_result
                )
            )

        else:
            steps.append(
                AgentStep(
                    tool_name=(
                        "analyze_prediction"
                    ),
                    status="skipped",
                    reason=(
                        "The request location has no "
                        "regional reference data."
                    ),
                    result=None,
                )
            )

        # 4. Search of the known issues
        if issue_codes:
            issue_search_result = (
                search_known_issues(
                    observed_issue_codes=(
                        issue_codes
                    ),
                    known_issues=(
                        self._dependencies
                        .known_issues
                    ),
                )
            )

            steps.append(
                AgentStep(
                    tool_name=(
                        "search_known_issues"
                    ),
                    status="executed",
                    reason=(
                        "Detected issue codes require "
                        "comparison with known issues."
                    ),
                    result=issue_search_result,
                )
            )

        else:
            steps.append(
                AgentStep(
                    tool_name=(
                        "search_known_issues"
                    ),
                    status="skipped",
                    reason=(
                        "No issue codes were detected."
                    ),
                    result=None,
                )
            )

        # 5. Aggregate prompts
        system_prompt, user_prompt = (
            build_agent_prompts(
                request=request,
                steps=steps,
            )
        )

        # 6. Explanation from the llm
        llm_response = (
            self._dependencies
            .llm_provider
            .generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        )

        status = (
            "completed_with_issues"
            if issue_codes
            else "completed"
        )

        return AgentRun(
            request_id=request.request_id,
            status=status,
            issue_codes=sorted(issue_codes),
            steps=steps,
            llm_response=llm_response,
        )

    @staticmethod
    def _extract_issue_codes(
        result: ToolResult,
    ) -> set[str]:
        raw_codes = result.data.get(
            "issue_codes",
            [],
        )

        if not isinstance(raw_codes, list):
            return set()

        return {
            str(code)
            for code in raw_codes
        }