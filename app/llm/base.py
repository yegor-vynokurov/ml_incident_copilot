from typing import Protocol

from app.schemas import LLMResponse


class LLMProviderError(RuntimeError):
    """Base error due working with llm provider."""


class LLMConfigurationError(LLMProviderError):
    """Provider has incorrect settings."""


class LLMEmptyResponseError(LLMProviderError):
    """Model does not return text."""


class LLMProvider(Protocol):
    """
    Common interface for any llm provider.
    Inherit Protocol and check if the provider has generate method
    """

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        ...