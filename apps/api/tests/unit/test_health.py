from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_atlas_api.config import Settings
from ai_atlas_api.db import DatabaseReadiness
from ai_atlas_api.main import create_app


def make_app(
    readiness_probe: Callable[[str | None], Awaitable[DatabaseReadiness]] | None = None,
    *,
    database_url: str | None = None,
) -> FastAPI:
    settings = Settings(_env_file=None, database_url=database_url)
    return create_app(settings=settings, readiness_probe=readiness_probe)


async def test_liveness_does_not_depend_on_database_or_gemini() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_fails_when_database_is_not_configured() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "not_configured", "vector": "not_checked"},
    }


async def test_readiness_reports_database_and_vector_extension() -> None:
    async def ready_probe(_: str | None) -> DatabaseReadiness:
        return DatabaseReadiness(database="ok", vector="ok")

    app = make_app(ready_probe, database_url="postgresql://example.invalid/ai_atlas")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "vector": "ok"},
    }


async def test_readiness_hides_connection_error_details() -> None:
    async def failed_probe(_: str | None) -> DatabaseReadiness:
        return DatabaseReadiness(database="unavailable", vector="not_checked")

    app = make_app(failed_probe, database_url="postgresql://example.invalid/ai_atlas")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable", "vector": "not_checked"},
    }


async def test_readiness_fails_when_vector_extension_is_missing() -> None:
    async def missing_vector_probe(_: str | None) -> DatabaseReadiness:
        return DatabaseReadiness(database="ok", vector="missing")

    app = make_app(missing_vector_probe, database_url="postgresql://example.invalid/ai_atlas")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "vector": "missing"},
    }
