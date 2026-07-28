from datetime import date

from app.schemas import (
    ModelMetadata,
    PredictionRequest,
)
from app.tools.model_registry import (
    get_model_metadata,
)


def test_detects_model_location_mismatch():
    request = PredictionRequest(
        request_id="REQ-3",
        location="district_08",
        area=5000,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=25000,
        model_version="district_07_v3",
    )

    registry = {
        "district_07_v3": ModelMetadata(
            model_version="district_07_v3",
            location="district_07",
            training_date=date(2026, 6, 15),
            validation_smape=18.4,
            supported_area_range=(300, 12000),
            is_active=True,
        )
    }

    result = get_model_metadata(
        request=request,
        registry=registry,
    )

    assert result.success is True

    assert (
        "model_location_mismatch"
        in result.data["issue_codes"]
    )