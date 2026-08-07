import json

from app.incident_builder import (
    IssueContext,
)



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