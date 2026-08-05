from datetime import (
    datetime,
    timezone,
)
from statistics import (
    mean,
    median,
)
from time import perf_counter

from app.agent import MLIncidentAgent
from app.evaluation.schemas import (
    CheckResult,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationMode,
    EvaluationSummary,
)
from app.schemas import AgentRun




def _check(
    *,
    name: str,
    category: str,
    passed: bool,
    expected=None,
    actual=None,
    message: str | None = None,
) -> CheckResult:
    return CheckResult(
        name=name,
        category=category,
        passed=passed,
        expected=expected,
        actual=actual,
        message=message,
    )




def _evaluate_explanations(
    *,
    case: EvaluationCase,
    run: AgentRun,
) -> list[CheckResult]:
    checks: list[CheckResult] = []

    findings_by_code = {
        finding.issue_code: finding
        for finding in run.report.findings
    }

    for rule in case.explanation_rules:
        finding = findings_by_code.get(
            rule.issue_code
        )

        if finding is None:
            checks.append(
                _check(
                    name=(
                        "explanation_exists:"
                        f"{rule.issue_code}"
                    ),
                    category="quality",
                    passed=False,
                    expected="finding exists",
                    actual=None,
                )
            )
            continue

        explanation = (
            finding.explanation.lower()
        )

        for index, term_group in enumerate(
            rule.required_term_groups
        ):
            normalized_terms = [
                term.lower()
                for term in term_group
            ]

            matched = any(
                term in explanation
                for term in normalized_terms
            )

            checks.append(
                _check(
                    name=(
                        "required_term_group:"
                        f"{rule.issue_code}:"
                        f"{index}"
                    ),
                    category="quality",
                    passed=matched,
                    expected=term_group,
                    actual=(
                        finding.explanation
                    ),
                    message=(
                        None
                        if matched
                        else (
                            "Explanation does not "
                            "contain any expected term."
                        )
                    ),
                )
            )

        for forbidden_term in (
            rule.forbidden_terms
        ):
            found = (
                forbidden_term.lower()
                in explanation
            )

            checks.append(
                _check(
                    name=(
                        "forbidden_term_absent:"
                        f"{rule.issue_code}:"
                        f"{forbidden_term}"
                    ),
                    category="quality",
                    passed=not found,
                    expected="absent",
                    actual=(
                        "present"
                        if found
                        else "absent"
                    ),
                )
            )

    return checks







def _evaluate_agent_run(
    *,
    case: EvaluationCase,
    run: AgentRun,
    mode: EvaluationMode,
    duration_ms: float,
) -> EvaluationCaseResult:
    checks: list[CheckResult] = []

    expected_codes = sorted(
        case.expected_issue_codes
    )

    actual_codes = sorted(
        run.issue_codes
    )

    checks.append(
        _check(
            name="agent_status",
            category="hard",
            passed=(
                run.status
                == case.expected_agent_status
            ),
            expected=(
                case.expected_agent_status
            ),
            actual=run.status,
        )
    )

    checks.append(
        _check(
            name="request_id",
            category="hard",
            passed=(
                run.request_id
                == case.request.request_id
            ),
            expected=case.request.request_id,
            actual=run.request_id,
        )
    )

    checks.append(
        _check(
            name="issue_codes",
            category="hard",
            passed=(
                actual_codes
                == expected_codes
            ),
            expected=expected_codes,
            actual=actual_codes,
        )
    )

    expected_report_status = (
        "needs_review"
        if expected_codes
        else "ok"
    )

    checks.append(
        _check(
            name="report_status",
            category="hard",
            passed=(
                run.report.status
                == expected_report_status
            ),
            expected=expected_report_status,
            actual=run.report.status,
        )
    )

    actual_report_codes = sorted(
        finding.issue_code
        for finding
        in run.report.findings
    )

    checks.append(
        _check(
            name="report_issue_codes",
            category="hard",
            passed=(
                actual_report_codes
                == expected_codes
            ),
            expected=expected_codes,
            actual=actual_report_codes,
        )
    )


    actual_step_statuses = {
        step.tool_name: step.status
        for step in run.steps
    }

    checks.append(
        _check(
            name="step_statuses",
            category="hard",
            passed=(
                actual_step_statuses
                == case.expected_step_statuses
            ),
            expected=(
                case.expected_step_statuses
            ),
            actual=actual_step_statuses,
        )
    )



    actual_evidence_tools = {
        finding.issue_code: (
            finding
            .evidence_ref
            .tool_name
        )
        for finding
        in run.report.findings
    }

    checks.append(
        _check(
            name="evidence_tools",
            category="hard",
            passed=(
                actual_evidence_tools
                == case.expected_evidence_tools
            ),
            expected=(
                case.expected_evidence_tools
            ),
            actual=actual_evidence_tools,
        )
    )


    trace_codes = sorted(
        trace.issue_code
        for trace
        in run.analysis_traces
    )

    checks.append(
        _check(
            name="analysis_trace_codes",
            category="hard",
            passed=(
                trace_codes
                == expected_codes
            ),
            expected=expected_codes,
            actual=trace_codes,
        )
    )


    if mode == "live":
        checks.extend(
            _evaluate_explanations(
                case=case,
                run=run,
            )
        )



    attempts_by_issue = {
        trace.issue_code: (
            trace.response.attempt_count
        )
        for trace
        in run.analysis_traces
    }

    repair_attempts = sum(
        max(attempts - 1, 0)
        for attempts
        in attempts_by_issue.values()
    )

    input_tokens = sum(
        trace.response.input_tokens or 0
        for trace
        in run.analysis_traces
    )

    output_tokens = sum(
        trace.response.output_tokens or 0
        for trace
        in run.analysis_traces
    )

    hard_checks = [
        check
        for check in checks
        if check.category == "hard"
    ]

    quality_checks = [
        check
        for check in checks
        if check.category == "quality"
    ]

    hard_passed = all(
        check.passed
        for check in hard_checks
    )

    quality_passed = all(
        check.passed
        for check in quality_checks
    )

    quality_evaluated = bool(
        quality_checks
    )

    return EvaluationCaseResult(
        case_id=case.case_id,
        title=case.title,
        tags=case.tags,
        passed=(
            hard_passed
            and quality_passed
        ),
        hard_passed=hard_passed,
        quality_passed=quality_passed,
        quality_evaluated=(
            quality_evaluated
        ),
        duration_ms=round(
            duration_ms,
            2,
        ),
        issue_codes=actual_codes,
        attempts_by_issue=(
            attempts_by_issue
        ),
        repair_attempts=(
            repair_attempts
        ),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        checks=checks,
    )




def evaluate_case(
    *,
    agent: MLIncidentAgent,
    case: EvaluationCase,
    mode: EvaluationMode,
) -> EvaluationCaseResult:
    started = perf_counter()

    try:
        run = agent.run(
            case.request
        )

    except Exception as exc:
        duration_ms = (
            perf_counter() - started
        ) * 1000

        return EvaluationCaseResult(
            case_id=case.case_id,
            title=case.title,
            tags=case.tags,
            passed=False,
            hard_passed=False,
            quality_passed=False,
            quality_evaluated=(
                mode == "live"
            ),
            duration_ms=round(
                duration_ms,
                2,
            ),
            checks=[
                _check(
                    name="agent_run_completed",
                    category="hard",
                    passed=False,
                    expected="successful run",
                    actual=(
                        type(exc).__name__
                    ),
                )
            ],
            error_type=(
                type(exc).__name__
            ),
            error_message=(
                str(exc)[:1000]
            ),
        )

    duration_ms = (
        perf_counter() - started
    ) * 1000

    return _evaluate_agent_run(
        case=case,
        run=run,
        mode=mode,
        duration_ms=duration_ms,
    )




def run_evaluation(
    *,
    agent: MLIncidentAgent,
    cases: list[EvaluationCase],
    mode: EvaluationMode,
    dataset_path: str,
) -> EvaluationSummary:
    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    results = [
        evaluate_case(
            agent=agent,
            case=case,
            mode=mode,
        )
        for case in cases
    ]

    total_cases = len(results)

    passed_cases = sum(
        result.passed
        for result in results
    )

    hard_passed_cases = sum(
        result.hard_passed
        for result in results
    )

    quality_results = [
        result
        for result in results
        if result.quality_evaluated
    ]

    quality_passed_cases = sum(
        result.quality_passed
        for result in quality_results
    )

    cases_with_llm = [
        result
        for result in results
        if result.attempts_by_issue
    ]

    first_pass_cases = sum(
        all(
            attempts == 1
            for attempts
            in result
            .attempts_by_issue
            .values()
        )
        for result in cases_with_llm
    )

    repair_used_cases = sum(
        result.repair_attempts > 0
        for result in results
    )

    durations = [
        result.duration_ms
        for result in results
    ]

    return EvaluationSummary(
        mode=mode,
        dataset_path=dataset_path,
        started_at=started_at,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=(
            total_cases - passed_cases
        ),
        hard_passed_cases=(
            hard_passed_cases
        ),
        hard_pass_rate=round(
            (
                hard_passed_cases
                / total_cases
                * 100
            )
            if total_cases
            else 0.0,
            2,
        ),
        quality_evaluated_cases=len(
            quality_results
        ),
        quality_passed_cases=(
            quality_passed_cases
        ),
        quality_pass_rate=(
            round(
                quality_passed_cases
                / len(quality_results)
                * 100,
                2,
            )
            if quality_results
            else None
        ),
        cases_with_llm=len(
            cases_with_llm
        ),
        first_pass_cases=(
            first_pass_cases
        ),
        first_pass_rate=(
            round(
                first_pass_cases
                / len(cases_with_llm)
                * 100,
                2,
            )
            if cases_with_llm
            else None
        ),
        repair_used_cases=(
            repair_used_cases
        ),
        average_duration_ms=round(
            mean(durations)
            if durations
            else 0.0,
            2,
        ),
        median_duration_ms=round(
            median(durations)
            if durations
            else 0.0,
            2,
        ),
        total_input_tokens=sum(
            result.input_tokens
            for result in results
        ),
        total_output_tokens=sum(
            result.output_tokens
            for result in results
        ),
        case_results=results,
    )
