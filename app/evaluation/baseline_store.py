import json
from pathlib import Path

from app.evaluation.baseline_schemas import (
    EvaluationBaseline,
)


def save_baseline(
    *,
    path: Path,
    baseline: EvaluationBaseline,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = baseline.model_dump(
        mode="json"
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_baseline(
    path: Path,
) -> EvaluationBaseline:
    raw = path.read_text(
        encoding="utf-8",
    )

    return EvaluationBaseline.model_validate_json(
        raw
    )