import json
from pathlib import Path

from app.config import load_settings
from app.llm.openai_provider import create_llm_provider
from app.schemas import PredictionRequest
from app.tools.issue_search import load_known_issues
from app.tools.model_registry import load_model_registry
from app.tools.prediction_analyzer import (
    load_location_stats,
)
from app.tools.runner import run_domain_tools


DATA_DIR = Path("data")


def main() -> None:
    request = PredictionRequest(
        request_id="REQ-1042",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    registry = load_model_registry(
        DATA_DIR / "model_registry.json"
    )

    stats_by_location = load_location_stats(
        DATA_DIR / "location_stats.json"
    )

    known_issues = load_known_issues(
        DATA_DIR / "known_issues.json"
    )

    tool_results = run_domain_tools(
        request=request,
        registry=registry,
        stats_by_location=stats_by_location,
        known_issues=known_issues,
    )

    facts = [
        result.model_dump(mode="json")
        for result in tool_results
    ]

    facts_json = json.dumps(
        facts,
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = """
You are an assistant for diagnosing ML prediction incidents.

Use only the facts provided by deterministic Python tools.
Do not invent metrics, model versions, causes, or evidence.
Clearly separate detected facts from possible explanations.
""".strip()

    user_prompt = f"""
Review the following tool results.

Write a short technical summary:
1. What problems were detected?
2. What evidence supports them?
3. Which checks should an engineer perform next?

Tool results:

{facts_json}
""".strip()

    settings = load_settings()
    provider = create_llm_provider(settings)

    response = provider.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    print("\nMODEL RESPONSE\n")
    print(response.text)

    print("\nMETADATA\n")
    print(
        response.model_dump_json(
            indent=2,
        )
    )


if __name__ == "__main__":
    main()