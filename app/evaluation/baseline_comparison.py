from datetime import (
    datetime,
    timezone,
)
import json
from pathlib import Path

from app.evaluation.baseline_schemas import (
    EvaluationBaseline,
)
from app.evaluation.comparison_schemas import (
    CurrentCriticalCaseResult,
    CurrentEvaluationMetrics,
    CurrentEvaluationSnapshot,
    EvaluationComparison,
    MetricComparison,
)
from app.evaluation.summary_reader import (
    EvaluationSummaryReport,
)






def _percentage_to_fraction(
    value: float | None,
) -> float | None:
    """
    Evaluation summary stores rates as
    0..100, while baseline stores them
    as 0..1.
    """

    if value is None:
        return None

    if value < 0.0 or value > 100.0:
        raise ValueError(
            "Evaluation percentage must be "
            "between 0 and 100. "
            f"Got {value!r}."
        )

    return value / 100.0




def _calculate_repair_rate(
    *,
    repair_used_cases: int,
    cases_with_llm: int,
) -> float | None:
    if cases_with_llm == 0:
        return None

    return (
        repair_used_cases
        / cases_with_llm
    )




def _get_expected_issue_codes(
    case,
) -> set[str]:
    """
    Read expected issue codes from the
    hard 'issue_codes' evaluation check.
    """

    for check in case.checks:
        if check.name != "issue_codes":
            continue

        if not isinstance(
            check.expected,
            list,
        ):
            return set()

        return {
            str(value)
            for value
            in check.expected
        }

    return set()



def _issue_quality_checks(
    *,
    case,
    issue_code: str,
):
    marker = (
        f":{issue_code}:"
    )

    return [
        check
        for check in case.checks
        if (
            check.category == "quality"
            and marker in check.name
        )
    ]



def _build_critical_case_result(
    *,
    summary: EvaluationSummaryReport,
    issue_code: str,
) -> CurrentCriticalCaseResult:
    relevant_cases = 0
    passed_cases = 0

    for case in summary.case_results:
        expected_issue_codes = (
            _get_expected_issue_codes(
                case
            )
        )

        if (
            issue_code
            not in expected_issue_codes
        ):
            continue

        relevant_cases += 1

        issue_detected = (
            issue_code
            in case.issue_codes
        )

        quality_checks = (
            _issue_quality_checks(
                case=case,
                issue_code=issue_code,
            )
        )

        quality_passed = all(
            check.passed
            for check
            in quality_checks
        )

        if (
            issue_detected
            and quality_passed
        ):
            passed_cases += 1

    if relevant_cases == 0:
        pass_rate = None

    else:
        pass_rate = (
            passed_cases
            / relevant_cases
        )

    return CurrentCriticalCaseResult(
        relevant_cases=(
            relevant_cases
        ),
        passed_cases=(
            passed_cases
        ),
        pass_rate=pass_rate,
    )



def build_current_snapshot(
    *,
    summary: EvaluationSummaryReport,
    baseline: EvaluationBaseline,
) -> CurrentEvaluationSnapshot:
    critical_cases = {
        issue_code: (
            _build_critical_case_result(
                summary=summary,
                issue_code=issue_code,
            )
        )
        for issue_code
        in baseline.critical_cases
    }

    return CurrentEvaluationSnapshot(
        mode=summary.mode,
        metrics=CurrentEvaluationMetrics(
            hard_pass_rate=(
                _percentage_to_fraction(
                    summary.hard_pass_rate
                )
            ),
            quality_pass_rate=(
                _percentage_to_fraction(
                    summary.quality_pass_rate
                )
            ),
            first_pass_rate=(
                _percentage_to_fraction(
                    summary.first_pass_rate
                )
            ),
            repair_rate=(
                _calculate_repair_rate(
                    repair_used_cases=(
                        summary
                        .repair_used_cases
                    ),
                    cases_with_llm=(
                        summary
                        .cases_with_llm
                    ),
                )
            ),
            median_duration_ms=(
                summary.median_duration_ms
            ),
        ),
        critical_cases=critical_cases,
    )



def _compare_metric(
    *,
    baseline_value: float | None,
    current_value: float | None,
    higher_is_better: bool,
) -> MetricComparison:
    if (
        baseline_value is None
        or current_value is None
    ):
        return MetricComparison(
            baseline=baseline_value,
            current=current_value,
            delta=None,
            status="not_compared",
        )

    delta = (
        current_value
        - baseline_value
    )

    tolerance = 1e-9

    if abs(delta) <= tolerance:
        status = "same"

    elif higher_is_better:
        status = (
            "improved"
            if delta > 0
            else "regressed"
        )

    else:
        status = (
            "improved"
            if delta < 0
            else "regressed"
        )

    return MetricComparison(
        baseline=baseline_value,
        current=current_value,
        delta=delta,
        status=status,
    )




def compare_with_baseline(
    *,
    baseline: EvaluationBaseline,
    current: CurrentEvaluationSnapshot,
    report_path: Path,
) -> EvaluationComparison:
    notes: list[str] = []

    if (
        baseline.source.mode
        != current.mode
    ):
        notes.append(
            "Baseline mode differs from "
            "current evaluation mode: "
            f"baseline={baseline.source.mode!r}, "
            f"current={current.mode!r}."
        )

    metric_comparisons = {
        "hard_pass_rate": (
            _compare_metric(
                baseline_value=(
                    baseline.metrics
                    .hard_pass_rate
                ),
                current_value=(
                    current.metrics
                    .hard_pass_rate
                ),
                higher_is_better=True,
            )
        ),
        "quality_pass_rate": (
            _compare_metric(
                baseline_value=(
                    baseline.metrics
                    .quality_pass_rate
                ),
                current_value=(
                    current.metrics
                    .quality_pass_rate
                ),
                higher_is_better=True,
            )
        ),
        "first_pass_rate": (
            _compare_metric(
                baseline_value=(
                    baseline.metrics
                    .first_pass_rate
                ),
                current_value=(
                    current.metrics
                    .first_pass_rate
                ),
                higher_is_better=True,
            )
        ),
        "repair_rate": (
            _compare_metric(
                baseline_value=(
                    baseline.metrics
                    .repair_rate
                ),
                current_value=(
                    current.metrics
                    .repair_rate
                ),
                higher_is_better=False,
            )
        ),
    }

    critical_comparisons: dict[
        str,
        MetricComparison,
    ] = {}

    for (
        issue_code,
        baseline_case,
    ) in baseline.critical_cases.items():
        current_case = (
            current
            .critical_cases
            .get(
                issue_code
            )
        )

        current_pass_rate = (
            current_case.pass_rate
            if current_case is not None
            else None
        )

        critical_comparisons[
            issue_code
        ] = _compare_metric(
            baseline_value=(
                baseline_case.pass_rate
            ),
            current_value=(
                current_pass_rate
            ),
            higher_is_better=True,
        )

    return EvaluationComparison(
        created_at=datetime.now(
            timezone.utc
        ),
        baseline_created_at=(
            baseline.created_at
        ),
        baseline_mode=(
            baseline.source.mode
        ),
        current_mode=current.mode,
        report_path=str(
            report_path
        ),
        metrics=(
            metric_comparisons
        ),
        critical_cases=(
            critical_comparisons
        ),
        notes=notes,
    )






def save_comparison(
    *,
    path: Path,
    comparison: EvaluationComparison,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = comparison.model_dump(
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