from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
import json

import pytest

from scripts.create_evaluation_baseline import create_baseline

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


def test_baseline_creation_requires_matching_live_cases(tmp_path: Path):
    summary = {
        "mode": "live",
        "hard_pass_rate": 100.0,
        "quality_pass_rate": 100.0,
        "first_pass_rate": 100.0,
        "repair_used_cases": 0,
        "cases_with_llm": 1,
        "case_results": [
            {
                "case_id": "location_mismatch",
                "passed": True,
                "hard_passed": True,
                "quality_passed": True,
                "quality_evaluated": True,
                "issue_codes": ["model_location_mismatch"],
                "checks": [
                    {
                        "name": "issue_codes",
                        "category": "hard",
                        "passed": True,
                        "expected": ["model_location_mismatch"],
                        "actual": ["model_location_mismatch"],
                    }
                ],
            }
        ],
    }
    paths = [tmp_path / f"summary-{index}.json" for index in range(3)]
    for path in paths:
        path.write_text(json.dumps(summary), encoding="utf-8")

    baseline = create_baseline(paths)
    assert baseline.source.case_ids == ["location_mismatch"]

    summary["case_results"][0]["case_id"] = "different_case"
    paths[-1].write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="different evaluation cases"):
        create_baseline(paths)

    summary["case_results"][0]["case_id"] = "location_mismatch"
    summary["case_results"][0]["passed"] = False
    paths[-1].write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="Every baseline evaluation case"):
        create_baseline(paths)
