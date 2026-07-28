from app.schemas import PredictionRequest
from app.tools.input_validator import validate_input


def test_detects_road_access_conflict():
    request = PredictionRequest(
        request_id="REQ-1",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = validate_input(
        request=request,
        supported_locations={"district_07"},
    )

    assert result.success is True
    assert result.data["is_valid"] is False

    assert (
        "road_access_conflict"
        in result.data["issue_codes"]
    )


def test_accepts_consistent_access_fields():
    request = PredictionRequest(
        request_id="REQ-2",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=True,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = validate_input(
        request=request,
        supported_locations={"district_07"},
    )

    assert result.success is True
    assert result.data["is_valid"] is True
    assert result.data["issue_codes"] == []