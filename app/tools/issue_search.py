import json
from pathlib import Path

from app.schemas import KnownIssue, ToolResult


def load_known_issues(
    path: Path,
) -> list[KnownIssue]:
    raw_data = json.loads(
        path.read_text(encoding="utf-8")
    )

    return [
        KnownIssue.model_validate(item)
        for item in raw_data
    ]


def search_known_issues(
    observed_issue_codes: set[str],
    known_issues: list[KnownIssue],
) -> ToolResult:
    """
    Looks for known issues by corresponding of the issue codes.
    """

    matches: list[dict] = []

    for issue in known_issues:
        trigger_codes = set(issue.trigger_codes)

        matched_codes = sorted(
            observed_issue_codes & trigger_codes
        )

        if not matched_codes:
            continue

        match_score = (
            len(matched_codes)
            / len(trigger_codes)
        )

        matches.append(
            {
                "issue_id": issue.issue_id,
                "title": issue.title,
                "matched_codes": matched_codes,
                "match_score": round(
                    match_score,
                    3,
                ),
                "possible_causes": (
                    issue.possible_causes
                ),
                "recommended_checks": (
                    issue.recommended_checks
                ),
            }
        )

    matches.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    return ToolResult(
        tool_name="search_known_issues",
        success=True,
        data={
            "observed_issue_codes": sorted(
                observed_issue_codes
            ),
            "matches": matches,
            "match_count": len(matches),
        },
    )