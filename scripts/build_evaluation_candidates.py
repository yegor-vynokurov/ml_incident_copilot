import argparse
from pathlib import Path

from app.evaluation.candidate_builder import (
    build_candidates,
)
from app.evaluation.candidate_store import (
    append_candidate,
    load_candidates,
    load_feedback_records,
    load_run_records,
)


DEFAULT_RUNS_PATH = Path(
    "data/runtime/runs.jsonl"
)

DEFAULT_FEEDBACK_PATH = Path(
    "data/runtime/feedback.jsonl"
)

DEFAULT_CANDIDATES_PATH = Path(
    "data/evaluation/candidates.jsonl"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build evaluation candidates "
            "from runtime feedback."
        )
    )

    parser.add_argument(
        "--runs",
        type=Path,
        default=DEFAULT_RUNS_PATH,
    )

    parser.add_argument(
        "--feedback",
        type=Path,
        default=DEFAULT_FEEDBACK_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CANDIDATES_PATH,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    runs = load_run_records(
        args.runs
    )

    feedback_records = (
        load_feedback_records(
            args.feedback
        )
    )

    existing_candidates = (
        load_candidates(
            args.output
        )
    )

    new_candidates = (
        build_candidates(
            runs=runs,
            feedback_records=(
                feedback_records
            ),
            existing_candidates=(
                existing_candidates
            ),
        )
    )

    for candidate in new_candidates:
        append_candidate(
            path=args.output,
            candidate=candidate,
        )

    eligible_feedback = sum(
        feedback.verdict
        != "correct"
        for feedback
        in feedback_records
    )

    print()
    print(
        "CANDIDATE BUILD COMPLETE"
    )
    print()
    print(
        f"Runtime runs: {len(runs)}"
    )
    print(
        "Feedback records: "
        f"{len(feedback_records)}"
    )
    print(
        "Eligible feedback: "
        f"{eligible_feedback}"
    )
    print(
        "Existing candidates: "
        f"{len(existing_candidates)}"
    )
    print(
        "New candidates: "
        f"{len(new_candidates)}"
    )
    print(
        f"Output: {args.output}"
    )


if __name__ == "__main__":
    main()