"""Accept a baseline only from three matching, fully passing live reports."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.baseline_comparison import build_current_snapshot
from app.evaluation.baseline_schemas import (
    BaselineMetrics,
    BaselineSource,
    CriticalCaseBaseline,
    EvaluationBaseline,
)
from app.evaluation.baseline_store import save_baseline
from app.evaluation.summary_reader import load_evaluation_summary


CRITICAL_ISSUE = "model_location_mismatch"
DEFAULT_BASELINE_PATH = Path("data/evaluation/baseline.json")


def create_baseline(report_paths: list[Path]) -> EvaluationBaseline:
    """Validate three live summaries and derive their accepted metrics."""
    if len(report_paths) != 3:
        raise ValueError("Exactly three live summary.json files are required.")

    summaries = [load_evaluation_summary(path) for path in report_paths]
    case_ids = sorted(case.case_id for case in summaries[0].case_results)
    if not case_ids or len(case_ids) != len(set(case_ids)):
        raise ValueError("The evaluation dataset must have unique case IDs.")

    template = EvaluationBaseline(
        created_at=datetime.now(timezone.utc),
        source=BaselineSource(mode="live", runs=3, case_ids=case_ids),
        metrics=BaselineMetrics(hard_pass_rate=1.0),
        critical_cases={CRITICAL_ISSUE: CriticalCaseBaseline(pass_rate=1.0)},
    )

    for summary in summaries:
        current_ids = sorted(case.case_id for case in summary.case_results)
        if current_ids != case_ids:
            raise ValueError("Baseline reports use different evaluation cases.")
        if any(
            not case.passed
            or not case.hard_passed
            or (case.quality_evaluated and not case.quality_passed)
            for case in summary.case_results
        ):
            raise ValueError("Every baseline evaluation case must pass.")
        snapshot = build_current_snapshot(summary=summary, baseline=template)
        metrics = snapshot.metrics
        critical = snapshot.critical_cases[CRITICAL_ISSUE]
        if (
            snapshot.mode != "live"
            or metrics.hard_pass_rate != 1.0
            or metrics.quality_pass_rate != 1.0
            or metrics.first_pass_rate != 1.0
            or metrics.repair_rate != 0.0
            or critical.pass_rate != 1.0
        ):
            raise ValueError("Each live report must pass all accepted baseline metrics.")

    return template.model_copy(
        update={
            "metrics": BaselineMetrics(
                hard_pass_rate=1.0,
                quality_pass_rate=1.0,
                first_pass_rate=1.0,
                repair_rate=0.0,
                median_duration_ms=None,
            )
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, nargs=3, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_BASELINE_PATH)
    args = parser.parse_args(argv)

    try:
        baseline = create_baseline(args.reports)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    save_baseline(path=args.output, baseline=baseline)
    print(f"Accepted baseline: {args.output}")
    print(f"Cases: {len(baseline.source.case_ids)}; live runs: 3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
