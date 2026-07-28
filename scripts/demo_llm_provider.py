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

from app.llm.factory import create_llm_provider


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

Use only facts explicitly present in the deterministic tool results.
Do not combine separate checks into one explanation.
Do not describe a check as failed when its value is true.
When explaining an issue, quote the exact relevant field names and values.
Do not claim that the model is wrong or that a prediction is an outlier
unless the tool results explicitly say so.
Describe possible causes as hypotheses, not detected facts.
Clearly separate:
1. detected facts,
2. possible causes,
3. recommended checks.
""".strip()

    user_prompt = f"""
Review the following deterministic tool results.

Write a concise technical summary.

For every detected issue:
- state the exact issue code;
- cite the exact evidence from tool results;
- list possible causes only if they are present in known issue matches;
- list recommended checks;
- do not mention successful checks as problems.

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