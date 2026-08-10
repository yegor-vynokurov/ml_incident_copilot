from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas import (
    PredictionRequest,
)


CandidateStatus = Literal[
    "pending",
    "approved",
    "rejected",
]


class EvaluationCandidate(BaseModel):
    """
    A runtime-feedback example that may later
    become an evaluation case.

    Candidate is NOT an EvaluationCase yet.
    A human must review it first.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    candidate_id: str = Field(
        min_length=1,
    )

    # Important for deduplication.
    feedback_id: str = Field(
        min_length=1,
    )

    trace_id: str = Field(
        min_length=1,
    )

    created_at: datetime

    status: CandidateStatus = "pending"

    # Original request that produced the run.
    source_request: PredictionRequest

    # What the system actually detected.
    actual_issue_codes: list[str]

    # Optional human correction.
    expected_issue_codes: (
        list[str] | None
    ) = None

    # Issue that the feedback is mainly about.
    affected_issue_code: str | None = None

    # Explanation produced by the system.
    actual_explanation: str | None = None

    # Optional human-provided correction.
    corrected_explanation: str | None = None

    feedback_verdict: Literal[
        "partially_correct",
        "incorrect",
    ]

    feedback_comment: str | None = None

    prompt_version: str = Field(
        min_length=1,
    )

    provider_names: list[str] = Field(
        default_factory=list,
    )

    model_names: list[str] = Field(
        default_factory=list,
    )

    review_notes: str | None = None