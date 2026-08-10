from typing import Any

from app.evaluation.candidate_schemas import (
    EvaluationCandidate,
)


def build_case_draft(
    candidate: EvaluationCandidate,
) -> dict[str, Any]:
    """
    Build a HUMAN-REVIEW draft.

    The result is intentionally NOT a valid
    EvaluationCase yet.
    """

    if candidate.status != "approved":
        raise ValueError(
            "Only approved candidates "
            "can be exported."
        )

    case_id = (
        "runtime_"
        + candidate.candidate_id
        .replace(
            "-",
            "_",
        )
    )

    return {
        "source_candidate_id": (
            candidate.candidate_id
        ),
        "source_trace_id": (
            candidate.trace_id
        ),
        "case_id": case_id,
        "title": (
            "Runtime feedback regression case"
        ),
        "tags": [
            "runtime-feedback",
            "needs-human-expectations",
        ],
        "request": (
            candidate
            .source_request
            .model_dump(
                mode="json"
            )
        ),
        "actual_issue_codes": (
            candidate.actual_issue_codes
        ),
        "suggested_expected_issue_codes": (
            candidate.expected_issue_codes
        ),
        "affected_issue_code": (
            candidate.affected_issue_code
        ),
        "actual_explanation": (
            candidate.actual_explanation
        ),
        "corrected_explanation": (
            candidate.corrected_explanation
        ),
        "feedback_comment": (
            candidate.feedback_comment
        ),

        # These fields must be completed
        # manually before copying the case
        # into cases.json.
        "TODO_expected_agent_status": None,
        "TODO_expected_step_statuses": None,
        "TODO_expected_evidence_tools": None,
        "TODO_explanation_rules": [],
    }




def build_approved_case_drafts(
    candidates: list[
        EvaluationCandidate
    ],
) -> list[dict[str, Any]]:
    drafts: list[
        dict[str, Any]
    ] = []

    for candidate in candidates:
        if candidate.status != "approved":
            continue

        drafts.append(
            build_case_draft(
                candidate
            )
        )

    return drafts