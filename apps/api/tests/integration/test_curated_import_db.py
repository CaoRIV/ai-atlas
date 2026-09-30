import copy
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from ai_atlas_api.curated_import import IMPORT_LOCK_KEY
from ai_atlas_api.migrations import upgrade

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[4]
TABLES = (
    "providers",
    "models",
    "categories",
    "capabilities",
    "tools",
    "tool_categories",
    "tool_models",
    "tool_capabilities",
    "tool_facts",
    "evidence",
    "tool_embeddings",
)


def uid(number: int) -> str:
    return f"60000000-0000-4000-8000-{number:012d}"


def source(number: int, clock: datetime) -> dict[str, Any]:
    return {
        "id": uid(number),
        "source_url": "https://docs.python.org/3/",
        "source_kind": "official_docs",
        "checked_at": (clock - timedelta(days=1)).isoformat(),
        "expires_at": (clock + timedelta(days=89)).isoformat(),
        "checked_by": "private-reviewer-DO-NOT-ECHO",
        "excerpt": "private-excerpt-DO-NOT-ECHO",
    }


def catalog_payload() -> dict[str, Any]:
    clock = datetime.now(UTC)
    facts = [
        {
            "id": uid(number),
            "key": key,
            "value": value,
            "verification_status": "unknown" if value is None else "verified",
            "evidence": [] if value is None else [source(100 + number, clock)],
        }
        for number, key, value in (
            (10, "api_available", True),
            (11, "capability:text_generation", True),
            (12, "model_usage:fixture-model", True),
            (13, "min_ram_gb", 8),
            (14, "pricing", None),
        )
    ]
    return {
        "schema_version": 1,
        "providers": [
            {
                "id": uid(1),
                "slug": "fixture-provider",
                "name": "Fixture provider",
                "website_url": "https://www.python.org/",
            }
        ],
        "models": [
            {
                "id": uid(4),
                "slug": "fixture-model",
                "name": "Fixture model",
                "provider_id": uid(1),
            }
        ],
        "categories": [
            {"id": uid(2), "slug": "coding-development", "name": "Coding"},
            {"id": uid(22), "slug": "learning-research", "name": "Learning"},
        ],
        "capabilities": [
            {
                "id": uid(3),
                "key": "text_generation",
                "name": "Text generation",
                "description": "Synthetic capability vocabulary.",
            }
        ],
        "tools": [
            {
                "id": uid(5),
                "slug": "fixture-tool",
                "name": "Fixture tool",
                "description": "Synthetic integration fixture; not a curated claim.",
                "official_url": "https://www.python.org/",
                "provider_id": uid(1),
                "tags": ["fixture"],
                "publication_status": "draft",
                "last_verified_at": (clock - timedelta(days=1)).isoformat(),
                "category_ids": [uid(2), uid(22)],
                "model_ids": [uid(4)],
                "capabilities": [{"capability_id": uid(3), "fact_id": uid(11)}],
                "facts": facts,
                "curation_notes": "private-note-DO-NOT-ECHO",
            }
        ],
    }


@pytest.fixture(scope="module")
def import_database() -> Iterator[str]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required for curated import integration tests.")
    database = f"ai_atlas_import_{uuid4().hex}"
    parameters = conninfo_to_dict(base_url)
    parameters["dbname"] = database
    test_url = make_conninfo(**parameters)
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    try:
        upgrade(test_url)
        yield test_url
    finally:
        with psycopg.connect(base_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))


@pytest.fixture
def import_context(import_database: str, tmp_path: Path) -> tuple[str, Path, dict[str, Any]]:
    with psycopg.connect(import_database) as connection:
        connection.execute("TRUNCATE providers, models, categories, capabilities, tools CASCADE")
        connection.execute("DROP FUNCTION IF EXISTS reject_curated_tool() CASCADE")
    return import_database, tmp_path, catalog_payload()


def write_payload(directory: Path, payload: dict[str, Any], name: str = "catalog.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def invoke(
    database_url: str,
    directory: Path,
    payload: dict[str, Any],
    *,
    command: str = "import",
    name: str = "catalog.json",
) -> subprocess.CompletedProcess[str]:
    path = write_payload(directory, payload, name)
    environment = {
        **os.environ,
        "DATABASE_URL": database_url,
        "PYTHONPATH": str(ROOT / "apps/api/src"),
        "PYTHONUTF8": "1",
    }
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_atlas_api.curated_cli",
            command,
            "--format",
            "json",
            str(path),
        ],
        cwd=directory,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )


def database_fingerprint(database_url: str) -> str:
    content = {}
    with psycopg.connect(database_url) as connection:
        for table in TABLES:
            content[table] = sorted(
                json.dumps(row[0], sort_keys=True)
                for row in connection.execute(
                    sql.SQL("SELECT to_jsonb(t) FROM {} t").format(sql.Identifier(table))
                )
            )
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def assert_redacted(result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    for marker in (
        "private-database-trigger-DO-NOT-ECHO",
        "private-reviewer-DO-NOT-ECHO",
        "private-excerpt-DO-NOT-ECHO",
        "private-note-DO-NOT-ECHO",
        "docs.python.org",
        "Traceback",
    ):
        assert marker not in output


def insert_embedding(connection: psycopg.Connection[Any]) -> None:
    vector = "[" + ",".join(["0"] * 1536) + "]"
    connection.execute(
        """INSERT INTO tool_embeddings(
               tool_id, model_key, content_hash, source_revision, embedding, embedded_at
           ) VALUES (%s, 'fixture-embedding', 'fixture-hash', 1, %s::vector, CURRENT_TIMESTAMP)""",
        (uid(5), vector),
    )


def test_initial_import_reimport_and_dry_run_are_idempotent(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, payload = import_context
    first = invoke(database_url, directory, payload)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["summary"] == {
        "added": 15,
        "updated": 0,
        "unchanged": 0,
    }
    with psycopg.connect(database_url) as connection:
        tool = connection.execute(
            "SELECT revision, updated_at, search_vector::text FROM tools WHERE id = %s",
            (uid(5),),
        ).fetchone()
        assert tool is not None
        assert tool[0] == 1
        assert "coding-development" in tool[2]
        assert "text" in tool[2] and "generation" in tool[2]
        assert connection.execute(
            "SELECT count(*) FROM evidence WHERE fact_revision = 1"
        ).fetchone() == (4,)
        initial_updated_at = tool[1]
    first_fingerprint = database_fingerprint(database_url)

    second = invoke(database_url, directory, payload)
    dry_run = invoke(database_url, directory, payload, command="dry-run")
    assert second.returncode == dry_run.returncode == 0
    assert json.loads(second.stdout)["summary"] == {
        "added": 0,
        "updated": 0,
        "unchanged": 15,
    }
    assert json.loads(dry_run.stdout)["summary"] == {
        "added": 0,
        "updated": 0,
        "unchanged": 15,
    }
    assert database_fingerprint(database_url) == first_fingerprint
    with psycopg.connect(database_url) as connection:
        assert connection.execute(
            "SELECT revision, updated_at FROM tools WHERE id = %s", (uid(5),)
        ).fetchone() == (1, initial_updated_at)
        assert connection.execute(
            "SELECT array_agg(revision ORDER BY key) FROM tool_facts WHERE tool_id = %s",
            (uid(5),),
        ).fetchone() == ([1, 1, 1, 1, 1],)
    assert_redacted(first)
    assert_redacted(second)


def test_content_change_bumps_revisions_once_preserves_history_and_reindexes(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, baseline = import_context
    assert invoke(database_url, directory, baseline).returncode == 0
    with psycopg.connect(database_url) as connection:
        insert_embedding(connection)

    payload = copy.deepcopy(baseline)
    tool = payload["tools"][0]
    tool["name"] = "Renamed import tool"
    tool["tags"] = ["changed-tag"]
    tool["category_ids"] = [uid(22)]
    api_fact = tool["facts"][0]
    api_fact["value"] = False
    api_fact["evidence"][0]["id"] = uid(210)
    changed = invoke(database_url, directory, payload)
    assert changed.returncode == 0, changed.stderr
    assert json.loads(changed.stdout)["summary"] == {
        "added": 1,
        "updated": 2,
        "unchanged": 12,
    }
    with psycopg.connect(database_url) as connection:
        tool_row = connection.execute(
            "SELECT revision, search_vector::text FROM tools WHERE id = %s", (uid(5),)
        ).fetchone()
        assert tool_row is not None and tool_row[0] == 2
        assert "renamed" in tool_row[1] and "changed-tag" in tool_row[1]
        assert "coding-development" not in tool_row[1]
        assert connection.execute(
            "SELECT category_id::text FROM tool_categories WHERE tool_id = %s", (uid(5),)
        ).fetchall() == [(uid(22),)]
        assert connection.execute(
            "SELECT value, verification_status, revision FROM tool_facts WHERE id = %s",
            (uid(10),),
        ).fetchone() == (False, "verified", 2)
        assert connection.execute(
            "SELECT id::text, fact_revision FROM evidence WHERE fact_id = %s "
            "ORDER BY fact_revision",
            (uid(10),),
        ).fetchall() == [(uid(110), 1), (uid(210), 2)]
        assert connection.execute(
            "SELECT count(*) FROM tool_embeddings WHERE tool_id = %s", (uid(5),)
        ).fetchone() == (0,)
    changed_fingerprint = database_fingerprint(database_url)
    assert invoke(database_url, directory, payload).returncode == 0
    assert database_fingerprint(database_url) == changed_fingerprint
    assert_redacted(changed)
    payload["tools"][0]["facts"][3]["evidence"].append(source(213, datetime.now(UTC)))
    additive = invoke(database_url, directory, payload)
    assert additive.returncode == 0
    assert json.loads(additive.stdout)["summary"] == {
        "added": 1,
        "updated": 0,
        "unchanged": 15,
    }
    with psycopg.connect(database_url) as connection:
        assert connection.execute(
            "SELECT revision FROM tool_facts WHERE id = %s", (uid(13),)
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT fact_revision FROM evidence WHERE id = %s", (uid(213),)
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT revision FROM tools WHERE id = %s", (uid(5),)
        ).fetchone() == (2,)
    additive_fingerprint = database_fingerprint(database_url)
    assert invoke(database_url, directory, payload).returncode == 0
    assert database_fingerprint(database_url) == additive_fingerprint
    assert_redacted(additive)


def test_verified_status_transition_requires_new_current_revision_evidence(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, payload = import_context
    payload["tools"][0]["facts"][0]["verification_status"] = "unverified"
    assert invoke(database_url, directory, payload).returncode == 0
    before = database_fingerprint(database_url)

    proposal = copy.deepcopy(payload)
    proposal["tools"][0]["facts"][0]["verification_status"] = "verified"
    rejected = invoke(database_url, directory, proposal)
    assert rejected.returncode == 2
    report = json.loads(rejected.stdout)
    assert report["changes"] == []
    assert {error["code"] for error in report["errors"]} == {
        "verified_transition_requires_new_evidence"
    }
    assert database_fingerprint(database_url) == before

    proposal["tools"][0]["facts"][0]["evidence"].append(source(210, datetime.now(UTC)))
    accepted = invoke(database_url, directory, proposal)
    assert accepted.returncode == 0
    with psycopg.connect(database_url) as connection:
        assert connection.execute(
            "SELECT verification_status, revision FROM tool_facts WHERE id = %s", (uid(10),)
        ).fetchone() == ("verified", 2)
        assert connection.execute(
            "SELECT id::text, fact_revision FROM evidence WHERE fact_id = %s "
            "ORDER BY fact_revision, id",
            (uid(10),),
        ).fetchall() == [(uid(110), 1), (uid(210), 2)]
    assert_redacted(rejected)
    assert_redacted(accepted)


def test_referenced_capability_key_and_model_slug_cannot_break_fact_namespaces(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, baseline = import_context
    assert invoke(database_url, directory, baseline).returncode == 0
    before = database_fingerprint(database_url)
    capability = copy.deepcopy(baseline["capabilities"][0])
    capability["key"] = "code_generation"
    model = copy.deepcopy(baseline["models"][0])
    model["slug"] = "renamed-model"
    patch = {
        "schema_version": 1,
        "providers": [],
        "models": [model],
        "categories": [],
        "capabilities": [capability],
        "tools": [],
    }
    result = invoke(database_url, directory, patch)
    assert result.returncode == 2
    assert {error["code"] for error in json.loads(result.stdout)["errors"]} == {
        "referenced_capability_key_is_immutable",
        "referenced_model_slug_is_immutable",
    }
    assert database_fingerprint(database_url) == before
    assert_redacted(result)


def test_taxonomy_label_change_reindexes_linked_omitted_tool(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, baseline = import_context
    assert invoke(database_url, directory, baseline).returncode == 0
    with psycopg.connect(database_url) as connection:
        insert_embedding(connection)

    category = copy.deepcopy(baseline["categories"][0])
    category["name"] = "Software engineering"
    taxonomy_patch = {
        "schema_version": 1,
        "providers": [],
        "models": [],
        "categories": [category],
        "capabilities": [],
        "tools": [],
    }
    changed = invoke(database_url, directory, taxonomy_patch)
    assert changed.returncode == 0, changed.stderr
    assert json.loads(changed.stdout)["summary"] == {
        "added": 0,
        "updated": 1,
        "unchanged": 0,
    }
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT revision, search_vector::text FROM tools WHERE id = %s", (uid(5),)
        ).fetchone()
        assert row is not None and row[0] == 2 and "software" in row[1]
        assert connection.execute(
            "SELECT count(*) FROM tool_embeddings WHERE tool_id = %s", (uid(5),)
        ).fetchone() == (0,)
    assert_redacted(changed)


def test_database_error_rolls_back_earlier_entity_writes_and_sanitizes_cli(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, payload = import_context
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """CREATE FUNCTION reject_curated_tool() RETURNS trigger LANGUAGE plpgsql AS $$
               BEGIN RAISE EXCEPTION 'private-database-trigger-DO-NOT-ECHO'; END $$"""
        )
        connection.execute(
            """CREATE TRIGGER reject_curated_tool BEFORE INSERT ON tools
               FOR EACH ROW EXECUTE FUNCTION reject_curated_tool()"""
        )
    failed = invoke(database_url, directory, payload)
    assert failed.returncode == 3
    report = json.loads(failed.stdout)
    assert report["status"] == "unavailable"
    assert report["changes"] == []
    assert report["errors"] == [{"field": "existing", "code": "CATALOG_UNAVAILABLE"}]
    with psycopg.connect(database_url) as connection:
        for table in ("providers", "models", "categories", "capabilities", "tools"):
            assert connection.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone() == (0,)
    assert_redacted(failed)


def test_import_lock_timeout_has_no_partial_write(
    import_context: tuple[str, Path, dict[str, Any]],
) -> None:
    database_url, directory, payload = import_context
    with psycopg.connect(database_url) as blocker:
        blocker.execute("SELECT pg_advisory_xact_lock(%s)", (IMPORT_LOCK_KEY,))
        result = invoke(database_url, directory, payload)
    assert result.returncode == 3
    assert json.loads(result.stdout)["errors"] == [
        {"field": "existing", "code": "CATALOG_UNAVAILABLE"}
    ]
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT count(*) FROM tools").fetchone() == (0,)
    assert_redacted(result)
