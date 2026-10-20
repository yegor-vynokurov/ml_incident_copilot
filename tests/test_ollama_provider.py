import pytest

from app.schemas import IssueAnalysis

from app.llm.base import (
    LLMStructuredOutputError,
)

from app.llm import OpenAIProvider, OllamaProvider

class FakeStructuredMessage:
    """Fake valid per-issue explanation."""

    content = '{"explanation": "Access fields are inconsistent."}'
    

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




def test_ollama_returns_structured_issue_analysis():
    client = FakeStructuredOllamaClient()

    provider = OllamaProvider(
        model="test-model",
        client=client,
    )

    result = provider.generate_structured(
        system_prompt="Use verified facts.",
        user_prompt="Create a report.",
        response_model=IssueAnalysis,
    )

    assert isinstance(
        result.parsed,
        IssueAnalysis,
    )

    assert result.parsed.explanation == "Access fields are inconsistent."

    assert client.last_call is not None

    assert client.last_call["format"] == (
        IssueAnalysis.model_json_schema()
    )

    assert (
        client.last_call["options"][
            "temperature"
        ]
        == 0
    )

class InvalidStructuredMessage:
    """Invalid structured response."""

    content = '{"explanation": "short"}'


class InvalidStructuredResponse:
    message = InvalidStructuredMessage()
    model = "test-model"

    prompt_eval_count = 10
    eval_count = 10


class InvalidStructuredClient:
    def chat(self, **kwargs):
        return InvalidStructuredResponse()


def test_ollama_rejects_invalid_structured_output():
    provider = OllamaProvider(
        model="test-model",
        client=InvalidStructuredClient(),
    )

    with pytest.raises(
        LLMStructuredOutputError
    ):
        provider.generate_structured(
            system_prompt="Use facts.",
            user_prompt="Create report.",
            response_model=IssueAnalysis,
        )
