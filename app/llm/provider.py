from typing import Any

import openai
from openai import OpenAI

from app.llm.base import (
    LLMConfigurationError,
    LLMEmptyResponseError,
    LLMProviderError,
)
from app.schemas import LLMResponse


class OpenAIProvider:
    provider_name = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
        client: Any | None = None,
    ) -> None:
        model = model.strip()

        if not model:
            raise LLMConfigurationError(
                "OpenAI model name is empty."
            )

        if timeout_seconds <= 0:
            raise LLMConfigurationError(
                "timeout_seconds must be greater than 0."
            )

        if max_retries < 0:
            raise LLMConfigurationError(
                "max_retries cannot be negative."
            )

        self.model = model

        if client is not None:
            # Used in unit tests for fake provider.
            self._client = client
            return

        if not api_key:
            raise LLMConfigurationError(
                "OpenAI API key is not configured."
            )

        self._client = OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        """
        Send text to the model.

        Return simple text now
        """

        if not system_prompt.strip():
            raise ValueError(
                "system_prompt cannot be empty."
            )

        if not user_prompt.strip():
            raise ValueError(
                "user_prompt cannot be empty."
            )

        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt,
            )

        except openai.APIError as exc:
            raise LLMProviderError(
                f"OpenAI request failed: {type(exc).__name__}"
            ) from exc

        text = response.output_text.strip()

        if not text:
            raise LLMEmptyResponseError(
                "OpenAI returned an empty text response."
            )

        usage = getattr(response, "usage", None)

        input_tokens = (
            getattr(usage, "input_tokens", None)
            if usage is not None
            else None
        )

        output_tokens = (
            getattr(usage, "output_tokens", None)
            if usage is not None
            else None
        )

        request_id = getattr(
            response,
            "_request_id",
            None,
        )

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model=self.model,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )