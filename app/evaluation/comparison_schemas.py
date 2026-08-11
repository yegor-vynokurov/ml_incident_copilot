from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


ComparisonStatus = Literal[
    "same",
    "improved",
    "regressed",
    "not_compared",
]


class CurrentEvaluationMetrics(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    hard_pass_rate: float = Field(
        ge=0.0,
        le=1.0,
    )

    quality_pass_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    first_pass_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    repair_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    median_duration_ms: float | None = Field(
        default=None,
        ge=0.0,
    )


class CurrentCriticalCaseResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    relevant_cases: int = Field(
        ge=0,
    )

    passed_cases: int = Field(
        ge=0,
    )

    pass_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class CurrentEvaluationSnapshot(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    mode: str

    metrics: CurrentEvaluationMetrics

    critical_cases: dict[
        str,
        CurrentCriticalCaseResult,
    ] = Field(
        default_factory=dict,
    )


class MetricComparison(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    baseline: float | None
    current: float | None
    delta: float | None

    status: ComparisonStatus


class EvaluationComparison(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    created_at: datetime

    baseline_created_at: datetime

    baseline_mode: str
    current_mode: str

    report_path: str

    metrics: dict[
        str,
        MetricComparison,
    ]

    critical_cases: dict[
        str,
        MetricComparison,
    ] = Field(
        default_factory=dict,
    )

    notes: list[str] = Field(
        default_factory=list,
    )