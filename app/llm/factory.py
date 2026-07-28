from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


def create_llm_provider(
    settings: Settings,
) -> LLMProvider:
    if settings.llm_provider == "ollama":
        assert settings.ollama_model is not None

        return OllamaProvider(
            model=settings.ollama_model,
            host=settings.ollama_host,
            timeout_seconds=(
                settings.llm_timeout_seconds
            ),
        )

    if settings.llm_provider == "openai":
        assert settings.openai_model is not None
        assert settings.openai_api_key is not None

        return OpenAIProvider(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            timeout_seconds=(
                settings.llm_timeout_seconds
            ),
            max_retries=settings.llm_max_retries,
        )

    raise ValueError(
        f"Unsupported LLM provider: "
        f"{settings.llm_provider}"
    )