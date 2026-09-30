from collections.abc import Awaitable, Callable, Mapping
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from ai_atlas_api.catalog import CatalogError, CatalogRepository
from ai_atlas_api.catalog_models import ErrorBody, ErrorDetail, ErrorResponse
from ai_atlas_api.catalog_routes import catalog_router
from ai_atlas_api.config import Settings
from ai_atlas_api.db import DatabaseReadiness, check_database_readiness

ReadinessProbe = Callable[[str | None], Awaitable[DatabaseReadiness]]


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str]


def create_app(
    settings: Settings | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings()
    probe = readiness_probe or check_database_readiness
    application = FastAPI(title="AI Atlas API", version="0.1.0")

    @application.middleware("http")
    async def request_identity(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            request.state.request_id = UUID(request.headers.get("X-Request-ID", ""))
        except ValueError:
            request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    def error_response(
        request: Request,
        status: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(code=code, message=message, details=details or []),
            request_id=request.state.request_id,
        )
        response = JSONResponse(
            status_code=status,
            content=body.model_dump(mode="json"),
            headers=headers,
        )
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    @application.exception_handler(CatalogError)
    async def catalog_error(request: Request, exc: CatalogError) -> JSONResponse:
        details = [ErrorDetail(field=exc.field, reason=exc.code.lower())] if exc.field else []
        return error_response(request, exc.status, exc.code, exc.message, details)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            ErrorDetail(field=".".join(str(part) for part in error["loc"]), reason=error["type"])
            for error in exc.errors()
        ]
        return error_response(
            request, 422, "VALIDATION_ERROR", "Dữ liệu đầu vào không hợp lệ.", details
        )

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            request,
            exc.status_code,
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            "Request không thể thực hiện.",
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return error_response(request, 500, "INTERNAL_ERROR", "Đã xảy ra lỗi hệ thống.")

    application.include_router(
        catalog_router(CatalogRepository(runtime_settings.database_url_value()))
    )

    @application.get("/health/live", response_model=LivenessResponse)
    async def liveness() -> LivenessResponse:
        return LivenessResponse()

    @application.get(
        "/health/ready",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse}},
    )
    async def readiness() -> ReadinessResponse | JSONResponse:
        database = await probe(runtime_settings.database_url_value())
        response = ReadinessResponse(
            status="ready" if database.ready else "not_ready",
            checks={"database": database.database, "vector": database.vector},
        )
        if database.ready:
            return response
        return JSONResponse(status_code=503, content=response.model_dump())

    return application


app = create_app()
