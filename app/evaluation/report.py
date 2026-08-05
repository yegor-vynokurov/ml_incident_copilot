import csv
from datetime import datetime
from pathlib import Path

from app.evaluation.schemas import (
    EvaluationSummary,
)



def _build_markdown(
    summary: EvaluationSummary,
) -> str:
    quality_rate = (
        f"{summary.quality_pass_rate}%"
        if (
            summary.quality_pass_rate
            is not None
        )
        else "not evaluated"
    )

    first_pass_rate = (
        f"{summary.first_pass_rate}%"
        if (
            summary.first_pass_rate
            is not None
        )
        else "not applicable"
    )

    lines = [
        "# ML Incident Copilot Evaluation",
        "",
        f"- Mode: `{summary.mode}`",
        (
            f"- Dataset: "
            f"`{summary.dataset_path}`"
        ),
        (
            f"- Cases: "
            f"{summary.total_cases}"
        ),
        (
            f"- Passed: "
            f"{summary.passed_cases}"
        ),
        (
            f"- Failed: "
            f"{summary.failed_cases}"
        ),
        (
            f"- Hard pass rate: "
            f"{summary.hard_pass_rate}%"
        ),
        (
            f"- Quality pass rate: "
            f"{quality_rate}"
        ),
        (
            f"- First-pass LLM rate: "
            f"{first_pass_rate}"
        ),
        (
            f"- Cases using repair: "
            f"{summary.repair_used_cases}"
        ),
        (
            f"- Average duration: "
            f"{summary.average_duration_ms} ms"
        ),
        (
            f"- Median duration: "
            f"{summary.median_duration_ms} ms"
        ),
        (
            f"- Input tokens: "
            f"{summary.total_input_tokens}"
        ),
        (
            f"- Output tokens: "
            f"{summary.total_output_tokens}"
        ),
        "",
        "## Case results",
        "",
        (
            "| Case | Hard | Quality | "
            "Duration, ms | Repairs | Issues |"
        ),
        (
            "|---|---:|---:|---:|---:|---|"
        ),
    ]

    for result in summary.case_results:
        quality_status = (
            "PASS"
            if result.quality_passed
            else "FAIL"
        )

        if not result.quality_evaluated:
            quality_status = "N/A"

        issues = (
            ", ".join(
                result.issue_codes
            )
            or "none"
        )

        lines.append(
            "| "
            f"{result.case_id} | "
            f"{'PASS' if result.hard_passed else 'FAIL'} | "
            f"{quality_status} | "
            f"{result.duration_ms} | "
            f"{result.repair_attempts} | "
            f"{issues} |"
        )

    failed_results = [
        result
        for result in summary.case_results
        if not result.passed
    ]

    if failed_results:
        lines.extend(
            [
                "",
                "## Failures",
            ]
        )

        for result in failed_results:
            lines.extend(
                [
                    "",
                    (
                        f"### {result.case_id}"
                    ),
                ]
            )

            if result.error_type:
                lines.append(
                    (
                        f"- Error: "
                        f"`{result.error_type}`"
                    )
                )

                lines.append(
                    (
                        f"- Message: "
                        f"{result.error_message}"
                    )
                )

            for check in result.checks:
                if check.passed:
                    continue

                lines.append(
                    (
                        f"- [{check.category}] "
                        f"`{check.name}`: "
                        f"expected `{check.expected}`, "
                        f"actual `{check.actual}`"
                    )
                )

    return "\n".join(lines) + "\n"




def write_evaluation_report(
    *,
    summary: EvaluationSummary,
    output_root: Path,
) -> Path:
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_dir = (
        output_root
        / timestamp
    )

    report_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    json_path = (
        report_dir
        / "summary.json"
    )

    json_path.write_text(
        summary.model_dump_json(
            indent=2,
        ),
        encoding="utf-8",
    )

    markdown_path = (
        report_dir
        / "report.md"
    )

    markdown_path.write_text(
        _build_markdown(
            summary
        ),
        encoding="utf-8",
    )

    csv_path = (
        report_dir
        / "cases.csv"
    )

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "case_id",
                "passed",
                "hard_passed",
                "quality_passed",
                "duration_ms",
                "repair_attempts",
                "input_tokens",
                "output_tokens",
                "issue_codes",
                "error_type",
            ],
        )

        writer.writeheader()

        for result in (
            summary.case_results
        ):
            writer.writerow(
                {
                    "case_id": (
                        result.case_id
                    ),
                    "passed": (
                        result.passed
                    ),
                    "hard_passed": (
                        result.hard_passed
                    ),
                    "quality_passed": (
                        result.quality_passed
                    ),
                    "duration_ms": (
                        result.duration_ms
                    ),
                    "repair_attempts": (
                        result.repair_attempts
                    ),
                    "input_tokens": (
                        result.input_tokens
                    ),
                    "output_tokens": (
                        result.output_tokens
                    ),
                    "issue_codes": (
                        ",".join(
                            result.issue_codes
                        )
                    ),
                    "error_type": (
                        result.error_type or ""
                    ),
                }
            )

    return report_dir