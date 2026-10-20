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

        explanation = self._extract_grounded_statement(user_prompt)

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

    @staticmethod
    def _extract_grounded_statement(user_prompt: str) -> str:
        marker = "Verified grounded statement:\n"
        if marker not in user_prompt:
            raise RuntimeError("Grounded statement was not found in prompt.")
        statement = user_prompt.split(marker, maxsplit=1)[1].split(
            "\n\nTask:", maxsplit=1
        )[0].strip()
        if not statement:
            raise RuntimeError("Grounded statement is empty.")
        return statement
