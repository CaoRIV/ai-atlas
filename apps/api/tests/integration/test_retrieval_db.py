import os
from collections.abc import Iterator, Sequence
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from ai_atlas_api.catalog import CatalogRepository
from ai_atlas_api.config import Settings
from ai_atlas_api.migrations import upgrade
from ai_atlas_api.providers.gemini import EmbeddingBatch, GeminiRequestError
from ai_atlas_api.reindex_cli import run_reindex
from ai_atlas_api.retrieval import (
    SEMANTIC_RETRIEVAL_WARNING,
    EmbeddingIndex,
    EmbeddingProfile,
    HybridRetriever,
)

pytestmark = pytest.mark.integration


def uid(number: int) -> UUID:
    return UUID(f"90000000-0000-4000-8000-{number:012d}")


def vector(axis: int) -> list[float]:
    values = [0.0] * 1536
    values[axis] = 1.0
    return values


class StubEmbeddingProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def embed(
        self,
        texts: Sequence[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingBatch:
        self.calls.append((task_type, tuple(texts)))
        vectors = []
        for text in texts:
            use_vector_axis = "Vector Studio" in text or "semantic images" in text.casefold()
            vectors.append(vector(1 if use_vector_axis else 0))
        return EmbeddingBatch(
            vectors=vectors,
            model="gemini-embedding-2",
            dimension=1536,
        )


class FailingEmbeddingProvider:
    def embed(
        self,
        texts: Sequence[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingBatch:
        del texts, task_type
        raise GeminiRequestError("safe failure")


@pytest.fixture(scope="module")
def retrieval_database() -> Iterator[str]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required for retrieval integration tests.")
    database_name = f"ai_atlas_retrieval_{uuid4().hex}"
    parameters = conninfo_to_dict(base_url)
    parameters["dbname"] = database_name
    test_url = make_conninfo(**parameters)
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    try:
        upgrade(test_url)
        yield test_url
    finally:
        with psycopg.connect(base_url, autocommit=True) as connection:
            connection.execute(
                """SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                   WHERE datname = %s AND pid <> pg_backend_pid()""",
                (database_name,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))


@pytest.fixture
def retrieval_context(retrieval_database: str) -> tuple[str, dict[str, UUID]]:
    with psycopg.connect(retrieval_database) as connection:
        connection.execute(
            """TRUNCATE tool_embeddings, tool_capabilities, evidence, tool_facts,
                        tool_categories, tool_models, tools, capabilities, categories,
                        models, providers CASCADE"""
        )
        ids = seed_catalog(connection)
    return retrieval_database, ids


def execute_many(
    connection: psycopg.Connection[Any],
    statement: str,
    rows: Sequence[Sequence[object]],
) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(statement, rows)


def seed_catalog(connection: psycopg.Connection[Any]) -> dict[str, UUID]:
    ids = {
        "alpha": uid(1),
        "vector": uid(2),
        "archived": uid(3),
        "category": uid(10),
        "capability": uid(11),
        "fact": uid(12),
    }
    connection.execute(
        "INSERT INTO categories (id, slug, name) VALUES (%s, %s, %s)",
        (ids["category"], "creative-tools", "Creative Tools"),
    )
    connection.execute(
        "INSERT INTO capabilities (id, key, name, description) VALUES (%s, %s, %s, %s)",
        (ids["capability"], "image_generation", "Image generation", "Creates images"),
    )
    execute_many(
        connection,
        """INSERT INTO tools (
               id, slug, name, description, official_url, publication_status, revision
           ) VALUES (%s, %s, %s, %s, %s, %s, 1)""",
        [
            (
                ids["alpha"],
                "alpha-writer",
                "Alpha Writer",
                "Keyword writing assistant",
                "https://example.invalid/alpha",
                "published",
            ),
            (
                ids["vector"],
                "vector-studio",
                "Vector Studio",
                "Visual creation workspace",
                "https://example.invalid/vector",
                "published",
            ),
            (
                ids["archived"],
                "archived-tool",
                "Archived Tool",
                "Must not be embedded",
                "https://example.invalid/archived",
                "archived",
            ),
        ],
    )
    execute_many(
        connection,
        "INSERT INTO tool_categories (tool_id, category_id) VALUES (%s, %s)",
        [
            (ids["alpha"], ids["category"]),
            (ids["vector"], ids["category"]),
        ],
    )
    connection.execute(
        """INSERT INTO tool_facts (
               id, tool_id, key, value, verification_status, revision
           ) VALUES (%s, %s, %s, 'true'::jsonb, 'verified', 1)""",
        (ids["fact"], ids["vector"], "capability:image_generation"),
    )
    connection.execute(
        """INSERT INTO tool_capabilities (tool_id, capability_id, fact_id)
           VALUES (%s, %s, %s)""",
        (ids["vector"], ids["capability"], ids["fact"]),
    )
    connection.execute(
        """UPDATE tools SET search_vector =
             setweight(to_tsvector('simple', name), 'A') ||
             setweight(to_tsvector('simple', description), 'B')"""
    )
    return ids


def test_reindex_is_incremental_and_vector_search_rejects_stale_rows(
    retrieval_context: tuple[str, dict[str, UUID]],
) -> None:
    database_url, ids = retrieval_context
    settings = Settings(_env_file=None, database_url=database_url)
    provider = StubEmbeddingProvider()
    profile = EmbeddingProfile.from_settings(settings)
    repository = CatalogRepository(database_url)
    index = EmbeddingIndex(repository)

    first = run_reindex(settings, provider=provider, batch_size=10)
    assert first.status == "ok"
    assert first.report is not None
    assert first.report.to_dict() == {
        "total": 2,
        "embedded": 2,
        "stored": 2,
        "unchanged": 0,
        "stale_during_write": 0,
        "batches": 1,
        "model_key": profile.model_key,
    }
    assert provider.calls[0][0] == "RETRIEVAL_DOCUMENT"
    assert len(provider.calls[0][1]) == 2

    second = run_reindex(settings, provider=provider)
    assert second.report is not None
    assert (second.report.embedded, second.report.unchanged, len(provider.calls)) == (0, 2, 1)

    with repository.connection() as connection:
        ranked = index.vector_ranked(connection, vector(1), profile)
    assert ranked[:2] == (ids["vector"], ids["alpha"])

    with psycopg.connect(database_url) as connection:
        connection.execute(
            """UPDATE tools SET description = %s, revision = revision + 1,
                                search_vector = to_tsvector('simple', name || ' ' || %s)
               WHERE id = %s""",
            ("Updated writing assistant", "Updated writing assistant", ids["alpha"]),
        )
    changed = run_reindex(settings, provider=provider)
    assert changed.report is not None
    assert (changed.report.embedded, changed.report.stored, changed.report.unchanged) == (1, 1, 1)
    assert len(provider.calls[-1][1]) == 1

    with psycopg.connect(database_url) as connection:
        connection.execute(
            """UPDATE tool_embeddings SET content_hash = 'corrupt'
               WHERE tool_id = %s AND model_key = %s""",
            (ids["vector"], profile.model_key),
        )
    with repository.connection() as connection:
        hash_checked = index.vector_ranked(connection, vector(1), profile)
        wrong_model = index.vector_ranked(
            connection,
            vector(1),
            EmbeddingProfile("google_gemini", "different-model", 1536),
        )
    assert ids["vector"] not in hash_checked
    assert wrong_model == ()

    repaired = run_reindex(settings, provider=provider)
    assert repaired.report is not None and repaired.report.embedded == 1
    with psycopg.connect(database_url) as connection:
        connection.execute(
            "UPDATE tools SET revision = revision + 1 WHERE id = %s",
            (ids["vector"],),
        )
    with repository.connection() as connection:
        revision_checked = index.vector_ranked(connection, vector(1), profile)
    assert ids["vector"] not in revision_checked


def test_hybrid_retrieval_falls_back_to_keyword_on_embedding_failure(
    retrieval_context: tuple[str, dict[str, UUID]],
) -> None:
    database_url, ids = retrieval_context
    repository = CatalogRepository(database_url)
    retriever = HybridRetriever(
        EmbeddingIndex(repository),
        EmbeddingProfile("google_gemini", "gemini-embedding-2", 1536),
        FailingEmbeddingProvider(),
    )

    result = retriever.retrieve("Alpha Writer")

    assert result.tool_ids[0] == ids["alpha"]
    assert result.warnings == (SEMANTIC_RETRIEVAL_WARNING,)


def test_hybrid_retrieval_fuses_keyword_and_exact_vector_results(
    retrieval_context: tuple[str, dict[str, UUID]],
) -> None:
    database_url, ids = retrieval_context
    repository = CatalogRepository(database_url)
    profile = EmbeddingProfile("google_gemini", "gemini-embedding-2", 1536)
    provider = StubEmbeddingProvider()
    index = EmbeddingIndex(repository)
    index.reindex(provider, profile)
    retriever = HybridRetriever(index, profile, provider)

    result = retriever.retrieve("Find semantic images")

    assert result.tool_ids[0] == ids["vector"]
    assert result.warnings == ()
    assert provider.calls[-1][0] == "RETRIEVAL_QUERY"
