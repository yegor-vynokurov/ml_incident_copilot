import json
from pathlib import Path

from app.schemas import (
    LocationStats,
    PredictionRequest,
    ToolResult,
)


SPARSE_SAMPLE_THRESHOLD = 30


def load_location_stats(
    path: Path,
) -> dict[str, LocationStats]:
    raw_data = json.loads(
        path.read_text(encoding="utf-8")
    )

    stats = [
        LocationStats.model_validate(item)
        for item in raw_data
    ]

    return {
        item.location: item
        for item in stats
    }


def analyze_prediction(
    request: PredictionRequest,
    stats_by_location: dict[str, LocationStats],
) -> ToolResult:
    """
    Compare prediction with synthetic local statistic as baseline.
    """

    stats = stats_by_location.get(request.location)

    if stats is None:
        return ToolResult(
            tool_name="analyze_prediction",
            success=True,
            data={
                "reference_available": False,
                "issue_codes": [
                    "missing_location_reference"
                ],
            },
        )

    predicted_price_per_area = (
        request.predicted_price / request.area
    )

    deviation_from_median_pct = (
        (
            predicted_price_per_area
            - stats.median_price_per_area
        )
        / stats.median_price_per_area
        * 100
    )

    issue_codes: list[str] = []

    if (
        predicted_price_per_area
        < stats.p10_price_per_area
    ):
        price_band = "below_reference_range"
        issue_codes.append(
            "prediction_below_reference_range"
        )

    elif (
        predicted_price_per_area
        > stats.p90_price_per_area
    ):
        price_band = "above_reference_range"
        issue_codes.append(
            "prediction_above_reference_range"
        )

    else:
        price_band = "within_reference_range"

    if stats.sample_size < SPARSE_SAMPLE_THRESHOLD:
        issue_codes.append("sparse_location_data")


    evidence: list[dict] = []

    if price_band == "below_reference_range":
        evidence.append(
            {
                "issue_code": "prediction_below_reference_range",
                "fields": {
                    "predicted_price_per_area": round(
                        predicted_price_per_area,
                        4,
                    ),
                    "p10_price_per_area": (
                        stats.p10_price_per_area
                    ),
                    "median_price_per_area": (
                        stats.median_price_per_area
                    ),
                    "deviation_from_median_pct": round(
                        deviation_from_median_pct,
                        2,
                    ),
                    "reference_sample_size": (
                        stats.sample_size
                    ),
                },
                "description": (
                    "The predicted price per area is below "
                    "the configured regional p10 reference."
                ),
            }
        )

    return ToolResult(
        tool_name="analyze_prediction",
        success=True,
        data={
            "reference_available": True,
            "predicted_price_per_area": round(
                predicted_price_per_area,
                4,
            ),
            "median_price_per_area": (
                stats.median_price_per_area
            ),
            "p10_price_per_area": (
                stats.p10_price_per_area
            ),
            "p90_price_per_area": (
                stats.p90_price_per_area
            ),
            "deviation_from_median_pct": round(
                deviation_from_median_pct,
                2,
            ),
            "price_band": price_band,
            "reference_sample_size": (
                stats.sample_size
            ),
            "issue_codes": issue_codes,
        },
    )