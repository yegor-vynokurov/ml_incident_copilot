from datetime import (
    datetime,
    timezone,
)

from app.evaluation.comparison_schemas import (
    EvaluationComparison,
    MetricComparison,
)
from app.evaluation.release_gate import (
    evaluate_release_gate,
)
from app.evaluation.release_gate_schemas import (
    ReleaseGatePolicy,
)

from app.evaluation.comparison_schemas import (
    ComparisonStatus,
    EvaluationComparison,
    MetricComparison,
)


from pathlib import Path

from app.evaluation.release_gate_store import (
    load_release_gate_policy,
)




def _policy() -> ReleaseGatePolicy:
    return ReleaseGatePolicy(
        required_mode="live",
        blocking_metrics=[
            "hard_pass_rate",
            "quality_pass_rate",
        ],
        warning_metrics=[
            "first_pass_rate",
            "repair_rate",
        ],
        block_on_critical_regression=True,
        block_on_missing_critical_case=True,
        block_on_not_compared_blocking_metric=True,
    )




def _metric(
    *,
    baseline: float,
    current: float,
    status: ComparisonStatus,
) -> MetricComparison:
    return MetricComparison(
        baseline=baseline,
        current=current,
        delta=(
            current - baseline
        ),
        status=status,
    )



def _perfect_comparison() -> EvaluationComparison:
    now = datetime.now(
        timezone.utc
    )

    return EvaluationComparison(
        created_at=now,
        baseline_created_at=now,
        baseline_mode="live",
        current_mode="live",
        report_path="summary.json",
        metrics={
            "hard_pass_rate": _metric(
                baseline=1.0,
                current=1.0,
                status="same",
            ),
            "quality_pass_rate": _metric(
                baseline=1.0,
                current=1.0,
                status="same",
            ),
            "first_pass_rate": _metric(
                baseline=1.0,
                current=1.0,
                status="same",
            ),
            "repair_rate": _metric(
                baseline=0.0,
                current=0.0,
                status="same",
            ),
        },
        critical_cases={
            "model_location_mismatch": (
                _metric(
                    baseline=1.0,
                    current=1.0,
                    status="same",
                )
            ),
        },
        notes=[],
    )




def test_perfect_comparison_passes_gate():
    result = evaluate_release_gate(
        comparison=(
            _perfect_comparison()
        ),
        policy=_policy(),
    )

    assert result.decision == "pass"
    assert result.blocking_failures == []
    assert result.warnings == []


def test_dataset_mismatch_blocks_release():
    comparison = _perfect_comparison().model_copy(
        update={"dataset_matches": False}
    )
    result = evaluate_release_gate(comparison=comparison, policy=_policy())
    assert result.decision == "fail"
    assert "evaluation_dataset" in result.blocking_failures

def test_hard_regression_fails_gate():
    comparison = (
        _perfect_comparison()
    )

    comparison.metrics[
        "hard_pass_rate"
    ] = _metric(
        baseline=1.0,
        current=0.8,
        status="regressed",
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "fail"

    assert (
        "hard_pass_rate"
        in result.blocking_failures
    )


def test_quality_regression_fails_gate():
    comparison = (
        _perfect_comparison()
    )

    comparison.metrics[
        "quality_pass_rate"
    ] = _metric(
        baseline=1.0,
        current=0.8,
        status="regressed",
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "fail"

    assert (
        "quality_pass_rate"
        in result.blocking_failures
    )



def test_first_pass_regression_warns_but_passes():
    comparison = (
        _perfect_comparison()
    )

    comparison.metrics[
        "first_pass_rate"
    ] = _metric(
        baseline=1.0,
        current=0.8,
        status="regressed",
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "pass"

    assert (
        "first_pass_rate"
        in result.warnings
    )

    assert (
        result.blocking_failures
        == []
    )



def test_repair_regression_warns_but_passes():
    comparison = (
        _perfect_comparison()
    )

    comparison.metrics[
        "repair_rate"
    ] = _metric(
        baseline=0.0,
        current=0.2,
        status="regressed",
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "pass"

    assert (
        "repair_rate"
        in result.warnings
    )



def test_critical_case_regression_fails_gate():
    comparison = (
        _perfect_comparison()
    )

    comparison.critical_cases[
        "model_location_mismatch"
    ] = _metric(
        baseline=1.0,
        current=0.0,
        status="regressed",
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "fail"

    assert (
        "critical_case:"
        "model_location_mismatch"
        in result.blocking_failures
    )



def test_wrong_evaluation_mode_fails_gate():
    comparison = (
        _perfect_comparison()
    )

    comparison.current_mode = (
        "deterministic"
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "fail"

    assert (
        "evaluation_mode"
        in result.blocking_failures
    )



def test_missing_blocking_metric_fails_gate():
    comparison = (
        _perfect_comparison()
    )

    comparison.metrics[
        "quality_pass_rate"
    ] = MetricComparison(
        baseline=1.0,
        current=None,
        delta=None,
        status="not_compared",
    )

    result = evaluate_release_gate(
        comparison=comparison,
        policy=_policy(),
    )

    assert result.decision == "fail"

    assert (
        "quality_pass_rate"
        in result.blocking_failures
    )



def test_project_release_policy_loads():
    policy = load_release_gate_policy(
        Path(
            "data/evaluation/"
            "release_policy.json"
        )
    )

    assert (
        policy.required_mode
        == "live"
    )

    assert (
        "hard_pass_rate"
        in policy.blocking_metrics
    )

    assert (
        "quality_pass_rate"
        in policy.blocking_metrics
    )

    assert (
        "first_pass_rate"
        in policy.warning_metrics
    )
