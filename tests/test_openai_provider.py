from types import SimpleNamespace

import pytest

from app.llm.base import LLMStructuredOutputError
from app.llm.openai_provider import OpenAIProvider
from app.schemas import IssueAnalysis


class FakeResponses:
    def __init__(self, parsed):
        self.parsed = parsed
        self.last_call = None

    def parse(self, **kwargs):
        self.last_call = kwargs
        return SimpleNamespace(
            output_parsed=self.parsed,
            output_text='{"explanation":"Verified evidence requires review."}',
            usage=SimpleNamespace(input_tokens=12, output_tokens=8),
            _request_id="fake-request",
        )


def test_openai_structured_contract_without_network():
    responses = FakeResponses(
        IssueAnalysis(explanation="Verified evidence requires review.")
    )
    provider = OpenAIProvider(
        model="fake-model",
        client=SimpleNamespace(responses=responses),
    )

    result = provider.generate_structured(
        system_prompt="Use only evidence.",
        user_prompt="Explain the issue.",
        response_model=IssueAnalysis,
    )

    assert result.parsed.explanation == "Verified evidence requires review."
    assert result.input_tokens == 12
    assert responses.last_call["model"] == "fake-model"
    assert responses.last_call["text_format"] is IssueAnalysis


def test_openai_missing_parsed_output_is_rejected():
    provider = OpenAIProvider(
        model="fake-model",
        client=SimpleNamespace(responses=FakeResponses(None)),
    )

    with pytest.raises(LLMStructuredOutputError):
        provider.generate_structured(
            system_prompt="Use only evidence.",
            user_prompt="Explain the issue.",
            response_model=IssueAnalysis,
        )
