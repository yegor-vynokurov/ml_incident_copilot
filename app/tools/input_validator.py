from collections.abc import Collection

from app.schemas import PredictionRequest, ToolResult

def validate_input(
    request: PredictionRequest,
    supported_locations: Collection[str],
) -> ToolResult:
    """
    Checks domains' rules for the request.
    """

    issue_codes: list[str] = []
    checks: dict[str, bool] = {}

    # check is the location in the request is available in the models:

    location_supported = request.location in supported_locations
    checks["location_supported"] = location_supported

    if not location_supported:
        issue_codes.append("unsupported_location")

    # checks contradiction between road frontage 0 and is landlocked not true:

    road_access_consistent = not (
        request.road_frontage == 0
        and request.is_landlocked is False
    )

    checks["road_access_consistent"] = road_access_consistent

    if not road_access_consistent:
        issue_codes.append("road_access_conflict")

    return ToolResult(
        tool_name="validate_input",
        success=True, # if false then the tool was worked incorrectly
        data={
            "is_valid": len(issue_codes) == 0,
            "issue_codes": sorted(set(issue_codes)),
            "checks": checks,
        },
    )