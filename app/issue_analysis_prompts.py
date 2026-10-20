import json

from app.incident_builder import (
    IssueContext,
)
from app.llm.base import LLMStructuredOutputError
from app.schemas import IssueAnalysis



ISSUE_ANALYSIS_SYSTEM_PROMPT = """
You analyze exactly one ML prediction incident issue.

Python has already determined:
- the issue code;
- the evidence source;
- possible causes;
- recommended checks.

Do not select, modify, or repeat those fields.

Return only the structured fields defined by the supplied JSON Schema.

Write a concise technical explanation based only on the deterministic
evidence below.

Do not:
- add new facts;
- discuss another issue;
- add recommendations;
- return an issue code;
- return an evidence reference;
- return causes or checks;
- use Markdown.

- do not infer or add currency symbols, measurement units, or domain
  labels that are not explicitly present in the evidence;
- describe contradictions without deciding which field is incorrect;
- treat possible causes only as hypotheses;
- prefer exact field names from the evidence.


For location mismatches:
- state the exact request location and model metadata location;
- explain only that the locations do not match;
- do not infer that the model is outdated, deprecated, stale, or inactive
  unless the evidence explicitly says so;
- do not invent routing errors or invalid request parameters;
- do not introduce possible causes that are absent from the approved
  possible causes.

Do not infer a root cause when no approved possible causes are provided.
Describe only the observed inconsistency.

""".strip()
ISSUE_ANALYSIS_PROMPT_VERSION = (
    "grounded-explanation-v1"
)






def build_issue_analysis_prompts(
    context: IssueContext,
) -> tuple[str, str]:
    system_prompt = (
        ISSUE_ANALYSIS_SYSTEM_PROMPT
    )

    relevant_evidence_json = json.dumps(
        context.relevant_evidence,
        ensure_ascii=False,
        indent=2,
    )

    user_prompt = (
        "Issue code for context:\n"
        f"{context.issue_code}\n\n"
        "Verified relevant evidence:\n"
        f"{relevant_evidence_json}\n\n"
        "Verified grounded statement:\n"
        f"{context.grounded_statement}\n\n"
        "Task:\n"
        "Write a concise engineering "
        "explanation of this issue.\n"
        "Preserve the meaning and exact values "
        "of the grounded statement.\n"
        "Do not add facts, causes, units, "
        "currency, or assumptions.\n"
        "Return only the required JSON object."
    )

    return (
        system_prompt,
        user_prompt,
    )


def validate_issue_explanation(
    context: IssueContext,
    analysis: IssueAnalysis,
) -> None:
    """Reject missing or contradictory facts for fragile issue types."""
    text = analysis.explanation.lower().replace(",", "")
    evidence = context.relevant_evidence
    missing: list[str] = []

    if context.issue_code == "sparse_location_data":
        for key in ("reference_sample_size", "sparse_sample_threshold"):
            if str(evidence[key]) not in text:
                missing.append(key)
        if not any(word in text for word in ("sample", "record")):
            missing.append("sample or record")
        if any(
            phrase in text
            for phrase in ("mismatch", "model metadata", "model location")
        ):
            missing.append("no unrelated model-location claim")

    if context.issue_code == "prediction_above_reference_range":
        value = evidence["predicted_price_per_area"]
        acceptable = {str(value), f"{value:g}"}
        if not any(candidate in text for candidate in acceptable):
            missing.append("predicted_price_per_area")
        if "p90" not in text and str(evidence["p90_price_per_area"]) not in text:
            missing.append("p90 reference")
        if not any(word in text for word in ("above", "exceed", "higher")):
            missing.append("above-range comparison")
        if "below" in text:
            missing.append("no below-range claim")

    if missing:
        raise LLMStructuredOutputError(
            "Explanation omitted or contradicted verified evidence.",
            raw_text=analysis.model_dump_json(),
            validation_errors=[
                {
                    "loc": ("explanation",),
                    "msg": "Required: " + ", ".join(missing),
                }
            ],
        )
