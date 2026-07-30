from datetime import date
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, ConfigDict


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


class LLMResponse(BaseModel):
    text: str

    provider: str
    model: str

    request_id: str | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None


ToolName = Literal[
    "validate_input",
    "get_model_metadata",
    "analyze_prediction",
    "search_known_issues",
]

EvidenceToolName = Literal[
    "validate_input",
    "get_model_metadata",
    "analyze_prediction",
]

class EvidenceReference(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    tool_name: EvidenceToolName

class AgentStep(BaseModel):
    """
    Note about one step of agent

    status:
    - executed: tool was executed;
    - skipped: agent decided to not call the tool.
    """

    tool_name: ToolName
    status: Literal["executed", "skipped"]
    reason: str

    result: ToolResult | None = None




from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceReference(BaseModel):
    """
    Инструмент, который обнаружил проблему,
    указанную в родительском finding.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    tool_name: Literal[
        "validate_input",
        "get_model_metadata",
        "analyze_prediction",
    ]


    


class IncidentFinding(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    issue_code: str

    explanation: str = Field(
        min_length=1,
        max_length=500,
    )

    evidence_ref: EvidenceReference

    possible_causes: list[str] = Field(
        default_factory=list,
    )

    recommended_checks: list[str] = Field(
        default_factory=list,
    )


class IncidentReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    request_id: str

    status: Literal[
        "ok",
        "needs_review",
    ]

    summary: str = Field(
        min_length=1,
        max_length=500,
    )

    findings: list[IncidentFinding] = Field(
        default_factory=list,
    )



StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)


class StructuredLLMResponse(
    BaseModel,
    Generic[StructuredModelT],
):
    """
    Универсальный ответ LLM с валидированной моделью.
    """

    raw_text: str

    parsed: StructuredModelT

    provider: str
    model: str

    request_id: str | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None
    attempt_count: int = Field(
                                default=1,
                                ge=1,
                            )


class IssueAnalysisTrace(BaseModel):
    """
    result of the llm-analyze for one problem.
    """

    issue_code: str

    response: StructuredLLMResponse[
        IssueAnalysis
    ]


class AgentRun(BaseModel):
    request_id: str

    status: Literal[
        "completed",
        "completed_with_issues",
    ]

    issue_codes: list[str] = Field(
        default_factory=list,
    )

    steps: list[AgentStep] = Field(
        default_factory=list,
    )

    report: IncidentReport

    analysis_traces: list[
        IssueAnalysisTrace
    ] = Field(
        default_factory=list,
    )



class IssueAnalysis(BaseModel):
    """
    Единственная часть finding,
    которую создаёт LLM.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    explanation: str = Field(
        min_length=10,
        max_length=500,
    )


