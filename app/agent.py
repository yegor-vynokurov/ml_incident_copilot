from dataclasses import dataclass

from app.agent_prompts import (
    build_agent_prompts,
)
from app.llm.base import LLMProvider
from app.schemas import (
    AgentRun,
    AgentStep,
    KnownIssue,
    LocationStats,
    ModelMetadata,
    PredictionRequest,
    ToolResult,
)
from app.tools.input_validator import (
    validate_input,
)
from app.tools.issue_search import (
    search_known_issues,
)
from app.tools.model_registry import (
    get_model_metadata,
)
from app.tools.prediction_analyzer import (
    analyze_prediction,
)


@dataclass(frozen=True)
class AgentDependencies:
    """
    All dependencies needed for agent
    """

    registry: dict[str, ModelMetadata]

    stats_by_location: dict[
        str,
        LocationStats,
    ]

    known_issues: list[KnownIssue]

    llm_provider: LLMProvider