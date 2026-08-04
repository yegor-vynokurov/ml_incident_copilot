import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
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
)
from app.bootstrap import build_agent
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


logger = logging.getLogger(__name__)


class AgentRunner(Protocol):
    """
    the iterface
    """

    def run(
        self,
        request: PredictionRequest,
    ) -> AgentRun:
        ...


def get_agent(
    request: Request,
) -> AgentRunner:
    """
    to get the created agent from the state of fastapi app
    """

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
    """
    collects any API-error
    in single format.
    """

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
    """
    Leave for the client only safe and useful part of pydantic errors
    """

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
    *,
    agent: AgentRunner | None = None,
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
        app.state.agent = (
            agent
            if agent is not None
            else build_agent()
        )

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
            exc_info=exc,
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
            exc_info=exc,
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
            exc_info=exc,
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
            exc_info=exc,
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
        request: Request,
        payload: PredictionRequest,
        agent: AgentDependency,
    ) -> AgentRun:
        request.state.request_id = (
            payload.request_id
        )

        return agent.run(
            payload
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