from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)


class SummaryCheck(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    name: str
    category: str
    passed: bool

    expected: Any = None
    actual: Any = None


class SummaryCaseResult(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    case_id: str

    passed: bool
    hard_passed: bool

    quality_passed: bool
    quality_evaluated: bool

    issue_codes: list[str] = Field(
        default_factory=list,
    )

    attempts_by_issue: dict[
        str,
        int,
    ] = Field(
        default_factory=dict,
    )

    repair_attempts: int = 0

    checks: list[
        SummaryCheck
    ] = Field(
        default_factory=list,
    )


class EvaluationSummaryReport(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
    )

    mode: str

    hard_pass_rate: float

    quality_pass_rate: float | None

    first_pass_rate: float | None

    repair_used_cases: int = Field(
        ge=0,
    )

    cases_with_llm: int = Field(
        ge=0,
    )

    median_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
    )

    case_results: list[
        SummaryCaseResult
    ]



class EvaluationSummaryReadError(
    ValueError
):
    pass



def load_evaluation_summary(
    path: Path,
) -> EvaluationSummaryReport:
    if not path.exists():
        raise EvaluationSummaryReadError(
            "Evaluation summary does not exist: "
            f"{path}"
        )

    try:
        raw = path.read_text(
            encoding="utf-8",
        )

    except OSError as exc:
        raise EvaluationSummaryReadError(
            "Could not read evaluation summary: "
            f"{path}"
        ) from exc

    try:
        return (
            EvaluationSummaryReport
            .model_validate_json(
                raw
            )
        )

    except ValidationError as exc:
        raise EvaluationSummaryReadError(
            "Evaluation summary has an "
            "unexpected structure: "
            f"{path}"
        ) from exc