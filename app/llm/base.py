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
    Model does not return answer as in needed schema.
    """



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