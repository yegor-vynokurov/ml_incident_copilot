import logging
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import (
    Annotated,
    Any,
    Protocol,
    cast,
)
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Request,
    status,
)
from fastapi.exceptions import (
    RequestValidationError,
)
from fastapi.responses import (
    JSONResponse,
)

from app.api_models import (
    APIError,
    ErrorResponse,
    HealthResponse,
    IncidentFeedbackRequest,
    IncidentFeedbackResponse,
)
from app.bootstrap import build_agent, build_run_store
from app.incident_builder import (
    IncidentBuildError,
)
from app.llm.base import (
    LLMEmptyResponseError,
    LLMProviderError,
    LLMRepairExhaustedError,
    LLMStructuredOutputError,
)
from app.report_validation import (
    ReportGroundingError,
)
from app.schemas import (
    AgentRun,
    PredictionRequest,
)

from app.observability.records import (
    build_error_run_record,
    build_success_run_record,
)

from app.observability.schemas import (
    IncidentFeedbackRecord,
)

from app.observability.store import (
    RunStore,
    RunNotFoundError,
)




logger = logging.getLogger(__name__)


def configure_app_logging() -> None:
    """Send application events to container stdout once per process."""
    app_logger = logging.getLogger("app")
    level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    app_logger.setLevel(level if isinstance(level, int) else logging.INFO)
    app_logger.propagate = False

    if any(handler.name == "incident-copilot-stdout" for handler in app_logger.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.set_name("incident-copilot-stdout")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    app_logger.addHandler(handler)


class AgentRunner(Protocol):
    """Minimal agent interface used by the HTTP layer."""

    def run(
        self,
        request: PredictionRequest,
    ) -> AgentRun:
        ...


def get_agent(
    request: Request,
) -> AgentRunner:
    """Get the agent initialized by the FastAPI lifespan."""

    agent = getattr(
        request.app.state,
        "agent",
        None,
    )

    if agent is None:
        raise RuntimeError(
            "Agent was not initialized."
        )

    return cast(
        AgentRunner,
        agent,
    )



def get_run_store(
    request: Request,
) -> RunStore:
    return request.app.state.run_store



AgentDependency = Annotated[
    AgentRunner,
    Depends(get_agent),
]


def _get_trace_id(
    request: Request,
) -> str:
    return str(
        getattr(
            request.state,
            "trace_id",
            "unknown",
        )
    )


def _get_domain_request_id(
    request: Request,
) -> str | None:
    value = getattr(
        request.state,
        "request_id",
        None,
    )

    if value is None:
        return None

    return str(value)


def _create_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
    details: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ) = None,
) -> JSONResponse:
    """Return an API error using the shared response schema."""

    response_model = ErrorResponse(
        error=APIError(
            code=code,
            message=message,
            retryable=retryable,
            trace_id=_get_trace_id(
                request
            ),
            request_id=(
                _get_domain_request_id(
                    request
                )
            ),
            details=details,
        )
    )

    return JSONResponse(
        status_code=status_code,
        content=response_model.model_dump(
            mode="json",
        ),
    )


def _validation_error_details(
    exc: RequestValidationError,
) -> list[dict[str, Any]]:
    """Expose only useful, safe fields from validation errors."""

    details: list[
        dict[str, Any]
    ] = []

    for error in exc.errors():
        details.append(
            {
                "location": [
                    str(part)
                    for part
                    in error.get(
                        "loc",
                        [],
                    )
                ],
                "message": str(
                    error.get(
                        "msg",
                        "Validation error",
                    )
                ),
                "type": str(
                    error.get(
                        "type",
                        "validation_error",
                    )
                ),
            }
        )

    return details


ERROR_RESPONSES = {
    422: {
        "model": ErrorResponse,
        "description": (
            "The request body does not match "
            "PredictionRequest."
        ),
    },
    502: {
        "model": ErrorResponse,
        "description": (
            "The LLM returned an invalid response."
        ),
    },
    503: {
        "model": ErrorResponse,
        "description": (
            "The configured LLM provider "
            "is unavailable."
        ),
    },
    500: {
        "model": ErrorResponse,
        "description": (
            "The service encountered an "
            "internal consistency error."
        ),
    },
}





def create_app(
    agent: AgentRunner | None = None,
    run_store: RunStore | None = None,
) -> FastAPI:
    """
    Application factory.

    In a normal run, creates the real agent.
    In tests, uses the supplied fake agent.
    """

    @asynccontextmanager
    async def lifespan(
        app: FastAPI,
    ) -> AsyncGenerator[None, None]:
        configure_app_logging()
        app.state.agent = (
            agent
            if agent is not None
            else build_agent()
        )

        app.state.run_store = (
            run_store
            if run_store is not None
            else build_run_store()
        )

        logger.info("service_ready agent=%s", type(app.state.agent).__name__)

        yield

        del app.state.agent

    app = FastAPI(
        title="ML Incident Copilot API",
        summary=(
            "AI-assisted diagnostics for "
            "ML prediction incidents."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def add_trace_id(
        request: Request,
        call_next,
    ):
        supplied_trace_id = (
            request.headers.get(
                "X-Trace-ID"
            )
        )

        trace_id = (
            supplied_trace_id
            if supplied_trace_id
            else uuid4().hex
        )

        # Do not allow a client to send
        # an extremely long trace ID.
        request.state.trace_id = (
            trace_id[:128]
        )

        response = await call_next(
            request
        )

        response.headers[
            "X-Trace-ID"
        ] = request.state.trace_id

        return response

    @app.exception_handler(
        RequestValidationError
    )
    async def handle_request_validation(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning(
            "request_rejected trace_id=%r path=%r error_count=%d",
            _get_trace_id(request),
            request.url.path,
            len(exc.errors()),
        )
        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_422_UNPROCESSABLE_CONTENT
            ),
            code="request_validation_error",
            message=(
                "The request body does not "
                "match the expected schema."
            ),
            retryable=False,
            details=(
                _validation_error_details(
                    exc
                )
            ),
        )

    @app.exception_handler(
        LLMRepairExhaustedError
    )
    async def handle_repair_exhausted(
        request: Request,
        exc: LLMRepairExhaustedError,
    ) -> JSONResponse:
        logger.warning(
            "LLM repair exhausted. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            code="llm_output_invalid",
            message=(
                "The LLM returned an invalid "
                "response after the repair attempt."
            ),
            retryable=True,
        )

    @app.exception_handler(
        LLMStructuredOutputError
    )
    async def handle_structured_output(
        request: Request,
        exc: LLMStructuredOutputError,
    ) -> JSONResponse:
        logger.warning(
            "Invalid structured LLM output. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            code="llm_output_invalid",
            message=(
                "The LLM returned a response "
                "that does not match the "
                "required schema."
            ),
            retryable=True,
        )

    @app.exception_handler(
        LLMEmptyResponseError
    )
    async def handle_empty_llm_response(
        request: Request,
        exc: LLMEmptyResponseError,
    ) -> JSONResponse:
        logger.warning(
            "Empty LLM response. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            code="llm_empty_response",
            message=(
                "The LLM returned an "
                "empty response."
            ),
            retryable=True,
        )

    @app.exception_handler(
        LLMProviderError
    )
    async def handle_llm_provider_error(
        request: Request,
        exc: LLMProviderError,
    ) -> JSONResponse:
        logger.warning(
            "LLM provider error. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            code="llm_provider_unavailable",
            message=(
                "The LLM service is "
                "temporarily unavailable."
            ),
            retryable=True,
        )

    @app.exception_handler(
        IncidentBuildError
    )
    async def handle_incident_build_error(
        request: Request,
        exc: IncidentBuildError,
    ) -> JSONResponse:
        logger.exception(
            "Incident build error. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
            exc_info=exc,
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            code="internal_consistency_error",
            message=(
                "The incident report could "
                "not be assembled safely."
            ),
            retryable=False,
        )

    @app.exception_handler(
        ReportGroundingError
    )
    async def handle_grounding_error(
        request: Request,
        exc: ReportGroundingError,
    ) -> JSONResponse:
        logger.exception(
            "Report grounding error. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
            exc_info=exc,
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            code="internal_consistency_error",
            message=(
                "The generated report failed "
                "an internal consistency check."
            ),
            retryable=False,
        )

    @app.exception_handler(
        Exception
    )
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unexpected API error. "
            "trace_id=%s request_id=%s",
            _get_trace_id(request),
            _get_domain_request_id(
                request
            ),
            exc_info=exc,
        )

        return _create_error_response(
            request=request,
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            code="internal_server_error",
            message=(
                "The service encountered "
                "an unexpected error."
            ),
            retryable=False,
        )



    @app.exception_handler(
        RunNotFoundError
    )
    async def handle_run_not_found(
        request: Request,
        exc: RunNotFoundError,
    ) -> JSONResponse:
        logger.warning(
            "feedback_run_not_found trace_id=%r requested_trace_id=%r",
            _get_trace_id(request),
            exc.trace_id,
        )
        trace_id = getattr(
            request.state,
            "trace_id",
            None,
        )

        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error=APIError(
                    code="run_not_found",
                    message=str(exc),
                    retryable=False,
                    trace_id=trace_id,
                    request_id=None,
                    details={
                        "requested_trace_id": (
                            exc.trace_id
                        )
                    },
                )
            ).model_dump(
                mode="json"
            ),
        )




    router = APIRouter(
        prefix="/v1",
    )

    @router.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
    )
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=(
                "ml-incident-copilot"
            ),
            version="0.1.0",
        )




    

    @router.post(
        "/incidents/analyze",
        response_model=AgentRun,
        responses=ERROR_RESPONSES,
        tags=["incidents"],
    )
    def analyze_incident(
        payload: PredictionRequest,
        request: Request,
        agent: AgentRunner = Depends(
            get_agent
        ),
        run_store: RunStore = Depends(
            get_run_store
        ),
    ) -> AgentRun:

        request.state.request_id = (
            payload.request_id
        )
        
        trace_id = request.state.trace_id

        started = perf_counter()
        logger.info(
            "analysis_started trace_id=%r request_id=%r",
            trace_id,
            payload.request_id,
        )

        try:
            agent_run = agent.run(
                payload
            )

        except Exception as exc:
            duration_ms = (
                perf_counter() - started
            ) * 1000

            error_record = (
                build_error_run_record(
                    trace_id=trace_id,
                    request=payload,
                    duration_ms=duration_ms,
                    error=exc,
                )
            )

            run_store.append_run(
                error_record
            )

            logger.warning(
                "analysis_failed trace_id=%r request_id=%r error_type=%s duration_ms=%.2f",
                trace_id,
                payload.request_id,
                type(exc).__name__,
                duration_ms,
            )

            raise

        duration_ms = (
            perf_counter() - started
        ) * 1000

        success_record = (
            build_success_run_record(
                trace_id=trace_id,
                request=payload,
                agent_run=agent_run,
                duration_ms=duration_ms,
            )
        )

        run_store.append_run(
            success_record
        )

        logger.info(
            "analysis_completed trace_id=%r request_id=%r status=%s "
            "issue_codes=%r providers=%r models=%r llm_calls=%d duration_ms=%.2f",
            trace_id,
            payload.request_id,
            agent_run.status,
            agent_run.issue_codes,
            success_record.providers,
            success_record.models,
            len(agent_run.analysis_traces),
            duration_ms,
        )

        return agent_run


    @app.post(
        "/v1/incidents/{trace_id}/feedback",
        response_model=(
            IncidentFeedbackResponse
        ),
    )
    def submit_incident_feedback(
        trace_id: str,
        payload: IncidentFeedbackRequest,
        run_store: RunStore = Depends(
            get_run_store
        ),
    ) -> IncidentFeedbackResponse:
        existing_run = run_store.get_run(
            trace_id
        )

        if existing_run is None:
            raise RunNotFoundError(
                trace_id
            )

        feedback_id = str(
            uuid4()
        )

        record = IncidentFeedbackRecord(
            feedback_id=feedback_id,
            trace_id=trace_id,
            created_at=datetime.now(
                timezone.utc
            ),
            verdict=payload.verdict,
            issue_code=payload.issue_code,
            expected_issue_codes=(
                payload.expected_issue_codes
            ),
            comment=payload.comment,
            corrected_explanation=(
                payload.corrected_explanation
            ),
        )

        run_store.append_feedback(
            record
        )

        logger.info(
            "feedback_recorded trace_id=%r feedback_id=%r verdict=%s issue_code=%r",
            trace_id,
            feedback_id,
            payload.verdict,
            payload.issue_code,
        )

        return IncidentFeedbackResponse(
            feedback_id=feedback_id,
            trace_id=trace_id,
            status="recorded",
        )






    @app.get(
        "/",
        tags=["service"],
    )
    def root() -> dict[str, str]:
        return {
            "service": "ml-incident-copilot",
            "status": "running",
            "docs": "/docs",
            "health": "/v1/health",
        }

    app.include_router(
        router
    )

    return app


app = create_app()
