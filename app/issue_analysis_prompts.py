import json

from app.incident_builder import (
    IssueContext,
)


def build_issue_analysis_prompts(
    context: IssueContext,
) -> tuple[str, str]:
    evidence_json = json.dumps(
        context.evidence,
        ensure_ascii=False,
        indent=2,
    )

    causes_json = json.dumps(
        context.possible_causes,
        ensure_ascii=False,
        indent=2,
    )

    checks_json = json.dumps(
        context.recommended_checks,
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = """
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

""".strip()

    user_prompt = f"""
Analyze this single issue.

Issue code for context:
{context.issue_code}

Deterministic evidence:
{evidence_json}

Approved possible causes:
{causes_json}

Approved engineering checks:
{checks_json}

Write one or two concise sentences explaining:
- what the evidence shows;
- why the issue requires engineering review.

Possible causes may be described only as hypotheses.
Do not provide actions or recommendations.

Use numeric values exactly as provided.
Do not add currency symbols or measurement units.
If two fields conflict, describe the inconsistency without claiming
which field is false.
""".strip()

    return system_prompt, user_prompt