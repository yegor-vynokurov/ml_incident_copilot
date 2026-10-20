import json
from pathlib import Path

from app.config import load_settings
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

Use only facts explicitly present in the request and deterministic
tool results.

Rules:
1. Do not invent metrics, values, model versions, causes, or evidence.
2. Do not describe a successful check as a problem.
3. Quote exact field names and values when they are available.
4. Do not claim that a prediction is wrong.
5. Do not call a prediction an outlier unless a tool explicitly says so.
6. Possible causes must be copied only from known issue matches.
7. Recommended checks must be copied only from known issue matches.
8. Do not add external data sources, technologies, services, maps,
   databases, or remediation steps.
9. Do not recommend retraining unless it appears explicitly in the
   deterministic tool results.
10. Clearly separate detected facts, possible causes, and checks.
11. Keep the response concise and technical.
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

For possible causes and recommended checks:
- copy the original meaning from known issue matches;
- do not expand the recommendations with new examples;
- do not suggest additional actions.
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
