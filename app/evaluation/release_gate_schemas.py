from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


GateDecision = Literal[
    "pass",
    "fail",
]


GateCheckStatus = Literal[
    "pass",
    "fail",
    "warning",
]


class ReleaseGatePolicy(BaseModel):
    """
    Versioned rules used to decide whether
    an evaluation comparison is releasable.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    required_mode: str = "live"

    blocking_metrics: list[str] = Field(
        default_factory=list,
    )

    warning_metrics: list[str] = Field(
        default_factory=list,
    )

    block_on_critical_regression: bool = True

    block_on_missing_critical_case: bool = True

    block_on_not_compared_blocking_metric: bool = True


class ReleaseGateCheck(BaseModel):
    """
    Result of one release-policy rule.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    name: str = Field(
        min_length=1,
    )

    status: GateCheckStatus

    message: str = Field(
        min_length=1,
    )

    baseline: float | None = None
    current: float | None = None
    delta: float | None = None


class ReleaseGateResult(BaseModel):
    """
    Final result after applying release policy.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    decision: GateDecision

    checks: list[
        ReleaseGateCheck
    ] = Field(
        default_factory=list,
    )

    blocking_failures: list[str] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )