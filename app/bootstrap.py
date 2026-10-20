"""Construct application services from bundled reference data."""

from pathlib import Path

from app.agent import AgentDependencies, MLIncidentAgent
from app.config import load_settings
from app.llm.base import LLMProvider
from app.llm.factory import create_llm_provider
from app.observability.store import JsonlRunStore, RunStore
from app.tools.issue_search import load_known_issues
from app.tools.model_registry import load_model_registry
from app.tools.prediction_analyzer import load_location_stats


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def build_run_store() -> RunStore:
    """Store runtime records beside the bundled data directory."""
    return JsonlRunStore(
        runs_path=DATA_DIR / "runtime/runs.jsonl",
        feedback_path=DATA_DIR / "runtime/feedback.jsonl",
    )


def build_agent(
    *, llm_provider: LLMProvider | None = None,
) -> MLIncidentAgent:
    """Build an agent, optionally with an offline provider."""
    registry = load_model_registry(DATA_DIR / "model_registry.json")
    stats_by_location = load_location_stats(DATA_DIR / "location_stats.json")
    known_issues = load_known_issues(DATA_DIR / "known_issues.json")

    provider = llm_provider
    if provider is None:
        provider = create_llm_provider(load_settings())

    return MLIncidentAgent(
        AgentDependencies(
            registry=registry,
            stats_by_location=stats_by_location,
            known_issues=known_issues,
            llm_provider=provider,
        )
    )
