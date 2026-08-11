import argparse
from pathlib import Path

from app.evaluation.baseline_comparison import (
    build_current_snapshot,
    compare_with_baseline,
    save_comparison,
)
from app.evaluation.baseline_store import (
    load_baseline,
)
from app.evaluation.summary_reader import (
    load_evaluation_summary,
)


DEFAULT_BASELINE_PATH = Path(
    "data/evaluation/baseline.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare an evaluation summary "
            "with the accepted baseline."
        )
    )

    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help=(
            "Path to evaluation summary.json."
        ),
    )

    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    return parser.parse_args()



def _format_rate(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    return f"{value:.1%}"



def _format_delta(
    value: float | None,
) -> str:
    if value is None:
        return "n/a"

    return f"{value:+.1%}"



def _print_metric(
    *,
    title: str,
    comparison,
) -> None:
    print(title)

    print(
        "  baseline: "
        f"{_format_rate(comparison.baseline)}"
    )

    print(
        "  current:  "
        f"{_format_rate(comparison.current)}"
    )

    print(
        "  delta:    "
        f"{_format_delta(comparison.delta)}"
    )

    print(
        "  status:   "
        f"{comparison.status.upper()}"
    )

    print()



def main() -> None:
    args = parse_args()

    baseline = load_baseline(
        args.baseline
    )

    summary = load_evaluation_summary(
        args.report
    )

    current = build_current_snapshot(
        summary=summary,
        baseline=baseline,
    )

    comparison = compare_with_baseline(
        baseline=baseline,
        current=current,
        report_path=args.report,
    )

    output_path = (
        args.output
        if args.output is not None
        else (
            args.report.parent
            / "baseline_comparison.json"
        )
    )

    save_comparison(
        path=output_path,
        comparison=comparison,
    )

    print()
    print(
        "EVALUATION BASELINE COMPARISON"
    )
    print()

    _print_metric(
        title="Hard pass rate",
        comparison=(
            comparison.metrics[
                "hard_pass_rate"
            ]
        ),
    )

    _print_metric(
        title="Quality pass rate",
        comparison=(
            comparison.metrics[
                "quality_pass_rate"
            ]
        ),
    )

    _print_metric(
        title="First-pass rate",
        comparison=(
            comparison.metrics[
                "first_pass_rate"
            ]
        ),
    )

    _print_metric(
        title="Repair rate",
        comparison=(
            comparison.metrics[
                "repair_rate"
            ]
        ),
    )

    print("Critical cases")
    print()

    for (
        issue_code,
        critical,
    ) in comparison.critical_cases.items():
        print(
            f"  {issue_code}: "
            f"{critical.status.upper()}"
        )

        print(
            "    baseline: "
            f"{_format_rate(critical.baseline)}"
        )

        print(
            "    current:  "
            f"{_format_rate(critical.current)}"
        )

    if comparison.notes:
        print()
        print("Notes")

        for note in comparison.notes:
            print(
                f"  - {note}"
            )

    print()
    print(
        f"Comparison saved: {output_path}"
    )


if __name__ == "__main__":
    main()