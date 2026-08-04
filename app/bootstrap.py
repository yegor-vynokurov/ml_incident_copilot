from app.agent import (
    AgentDependencies,
    MLIncidentAgent,
)

from pathlib import Path

from app.agent import (
    AgentDependencies,
    MLIncidentAgent,
)
from app.config import load_settings
from app.llm.factory import (
    create_llm_provider,
)
from app.schemas import PredictionRequest
from app.tools.issue_search import (
    load_known_issues,
)
from app.tools.model_registry import (
    load_model_registry,
)
from app.tools.prediction_analyzer import (
    load_location_stats,
)


DATA_DIR = Path("data")



def build_agent() -> MLIncidentAgent:
    """
    load the agent
    """


    registry = load_model_registry(
        DATA_DIR / "model_registry.json"
    )

    stats_by_location = load_location_stats(
        DATA_DIR / "location_stats.json"
    )

    known_issues = load_known_issues(
        DATA_DIR / "known_issues.json"
    )

    settings = load_settings()

    llm_provider = create_llm_provider(
        settings
    )


    dependencies = AgentDependencies(
        registry=registry,
        stats_by_location=(
            stats_by_location
        ),
        known_issues=known_issues,
        llm_provider=llm_provider,
    )

    return MLIncidentAgent(
        dependencies
    )