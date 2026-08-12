import json

from app.bootstrap import (
    build_agent,
)
from app.schemas import (
    PredictionRequest,
)


def main() -> None:
    agent = build_agent()

    request = PredictionRequest(
        request_id="DEMO-001",
        location="district_07",
        area=8500,
        road_frontage=0,
        is_landlocked=False,
        predicted_price=12000,
        model_version="district_07_v3",
    )

    result = agent.run(
        request
    )

    print()
    print("=" * 72)
    print("ML INCIDENT COPILOT DEMO")
    print("=" * 72)
    print()

    print("INPUT")
    print()

    print(
        json.dumps(
            request.model_dump(
                mode="json"
            ),
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print("RESULT")
    print()

    print(
        json.dumps(
            result.model_dump(
                mode="json"
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()