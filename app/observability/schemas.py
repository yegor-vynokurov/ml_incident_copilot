from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas import (
    AgentRun,
    PredictionRequest,
)


RunOutcome = Literal[
    "success",
    "error",
]

FeedbackVerdict = Literal[
    "correct",
    "partially_correct",
    "incorrect",
]








class IncidentRunRecord(BaseModel):
    """
    One persisted API analysis run.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    trace_id: str = Field(
        min_length=1,
    )

    created_at: datetime

    duration_ms: float = Field(
        ge=0,
    )

    outcome: RunOutcome

    request: PredictionRequest

    agent_run: AgentRun | None = None

    prompt_version: str = Field(
        min_length=1,
    )

    providers: list[str] = Field(
        default_factory=list,
    )

    models: list[str] = Field(
        default_factory=list,
    )

    error_type: str | None = None
    error_message: str | None = None





@model_validator(
    mode="after"
)
def validate_outcome(
    self,
) -> "IncidentRunRecord":
    if self.outcome == "success":
        if self.agent_run is None:
            raise ValueError(
                "Successful run must contain "
                "agent_run."
            )

        if (
            self.error_type is not None
            or self.error_message is not None
        ):
            raise ValueError(
                "Successful run must not "
                "contain error fields."
            )

    if self.outcome == "error":
        if self.agent_run is not None:
            raise ValueError(
                "Failed run must not contain "
                "agent_run."
            )

        if self.error_type is None:
            raise ValueError(
                "Failed run must contain "
                "error_type."
            )

    return self


class IncidentFeedbackRecord(BaseModel):
    """
    Human feedback connected to one run.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    feedback_id: str = Field(
        min_length=1,
    )

    trace_id: str = Field(
        min_length=1,
    )

    created_at: datetime

    verdict: FeedbackVerdict

    issue_code: str | None = None

    expected_issue_codes: list[str] | None = None

    comment: str | None = Field(
        default=None,
        max_length=2000,
    )

    corrected_explanation: str | None = Field(
        default=None,
        max_length=2000,
    )



