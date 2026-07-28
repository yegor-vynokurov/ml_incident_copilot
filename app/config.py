import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Error of the app config."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str

    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 1


def load_settings() -> Settings:
    """
    Load settings from .env variables.
    """

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()

    if not api_key:
        raise ConfigurationError(
            "OPENAI_API_KEY is not configured."
        )

    if not model:
        raise ConfigurationError(
            "OPENAI_MODEL is not configured."
        )

    timeout_raw = os.getenv(
        "LLM_TIMEOUT_SECONDS",
        "30",
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

    return Settings(
        openai_api_key=api_key,
        openai_model=model,
        llm_timeout_seconds=timeout_seconds,
        llm_max_retries=max_retries,
    )