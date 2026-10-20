import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Invalid application configuration."""


@dataclass(frozen=True)
class Settings:
    llm_provider: Literal["openai", "ollama"]

    llm_timeout_seconds: float = 120.0
    llm_max_retries: int = 1

    openai_api_key: str | None = None
    openai_model: str | None = None

    ollama_host: str = "http://localhost:11434"
    ollama_model: str | None = None


def load_settings() -> Settings:
    load_dotenv()

    provider = os.getenv(
        "LLM_PROVIDER",
        "ollama",
    ).strip().lower()

    if provider not in {"openai", "ollama"}:
        raise ConfigurationError(
            "LLM_PROVIDER must be 'openai' or 'ollama'."
        )

    timeout_raw = os.getenv(
        "LLM_TIMEOUT_SECONDS",
        "120",
    )

    retries_raw = os.getenv(
        "LLM_MAX_RETRIES",
        "1",
    )

    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ConfigurationError(
            "LLM_TIMEOUT_SECONDS must be a number."
        ) from exc

    try:
        max_retries = int(retries_raw)
    except ValueError as exc:
        raise ConfigurationError(
            "LLM_MAX_RETRIES must be an integer."
        ) from exc

    if timeout_seconds <= 0:
        raise ConfigurationError(
            "LLM_TIMEOUT_SECONDS must be greater than 0."
        )

    if max_retries < 0:
        raise ConfigurationError(
            "LLM_MAX_RETRIES cannot be negative."
        )

    openai_api_key = (
        os.getenv("OPENAI_API_KEY", "").strip() or None
    )

    openai_model = (
        os.getenv("OPENAI_MODEL", "").strip() or None
    )

    ollama_host = os.getenv(
        "OLLAMA_HOST",
        "http://localhost:11434",
    ).strip()

    ollama_model = (
        os.getenv("OLLAMA_MODEL", "").strip() or None
    )

    if provider == "openai":
        if not openai_api_key:
            raise ConfigurationError(
                "OPENAI_API_KEY is required "
                "when LLM_PROVIDER=openai."
            )

        if not openai_model:
            raise ConfigurationError(
                "OPENAI_MODEL is required "
                "when LLM_PROVIDER=openai."
            )

    if provider == "ollama":
        if not ollama_model:
            raise ConfigurationError(
                "OLLAMA_MODEL is required "
                "when LLM_PROVIDER=ollama."
            )

        if not ollama_host:
            raise ConfigurationError(
                "OLLAMA_HOST cannot be empty."
            )

    return Settings(
        llm_provider=provider,
        llm_timeout_seconds=timeout_seconds,
        llm_max_retries=max_retries,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
    )
