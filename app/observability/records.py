from datetime import (
    datetime,
    timezone,
)

from app.issue_analysis_prompts import (
    ISSUE_ANALYSIS_PROMPT_VERSION,
)
from app.observability.schemas import (
    IncidentRunRecord,
)
from app.schemas import (
    AgentRun,
    PredictionRequest,
)



def build_success_run_record(
    *,
    trace_id: str,
    request: PredictionRequest,
    agent_run: AgentRun,
    duration_ms: float,
) -> IncidentRunRecord:
    providers = sorted(
        {
            trace.response.provider
            for trace
            in agent_run.analysis_traces
        }
    )

    models = sorted(
        {
            trace.response.model
            for trace
            in agent_run.analysis_traces
        }
    )

    return IncidentRunRecord(
        trace_id=trace_id,
        created_at=datetime.now(
            timezone.utc
        ),
        duration_ms=round(
            duration_ms,
            2,
        ),
        outcome="success",
        request=request,
        agent_run=agent_run,
        prompt_version=(
            ISSUE_ANALYSIS_PROMPT_VERSION
        ),
        providers=providers,
        models=models,
    )



def build_error_run_record(
    *,
    trace_id: str,
    request: PredictionRequest,
    duration_ms: float,
    error: Exception,
) -> IncidentRunRecord:
    return IncidentRunRecord(
        trace_id=trace_id,
        created_at=datetime.now(
            timezone.utc
        ),
        duration_ms=round(
            duration_ms,
            2,
        ),
        outcome="error",
        request=request,
        agent_run=None,
        prompt_version=(
            ISSUE_ANALYSIS_PROMPT_VERSION
        ),
        providers=[],
        models=[],
        error_type=(
            type(error).__name__
        ),
        error_message=(
            str(error)[:2000]
        ),
    )