from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class BaselineSource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    mode: Literal[
        "deterministic",
        "live",
    ]

    runs: int = Field(
        ge=1,
    )


class BaselineMetrics(BaseModel):
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


class CriticalCaseBaseline(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    pass_rate: float = Field(
        ge=0.0,
        le=1.0,
    )


class EvaluationBaseline(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    created_at: datetime

    source: BaselineSource

    metrics: BaselineMetrics

    critical_cases: dict[
        str,
        CriticalCaseBaseline,
    ] = Field(
        default_factory=dict,
    )