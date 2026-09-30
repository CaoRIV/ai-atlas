from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from ai_atlas_api.catalog import CatalogRepository
from ai_atlas_api.catalog_models import CatalogQuery
from ai_atlas_api.config import Settings
from ai_atlas_api.main import create_app


def test_query_normalizes_unicode_and_defaults() -> None:
    query = CatalogQuery(q="  ho\u0300a  ", category=" coding-development , research-learning ")
    assert query.q == "hòa"
    assert query.category_slugs == ["coding-development", "research-learning"]
    assert query.effective_sort == "relevance"
    assert CatalogQuery(q="   ").effective_sort == "name"
    assert CatalogQuery(api_available="false").api_available is False


@pytest.mark.parametrize(
    "values",
    [
        {"q": "x" * 201},
        {"category": ""},
        {"category": "a,,b"},
        {"category": ",".join(["a"] * 9)},
        {"category": "UPPER"},
        {"sort": "relevance"},
        {"api_available": "0"},
        {"open_source": "yes"},
        {"platform": "desktop"},
        {"page": 0},
        {"page_size": 101},
        {"owner_id": "someone"},
    ],
)
def test_query_rejects_unsupported_input(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CatalogQuery.model_validate(values)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tools?extra=secret",
        "/api/v1/tools?api_available=yes",
        "/api/v1/tools?open_source=0",
        "/api/v1/tools?sort=relevance&q=%20",
        "/api/v1/tools?page=0",
        "/api/v1/tools?page_size=101",
        "/api/v1/tools?platform=invalid",
        "/api/v1/tools?pricing_model=cheap",
        "/api/v1/tools?category=",
        "/api/v1/tools?category=a,,b",
        "/api/v1/tools?q=a&q=b",
        "/api/v1/tools?category=a&category=b",
        "/api/v1/categories?page=1",
        "/api/v1/tools/not-a-uuid",
        f"/api/v1/tools/{uuid4()}?include_draft=true",
    ],
)
async def test_invalid_requests_have_safe_error_envelope(path: str) -> None:
    app = create_app(Settings(_env_file=None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]
    assert body["request_id"] == response.headers["X-Request-ID"]
    UUID(body["request_id"])
    assert "secret" not in response.text


async def test_request_id_and_unconfigured_catalog() -> None:
    app = create_app(Settings(_env_file=None))
    request_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tools", headers={"X-Request-ID": request_id})
        invalid = await client.get("/api/v1/categories", headers={"X-Request-ID": "bad"})
    assert response.status_code == invalid.status_code == 503
    assert response.json()["error"]["code"] == "CATALOG_UNAVAILABLE"
    assert response.json()["request_id"] == response.headers["X-Request-ID"] == request_id
    UUID(invalid.json()["request_id"])


async def test_database_connection_failure_is_sanitized() -> None:
    app = create_app(
        Settings(
            _env_file=None, database_url="postgresql://user:private-password@127.0.0.1:1/catalog"
        )
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/tools")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CATALOG_UNAVAILABLE"
    assert "private-password" not in response.text
    assert "127.0.0.1" not in response.text


async def test_method_not_allowed_preserves_allow_and_request_id() -> None:
    app = create_app(Settings(_env_file=None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/tools")
    assert response.status_code == 405
    assert response.headers["Allow"] == "GET"
    body = response.json()
    assert body["error"]["code"] == "HTTP_ERROR"
    assert body["request_id"] == response.headers["X-Request-ID"]
    UUID(body["request_id"])


async def test_unexpected_errors_do_not_expose_internals(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_: CatalogRepository) -> list[object]:
        raise RuntimeError("private SQL and password")

    monkeypatch.setattr(CatalogRepository, "categories", broken)
    app = create_app(Settings(_env_file=None))
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/categories")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private" not in response.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_openapi_declares_public_contracts() -> None:
    schema = create_app(Settings(_env_file=None)).openapi()
    routes = schema["paths"]
    assert not routes["/api/v1/categories"]["get"].get("parameters", [])
    operation = routes["/api/v1/tools"]["get"]
    assert {parameter["name"] for parameter in operation["parameters"]} == set(
        CatalogQuery.model_fields
    )
    assert "security" not in operation
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ToolsResponse"
    )
    for path in ("/api/v1/categories", "/api/v1/tools", "/api/v1/tools/{tool_id}"):
        assert {"200", "422", "503", "500"} <= set(routes[path]["get"]["responses"])
    assert "404" in routes["/api/v1/tools/{tool_id}"]["get"]["responses"]
