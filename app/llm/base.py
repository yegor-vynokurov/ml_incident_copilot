from typing import Protocol, TypeVar
from pydantic import BaseModel 

from app.schemas import (
    LLMResponse,
    StructuredLLMResponse,
)

StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)


class LLMProviderError(RuntimeError):
    """Base error due working with llm provider."""


class LLMConfigurationError(LLMProviderError):
    """Provider has incorrect settings."""


class LLMEmptyResponseError(LLMProviderError):
    """Model does not return text."""

class LLMStructuredOutputError(
    LLMProviderError
):
    """
    Answer LLM does not pass Pydantic validation.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_text: str | None = None,
        validation_errors: list[dict] | None = None,
    ) -> None:
        super().__init__(message)

        self.raw_text = raw_text

        self.validation_errors = (
            validation_errors or []
        )


class LLMRepairExhaustedError(
    LLMProviderError
):
    """Generation and repair did not produce a valid, grounded response."""


class LLMProvider(Protocol):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        ...

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModelT],
    ) -> StructuredLLMResponse[
        StructuredModelT
    ]:
        ...
