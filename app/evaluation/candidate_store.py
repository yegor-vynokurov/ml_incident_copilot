from pathlib import Path
from typing import (
    TypeVar,
)

from pydantic import (
    BaseModel,
    ValidationError,
)

from app.evaluation.candidate_schemas import (
    EvaluationCandidate,
)
from app.observability.schemas import (
    IncidentFeedbackRecord,
    IncidentRunRecord,
)


ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)


class CandidateStoreError(
    ValueError
):
    """
    A JSONL runtime/evaluation file could not
    be read or validated.
    """


def _load_jsonl(
    *,
    path: Path,
    model_type: type[ModelT],
) -> list[ModelT]:
    """
    Read a JSONL file and validate every
    non-empty line using Pydantic.
    """

    if not path.exists():
        return []

    try:
        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()

    except OSError as exc:
        raise CandidateStoreError(
            f"Could not read JSONL file: {path}"
        ) from exc

    records: list[ModelT] = []

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        if not line.strip():
            continue

        try:
            record = (
                model_type
                .model_validate_json(
                    line
                )
            )

        except ValidationError as exc:
            raise CandidateStoreError(
                "Invalid JSONL record in "
                f"{path} at line "
                f"{line_number}."
            ) from exc

        except ValueError as exc:
            raise CandidateStoreError(
                "Invalid JSON in "
                f"{path} at line "
                f"{line_number}."
            ) from exc

        records.append(
            record
        )

    return records


def load_run_records(
    path: Path,
) -> list[IncidentRunRecord]:
    return _load_jsonl(
        path=path,
        model_type=(
            IncidentRunRecord
        ),
    )


def load_feedback_records(
    path: Path,
) -> list[IncidentFeedbackRecord]:
    return _load_jsonl(
        path=path,
        model_type=(
            IncidentFeedbackRecord
        ),
    )


def load_candidates(
    path: Path,
) -> list[EvaluationCandidate]:
    return _load_jsonl(
        path=path,
        model_type=(
            EvaluationCandidate
        ),
    )


def append_candidate(
    *,
    path: Path,
    candidate: EvaluationCandidate,
) -> None:
    """
    Append one candidate as one JSONL line.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = (
        candidate.model_dump_json()
    )

    try:
        with path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                serialized
            )
            file.write(
                "\n"
            )

    except OSError as exc:
        raise CandidateStoreError(
            "Could not append evaluation "
            f"candidate to {path}."
        ) from exc