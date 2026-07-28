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

    settings = load_settings()

    llm_provider = create_llm_provider(
        settings
    )

    dependencies = AgentDependencies(
        registry=registry,
        stats_by_location=stats_by_location,
        known_issues=known_issues,
        llm_provider=llm_provider,
    )

    agent = MLIncidentAgent(
        dependencies=dependencies
    )

    result = agent.run(request)

    print("\nAGENT RESPONSE\n")
    print(result.llm_response.text)


    print('\nSTRUCTURED TEXT\n')
    print(
        result.llm_response
        .parsed
        .model_dump_json(
            indent=2,
        )
    )

    print("\nISSUE CODES\n")

    for issue_code in result.issue_codes:
        print(f"- {issue_code}")

    print("\nAGENT STEPS\n")

    for step in result.steps:
        print(
            f"- {step.tool_name}: "
            f"{step.status}"
        )

        print(
            f"  reason: {step.reason}"
        )

    print("\nFULL AGENT RUN\n")

    print(
        result.model_dump_json(
            indent=2,
        )
    )


if __name__ == "__main__":
    main()