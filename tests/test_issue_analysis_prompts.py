from app.incident_builder import (
    IssueContext,
)
from app.issue_analysis_prompts import (
    build_issue_analysis_prompts,
)


def test_location_mismatch_prompt_contains_only_relevant_evidence():
    context = IssueContext(
        issue_code=(
            "model_location_mismatch"
        ),
        evidence_tool=(
            "get_model_metadata"
        ),

        # Full evidence is saved for report and trassing.
        evidence=[
            {
                "issue_code": (
                    "model_location_mismatch"
                ),
                "tool_name": (
                    "get_model_metadata"
                ),
                "details": {
                    "metadata": {
                        "model_version": (
                            "district_07_v3"
                        ),
                        "location": (
                            "district_07"
                        ),
                        "is_active": True,
                    }
                },
            }
        ],

        # Only these data must see the LLM.
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

    # Check if the issue code is passed.
    assert (
        "model_location_mismatch"
        in user_prompt
    )

    # Checked thant needed values are passed.
    assert (
        "unknown_district"
        in user_prompt
    )

    assert (
        "district_07"
        in user_prompt
    )

    # Checked that unnecessary version of the model is not passed to the prompt.
    assert (
        "district_07_v3"
        not in user_prompt
    )

    assert (
        "model_version"
        not in user_prompt
    )


def test_low_prediction_prompt_contains_only_relevant_values():
    context = IssueContext(
        issue_code=(
            "prediction_below_reference_range"
        ),
        evidence_tool=(
            "analyze_prediction"
        ),
        evidence=[
            {
                "issue_code": (
                    "prediction_below_reference_range"
                ),
                "tool_name": (
                    "analyze_prediction"
                ),
                "details": {
                    "predicted_price_per_area": (
                        1.4118
                    ),
                    "p10_price_per_area": 2.3,
                    "median_price_per_area": 4.2,
                    "p90_price_per_area": 7.8,
                    "reference_sample_size": 184,
                },
            }
        ],
        relevant_evidence={
            "predicted_price_per_area": (
                1.4118
            ),
            "p10_price_per_area": 2.3,
            "median_price_per_area": 4.2,
        },
        grounded_statement=(
            "The predicted price per area "
            "1.4118 is below the regional "
            "p10 value 2.3. "
            "The regional median is 4.2."
        ),
        possible_causes=[],
        recommended_checks=[],
    )

    _, user_prompt = (
        build_issue_analysis_prompts(
            context
        )
    )

    assert "1.4118" in user_prompt
    assert "2.3" in user_prompt
    assert "4.2" in user_prompt

    assert (
        "p90_price_per_area"
        not in user_prompt
    )

    assert (
        "reference_sample_size"
        not in user_prompt
    )

    assert "$" not in user_prompt
    assert "USD" not in user_prompt

