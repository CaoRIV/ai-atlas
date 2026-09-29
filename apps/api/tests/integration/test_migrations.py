import os
from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from ai_atlas_api.migrations import downgrade, get_status, upgrade

CATALOG_TABLES = (
    "providers",
    "models",
    "categories",
    "capabilities",
    "tools",
    "tool_categories",
    "tool_models",
)


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

    assert [migration.version for migration in applied] == [1]
    assert [(status.version, status.applied) for status in get_status(migration_database_url)] == [
        (1, True)
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

    assert set(CATALOG_TABLES).issubset(existing_tables)
    assert vector_enabled == (True,)

    rolled_back = downgrade(migration_database_url, target_version=0)

    assert [migration.version for migration in rolled_back] == [1]
    with psycopg.connect(migration_database_url) as connection:
        remaining = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            """,
            (list(CATALOG_TABLES),),
        ).fetchall()
        history_count = connection.execute("SELECT count(*) FROM schema_migrations").fetchone()

    assert remaining == []
    assert history_count == (0,)
    assert [migration.version for migration in upgrade(migration_database_url)] == [1]


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
