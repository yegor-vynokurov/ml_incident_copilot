from collections import defaultdict
from dataclasses import dataclass
from typing import Any, cast

from pydantic import (
    BaseModel,
    ConfigDict,
)

from app.schemas import (
    AgentStep,
    EvidenceReference,
    EvidenceToolName,
    IncidentFinding,
    IncidentReport,
    IssueAnalysis,
    PredictionRequest,
)


class IncidentBuildError(ValueError):
    """
    Determine incident report did not collected
    """


@dataclass(frozen=True)
class IssueContext:
    issue_code: str

    evidence_tool: EvidenceToolName

    evidence: list[dict[str, Any]]

    relevant_evidence: dict[str, Any]

    grounded_statement: str

    possible_causes: list[str]

    recommended_checks: list[str]



from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
)


class GroundedIssueData(BaseModel):
    """
    Facts that python creates especially for expalinig of the one problem
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    relevant_evidence: dict[str, Any]

    grounded_statement: str


EVIDENCE_TOOL_NAMES = {
    "validate_input",
    "get_model_metadata",
    "analyze_prediction",
}


def _append_unique(
    target: list[str],
    values: list,
) -> None:
    for value in values:
        string_value = str(value)

        if string_value not in target:
            target.append(string_value)


def build_issue_contexts(
    *,
    issue_codes: set[str],
    steps: list[AgentStep],
    request: PredictionRequest,
) -> list[IssueContext]:
    """
    Creates one deterministic card for each issue code
    """

    source_by_code: dict[
        str,
        EvidenceToolName,
    ] = {}

    source_data_by_code: dict[
        str,
        dict[str, Any],
    ] = {}

    evidence_by_code: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    causes_by_code: dict[
        str,
        list[str],
    ] = defaultdict(list)

    checks_by_code: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for step in steps:
        if (
            step.status != "executed"
            or step.result is None
        ):
            continue

        result_data = step.result.data

        if (
            step.tool_name
            in EVIDENCE_TOOL_NAMES
        ):
            raw_codes = result_data.get(
                "issue_codes",
                [],
            )

            if isinstance(raw_codes, list):
                for raw_code in raw_codes:
                    issue_code = str(
                        raw_code
                    )

                    if (
                        issue_code
                        not in source_by_code
                    ):
                        source_by_code[
                            issue_code
                        ] = cast(
                            EvidenceToolName,
                            step.tool_name,
                        )

                        source_data_by_code[
                            issue_code
                        ] = result_data

            raw_evidence = result_data.get(
                "evidence",
                [],
            )

            if isinstance(
                raw_evidence,
                list,
            ):
                for item in raw_evidence:
                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    evidence_code = item.get(
                        "issue_code"
                    )

                    if evidence_code is None:
                        continue

                    evidence_by_code[
                        str(evidence_code)
                    ].append(item)

        if (
            step.tool_name
            == "search_known_issues"
        ):
            matches = result_data.get(
                "matches",
                [],
            )

            if not isinstance(matches, list):
                continue

            for match in matches:
                if not isinstance(
                    match,
                    dict,
                ):
                    continue

                matched_codes = match.get(
                    "matched_codes",
                    [],
                )

                possible_causes = match.get(
                    "possible_causes",
                    [],
                )

                recommended_checks = match.get(
                    "recommended_checks",
                    [],
                )

                if not isinstance(
                    matched_codes,
                    list,
                ):
                    continue

                for raw_code in matched_codes:
                    issue_code = str(
                        raw_code
                    )

                    if isinstance(
                        possible_causes,
                        list,
                    ):
                        _append_unique(
                            causes_by_code[
                                issue_code
                            ],
                            possible_causes,
                        )

                    if isinstance(
                        recommended_checks,
                        list,
                    ):
                        _append_unique(
                            checks_by_code[
                                issue_code
                            ],
                            recommended_checks,
                        )

    contexts: list[IssueContext] = []

    for issue_code in sorted(
        issue_codes
    ):
        evidence_tool = source_by_code.get(
            issue_code
        )

        if evidence_tool is None:
            raise IncidentBuildError(
                "No deterministic source tool "
                f"was found for {issue_code!r}."
            )

        source_data = (
            source_data_by_code.get(
                issue_code
            )
        )

        if source_data is None:
            raise IncidentBuildError(
                "No deterministic source data "
                f"was found for {issue_code!r}."
            )

        evidence = evidence_by_code.get(
            issue_code,
            [],
        )


        if not evidence:
            fallback_details = {
                key: value
                for key, value
                in source_data.items()
                if key != "issue_codes"
            }

            evidence = [
                {
                    "issue_code": issue_code,
                    "tool_name": evidence_tool,
                    "details": (
                        fallback_details
                    ),
                }
            ]

        grounded_data = (
            build_grounded_issue_data(
                issue_code=issue_code,
                request=request,
                source_data=source_data,
            )
        )

        contexts.append(
            IssueContext(
                issue_code=issue_code,
                evidence_tool=(
                    evidence_tool
                ),
                evidence=evidence,
                relevant_evidence=dict(
                    grounded_data
                    .relevant_evidence
                ),
                grounded_statement=(
                    grounded_data
                    .grounded_statement
                ),
                possible_causes=list(
                    causes_by_code[
                        issue_code
                    ]
                ),
                recommended_checks=list(
                    checks_by_code[
                        issue_code
                    ]
                ),
            )
        )

    return contexts


def build_incident_report(
    *,
    request_id: str,
    contexts: list[IssueContext],
    analyses_by_code: dict[
        str,
        IssueAnalysis,
    ],
) -> IncidentReport:
    expected_codes = {
        context.issue_code
        for context in contexts
    }

    if set(
        analyses_by_code
    ) != expected_codes:
        raise IncidentBuildError(
            "Issue analyses do not match "
            "deterministic issue contexts."
        )

    findings: list[
        IncidentFinding
    ] = []

    for context in contexts:
        analysis = analyses_by_code[
            context.issue_code
        ]

        findings.append(
            IncidentFinding(
                issue_code=(
                    context.issue_code
                ),
                explanation=(
                    analysis.explanation
                ),
                evidence_ref=(
                    EvidenceReference(
                        tool_name=(
                            context
                            .evidence_tool
                        )
                    )
                ),
                possible_causes=list(
                    context.possible_causes
                ),
                recommended_checks=list(
                    context
                    .recommended_checks
                ),
            )
        )

    if not findings:
        return IncidentReport(
            request_id=request_id,
            status="ok",
            summary=(
                "No configured issue "
                "was detected."
            ),
            findings=[],
        )

    issue_list = ", ".join(
        finding.issue_code
        for finding in findings
    )

    issue_count = len(findings)

    noun = (
        "issue"
        if issue_count == 1
        else "issues"
    )

    summary = (
        f"Detected {issue_count} configured "
        f"{noun} requiring review: "
        f"{issue_list}."
    )

    return IncidentReport(
        request_id=request_id,
        status="needs_review",
        summary=summary,
        findings=findings,
    )









def build_grounded_issue_data(
    *,
    issue_code: str,
    request: PredictionRequest,
    source_data: dict[str, Any],
) -> GroundedIssueData:
    if issue_code == "road_access_conflict":
        return GroundedIssueData(
            relevant_evidence={
                "road_frontage": (
                    request.road_frontage
                ),
                "is_landlocked": (
                    request.is_landlocked
                ),
            },
            grounded_statement=(
                "The request contains "
                "inconsistent road-access fields: "
                f"road_frontage="
                f"{request.road_frontage!r} and "
                f"is_landlocked="
                f"{request.is_landlocked!r}."
            ),
        )

    if issue_code == "unsupported_location":
        return GroundedIssueData(
            relevant_evidence={
                "request_location": (
                    request.location
                ),
            },
            grounded_statement=(
                "The request location "
                f'"{request.location}" is not '
                "supported by the configured "
                "location registry."
            ),
        )

    if issue_code == "model_location_mismatch":
        metadata = source_data.get(
            "metadata"
        )

        if not isinstance(
            metadata,
            dict,
        ):
            raise IncidentBuildError(
                "Model metadata is missing "
                "for model_location_mismatch."
            )

        model_location = metadata.get(
            "location"
        )

        if not isinstance(
            model_location,
            str,
        ):
            raise IncidentBuildError(
                "Model metadata location "
                "is missing or is not a string."
            )

        request_location = (
            request.location
        )

        return GroundedIssueData(
            relevant_evidence={
                "request_location": (
                    request_location
                ),
                "model_location": (
                    model_location
                ),
            },
            grounded_statement=(
                "The request location "
                f'"{request_location}" does not '
                "match the model metadata "
                f'location "{model_location}".'
            ),
        )

    if (
        issue_code
        == "prediction_below_reference_range"
    ):
        predicted_price_per_area = (
            source_data.get(
                "predicted_price_per_area"
            )
        )

        p10_price_per_area = (
            source_data.get(
                "p10_price_per_area"
            )
        )

        median_price_per_area = (
            source_data.get(
                "median_price_per_area"
            )
        )

        numeric_values = (
            predicted_price_per_area,
            p10_price_per_area,
            median_price_per_area,
        )

        if any(
            not isinstance(
                value,
                (int, float),
            )
            or isinstance(
                value,
                bool,
            )
            for value in numeric_values
        ):
            raise IncidentBuildError(
                "Prediction reference values "
                "are missing or are not numeric."
            )

        return GroundedIssueData(
            relevant_evidence={
                "predicted_price_per_area": (
                    predicted_price_per_area
                ),
                "p10_price_per_area": (
                    p10_price_per_area
                ),
                "median_price_per_area": (
                    median_price_per_area
                ),
            },
            grounded_statement=(
                "The predicted price per area "
                f"{predicted_price_per_area} "
                "is below the regional p10 "
                f"value {p10_price_per_area}. "
                "The regional median is "
                f"{median_price_per_area}."
            ),
        )

    return GroundedIssueData(
        relevant_evidence={
            "issue_code": issue_code,
        },
        grounded_statement=(
            "The deterministic tools detected "
            "the configured issue "
            f'"{issue_code}".'
        ),
    )