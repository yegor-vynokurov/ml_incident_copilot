from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.llm.base import (
    LLMProvider,
    LLMRepairExhaustedError,
    LLMStructuredOutputError,
)
from app.schemas import StructuredLLMResponse


StructuredModelT = TypeVar(
    "StructuredModelT",
    bound=BaseModel,
)


def _format_validation_errors(
    errors: list[dict],
) -> str:
    if not errors:
        return (
            "The response did not match "
            "the requested schema."
        )

    lines: list[str] = []

    for error in errors:
        location = ".".join(
            str(part)
            for part in error.get(
                "loc",
                [],
            )
        )

        message = str(
            error.get(
                "msg",
                "Validation error",
            )
        )

        lines.append(
            f"- {location or '<root>'}: "
            f"{message}"
        )

    return "\n".join(lines)


def _build_repair_prompt(
    *,
    original_user_prompt: str,
    error: LLMStructuredOutputError,
) -> str:
    validation_text = (
        _format_validation_errors(
            error.validation_errors
        )
    )

    previous_output = (
        error.raw_text
        or "<raw output unavailable>"
    )

    # Do not put in repair limitless answer.
    previous_output = previous_output[:4000]

    return f"""
The previous response was invalid.

Validation errors:
{validation_text}

Previous invalid response:
{previous_output}

Correct the response.

Important rules:
- follow the supplied JSON Schema exactly;
- return only fields defined by the schema;
- remove all extra fields;
- do not preserve fields that caused validation errors;
- return only valid JSON;
- do not use Markdown code fences.

Original task:
{original_user_prompt}
""".strip()


def generate_structured_with_repair(
    *,
    provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
    response_model: type[StructuredModelT],
    max_repair_attempts: int = 1,
    validate_parsed: Callable[[StructuredModelT], None] | None = None,
) -> StructuredLLMResponse[
    StructuredModelT
]:
    """Generate a structured response with bounded validation and repair."""

    if max_repair_attempts < 0:
        raise ValueError(
            "max_repair_attempts cannot "
            "be negative."
        )

    current_user_prompt = user_prompt

    last_error: (
        LLMStructuredOutputError | None
    ) = None

    total_attempts = (
        max_repair_attempts + 1
    )

    for attempt_index in range(
        total_attempts
    ):
        try:
            response = (
                provider.generate_structured(
                    system_prompt=system_prompt,
                    user_prompt=(
                        current_user_prompt
                    ),
                    response_model=(
                        response_model
                    ),
                )
            )

            if validate_parsed is not None:
                validate_parsed(response.parsed)

            return response.model_copy(
                update={
                    "attempt_count": (
                        attempt_index + 1
                    )
                }
            )

        except LLMStructuredOutputError as exc:
            last_error = exc

            is_last_attempt = (
                attempt_index
                >= max_repair_attempts
            )

            if is_last_attempt:
                break

            current_user_prompt = (
                _build_repair_prompt(
                    original_user_prompt=(
                        user_prompt
                    ),
                    error=exc,
                )
            )

    raise LLMRepairExhaustedError(
        "Structured LLM output remained "
        f"invalid or ungrounded after {total_attempts} "
        "attempts."
    ) from last_error
