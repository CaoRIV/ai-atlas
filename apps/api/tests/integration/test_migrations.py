import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb

from ai_atlas_api.config import Settings
from ai_atlas_api.migrations import downgrade, get_status, upgrade

CORE_TABLES = (
    "providers",
    "models",
    "categories",
    "capabilities",
    "tools",
    "tool_categories",
    "tool_models",
)
FACT_TABLES = ("tool_facts", "evidence", "tool_capabilities", "tool_embeddings")
MIGRATED_TABLES = CORE_TABLES + FACT_TABLES
FRESH_VERIFIED_TRUE_QUERY = """
    SELECT EXISTS (
        SELECT 1
        FROM tool_facts AS fact
        JOIN evidence AS source
          ON source.fact_id = fact.id
         AND source.fact_revision = fact.revision
        WHERE fact.id = %s
          AND fact.verification_status = 'verified'
          AND fact.value = 'true'::jsonb
          AND source.checked_at <= CURRENT_TIMESTAMP
          AND CURRENT_TIMESTAMP < source.expires_at
    )
"""


@pytest.fixture
def migration_database_url() -> Iterator[str]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required for migration integration tests.")

    database_name = f"ai_atlas_migration_{uuid4().hex}"
    base_parameters = conninfo_to_dict(base_url)
    test_parameters = dict(base_parameters)
    test_parameters["dbname"] = database_name
    test_url = make_conninfo(**test_parameters)

    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    try:
        yield test_url
    finally:
        with psycopg.connect(base_url, autocommit=True) as connection:
            connection.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (database_name,),
            )
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
            )


@pytest.mark.integration
def test_catalog_migration_applies_rolls_back_and_reapplies_cleanly(
    migration_database_url: str,
) -> None:
    applied = upgrade(migration_database_url)

    assert [migration.version for migration in applied] == [1, 2]
    assert [(status.version, status.applied) for status in get_status(migration_database_url)] == [
        (1, True),
        (2, True),
    ]

    with psycopg.connect(migration_database_url) as connection:
        existing_tables = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            ).fetchall()
        }
        vector_enabled = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        ).fetchone()

    assert set(MIGRATED_TABLES).issubset(existing_tables)
    assert vector_enabled == (True,)

    rolled_back = downgrade(migration_database_url, target_version=0)

    assert [migration.version for migration in rolled_back] == [2, 1]
    with psycopg.connect(migration_database_url) as connection:
        remaining = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (list(MIGRATED_TABLES),),
        ).fetchall()
        history_count = connection.execute("SELECT count(*) FROM schema_migrations").fetchone()

    assert remaining == []
    assert history_count == (0,)
    assert [migration.version for migration in upgrade(migration_database_url)] == [1, 2]


@pytest.mark.integration
def test_fact_freshness_preserves_history_and_unknown_fails_closed(
    migration_database_url: str,
) -> None:
    upgrade(migration_database_url)
    tool_id = uuid4()
    verified_fact_id = uuid4()
    unknown_fact_id = uuid4()
    expired_fact_id = uuid4()
    now = datetime.now(UTC)

    with psycopg.connect(migration_database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO tools (id, slug, name, description, official_url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                tool_id,
                "facts-fixture",
                "Facts fixture",
                "Synthetic integration fixture.",
                "https://example.com/facts",
            ),
        )
        connection.execute(
            """
            INSERT INTO tool_facts (
                id, tool_id, key, value, verification_status, revision
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (verified_fact_id, tool_id, "api_available", Jsonb(True), "verified", 1),
        )
        connection.execute(
            """
            INSERT INTO tool_facts (
                id, tool_id, key, value, verification_status, revision
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (unknown_fact_id, tool_id, "offline_supported", Jsonb(None), "unknown", 1),
        )
        connection.execute(
            """
            INSERT INTO tool_facts (
                id, tool_id, key, value, verification_status, revision
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (expired_fact_id, tool_id, "open_source", Jsonb(True), "verified", 1),
        )
        connection.execute(
            """
            INSERT INTO evidence (
                id, fact_id, fact_revision, source_url, source_kind,
                checked_at, expires_at, checked_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                verified_fact_id,
                1,
                "https://example.com/docs/api",
                "official_docs",
                now - timedelta(days=1),
                now + timedelta(days=89),
                "integration-test",
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence (
                id, fact_id, fact_revision, source_url, source_kind,
                checked_at, expires_at, checked_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                expired_fact_id,
                1,
                "https://example.com/docs/license",
                "official_docs",
                now - timedelta(days=2),
                now - timedelta(days=1),
                "integration-test",
            ),
        )

        assert connection.execute(FRESH_VERIFIED_TRUE_QUERY, (verified_fact_id,)).fetchone() == (
            True,
        )
        assert connection.execute(FRESH_VERIFIED_TRUE_QUERY, (unknown_fact_id,)).fetchone() == (
            False,
        )
        assert connection.execute(FRESH_VERIFIED_TRUE_QUERY, (expired_fact_id,)).fetchone() == (
            False,
        )

        connection.execute(
            """
            UPDATE tool_facts
            SET revision = 2, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (verified_fact_id,),
        )
        assert connection.execute(FRESH_VERIFIED_TRUE_QUERY, (verified_fact_id,)).fetchone() == (
            False,
        )
        assert connection.execute(
            "SELECT count(*) FROM evidence WHERE fact_id = %s", (verified_fact_id,)
        ).fetchone() == (1,)

        connection.execute(
            """
            INSERT INTO evidence (
                id, fact_id, fact_revision, source_url, source_kind,
                checked_at, expires_at, checked_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                verified_fact_id,
                2,
                "https://example.com/docs/api-v2",
                "official_docs",
                now,
                now + timedelta(days=90),
                "integration-test",
            ),
        )
        assert connection.execute(FRESH_VERIFIED_TRUE_QUERY, (verified_fact_id,)).fetchone() == (
            True,
        )


@pytest.mark.integration
def test_fact_constraints_and_capability_require_the_same_tool(
    migration_database_url: str,
) -> None:
    upgrade(migration_database_url)
    first_tool_id = uuid4()
    second_tool_id = uuid4()
    capability_id = uuid4()
    fact_id = uuid4()
    now = datetime.now(UTC)

    with psycopg.connect(migration_database_url, autocommit=True) as connection:
        for tool_id, slug in ((first_tool_id, "first-tool"), (second_tool_id, "second-tool")):
            connection.execute(
                """
                INSERT INTO tools (id, slug, name, description, official_url)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (tool_id, slug, slug, "Synthetic fixture.", f"https://example.com/{slug}"),
            )
        connection.execute(
            """
            INSERT INTO capabilities (id, key, name, description)
            VALUES (%s, %s, %s, %s)
            """,
            (capability_id, "text_generation", "Text generation", "Generates text."),
        )
        connection.execute(
            """
            INSERT INTO tool_facts (
                id, tool_id, key, value, verification_status, revision
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                fact_id,
                first_tool_id,
                "capability:text_generation",
                Jsonb(True),
                "verified",
                1,
            ),
        )
        connection.execute(
            """
            INSERT INTO tool_capabilities (tool_id, capability_id, fact_id)
            VALUES (%s, %s, %s)
            """,
            (first_tool_id, capability_id, fact_id),
        )

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            connection.execute(
                """
                INSERT INTO tool_capabilities (tool_id, capability_id, fact_id)
                VALUES (%s, %s, %s)
                """,
                (second_tool_id, capability_id, fact_id),
            )

        with pytest.raises(psycopg.errors.UniqueViolation):
            connection.execute(
                """
                INSERT INTO tool_facts (
                    id, tool_id, key, value, verification_status, revision
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    first_tool_id,
                    "capability:text_generation",
                    Jsonb(True),
                    "verified",
                    1,
                ),
            )

        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                """
                INSERT INTO tool_facts (
                    id, tool_id, key, value, verification_status, revision
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (uuid4(), first_tool_id, "invalid", Jsonb(True), "trusted", 1),
            )

        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                """
                INSERT INTO evidence (
                    id, fact_id, fact_revision, source_url, source_kind,
                    checked_at, expires_at, checked_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    fact_id,
                    1,
                    "https://example.com/docs",
                    "official_docs",
                    now,
                    now,
                    "integration-test",
                ),
            )


@pytest.mark.integration
def test_embedding_dimension_matches_runtime_configuration(
    migration_database_url: str,
) -> None:
    upgrade(migration_database_url)
    settings = Settings(_env_file=None)
    tool_id = uuid4()
    configured_vector = "[" + ",".join("0" for _ in range(settings.embedding_dim)) + "]"

    with psycopg.connect(migration_database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO tools (id, slug, name, description, official_url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                tool_id,
                "embedding-fixture",
                "Embedding fixture",
                "Synthetic integration fixture.",
                "https://example.com/embedding",
            ),
        )
        connection.execute(
            """
            INSERT INTO tool_embeddings (
                tool_id, model_key, content_hash, source_revision, embedding, embedded_at
            ) VALUES (%s, %s, %s, %s, %s::vector, %s)
            """,
            (
                tool_id,
                settings.embedding_model,
                "sha256:configured",
                1,
                configured_vector,
                datetime.now(UTC),
            ),
        )
        dimensions = connection.execute(
            "SELECT vector_dims(embedding) FROM tool_embeddings WHERE tool_id = %s",
            (tool_id,),
        ).fetchone()

        assert dimensions == (settings.embedding_dim,)

        with pytest.raises(psycopg.errors.DataException):
            connection.execute(
                """
                INSERT INTO tool_embeddings (
                    tool_id, model_key, content_hash, source_revision, embedding, embedded_at
                ) VALUES (%s, %s, %s, %s, %s::vector, %s)
                """,
                (
                    tool_id,
                    "wrong-dimension",
                    "sha256:wrong",
                    1,
                    "[0,0,0]",
                    datetime.now(UTC),
                ),
            )


@pytest.mark.integration
def test_catalog_constraints_and_delete_rules(migration_database_url: str) -> None:
    upgrade(migration_database_url)
    provider_id = uuid4()
    model_id = uuid4()
    category_id = uuid4()
    capability_id = uuid4()
    tool_id = uuid4()

    with psycopg.connect(migration_database_url, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO providers (id, name, slug) VALUES (%s, %s, %s)",
            (provider_id, "Example Provider", "example-provider"),
        )
        connection.execute(
            "INSERT INTO models (id, provider_id, name, slug) VALUES (%s, %s, %s, %s)",
            (model_id, provider_id, "Example Model", "example-model"),
        )
        connection.execute(
            "INSERT INTO categories (id, name, slug) VALUES (%s, %s, %s)",
            (category_id, "Developer Tools", "developer-tools"),
        )
        connection.execute(
            """
            INSERT INTO capabilities (id, key, name, description)
            VALUES (%s, %s, %s, %s)
            """,
            (capability_id, "text_generation", "Text generation", "Generates text."),
        )
        connection.execute(
            """
            INSERT INTO tools (
                id,
                slug,
                name,
                description,
                official_url,
                provider_id,
                tags,
                publication_status,
                revision
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tool_id,
                "example-tool",
                "Example Tool",
                "Synthetic integration fixture.",
                "https://example.com/tool",
                provider_id,
                ["developer"],
                "published",
                1,
            ),
        )
        connection.execute(
            "INSERT INTO tool_categories (tool_id, category_id) VALUES (%s, %s)",
            (tool_id, category_id),
        )
        connection.execute(
            "INSERT INTO tool_models (tool_id, model_id) VALUES (%s, %s)",
            (tool_id, model_id),
        )

        with pytest.raises(psycopg.errors.UniqueViolation):
            connection.execute(
                "INSERT INTO providers (id, name, slug) VALUES (%s, %s, %s)",
                (uuid4(), "Duplicate", "example-provider"),
            )

        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                """
                INSERT INTO tools (
                    id, slug, name, description, official_url, publication_status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    "invalid-status",
                    "Invalid Status",
                    "Synthetic integration fixture.",
                    "https://example.com/invalid",
                    "hidden",
                ),
            )

        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                """
                INSERT INTO tools (
                    id, slug, name, description, official_url, revision
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    "invalid-revision",
                    "Invalid Revision",
                    "Synthetic integration fixture.",
                    "https://example.com/revision",
                    0,
                ),
            )

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            connection.execute(
                "INSERT INTO tool_categories (tool_id, category_id) VALUES (%s, %s)",
                (tool_id, uuid4()),
            )

        with pytest.raises(psycopg.errors.UniqueViolation):
            connection.execute(
                "INSERT INTO tool_models (tool_id, model_id) VALUES (%s, %s)",
                (tool_id, model_id),
            )

        connection.execute("DELETE FROM providers WHERE id = %s", (provider_id,))
        model_provider = connection.execute(
            "SELECT provider_id FROM models WHERE id = %s", (model_id,)
        ).fetchone()
        tool_provider = connection.execute(
            "SELECT provider_id FROM tools WHERE id = %s", (tool_id,)
        ).fetchone()

        assert model_provider == (None,)
        assert tool_provider == (None,)

        connection.execute("DELETE FROM tools WHERE id = %s", (tool_id,))
        category_links = connection.execute(
            "SELECT count(*) FROM tool_categories WHERE tool_id = %s", (tool_id,)
        ).fetchone()
        model_links = connection.execute(
            "SELECT count(*) FROM tool_models WHERE tool_id = %s", (tool_id,)
        ).fetchone()

    assert category_links == (0,)
    assert model_links == (0,)
