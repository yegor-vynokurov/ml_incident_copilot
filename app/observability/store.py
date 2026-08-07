from pathlib import Path
from threading import Lock
from typing import Protocol

from app.observability.schemas import (
    IncidentFeedbackRecord,
    IncidentRunRecord,
)




class RunNotFoundError(
    LookupError
):
    def __init__(
        self,
        trace_id: str,
    ) -> None:
        self.trace_id = trace_id

        super().__init__(
            "Runtime record was not found "
            f"for trace_id={trace_id!r}."
        )


class RunStore(Protocol):
    """
    Persistence interface for runtime records.
    """

    def append_run(
        self,
        record: IncidentRunRecord,
    ) -> None:
        ...

    def append_feedback(
        self,
        record: IncidentFeedbackRecord,
    ) -> None:
        ...

    def get_run(
        self,
        trace_id: str,
    ) -> IncidentRunRecord | None:
        ...








class JsonlRunStore:
    """
    Append-only local JSONL storage.

    Suitable for local development and
    single-process MVP usage.
    """

    def __init__(
        self,
        *,
        runs_path: Path,
        feedback_path: Path,
    ) -> None:
        self._runs_path = runs_path
        self._feedback_path = feedback_path
        self._lock = Lock()

        self._runs_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._feedback_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


    def append_run(
        self,
        record: IncidentRunRecord,
    ) -> None:
        serialized = (
            record.model_dump_json()
        )

        with self._lock:
            with self._runs_path.open(
                "a",
                encoding="utf-8",
            ) as file:
                file.write(serialized)
                file.write("\n")


    def append_feedback(
        self,
        record: IncidentFeedbackRecord,
    ) -> None:
        serialized = (
            record.model_dump_json()
        )

        with self._lock:
            with self._feedback_path.open(
                "a",
                encoding="utf-8",
            ) as file:
                file.write(serialized)
                file.write("\n")


    def get_run(
        self,
        trace_id: str,
    ) -> IncidentRunRecord | None:
        if not self._runs_path.exists():
            return None

        with self._lock:
            lines = self._runs_path.read_text(
                encoding="utf-8",
            ).splitlines()

        for line in reversed(lines):
            if not line.strip():
                continue

            record = (
                IncidentRunRecord
                .model_validate_json(
                    line
                )
            )

            if record.trace_id == trace_id:
                return record

        return None




