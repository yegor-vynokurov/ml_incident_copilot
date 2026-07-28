from app.schemas import IncidentReport

from app.llm.base import (
    LLMStructuredOutputError,
)

class FakeStructuredMessage:
    '''fake response'''

    content = """
{
  "request_id": "REQ-1",
  "status": "needs_review",
  "summary": "One issue requires review.",
  "findings": [
    {
      "issue_code": "road_access_conflict",
      "explanation": "Access fields are inconsistent.",
      "evidence_refs": [
        {
          "tool_name": "validate_input",
          "issue_code": "road_access_conflict"
        }
      ],
      "possible_causes": [
        "Incorrect source data"
      ],
      "recommended_checks": [
        "Verify the source record"
      ]
    }
  ]
}
""".strip()


class FakeStructuredOllamaResponse:
    message = FakeStructuredMessage()
    model = "test-model"

    prompt_eval_count = 200
    eval_count = 80


class FakeStructuredOllamaClient:
    def __init__(self) -> None:
        self.last_call: dict | None = None

    def chat(
        self,
        *,
        model: str,
        messages: list[dict],
        stream: bool,
        format: dict,
        options: dict,
    ) -> FakeStructuredOllamaResponse:
        self.last_call = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "format": format,
            "options": options,
        }

        return FakeStructuredOllamaResponse()




def test_ollama_returns_structured_report():
    client = FakeStructuredOllamaClient()

    provider = OllamaProvider(
        model="test-model",
        client=client,
    )

    result = provider.generate_structured(
        system_prompt="Use verified facts.",
        user_prompt="Create a report.",
        response_model=IncidentReport,
    )

    assert isinstance(
        result.parsed,
        IncidentReport,
    )

    assert result.parsed.request_id == "REQ-1"

    assert (
        result.parsed.findings[0].issue_code
        == "road_access_conflict"
    )

    assert client.last_call is not None

    assert client.last_call["format"] == (
        IncidentReport.model_json_schema()
    )

    assert (
        client.last_call["options"][
            "temperature"
        ]
        == 0
    )

class InvalidStructuredMessage:
    '''test for incorrect json'''
    content = """
{
  "request_id": "REQ-1",
  "status": "wrong-status",
  "findings": "not-a-list"
}
""".strip()


class InvalidStructuredResponse:
    message = InvalidStructuredMessage()
    model = "test-model"

    prompt_eval_count = 10
    eval_count = 10


class InvalidStructuredClient:
    def chat(self, **kwargs):
        return InvalidStructuredResponse()