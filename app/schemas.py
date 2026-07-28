from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    request_id: str
    location: str
    area: float = Field(gt=0)
    road_frontage: float = Field(ge=0)
    is_landlocked: bool
    predicted_price: float = Field(gt=0)
    model_version: str


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class IncidentDiagnosis(BaseModel):
    request_id: str

    status: Literal["ok", "needs_review", "critical"]
    issue_type: str
    severity: Literal["low", "medium", "high"]

    evidence: list[str]
    possible_causes: list[str]
    recommended_actions: list[str]

    confidence: float = Field(ge=0, le=1)


class AgentError(BaseModel):
    status: Literal["error"] = "error"
    error_type: str
    message: str
    retryable: bool


class AgentResponse(BaseModel):
    diagnosis: IncidentDiagnosis | None = None
    error: AgentError | None = None


class PredictionRequest(BaseModel):
    request_id: str
    location: str

    area: float = Field(gt=0)
    road_frontage: float = Field(ge=0)
    is_landlocked: bool

    predicted_price: float = Field(gt=0)
    model_version: str


class ToolResult(BaseModel):
    """
    Universal response from any tool

    success shows is the tool was success
    found problem with data is not obviously success=False.
    """

    tool_name: str
    success: bool

    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class ModelMetadata(BaseModel):
    model_version: str
    location: str
    training_date: date

    validation_smape: float = Field(ge=0)
    supported_area_range: tuple[float, float]

    is_active: bool = True


class LocationStats(BaseModel):
    location: str

    median_price_per_area: float = Field(gt=0)
    p10_price_per_area: float = Field(gt=0)
    p90_price_per_area: float = Field(gt=0)

    sample_size: int = Field(ge=0)


class KnownIssue(BaseModel):
    issue_id: str
    title: str

    trigger_codes: list[str]

    possible_causes: list[str]
    recommended_checks: list[str]



