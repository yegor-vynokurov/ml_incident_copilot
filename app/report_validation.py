from collections import defaultdict

from app.schemas import (
    AgentStep,
    IncidentReport,
)


class ReportGroundingError(ValueError):
    """
    Structured report contains data that is not
    supported by deterministic tool results.
    """


def validate_report_grounding(
    *,
    report: IncidentReport,
    request_id: str,
    expected_issue_codes: set[str],
    steps: list[AgentStep],
) -> None:
    """Check structured facts against tool results.

    This does not validate the meaning of LLM-written explanations.
    """

    if report.request_id != request_id:
        raise ReportGroundingError(
            "Report request_id does not match "
            "the original request."
        )

    expected_status = (
        "needs_review"
        if expected_issue_codes
        else "ok"
    )

    if report.status != expected_status:
        raise ReportGroundingError(
            "Report status does not match "
            "detected issue codes."
        )

    returned_issue_codes = [
        finding.issue_code
        for finding in report.findings
    ]

    if len(returned_issue_codes) != len(
        set(returned_issue_codes)
    ):
        raise ReportGroundingError(
            "The report contains duplicate "
            "issue codes."
        )

    if set(returned_issue_codes) != (
        expected_issue_codes
    ):
        raise ReportGroundingError(
            "The report issue codes do not match "
            "the deterministic tool results."
        )

    issue_sources: dict[str, set[str]] = (
        defaultdict(set)
    )

    allowed_causes: dict[str, set[str]] = (
        defaultdict(set)
    )

    allowed_checks: dict[str, set[str]] = (
        defaultdict(set)
    )

    for step in steps:
        if (
            step.status != "executed"
            or step.result is None
        ):
            continue

        issue_codes = step.result.data.get(
            "issue_codes",
            [],
        )

        if isinstance(issue_codes, list):
            for issue_code in issue_codes:
                issue_sources[str(issue_code)].add(
                    step.tool_name
                )

        if (
            step.tool_name
            == "search_known_issues"
        ):
            matches = step.result.data.get(
                "matches",
                [],
            )

            if not isinstance(matches, list):
                continue

            for match in matches:
                matched_codes = match.get(
                    "matched_codes",
                    [],
                )

                causes = match.get(
                    "possible_causes",
                    [],
                )

                checks = match.get(
                    "recommended_checks",
                    [],
                )

                for issue_code in matched_codes:
                    code = str(issue_code)

                    allowed_causes[code].update(
                        str(cause)
                        for cause in causes
                    )

                    allowed_checks[code].update(
                        str(check)
                        for check in checks
                    )

    for finding in report.findings:
        issue_code = finding.issue_code

        evidence_tool = (
            finding.evidence_ref.tool_name
        )

        allowed_tools = issue_sources.get(
            issue_code,
            set(),
        )

        if evidence_tool not in allowed_tools:
            raise ReportGroundingError(
                f"Tool {evidence_tool!r} did not produce "
                f"issue {issue_code!r}. "
                f"Allowed tools: "
                f"{sorted(allowed_tools)}."
            )

        if not set(
            finding.possible_causes
        ).issubset(
            allowed_causes[issue_code]
        ):
            raise ReportGroundingError(
                f"Unsupported possible cause "
                f"for {issue_code}."
            )

        if not set(
            finding.recommended_checks
        ).issubset(
            allowed_checks[issue_code]
        ):
            raise ReportGroundingError(
                f"Unsupported recommended check "
                f"for {issue_code}."
            )
        
    if (
        not expected_issue_codes
        and report.findings
    ):
        raise ReportGroundingError(
            "A report without detected issues "
            "must have an empty findings list."
        )
