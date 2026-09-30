import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb

from ai_atlas_api.config import Settings
from ai_atlas_api.main import create_app
from ai_atlas_api.migrations import upgrade

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def catalog_database() -> Iterator[tuple[str, dict[str, UUID]]]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required for catalog integration tests.")
    database_name = f"ai_atlas_catalog_{uuid4().hex}"
    parameters = conninfo_to_dict(base_url)
    parameters["dbname"] = database_name
    test_url = make_conninfo(**parameters)
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    try:
        upgrade(test_url)
        with psycopg.connect(test_url) as connection:
            ids = seed_catalog(connection)
        yield test_url, ids
    finally:
        with psycopg.connect(base_url, autocommit=True) as connection:
            connection.execute(
                """SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                   WHERE datname = %s AND pid <> pg_backend_pid()""",
                (database_name,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))


def seed_catalog(connection: psycopg.Connection[Any]) -> dict[str, UUID]:
    now = datetime.now(UTC)
    ids: dict[str, UUID] = {}
    for slug, name in (("coding-development", "Coding"), ("research-learning", "Learning")):
        ids[slug] = uuid4()
        connection.execute(
            "INSERT INTO categories (id, slug, name) VALUES (%s, %s, %s)", (ids[slug], slug, name)
        )
    provider_id, model_id, capability_id = uuid4(), uuid4(), uuid4()
    connection.execute(
        "INSERT INTO providers (id, slug, name) VALUES (%s, 'fixture', 'Fixture')", (provider_id,)
    )
    connection.execute(
        "INSERT INTO models (id, slug, name) VALUES (%s, 'fixture-model', 'Model')", (model_id,)
    )
    connection.execute(
        """INSERT INTO capabilities (id, key, name, description)
                       VALUES (%s, 'text_generation', 'Text generation', 'Fixture')""",
        (capability_id,),
    )

    def fact(
        slug: str,
        key: str,
        value: object,
        state: str = "verified",
        window: str = "fresh",
        revision: int = 1,
    ) -> UUID:
        fact_id = uuid4()
        connection.execute(
            """INSERT INTO tool_facts
                           (id, tool_id, key, value, verification_status, revision)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
            (fact_id, ids[slug], key, Jsonb(value), state, revision),
        )
        checked = now - timedelta(days=2)
        expires = now + timedelta(days=2)
        if window == "expired":
            expires = now - timedelta(days=1)
        if window == "future":
            checked = now + timedelta(days=1)
        if window != "missing":
            connection.execute(
                """INSERT INTO evidence
                (id, fact_id, fact_revision, source_url, source_kind,
                 checked_at, expires_at, checked_by, excerpt)
                VALUES (%s, %s, %s, 'https://example.invalid/docs', 'official_docs',
                        %s, %s, 'private reviewer', 'unpublished notes')""",
                (uuid4(), fact_id, 1, checked, expires),
            )
        return fact_id

    for slug in (
        "alpha",
        "beta",
        "missing",
        "null",
        "stale",
        "revision",
        "future",
        "unverified",
        "no-evidence",
        "explicit-unknown",
        "tie-a",
        "tie-b",
        "archived",
        "draft",
    ):
        ids[slug] = uuid4()
        name = "Twin" if slug.startswith("tie-") else slug.title()
        status = slug if slug in ("archived", "draft") else "published"
        description = "hòa synthetic discovery" + (" Alpha" if slug == "beta" else "")
        connection.execute(
            """INSERT INTO tools
            (id, slug, name, description, official_url, publication_status, provider_id,
             tags, updated_at, last_verified_at, search_vector)
            VALUES (%s, %s, %s, %s, 'https://example.invalid/tool', %s, %s,
                    ARRAY['fixture-tag'], %s, %s,
                    setweight(to_tsvector('simple', %s), 'A') ||
                    setweight(to_tsvector('simple', %s), 'B'))""",
            (
                ids[slug],
                slug,
                name,
                description,
                status,
                provider_id if slug == "alpha" else None,
                now,
                now,
                name,
                description + " fixture-tag Coding Text generation",
            ),
        )
        connection.execute(
            "INSERT INTO tool_categories VALUES (%s, %s)", (ids[slug], ids["coding-development"])
        )
    connection.execute(
        "INSERT INTO tool_categories VALUES (%s, %s)", (ids["alpha"], ids["research-learning"])
    )
    for slug, flag, model, platforms in (
        ("alpha", True, "paid", ["windows"]),
        ("beta", False, "free", ["web"]),
    ):
        fact(slug, "api_available", flag)
        fact(slug, "open_source", {"status": flag, "license": None})
        fact(slug, "pricing", {"model": model})
        fact(slug, "platforms", platforms)
    for slug, state, window, revision in (
        ("null", "unknown", "fresh", 1),
        ("stale", "verified", "expired", 1),
        ("revision", "verified", "fresh", 2),
        ("future", "verified", "future", 1),
        ("unverified", "unverified", "fresh", 1),
        ("no-evidence", "verified", "missing", 1),
    ):
        for key, value in (
            ("api_available", True),
            ("open_source", {"status": True}),
            ("pricing", {"model": "paid"}),
            ("platforms", ["windows"]),
        ):
            fact(slug, key, None if slug == "null" else value, state, window, revision)
    fact("explicit-unknown", "pricing", {"model": "unknown"})
    fact("alpha", "identity", {"name": "Alpha", "official_url": "https://example.invalid/tool"})
    fact("alpha", "model_usage:fixture-model", True)
    connection.execute("INSERT INTO tool_models VALUES (%s, %s)", (ids["alpha"], model_id))
    fact("beta", "model_usage:fixture-model", False)
    connection.execute("INSERT INTO tool_models VALUES (%s, %s)", (ids["beta"], model_id))
    fact("stale", "model_usage:fixture-model", True, window="expired")
    connection.execute("INSERT INTO tool_models VALUES (%s, %s)", (ids["stale"], model_id))
    for slug, window in (("alpha", "fresh"), ("stale", "expired"), ("revision", "fresh")):
        fact_id = fact(
            slug,
            "capability:text_generation",
            True,
            window=window,
            revision=2 if slug == "revision" else 1,
        )
        connection.execute(
            "INSERT INTO tool_capabilities VALUES (%s, %s, %s)", (ids[slug], capability_id, fact_id)
        )
    # A second fresh source must not duplicate the tool or capability.
    connection.execute(
        """INSERT INTO evidence
        (id, fact_id, fact_revision, source_url, source_kind, checked_at, expires_at, checked_by)
        SELECT %s, id, revision, 'https://example.invalid/other', 'official_site', %s, %s,
               'private reviewer' FROM tool_facts
        WHERE tool_id = %s AND key = 'api_available'""",
        (uuid4(), now - timedelta(days=1), now + timedelta(days=1), ids["alpha"]),
    )
    return ids


@pytest.fixture
async def client(catalog_database: tuple[str, dict[str, UUID]]) -> Any:
    app = create_app(Settings(_env_file=None, database_url=catalog_database[0]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_categories_and_multi_category_or_do_not_duplicate(client: AsyncClient) -> None:
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    assert "pagination" not in response.json()
    response = await client.get(
        "/api/v1/tools", params={"category": "coding-development,research-learning"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"] == {"page": 1, "page_size": 20, "total": 12}
    assert len(body["data"]) == len({tool["id"] for tool in body["data"]}) == 12
    alpha = next(tool for tool in body["data"] if tool["slug"] == "alpha")
    assert len(alpha["categories"]) == 2
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert alpha["pricing"] == {"model": "paid", "verification_status": "verified"}


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"api_available": "true"}, {"alpha"}),
        ({"api_available": "false"}, {"beta"}),
        ({"open_source": "true"}, {"alpha"}),
        ({"open_source": "false"}, {"beta"}),
        ({"platform": "windows"}, {"alpha"}),
        ({"platform": "web"}, {"beta"}),
        ({"pricing_model": "paid"}, {"alpha"}),
        ({"pricing_model": "free"}, {"beta"}),
        (
            {"pricing_model": "unknown"},
            {
                "missing",
                "null",
                "stale",
                "revision",
                "future",
                "unverified",
                "no-evidence",
                "explicit-unknown",
                "tie-a",
                "tie-b",
            },
        ),
        ({"category": "research-learning", "api_available": "false"}, set()),
        (
            {
                "category": "research-learning",
                "api_available": "true",
                "platform": "windows",
                "pricing_model": "paid",
                "open_source": "true",
            },
            {"alpha"},
        ),
    ],
)
async def test_filters_fail_closed_and_combine_groups(
    client: AsyncClient, params: dict[str, str], expected: set[str]
) -> None:
    response = await client.get("/api/v1/tools", params=params)
    assert response.status_code == 200, response.text
    assert {tool["slug"] for tool in response.json()["data"]} == expected
    assert response.json()["pagination"]["total"] == len(expected)


@pytest.mark.parametrize("query", ["Alpha", "alpha", "fixture-tag", "synthetic", "ho\u0300a"])
async def test_keyword_name_slug_description_tags_and_unicode(
    client: AsyncClient, query: str
) -> None:
    response = await client.get("/api/v1/tools", params={"q": " " + query + " "})
    assert response.status_code == 200
    slugs = [tool["slug"] for tool in response.json()["data"]]
    assert "alpha" in slugs
    assert "archived" not in slugs and "draft" not in slugs
    if query.lower() == "alpha":
        assert slugs == ["alpha", "beta"]


async def test_exact_slug_and_whitespace_query(client: AsyncClient) -> None:
    exact = await client.get("/api/v1/tools", params={"q": "tie-a"})
    assert [tool["slug"] for tool in exact.json()["data"]] == ["tie-a"]
    omitted = await client.get("/api/v1/tools")
    blank = await client.get("/api/v1/tools", params={"q": "  "})
    assert omitted.json()["data"] == blank.json()["data"]


async def test_unknown_category_and_sql_input(client: AsyncClient) -> None:
    response = await client.get("/api/v1/tools?category=coding-development,absent")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    response = await client.get("/api/v1/tools", params={"q": "'; DROP TABLE tools; --"})
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert (await client.get("/api/v1/tools")).json()["pagination"]["total"] == 12


@pytest.mark.parametrize("sort", ["name", "updated", "relevance"])
async def test_stable_pagination_and_empty_page(client: AsyncClient, sort: str) -> None:
    params = {"sort": sort, "page_size": "1"}
    if sort == "relevance":
        params["q"] = "synthetic"
    full = await client.get("/api/v1/tools", params={**params, "page_size": "100"})
    expected = [tool["id"] for tool in full.json()["data"]]
    seen = []
    for page in range(1, 13):
        response = await client.get("/api/v1/tools", params={**params, "page": str(page)})
        assert response.status_code == 200
        seen.extend(tool["id"] for tool in response.json()["data"])
    assert seen == expected
    assert len(seen) == len(set(seen)) == 12
    empty = await client.get("/api/v1/tools", params={**params, "page": str(10**30)})
    assert empty.status_code == 200
    assert empty.json()["data"] == []
    assert empty.json()["pagination"]["total"] == 12


async def test_detail_provenance_and_private_fields(
    client: AsyncClient, catalog_database: tuple[str, dict[str, UUID]]
) -> None:
    response = await client.get(f"/api/v1/tools/{catalog_database[1]['alpha']}")
    assert response.status_code == 200
    tool = response.json()["data"]
    assert tool["provider"]["name"] == "Fixture"
    assert tool["models"][0]["name"] == "Model"
    assert tool["capabilities"][0]["key"] == "text_generation"
    assert tool["warnings"] == []
    assert tool["revision"] == 1
    assert tool["official_url"].startswith("https://")
    sources = {source["id"]: source for source in tool["evidence"]}
    for fact in tool["facts"]:
        assert fact["verification_status"] == "verified"
        assert fact["evidence_ids"]
        assert all(
            sources[evidence_id]["fact_key"] == fact["key"] for evidence_id in fact["evidence_ids"]
        )
    assert "checked_by" not in response.text and "private reviewer" not in response.text
    assert "excerpt" not in response.text and "unpublished notes" not in response.text


async def test_detail_verified_false_model_usage_does_not_publish_model(
    client: AsyncClient, catalog_database: tuple[str, dict[str, UUID]]
) -> None:
    response = await client.get(f"/api/v1/tools/{catalog_database[1]['beta']}")
    assert response.status_code == 200
    tool = response.json()["data"]
    fact = next(fact for fact in tool["facts"] if fact["key"] == "model_usage:fixture-model")
    assert fact["value"] is False
    assert fact["verification_status"] == "verified"
    assert fact["evidence_ids"] == [
        source["id"] for source in tool["evidence"] if source["fact_key"] == fact["key"]
    ]
    assert tool["models"] == []
    assert tool["warnings"] == []


@pytest.mark.parametrize(
    "slug", ["null", "stale", "revision", "future", "unverified", "no-evidence"]
)
async def test_detail_stale_values_are_labeled_and_not_claimed(
    client: AsyncClient, catalog_database: tuple[str, dict[str, UUID]], slug: str
) -> None:
    response = await client.get(f"/api/v1/tools/{catalog_database[1][slug]}")
    assert response.status_code == 200
    tool = response.json()["data"]
    assert tool["provider"] is None
    assert tool["models"] == []
    assert tool["capabilities"] == []
    for fact in tool["facts"]:
        assert fact["verification_status"] == ("unknown" if slug == "null" else "unverified")
        assert fact["evidence_ids"] == []
        assert f"fact_{fact['verification_status']}:{fact['key']}" in tool["warnings"]
        if fact["key"] == "api_available":
            assert fact["value"] is (None if slug == "null" else True)
    if slug == "revision":
        assert tool["evidence"] == []


@pytest.mark.parametrize("slug", ["archived", "draft", "absent"])
async def test_unpublished_or_absent_detail_is_404(
    client: AsyncClient, catalog_database: tuple[str, dict[str, UUID]], slug: str
) -> None:
    tool_id = catalog_database[1].get(slug, uuid4())
    response = await client.get(f"/api/v1/tools/{tool_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
