from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.schemas import (
    EvidenceToolName,
    PredictionRequest,
    ToolName,
)


EvaluationMode = Literal[
    "deterministic",
    "live",
]

StepStatus = Literal[
    "executed",
    "skipped",
]

CheckCategory = Literal[
    "hard",
    "quality",
]



class ExplanationRule(BaseModel):
    """
    small checking LLM-explanation for one problem
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    issue_code: str

    # in each group need to meet least one word
    required_term_groups: list[
        list[str]
    ] = Field(
        default_factory=list,
    )

    # There are forbidden words:
    forbidden_terms: list[str] = Field(
        default_factory=list,
    )


class EvaluationCase(BaseModel):
    """
    One short task with known answer
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    case_id: str = Field(
        min_length=1,
    )

    title: str = Field(
        min_length=1,
    )

    tags: list[str] = Field(
        default_factory=list,
    )

    request: PredictionRequest

    expected_issue_codes: list[str]

    expected_agent_status: Literal[
        "completed",
        "completed_with_issues",
    ]

    expected_step_statuses: dict[
        ToolName,
        StepStatus,
    ]

    expected_evidence_tools: dict[
        str,
        EvidenceToolName,
    ]

    explanation_rules: list[
        ExplanationRule
    ] = Field(
        default_factory=list,
    )


    @model_validator(
        mode="after"
    )
    def validate_expectations(
        self,
    ) -> "EvaluationCase":
        expected_codes = set(
            self.expected_issue_codes
        )

        if len(
            self.expected_issue_codes
        ) != len(expected_codes):
            raise ValueError(
                "expected_issue_codes "
                "contains duplicates."
            )

        required_status = (
            "completed_with_issues"
            if expected_codes
            else "completed"
        )

        if (
            self.expected_agent_status
            != required_status
        ):
            raise ValueError(
                "expected_agent_status "
                "does not match "
                "expected_issue_codes."
            )

        evidence_codes = set(
            self.expected_evidence_tools
        )

        if evidence_codes != expected_codes:
            raise ValueError(
                "expected_evidence_tools "
                "must contain exactly the "
                "expected issue codes."
            )

        expected_tools = {
            "validate_input",
            "get_model_metadata",
            "analyze_prediction",
            "search_known_issues",
        }

        if set(
            self.expected_step_statuses
        ) != expected_tools:
            raise ValueError(
                "expected_step_statuses "
                "must describe all agent tools."
            )

        for rule in self.explanation_rules:
            if (
                rule.issue_code
                not in expected_codes
            ):
                raise ValueError(
                    "Explanation rule refers "
                    "to an unexpected issue code."
                )

        return self




class CheckResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    name: str

    category: CheckCategory

    passed: bool

    expected: Any | None = None

    actual: Any | None = None

    message: str | None = None




class EvaluationCaseResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    case_id: str
    title: str
    tags: list[str]

    passed: bool
    hard_passed: bool
    quality_passed: bool
    quality_evaluated: bool

    duration_ms: float

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

    input_tokens: int = 0
    output_tokens: int = 0

    checks: list[
        CheckResult
    ] = Field(
        default_factory=list,
    )

    error_type: str | None = None
    error_message: str | None = None




class EvaluationSummary(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    mode: EvaluationMode

    dataset_path: str

    started_at: str

    total_cases: int
    passed_cases: int
    failed_cases: int

    hard_passed_cases: int
    hard_pass_rate: float

    quality_evaluated_cases: int
    quality_passed_cases: int
    quality_pass_rate: float | None

    cases_with_llm: int
    first_pass_cases: int
    first_pass_rate: float | None
    repair_used_cases: int

    average_duration_ms: float
    median_duration_ms: float

    total_input_tokens: int
    total_output_tokens: int

    case_results: list[
        EvaluationCaseResult
    ]