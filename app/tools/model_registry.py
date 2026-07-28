import json
from pathlib import Path

from app.schemas import (
    ModelMetadata,
    PredictionRequest,
    ToolResult,
)


def load_model_registry(
    path: Path,
) -> dict[str, ModelMetadata]:
    """
    load model registry from json.

    return dict:
    model_version -> ModelMetadata
    """

    raw_data = json.loads(
        path.read_text(encoding="utf-8")
    )

    # transform dicts with model data to ModelMetadata schema for checking and correction fields
    models = [
        ModelMetadata.model_validate(item)
        for item in raw_data
    ]

    return {
        model.model_version: model
        for model in models
    }


def get_model_metadata(
    request: PredictionRequest,
    registry: dict[str, ModelMetadata],
) -> ToolResult:
    """
    Checks the model that serve the request.
    """

    metadata = registry.get(request.model_version)

    # check if the model has metadata
    if metadata is None:
        return ToolResult(
            tool_name="get_model_metadata",
            success=True,
            data={
                "model_found": False,
                "issue_codes": [
                    "unknown_model_version"
                ],
            },
        )

    issue_codes: list[str] = []

    # check if the model is in active list:
    if not metadata.is_active:
        issue_codes.append("inactive_model_version")

    # check the corresponding of the location in the request and location when the model was trained
    if metadata.location != request.location:
        issue_codes.append("model_location_mismatch")

    # check area limiatations which model was trained:
    min_area, max_area = metadata.supported_area_range

    area_supported = min_area <= request.area <= max_area

    if not area_supported:
        issue_codes.append("area_outside_model_range")

    return ToolResult(
        tool_name="get_model_metadata",
        success=True,
        data={
            "model_found": True,
            "metadata": metadata.model_dump(
                mode="json"
            ),
            "area_supported": area_supported,
            "issue_codes": issue_codes,
        },
    )