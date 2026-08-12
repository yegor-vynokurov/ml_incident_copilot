import argparse
import subprocess
import sys
import time
from pathlib import Path

from app.evaluation.baseline_comparison import (
    build_current_snapshot,
    compare_with_baseline,
    save_comparison,
)
from app.evaluation.baseline_store import (
    load_baseline,
)
from app.evaluation.release_gate import (
    evaluate_release_gate,
    save_release_gate_result,
)
from app.evaluation.release_gate_store import (
    load_release_gate_policy,
)
from app.evaluation.summary_reader import (
    load_evaluation_summary,
)


DEFAULT_BASELINE_PATH = Path(
    "data/evaluation/baseline.json"
)

DEFAULT_POLICY_PATH = Path(
    "data/evaluation/release_policy.json"
)

DEFAULT_REPORTS_ROOT = Path(
    "reports/evaluation"
)


def _run_command(
    *,
    args: list[str],
    title: str,
) -> int:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
    print()

    completed = subprocess.run(
        args,
        check=False,
    )

    return completed.returncode


def _find_summary_files(
    reports_root: Path,
) -> set[Path]:
    if not reports_root.exists():
        return set()

    return {
        path.resolve()
        for path
        in reports_root.rglob(
            "summary.json"
        )
    }


def _find_new_summary(
    *,
    reports_root: Path,
    before: set[Path],
    evaluation_started_at: float,
) -> Path:
    after = _find_summary_files(
        reports_root
    )

    new_files = (
        after - before
    )

    if new_files:
        return max(
            new_files,
            key=lambda path: (
                path.stat().st_mtime
            ),
        )

    candidates = [
        path
        for path in after
        if (
            path.stat().st_mtime
            >= evaluation_started_at
        )
    ]

    if candidates:
        return max(
            candidates,
            key=lambda path: (
                path.stat().st_mtime
            ),
        )

    raise RuntimeError(
        "Live evaluation completed, "
        "but no new summary.json "
        "could be found."
    )


def _format_rate(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    return f"{value:.1%}"


def _print_comparison(
    comparison,
) -> None:
    print()
    print("=" * 72)
    print("3. BASELINE COMPARISON")
    print("=" * 72)
    print()

    metric_titles = {
        "hard_pass_rate": (
            "Hard pass rate"
        ),
        "quality_pass_rate": (
            "Quality pass rate"
        ),
        "first_pass_rate": (
            "First-pass rate"
        ),
        "repair_rate": (
            "Repair rate"
        ),
    }

    for (
        metric_name,
        title,
    ) in metric_titles.items():
        metric = (
            comparison.metrics.get(
                metric_name
            )
        )

        if metric is None:
            continue

        print(
            f"{title}: "
            f"{metric.status.upper()}"
        )

        print(
            "  baseline: "
            f"{_format_rate(metric.baseline)}"
        )

        print(
            "  current:  "
            f"{_format_rate(metric.current)}"
        )

        print()

    if comparison.critical_cases:
        print("Critical cases:")

        for (
            issue_code,
            result,
        ) in (
            comparison
            .critical_cases
            .items()
        ):
            print(
                f"  {issue_code}: "
                f"{result.status.upper()}"
            )

        print()

    if comparison.notes:
        print("Comparison notes:")

        for note in comparison.notes:
            print(
                f"  - {note}"
            )

        print()


def _print_gate_result(
    result,
) -> None:
    print()
    print("=" * 72)
    print("4. RELEASE GATE")
    print("=" * 72)
    print()

    for check in result.checks:
        marker = {
            "pass": "[PASS]",
            "fail": "[FAIL]",
            "warning": "[WARN]",
        }[check.status]

        print(
            f"{marker} "
            f"{check.name}: "
            f"{check.message}"
        )

    print()
    print(
        "FINAL DECISION: "
        f"{result.decision.upper()}"
    )

    if result.blocking_failures:
        print()
        print("Blocking failures:")

        for name in (
            result.blocking_failures
        ):
            print(
                f"  - {name}"
            )

    if result.warnings:
        print()
        print("Warnings:")

        for name in result.warnings:
            print(
                f"  - {name}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete local "
            "ML Incident Copilot release gate."
        )
    )

    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
    )

    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
    )

    parser.add_argument(
        "--reports-root",
        type=Path,
        default=DEFAULT_REPORTS_ROOT,
    )

    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help=(
            "Skip pytest. Intended only "
            "for development/debugging."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print()
    print("=" * 72)
    print("ML INCIDENT COPILOT RELEASE GATE")
    print("=" * 72)

    baseline = load_baseline(
        args.baseline
    )

    policy = (
        load_release_gate_policy(
            args.policy
        )
    )

    if not args.skip_tests:
        test_exit_code = _run_command(
            args=[
                sys.executable,
                "-m",
                "pytest",
                "-q",
            ],
            title="1. PYTEST",
        )

        if test_exit_code != 0:
            print()
            print(
                "RELEASE GATE STOPPED"
            )
            print(
                "Pytest failed."
            )
            print(
                "FINAL DECISION: FAIL"
            )

            return 1

    else:
        print()
        print(
            "1. PYTEST: SKIPPED"
        )

    summaries_before = (
        _find_summary_files(
            args.reports_root
        )
    )

    evaluation_started_at = (
        time.time()
    )

    evaluation_exit_code = _run_command(
        args=[
            sys.executable,
            "-m",
            "scripts.run_evaluation",
            "--mode",
            "live",
        ],
        title="2. LIVE EVALUATION",
    )

    if evaluation_exit_code != 0:
        print()
        print(
            "RELEASE GATE STOPPED"
        )
        print(
            "Live evaluation command failed."
        )
        print(
            "FINAL DECISION: FAIL"
        )

        return 1

    try:
        summary_path = (
            _find_new_summary(
                reports_root=(
                    args.reports_root
                ),
                before=(
                    summaries_before
                ),
                evaluation_started_at=(
                    evaluation_started_at
                ),
            )
        )

    except RuntimeError as exc:
        print()
        print(
            "RELEASE GATE STOPPED"
        )
        print(str(exc))
        print(
            "FINAL DECISION: FAIL"
        )

        return 1

    print()
    print(
        "Fresh evaluation summary:"
    )
    print(
        f"  {summary_path}"
    )

    summary = load_evaluation_summary(
        summary_path
    )

    if summary.mode != "live":
        print()
        print(
            "RELEASE GATE STOPPED"
        )
        print(
            "Fresh evaluation is not live: "
            f"{summary.mode!r}."
        )
        print(
            "FINAL DECISION: FAIL"
        )

        return 1

    current = build_current_snapshot(
        summary=summary,
        baseline=baseline,
    )

    comparison = compare_with_baseline(
        baseline=baseline,
        current=current,
        report_path=summary_path,
    )

    comparison_path = (
        summary_path.parent
        / "baseline_comparison.json"
    )

    save_comparison(
        path=comparison_path,
        comparison=comparison,
    )

    _print_comparison(
        comparison
    )

    gate_result = (
        evaluate_release_gate(
            comparison=comparison,
            policy=policy,
        )
    )

    gate_result_path = (
        summary_path.parent
        / "release_gate_result.json"
    )

    save_release_gate_result(
        path=gate_result_path,
        result=gate_result,
    )

    _print_gate_result(
        gate_result
    )

    print()
    print(
        "Artifacts:"
    )
    print(
        f"  summary: {summary_path}"
    )
    print(
        "  comparison: "
        f"{comparison_path}"
    )
    print(
        "  gate result: "
        f"{gate_result_path}"
    )

    if gate_result.decision == "fail":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )