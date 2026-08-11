from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from app.evaluation.baseline_comparison import (
    build_current_snapshot,
    compare_with_baseline,
)
from app.evaluation.baseline_schemas import (
    BaselineMetrics,
    BaselineSource,
    CriticalCaseBaseline,
    EvaluationBaseline,
)
from app.evaluation.summary_reader import (
    EvaluationSummaryReport,
)


import pytest




def _baseline() -> EvaluationBaseline:
    return EvaluationBaseline(
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
                    pass_rate=1.0
                )
            )
        },
    )



def _perfect_summary():
    return EvaluationSummaryReport(
        mode="live",
        hard_pass_rate=100.0,
        quality_pass_rate=100.0,
        first_pass_rate=100.0,
        repair_used_cases=0,
        cases_with_llm=5,
        median_duration_ms=2100.0,
        case_results=[
            {
                "case_id": (
                    "unsupported_location"
                ),
                "passed": True,
                "hard_passed": True,
                "quality_passed": True,
                "quality_evaluated": True,
                "issue_codes": [
                    "model_location_mismatch",
                    "unsupported_location",
                ],
                "attempts_by_issue": {
                    "model_location_mismatch": 1,
                    "unsupported_location": 1,
                },
                "repair_attempts": 0,
                "checks": [
                    {
                        "name": "issue_codes",
                        "category": "hard",
                        "passed": True,
                        "expected": [
                            "model_location_mismatch",
                            "unsupported_location",
                        ],
                        "actual": [
                            "model_location_mismatch",
                            "unsupported_location",
                        ],
                    },
                    {
                        "name": (
                            "required_term_group:"
                            "model_location_mismatch:0"
                        ),
                        "category": "quality",
                        "passed": True,
                        "expected": [
                            "model"
                        ],
                        "actual": (
                            "Model location mismatch."
                        ),
                    },
                ],
            }
        ],
    )


def test_perfect_current_matches_baseline():
    baseline = _baseline()
    summary = _perfect_summary()

    current = build_current_snapshot(
        summary=summary,
        baseline=baseline,
    )

    comparison = compare_with_baseline(
        baseline=baseline,
        current=current,
        report_path=Path(
            "summary.json"
        ),
    )

    assert (
        comparison
        .metrics[
            "hard_pass_rate"
        ]
        .status
        == "same"
    )

    assert (
        comparison
        .metrics[
            "quality_pass_rate"
        ]
        .status
        == "same"
    )

    assert (
        comparison
        .metrics[
            "first_pass_rate"
        ]
        .status
        == "same"
    )

    assert (
        comparison
        .metrics[
            "repair_rate"
        ]
        .status
        == "same"
    )

    assert (
        comparison
        .critical_cases[
            "model_location_mismatch"
        ]
        .status
        == "same"
    )



def test_quality_drop_is_regression():
    baseline = _baseline()

    summary = _perfect_summary()

    summary.quality_pass_rate = 80.0

    current = build_current_snapshot(
        summary=summary,
        baseline=baseline,
    )

    comparison = compare_with_baseline(
        baseline=baseline,
        current=current,
        report_path=Path(
            "summary.json"
        ),
    )

    quality = (
        comparison
        .metrics[
            "quality_pass_rate"
        ]
    )

    assert (
        quality.status
        == "regressed"
    )

    assert (
        quality.baseline
        == 1.0
    )

    assert (
        quality.current
        == 0.8
    )

    assert quality.delta == pytest.approx(
            -0.2
        )




def test_repair_increase_is_regression():
    baseline = _baseline()

    summary = _perfect_summary()

    summary.repair_used_cases = 1
    summary.cases_with_llm = 5

    current = build_current_snapshot(
        summary=summary,
        baseline=baseline,
    )

    comparison = compare_with_baseline(
        baseline=baseline,
        current=current,
        report_path=Path(
            "summary.json"
        ),
    )

    repair = (
        comparison
        .metrics[
            "repair_rate"
        ]
    )

    assert (
        repair.status
        == "regressed"
    )

    assert repair.current == pytest.approx(
        0.2
    )



def test_critical_issue_failure_is_regression():
    baseline = _baseline()

    summary = _perfect_summary()

    for check in (
        summary
        .case_results[0]
        .checks
    ):
        if (
            "model_location_mismatch"
            in check.name
        ):
            check.passed = False

    current = build_current_snapshot(
        summary=summary,
        baseline=baseline,
    )

    comparison = compare_with_baseline(
        baseline=baseline,
        current=current,
        report_path=Path(
            "summary.json"
        ),
    )

    critical = (
        comparison
        .critical_cases[
            "model_location_mismatch"
        ]
    )

    assert (
        critical.status
        == "regressed"
    )

    assert critical.current == 0.0



