from collections.abc import Collection

from app.schemas import PredictionRequest, ToolResult

def validate_input(
    request: PredictionRequest,
    supported_locations: Collection[str],
) -> ToolResult:
    issue_codes: list[str] = []
    evidence: list[dict] = []
    checks: dict[str, bool] = {}

    location_supported = (
        request.location in supported_locations
    )

    checks["location_supported"] = (
        location_supported
    )

    if not location_supported:
        issue_codes.append(
            "unsupported_location"
        )

        evidence.append(
            {
                "issue_code": "unsupported_location",
                "fields": {
                    "location": request.location,
                },
                "description": (
                    "The request location is not present "
                    "in the supported location list."
                ),
            }
        )

    road_access_consistent = not (
        request.road_frontage == 0
        and request.is_landlocked is False
    )

    checks["road_access_consistent"] = (
        road_access_consistent
    )

    if not road_access_consistent:
        issue_codes.append(
            "road_access_conflict"
        )

        evidence.append(
            {
                "issue_code": "road_access_conflict",
                "fields": {
                    "road_frontage": (
                        request.road_frontage
                    ),
                    "is_landlocked": (
                        request.is_landlocked
                    ),
                },
                "description": (
                    "road_frontage is 0 while "
                    "is_landlocked is false."
                ),
            }
        )

    reverse_road_access_consistent = not (
        request.road_frontage > 0
        and request.is_landlocked is True
    )

    checks[
        "reverse_road_access_consistent"
    ] = reverse_road_access_consistent

    if not reverse_road_access_consistent:
        issue_codes.append(
            "road_access_conflict"
        )

        evidence.append(
            {
                "issue_code": "road_access_conflict",
                "fields": {
                    "road_frontage": (
                        request.road_frontage
                    ),
                    "is_landlocked": (
                        request.is_landlocked
                    ),
                },
                "description": (
                    "road_frontage is greater than 0 "
                    "while is_landlocked is true."
                ),
            }
        )

    return ToolResult(
        tool_name="validate_input",
        success=True,
        data={
            "is_valid": len(issue_codes) == 0,
            "issue_codes": sorted(
                set(issue_codes)
            ),
            "checks": checks,
            "evidence": evidence,
        },
    )