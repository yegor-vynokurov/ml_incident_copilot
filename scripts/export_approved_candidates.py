import argparse
import json
from pathlib import Path

from app.evaluation.candidate_export import (
    build_approved_case_drafts,
)
from app.evaluation.candidate_store import (
    load_candidates,
)


DEFAULT_CANDIDATES_PATH = Path(
    "data/evaluation/candidates.jsonl"
)

DEFAULT_DRAFTS_PATH = Path(
    "data/evaluation/case_drafts.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export approved evaluation "
            "candidates into human-review "
            "case drafts."
        )
    )

    parser.add_argument(
        "--candidates",
        type=Path,
        default=DEFAULT_CANDIDATES_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DRAFTS_PATH,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    candidates = load_candidates(
        args.candidates
    )

    drafts = (
        build_approved_case_drafts(
            candidates
        )
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            drafts,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    approved_count = sum(
        candidate.status
        == "approved"
        for candidate
        in candidates
    )

    print()
    print(
        "APPROVED CANDIDATE "
        "EXPORT COMPLETE"
    )
    print()
    print(
        "Candidates: "
        f"{len(candidates)}"
    )
    print(
        "Approved candidates: "
        f"{approved_count}"
    )
    print(
        f"Drafts created: {len(drafts)}"
    )
    print(
        f"Output: {args.output}"
    )


if __name__ == "__main__":
    main()