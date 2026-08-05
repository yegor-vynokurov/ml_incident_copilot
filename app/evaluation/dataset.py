import json
from pathlib import Path

from pydantic import ValidationError

from app.evaluation.schemas import (
    EvaluationCase,
)


class EvaluationDatasetError(
    ValueError
):
    """
    Dataset is not read or loaded.
    """


def load_evaluation_cases(
    path: Path,
) -> list[EvaluationCase]:
    try:
        raw_text = path.read_text(
            encoding="utf-8",
        )

    except OSError as exc:
        raise EvaluationDatasetError(
            f"Could not read evaluation "
            f"dataset: {path}"
        ) from exc

    try:
        raw_data = json.loads(
            raw_text
        )

    except json.JSONDecodeError as exc:
        raise EvaluationDatasetError(
            "Evaluation dataset is not "
            "valid JSON."
        ) from exc

    if not isinstance(
        raw_data,
        list,
    ):
        raise EvaluationDatasetError(
            "Evaluation dataset root "
            "must be a JSON list."
        )

    try:
        cases = [
            EvaluationCase.model_validate(
                item
            )
            for item in raw_data
        ]

    except ValidationError as exc:
        raise EvaluationDatasetError(
            "Evaluation dataset does not "
            "match EvaluationCase schema."
        ) from exc

    case_ids = [
        case.case_id
        for case in cases
    ]

    if len(case_ids) != len(
        set(case_ids)
    ):
        raise EvaluationDatasetError(
            "Evaluation case IDs "
            "must be unique."
        )

    return cases