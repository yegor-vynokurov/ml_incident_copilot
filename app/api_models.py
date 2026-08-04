from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class HealthResponse(BaseModel):
    """
    Answer health endpoint.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    status: Literal["ok"]

    service: str

    version: str


class APIError(BaseModel):
    """
    Stable description of the one API-error.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    code: str = Field(
        min_length=1,
    )

    message: str = Field(
        min_length=1,
    )

    retryable: bool

    trace_id: str = Field(
        min_length=1,
    )

    request_id: str | None = None

    details: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ) = None


class ErrorResponse(BaseModel):
    """
    External nut of the error. 
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    error: APIError