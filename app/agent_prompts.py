import json

from app.schemas import (
    AgentStep,
    PredictionRequest,
)


def build_agent_prompts(
    *,
    request: PredictionRequest,
    steps: list[AgentStep],
) -> tuple[str, str]:
    """
    Creates system prompt and user prompt
    based on the results from the tools.
    """

    executed_steps = [
        step
        for step in steps
        if (
            step.status == "executed"
            and step.result is not None
        )
    ]

    tool_results = [
        {
            "tool_name": step.tool_name,
            "result": step.result.model_dump(
                mode="json"
            ),
        }
        for step in executed_steps
    ]

    request_json = json.dumps(
        request.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )

    results_json = json.dumps(
        tool_results,
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = """
You create structured reports for ML prediction incidents.

Use only facts explicitly present in the request and deterministic
tool results.

Rules:
1. Return data that matches the supplied JSON Schema.
2. Do not invent issue codes, values, causes, evidence, or checks.
3. Include every detected issue code exactly once.
4. Each finding must describe exactly one issue.
5. Do not mix evidence or explanations from different issue codes.
6. Use exactly one evidence_ref for each finding.
7. The evidence_ref must point to the tool that directly produced
   the finding issue_code.
8. Possible causes must come only from known issue matches.
9. Recommended checks must come only from known issue matches.
10. Do not add external sources, technologies, maps, or services.
11. If no issue codes were detected, use status "ok" and return an
    empty findings list.
12. If issue codes were detected, use status "needs_review".
""".strip()

    user_prompt = f"""
Create a structured incident report.

Request:
{request_json}

Deterministic tool results:
{results_json}

Required behavior:
- request_id must exactly equal the request request_id;
- each finding must contain one detected issue code;
- evidence_refs must point to a tool that returned that issue code;
- causes and checks must be copied from matching known issues;
- summary and explanation must be concise;
- do not include Markdown.
For each finding:
- discuss only that finding's issue_code;
- do not include facts belonging to another finding;
- evidence_ref must contain exactly one tool_name;
- do not repeat issue_code inside evidence_ref.
""".strip()

    
    return system_prompt, user_prompt