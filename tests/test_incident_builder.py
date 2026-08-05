from app.incident_builder import (
    build_grounded_issue_data,
)
from app.schemas import (
    PredictionRequest,
)


def test_low_prediction_has_minimal_grounded_data():
    request = PredictionRequest(
        request_id="TEST-PREDICTION-1",
        location="district_07",
        area=8500,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    source_data = {
        "reference_available": True,
        "predicted_price_per_area": 1.4118,
        "median_price_per_area": 4.2,
        "p10_price_per_area": 2.3,
        "p90_price_per_area": 7.8,
        "deviation_from_median_pct": -66.39,
        "price_band": (
            "below_reference_range"
        ),
        "reference_sample_size": 184,
        "issue_codes": [
            "prediction_below_reference_range"
        ],
    }

    result = build_grounded_issue_data(
        issue_code=(
            "prediction_below_reference_range"
        ),
        request=request,
        source_data=source_data,
    )

    assert result.relevant_evidence == {
        "predicted_price_per_area": 1.4118,
        "p10_price_per_area": 2.3,
        "median_price_per_area": 4.2,
    }

    assert "1.4118" in (
        result.grounded_statement
    )

    assert "2.3" in (
        result.grounded_statement
    )

    assert "4.2" in (
        result.grounded_statement
    )

    assert "$" not in (
        result.grounded_statement
    )

    assert "USD" not in (
        result.grounded_statement
    )

    assert (
        "p90_price_per_area"
        not in result.relevant_evidence
    )

    assert (
        "reference_sample_size"
        not in result.relevant_evidence
    )



def test_model_location_mismatch_uses_locations_only():
    request = PredictionRequest(
        request_id="TEST-LOCATION-1",
        location="unknown_district",
        area=8500,
        road_frontage=10,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    source_data = {
        "model_found": True,
        "metadata": {
            "model_version": (
                "district_07_v3"
            ),
            "location": "district_07",
            "training_date": "2026-06-15",
            "validation_smape": 18.4,
            "supported_area_range": [
                300.0,
                12000.0,
            ],
            "is_active": True,
        },
        "area_supported": True,
        "issue_codes": [
            "model_location_mismatch"
        ],
    }

    result = build_grounded_issue_data(
        issue_code=(
            "model_location_mismatch"
        ),
        request=request,
        source_data=source_data,
    )

    assert result.relevant_evidence == {
        "request_location": (
            "unknown_district"
        ),
        "model_location": "district_07",
    }

    assert "unknown_district" in (
        result.grounded_statement
    )

    assert "district_07" in (
        result.grounded_statement
    )

    assert (
        "district_07_v3"
        not in result.grounded_statement
    )

    assert (
        "model_version"
        not in result.relevant_evidence
    )




from app.incident_builder import (
    IssueContext,
)
from app.issue_analysis_prompts import (
    build_issue_analysis_prompts,
)


def test_prompt_contains_only_relevant_evidence():
    context = IssueContext(
        issue_code=(
            "model_location_mismatch"
        ),
        evidence_tool=(
            "get_model_metadata"
        ),
        evidence=[
            {
                "issue_code": (
                    "model_location_mismatch"
                ),
                "details": {
                    "model_version": (
                        "district_07_v3"
                    ),
                    "location": (
                        "district_07"
                    ),
                },
            }
        ],
        relevant_evidence={
            "request_location": (
                "unknown_district"
            ),
            "model_location": (
                "district_07"
            ),
        },
        grounded_statement=(
            "The request location "
            '"unknown_district" does not '
            "match the model metadata "
            'location "district_07".'
        ),
        possible_causes=[],
        recommended_checks=[],
    )

    _, user_prompt = (
        build_issue_analysis_prompts(
            context
        )
    )

    assert (
        "Issue code for context:"
        in user_prompt
    )

    assert (
        "model_location_mismatch"
        in user_prompt
    )

    assert (
        "unknown_district"
        in user_prompt
    )

    assert "district_07" in user_prompt

    assert (
        "district_07_v3"
        not in user_prompt
    )

    assert (
        "model_version"
        not in user_prompt
    )