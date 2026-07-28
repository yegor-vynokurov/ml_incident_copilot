from typing import Any

import httpx
from ollama import Client, ResponseError

from app.llm.base import (
    LLMConfigurationError,
    LLMEmptyResponseError,
    LLMProviderError,
)
from app.schemas import LLMResponse


class OllamaProvider:
    provider_name = "ollama"

    def __init__(
        self,
        *,
        model: str,
        host: str = "http://localhost:11434",
        timeout_seconds: float = 120.0,
        client: Any | None = None,
    ) -> None:
        model = model.strip()
        host = host.strip()

        if not model:
            raise LLMConfigurationError(
                "Ollama model name is empty."
            )

        if not host:
            raise LLMConfigurationError(
                "Ollama host is empty."
            )

        if timeout_seconds <= 0:
            raise LLMConfigurationError(
                "timeout_seconds must be greater than 0."
            )

        self.model = model
        self.host = host

        if client is not None:
            # Используется в unit tests.
            self._client = client
            return

        self._client = Client(
            host=host,
            timeout=timeout_seconds,
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        if not system_prompt.strip():
            raise ValueError(
                "system_prompt cannot be empty."
            )

        if not user_prompt.strip():
            raise ValueError(
                "user_prompt cannot be empty."
            )

        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                stream=False,
                options={
                    "temperature": 0.1,
                },
            )

        except ResponseError as exc:
            raise LLMProviderError(
                f"Ollama request failed: {exc.error}"
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMProviderError(
                "Could not connect to the local "
                "Ollama server."
            ) from exc

        text = (
            response.message.content or ""
        ).strip()

        if not text:
            raise LLMEmptyResponseError(
                "Ollama returned an empty response."
            )

        actual_model = getattr(
            response,
            "model",
            self.model,
        )

        input_tokens = getattr(
            response,
            "prompt_eval_count",
            None,
        )

        output_tokens = getattr(
            response,
            "eval_count",
            None,
        )

        return LLMResponse(
            text=text,
            provider=self.provider_name,
            model=actual_model or self.model,
            request_id=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )