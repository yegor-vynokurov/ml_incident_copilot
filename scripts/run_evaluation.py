import argparse
from pathlib import Path

from app.bootstrap import build_agent
from app.evaluation.dataset import (
    load_evaluation_cases,
)
from app.evaluation.fake_provider import (
    DeterministicEvaluationLLMProvider,
)
from app.evaluation.report import (
    write_evaluation_report,
)
from app.evaluation.runner import (
    run_evaluation,
)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate ML Incident Copilot."
        )
    )

    parser.add_argument(
        "--mode",
        choices=[
            "deterministic",
            "live",
        ],
        default="deterministic",
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(
            "data/evaluation/cases.json"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "reports/evaluation"
        ),
    )

    return parser.parse_args()



def main() -> None:
    args = parse_args()

    cases = load_evaluation_cases(
        args.dataset
    )

    if args.mode == "deterministic":
        provider = (
            DeterministicEvaluationLLMProvider()
        )

        agent = build_agent(
            llm_provider=provider
        )

    else:
        agent = build_agent()

    summary = run_evaluation(
        agent=agent,
        cases=cases,
        mode=args.mode,
        dataset_path=str(
            args.dataset
        ),
    )

    report_dir = (
        write_evaluation_report(
            summary=summary,
            output_root=(
                args.output_dir
            ),
        )
    )

    print()
    print("EVALUATION COMPLETE")
    print()
    print(
        f"Mode: {summary.mode}"
    )
    print(
        f"Cases: {summary.total_cases}"
    )
    print(
        "Hard pass rate: "
        f"{summary.hard_pass_rate}%"
    )
    print(
        "Quality pass rate: "
        f"{summary.quality_pass_rate}"
    )
    print(
        "First-pass rate: "
        f"{summary.first_pass_rate}"
    )
    print(
        "Repair used cases: "
        f"{summary.repair_used_cases}"
    )
    print(
        f"Report: {report_dir}"
    )

    if summary.failed_cases:
        raise SystemExit(1)


if __name__ == "__main__":
    main()




    