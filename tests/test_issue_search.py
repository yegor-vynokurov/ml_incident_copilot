from app.schemas import KnownIssue
from app.tools.issue_search import (
    search_known_issues,
)


def test_finds_known_issue_by_trigger_code():
    known_issues = [
        KnownIssue(
            issue_id="input_data_contradiction",
            title="Contradictory fields",
            trigger_codes=[
                "road_access_conflict"
            ],
            possible_causes=[
                "Mapping error"
            ],
            recommended_checks=[
                "Check source data"
            ],
        )
    ]

    result = search_known_issues(
        observed_issue_codes={
            "road_access_conflict"
        },
        known_issues=known_issues,
    )

    assert result.success is True
    assert result.data["match_count"] == 1

    assert (
        result.data["matches"][0]["issue_id"]
        == "input_data_contradiction"
    )