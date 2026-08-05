from typing import TypeVar

from pydantic import BaseModel

from app.schemas import (
    LLMResponse,
    StructuredLLMResponse,
)


StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)



EXPLANATIONS_BY_ISSUE = {
    "road_access_conflict": (
        "The road_frontage and is_landlocked "
        "fields are inconsistent and require "
        "source-data review."
    ),
    "prediction_below_reference_range": (
        "The prediction is below the configured "
        "regional reference range and requires "
        "engineering review."
    ),
    "unsupported_location": (
        "The request location is not supported "
        "by the configured regional data."
    ),
    "model_location_mismatch": (
        "The selected model location does not "
        "match the request location."
    ),
}




class DeterministicEvaluationLLMProvider:
    """
    Fake provider для повторяемой
    evaluation без Ollama.
    """

    provider_name = "evaluation-fake"
    model = "deterministic-eval-model"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        return LLMResponse(
            text="Deterministic evaluation response.",
            provider=self.provider_name,
            model=self.model,
        )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[
            StructuredModelT
        ],
    ) -> StructuredLLMResponse[
        StructuredModelT
    ]:
        issue_code = (
            self._extract_issue_code(
                user_prompt
            )
        )

        explanation = (
            EXPLANATIONS_BY_ISSUE.get(
                issue_code,
                (
                    "The deterministic evidence "
                    "indicates a configured issue "
                    "that requires engineering review."
                ),
            )
        )

        payload = {
            "explanation": explanation,
        }

        parsed = (
            response_model.model_validate(
                payload
            )
        )

        self.calls.append(
            {
                "issue_code": issue_code,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )

        return StructuredLLMResponse(
            raw_text=(
                parsed.model_dump_json()
            ),
            parsed=parsed,
            provider=self.provider_name,
            model=self.model,
            request_id=None,
            input_tokens=0,
            output_tokens=0,
            attempt_count=1,
        )

    @staticmethod
    def _extract_issue_code(
        user_prompt: str,
    ) -> str:
        marker = (
            "Issue code for context:"
        )

        if marker not in user_prompt:
            raise RuntimeError(
                "Issue code marker was "
                "not found in prompt."
            )

        remaining_text = (
            user_prompt.split(
                marker,
                maxsplit=1,
            )[1]
        )

        issue_code = (
            remaining_text
            .strip()
            .splitlines()[0]
            .strip()
        )

        if not issue_code:
            raise RuntimeError(
                "Issue code is empty."
            )

        return issue_code