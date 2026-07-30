from typing import Any

import httpx
from ollama import Client, ResponseError

from app.llm.base import (
    LLMConfigurationError,
    LLMEmptyResponseError,
    LLMProviderError,
    LLMStructuredOutputError,
)
from app.schemas import (
    LLMResponse,
    StructuredLLMResponse,
)

import json
from typing import Any, TypeVar

import httpx
from ollama import Client, ResponseError
from pydantic import BaseModel, ValidationError

StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)


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
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModelT],
    ) -> StructuredLLMResponse[
        StructuredModelT
    ]:
        if not system_prompt.strip():
            raise ValueError(
                "system_prompt cannot be empty."
            )

        if not user_prompt.strip():
            raise ValueError(
                "user_prompt cannot be empty."
            )

        schema = response_model.model_json_schema()

        schema_json = json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
        )

        grounded_user_prompt = f"""
    {user_prompt}

    Return only valid JSON.
    The response must match this JSON Schema exactly:

    {schema_json}

    Do not wrap the JSON in Markdown code fences.
    """.strip()

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
                        "content": grounded_user_prompt,
                    },
                ],
                stream=False,
                format=schema,
                options={
                    "temperature": 0,
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

        raw_text = (
            response.message.content or ""
        ).strip()

        if not raw_text:
            raise LLMEmptyResponseError(
                "Ollama returned an empty response."
            )

        try:
            parsed = (
                response_model.model_validate_json(
                    raw_text
                )
            )

        except ValidationError as exc:
            raise LLMStructuredOutputError(
                "Ollama returned JSON that does not "
                "match the requested schema.",
                raw_text=raw_text,
                validation_errors=exc.errors(),
            ) from exc

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

        return StructuredLLMResponse[
            StructuredModelT
        ](
            raw_text=raw_text,
            parsed=parsed,
            provider=self.provider_name,
            model=actual_model or self.model,
            request_id=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )