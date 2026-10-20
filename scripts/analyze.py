"""Analyze one JSON prediction request from a file or standard input."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.bootstrap import PROJECT_ROOT, build_agent
from app.evaluation.fake_provider import DeterministicEvaluationLLMProvider
from app.schemas import PredictionRequest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default=str(PROJECT_ROOT / "examples" / "prediction_request.json"),
        help="JSON request file, or - for standard input",
    )
    parser.add_argument(
        "--mode",
        choices=("deterministic", "live"),
        default="deterministic",
        help="Use a repeatable offline explanation or the configured LLM",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print the complete agent trace instead of only the report",
    )
    args = parser.parse_args(argv)

    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        request = PredictionRequest.model_validate_json(raw)
        provider = (
            DeterministicEvaluationLLMProvider()
            if args.mode == "deterministic"
            else None
        )
        result = build_agent(llm_provider=provider).run(request)
    except (OSError, ValidationError, ValueError, RuntimeError) as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1

    payload = result if args.full else result.report
    print(json.dumps(payload.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
