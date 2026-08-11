from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from app.evaluation.baseline_schemas import (
    BaselineMetrics,
    BaselineSource,
    CriticalCaseBaseline,
    EvaluationBaseline,
)
from app.evaluation.baseline_store import (
    save_baseline,
)


BASELINE_PATH = Path(
    "data/evaluation/baseline.json"
)


def main() -> None:
    baseline = EvaluationBaseline(
        created_at=datetime.now(
            timezone.utc
        ),
        source=BaselineSource(
            mode="live",
            runs=3,
        ),
        metrics=BaselineMetrics(
            hard_pass_rate=1.0,
            quality_pass_rate=1.0,
            first_pass_rate=1.0,
            repair_rate=0.0,
            median_duration_ms=None,
        ),
        critical_cases={
            "model_location_mismatch": (
                CriticalCaseBaseline(
                    pass_rate=1.0,
                )
            ),
        },
    )

    save_baseline(
        path=BASELINE_PATH,
        baseline=baseline,
    )

    print()
    print(
        "EVALUATION BASELINE CREATED"
    )
    print()
    print(
        f"Path: {BASELINE_PATH}"
    )
    print(
        "Hard pass rate: "
        f"{baseline.metrics.hard_pass_rate:.1%}"
    )
    print(
        "Quality pass rate: "
        f"{baseline.metrics.quality_pass_rate:.1%}"
    )
    print(
        "First-pass rate: "
        f"{baseline.metrics.first_pass_rate:.1%}"
    )
    print(
        "Repair rate: "
        f"{baseline.metrics.repair_rate:.1%}"
    )


if __name__ == "__main__":
    main()