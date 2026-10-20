from app.evaluation.comparison_schemas import (
    EvaluationComparison,
    MetricComparison,
)
from app.evaluation.release_gate_schemas import (
    ReleaseGateCheck,
    ReleaseGatePolicy,
    ReleaseGateResult,
)

import json
from pathlib import Path






def _evaluate_blocking_metric(
    *,
    name: str,
    comparison: MetricComparison,
    policy: ReleaseGatePolicy,
) -> ReleaseGateCheck:
    if comparison.status == "not_compared":
        if (
            policy
            .block_on_not_compared_blocking_metric
        ):
            return ReleaseGateCheck(
                name=name,
                status="fail",
                message=(
                    "Blocking metric was not "
                    "available for comparison."
                ),
                baseline=comparison.baseline,
                current=comparison.current,
                delta=comparison.delta,
            )

        return ReleaseGateCheck(
            name=name,
            status="warning",
            message=(
                "Blocking metric was not "
                "available for comparison."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    if comparison.status == "regressed":
        return ReleaseGateCheck(
            name=name,
            status="fail",
            message=(
                "Blocking metric regressed "
                "relative to baseline."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    return ReleaseGateCheck(
        name=name,
        status="pass",
        message=(
            "Blocking metric did not regress."
        ),
        baseline=comparison.baseline,
        current=comparison.current,
        delta=comparison.delta,
    )




def _evaluate_warning_metric(
    *,
    name: str,
    comparison: MetricComparison,
) -> ReleaseGateCheck:
    if comparison.status == "regressed":
        return ReleaseGateCheck(
            name=name,
            status="warning",
            message=(
                "Non-blocking metric regressed "
                "relative to baseline."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    if comparison.status == "not_compared":
        return ReleaseGateCheck(
            name=name,
            status="warning",
            message=(
                "Non-blocking metric was not "
                "available for comparison."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    return ReleaseGateCheck(
        name=name,
        status="pass",
        message=(
            "Non-blocking metric did not regress."
        ),
        baseline=comparison.baseline,
        current=comparison.current,
        delta=comparison.delta,
    )



def _evaluate_critical_case(
    *,
    issue_code: str,
    comparison: MetricComparison,
    policy: ReleaseGatePolicy,
) -> ReleaseGateCheck:
    check_name = (
        "critical_case:"
        f"{issue_code}"
    )

    if comparison.status == "not_compared":
        if (
            policy
            .block_on_missing_critical_case
        ):
            return ReleaseGateCheck(
                name=check_name,
                status="fail",
                message=(
                    "Critical case could not "
                    "be compared."
                ),
                baseline=comparison.baseline,
                current=comparison.current,
                delta=comparison.delta,
            )

        return ReleaseGateCheck(
            name=check_name,
            status="warning",
            message=(
                "Critical case could not "
                "be compared."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    if (
        comparison.status == "regressed"
        and policy.block_on_critical_regression
    ):
        return ReleaseGateCheck(
            name=check_name,
            status="fail",
            message=(
                "Critical case regressed "
                "relative to baseline."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    if comparison.status == "regressed":
        return ReleaseGateCheck(
            name=check_name,
            status="warning",
            message=(
                "Critical case regressed, "
                "but policy does not block "
                "on this regression."
            ),
            baseline=comparison.baseline,
            current=comparison.current,
            delta=comparison.delta,
        )

    return ReleaseGateCheck(
        name=check_name,
        status="pass",
        message=(
            "Critical case did not regress."
        ),
        baseline=comparison.baseline,
        current=comparison.current,
        delta=comparison.delta,
    )



def _evaluate_mode(
    *,
    comparison: EvaluationComparison,
    policy: ReleaseGatePolicy,
) -> ReleaseGateCheck:
    if (
        comparison.current_mode
        != policy.required_mode
    ):
        return ReleaseGateCheck(
            name="evaluation_mode",
            status="fail",
            message=(
                "Release evaluation used the "
                "wrong mode. "
                f"Required={policy.required_mode!r}, "
                f"current="
                f"{comparison.current_mode!r}."
            ),
        )

    if (
        comparison.baseline_mode
        != policy.required_mode
    ):
        return ReleaseGateCheck(
            name="evaluation_mode",
            status="fail",
            message=(
                "Baseline uses a mode that does "
                "not match release policy. "
                f"Required={policy.required_mode!r}, "
                f"baseline="
                f"{comparison.baseline_mode!r}."
            ),
        )

    return ReleaseGateCheck(
        name="evaluation_mode",
        status="pass",
        message=(
            "Baseline and current evaluation "
            "use the required mode."
        ),
    )



def evaluate_release_gate(
    *,
    comparison: EvaluationComparison,
    policy: ReleaseGatePolicy,
) -> ReleaseGateResult:
    checks: list[
        ReleaseGateCheck
    ] = []

    # 1. Evaluation mode
    checks.append(
        _evaluate_mode(
            comparison=comparison,
            policy=policy,
        )
    )

    checks.append(
        ReleaseGateCheck(
            name="evaluation_dataset",
            status="pass" if comparison.dataset_matches else "fail",
            message=(
                "Evaluation case IDs match the accepted baseline."
                if comparison.dataset_matches
                else "Evaluation case IDs differ from the accepted baseline."
            ),
        )
    )

    # 2. Blocking metrics
    for metric_name in (
        policy.blocking_metrics
    ):
        metric = (
            comparison.metrics.get(
                metric_name
            )
        )

        if metric is None:
            checks.append(
                ReleaseGateCheck(
                    name=metric_name,
                    status="fail",
                    message=(
                        "Blocking metric is "
                        "missing from comparison."
                    ),
                )
            )
            continue

        checks.append(
            _evaluate_blocking_metric(
                name=metric_name,
                comparison=metric,
                policy=policy,
            )
        )

    # 3. Warning-only metrics
    for metric_name in (
        policy.warning_metrics
    ):
        metric = (
            comparison.metrics.get(
                metric_name
            )
        )

        if metric is None:
            checks.append(
                ReleaseGateCheck(
                    name=metric_name,
                    status="warning",
                    message=(
                        "Non-blocking metric is "
                        "missing from comparison."
                    ),
                )
            )
            continue

        checks.append(
            _evaluate_warning_metric(
                name=metric_name,
                comparison=metric,
            )
        )

    # 4. Critical cases
    for (
        issue_code,
        critical_comparison,
    ) in comparison.critical_cases.items():
        checks.append(
            _evaluate_critical_case(
                issue_code=issue_code,
                comparison=(
                    critical_comparison
                ),
                policy=policy,
            )
        )

    blocking_failures = [
        check.name
        for check in checks
        if check.status == "fail"
    ]

    warnings = [
        check.name
        for check in checks
        if check.status == "warning"
    ]

    decision = (
        "fail"
        if blocking_failures
        else "pass"
    )

    return ReleaseGateResult(
        decision=decision,
        checks=checks,
        blocking_failures=(
            blocking_failures
        ),
        warnings=warnings,
    )




def save_release_gate_result(
    *,
    path: Path,
    result: ReleaseGateResult,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = result.model_dump(
        mode="json"
    )

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
