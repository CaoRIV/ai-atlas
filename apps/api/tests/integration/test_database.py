import os

import pytest
from httpx import ASGITransport, AsyncClient

from ai_atlas_api.config import Settings
from ai_atlas_api.db import check_database_readiness
from ai_atlas_api.main import create_app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_and_vector_extension_are_ready() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the database integration test.")

    readiness = await check_database_readiness(database_url)

    assert readiness.database == "ok"
    assert readiness.vector == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_readiness_uses_the_real_database() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the database integration test.")

    app = create_app(settings=Settings(_env_file=None, database_url=database_url))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "vector": "ok"},
    }
