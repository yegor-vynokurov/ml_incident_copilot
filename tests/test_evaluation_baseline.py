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
    load_baseline,
    save_baseline,
)


def test_baseline_round_trip(
    tmp_path: Path,
):
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

    path = (
        tmp_path
        / "baseline.json"
    )

    save_baseline(
        path=path,
        baseline=baseline,
    )

    loaded = load_baseline(
        path
    )

    assert (
        loaded.schema_version
        == "1.0"
    )

    assert (
        loaded.source.mode
        == "live"
    )

    assert (
        loaded.source.runs
        == 3
    )

    assert (
        loaded.metrics.hard_pass_rate
        == 1.0
    )

    assert (
        loaded.metrics.quality_pass_rate
        == 1.0
    )

    assert (
        loaded.metrics.first_pass_rate
        == 1.0
    )

    assert (
        loaded.metrics.repair_rate
        == 0.0
    )

    assert (
        loaded
        .critical_cases[
            "model_location_mismatch"
        ]
        .pass_rate
        == 1.0
    )