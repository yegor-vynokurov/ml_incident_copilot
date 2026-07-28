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
4. Do not include successful checks as findings.
5. For every finding, reference the deterministic tool that produced
   that issue code.
6. Possible causes must come only from known issue matches.
7. Recommended checks must come only from known issue matches.
8. Do not add external sources, technologies, maps, services, or steps.
9. Do not recommend retraining unless it appears in known issue matches.
10. If no issue codes were detected, use status "ok" and return an
    empty findings list.
11. If issue codes were detected, use status "needs_review".
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
""".strip()

    
    return system_prompt, user_prompt