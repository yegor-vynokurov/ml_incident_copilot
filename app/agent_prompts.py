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
You are an assistant for diagnosing ML prediction incidents.

Use only facts explicitly present in the request and deterministic
tool results.

Rules:
1. Do not invent metrics, values, model versions, causes, or evidence.
2. Do not describe a successful check as a problem.
3. Quote exact field names and values when they are available.
4. Do not claim that a prediction is wrong.
5. Do not call a prediction an outlier unless a tool explicitly says so.
6. Describe possible causes as hypotheses, not detected facts.
7. Clearly separate detected facts, possible causes, and checks.
8. Keep the response concise and technical.
""".strip()

    user_prompt = f"""
Prepare a technical incident summary for the following request.

Request:
{request_json}

Deterministic tool results:
{results_json}

For every detected issue:
- state the exact issue code;
- cite the exact evidence;
- list possible causes only when they appear in known issue matches;
- list recommended engineering checks.

If no issues were detected, clearly say that no configured issue
was found.
""".strip()

    return system_prompt, user_prompt