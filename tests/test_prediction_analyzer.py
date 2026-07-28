from app.schemas import (
    LocationStats,
    PredictionRequest,
)
from app.tools.prediction_analyzer import (
    analyze_prediction,
)


def test_detects_low_prediction():
    request = PredictionRequest(
        request_id="REQ-4",
        location="district_07",
        area=8500,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    stats = {
        "district_07": LocationStats(
            location="district_07",
            median_price_per_area=4.2,
            p10_price_per_area=2.3,
            p90_price_per_area=7.8,
            sample_size=184,
        )
    }

    result = analyze_prediction(
        request=request,
        stats_by_location=stats,
    )

    assert result.success is True

    assert (
        result.data["price_band"]
        == "below_reference_range"
    )

    assert (
        "prediction_below_reference_range"
        in result.data["issue_codes"]
    )