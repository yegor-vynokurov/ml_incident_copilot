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


DATASET_PATH = Path(
    "data/evaluation/cases.json"
)



def test_evaluation_dataset_loads():
    cases = load_evaluation_cases(
        DATASET_PATH
    )

    assert len(cases) == 6

    assert len(
        {
            case.case_id
            for case in cases
        }
    ) == 6




def test_deterministic_evaluation_passes():
    cases = load_evaluation_cases(
        DATASET_PATH
    )

    provider = (
        DeterministicEvaluationLLMProvider()
    )

    agent = build_agent(
        llm_provider=provider
    )

    summary = run_evaluation(
        agent=agent,
        cases=cases,
        mode="deterministic",
        dataset_path=str(
            DATASET_PATH
        ),
    )

    assert summary.total_cases == 6
    assert summary.failed_cases == 0
    assert summary.hard_pass_rate == 100.0

    # Normal case does not call LLM.
    assert summary.cases_with_llm == 5




def test_evaluation_report_is_written(
    tmp_path: Path,
):
    cases = load_evaluation_cases(
        DATASET_PATH
    )

    agent = build_agent(
        llm_provider=(
            DeterministicEvaluationLLMProvider()
        )
    )

    summary = run_evaluation(
        agent=agent,
        cases=cases,
        mode="deterministic",
        dataset_path=str(
            DATASET_PATH
        ),
    )

    report_dir = (
        write_evaluation_report(
            summary=summary,
            output_root=tmp_path,
        )
    )

    assert (
        report_dir
        / "summary.json"
    ).exists()

    assert (
        report_dir
        / "report.md"
    ).exists()

    assert (
        report_dir
        / "cases.csv"
    ).exists()



