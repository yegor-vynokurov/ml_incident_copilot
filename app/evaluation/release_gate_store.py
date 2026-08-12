from pathlib import Path

from pydantic import (
    ValidationError,
)

from app.evaluation.release_gate_schemas import (
    ReleaseGatePolicy,
)


class ReleaseGatePolicyReadError(
    ValueError
):
    pass


def load_release_gate_policy(
    path: Path,
) -> ReleaseGatePolicy:
    if not path.exists():
        raise ReleaseGatePolicyReadError(
            "Release gate policy does not exist: "
            f"{path}"
        )

    try:
        raw = path.read_text(
            encoding="utf-8",
        )

    except OSError as exc:
        raise ReleaseGatePolicyReadError(
            "Could not read release gate policy: "
            f"{path}"
        ) from exc

    try:
        return (
            ReleaseGatePolicy
            .model_validate_json(
                raw
            )
        )

    except ValidationError as exc:
        raise ReleaseGatePolicyReadError(
            "Release gate policy has an "
            "invalid structure: "
            f"{path}"
        ) from exc