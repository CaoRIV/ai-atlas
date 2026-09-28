from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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
