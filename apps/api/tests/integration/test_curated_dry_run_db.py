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
from psycopg.types.json import Jsonb

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
    return f"50000000-0000-4000-8000-{number:012d}"


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


def baseline_payload() -> dict[str, Any]:
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
            {"id": uid(4), "slug": "fixture-model", "name": "Fixture model", "provider_id": uid(1)}
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
def dry_run_database() -> Iterator[tuple[str, str, dict[str, Any]]]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required for dry-run integration tests.")
    database = f"ai_atlas_dry_run_{uuid4().hex}"
    reader = f"ai_atlas_reader_{uuid4().hex}"
    password = uuid4().hex
    parameters = conninfo_to_dict(base_url)
    parameters["dbname"] = database
    test_url = make_conninfo(**parameters)
    created_database = False
    created_role = False
    with psycopg.connect(base_url, autocommit=True) as connection:
        try:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
            created_database = True
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(reader),
                    sql.Literal(password),
                )
            )
            created_role = True
            upgrade(test_url)
            payload = baseline_payload()
            with psycopg.connect(test_url) as seed:
                provider = payload["providers"][0]
                seed.execute(
                    "INSERT INTO providers(id, slug, name, website_url) VALUES (%s,%s,%s,%s)",
                    tuple(provider[field] for field in ("id", "slug", "name", "website_url")),
                )
                model = payload["models"][0]
                seed.execute(
                    "INSERT INTO models(id, slug, name, provider_id) VALUES (%s,%s,%s,%s)",
                    tuple(model[field] for field in ("id", "slug", "name", "provider_id")),
                )
                for category in payload["categories"]:
                    seed.execute(
                        "INSERT INTO categories(id, slug, name) VALUES (%s,%s,%s)",
                        tuple(category[field] for field in ("id", "slug", "name")),
                    )
                capability = payload["capabilities"][0]
                seed.execute(
                    "INSERT INTO capabilities(id, key, name, description) VALUES (%s,%s,%s,%s)",
                    tuple(capability[field] for field in ("id", "key", "name", "description")),
                )
                tool = payload["tools"][0]
                seed.execute(
                    """INSERT INTO tools(id, slug, name, description, official_url, provider_id,
                                        tags, publication_status, last_verified_at, revision)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,7)""",
                    tuple(
                        tool[field]
                        for field in (
                            "id",
                            "slug",
                            "name",
                            "description",
                            "official_url",
                            "provider_id",
                            "tags",
                            "publication_status",
                            "last_verified_at",
                        )
                    ),
                )
                for category_id in tool["category_ids"]:
                    seed.execute(
                        "INSERT INTO tool_categories(tool_id, category_id) VALUES (%s,%s)",
                        (tool["id"], category_id),
                    )
                for model_id in tool["model_ids"]:
                    seed.execute(
                        "INSERT INTO tool_models(tool_id, model_id) VALUES (%s,%s)",
                        (tool["id"], model_id),
                    )
                for fact in tool["facts"]:
                    seed.execute(
                        """INSERT INTO tool_facts(id, tool_id, key, value,
                                                  verification_status, revision)
                                    VALUES (%s,%s,%s,%s,%s,2)""",
                        (
                            fact["id"],
                            tool["id"],
                            fact["key"],
                            Jsonb(fact["value"]),
                            fact["verification_status"],
                        ),
                    )
                    for evidence in fact["evidence"]:
                        seed.execute(
                            """INSERT INTO evidence(id, fact_id, fact_revision, source_url,
                                                    source_kind, checked_at, expires_at,
                                                    checked_by, excerpt)
                                        VALUES (%s,%s,2,%s,%s,%s,%s,%s,%s)""",
                            (
                                evidence["id"],
                                fact["id"],
                                *(
                                    evidence[field]
                                    for field in (
                                        "source_url",
                                        "source_kind",
                                        "checked_at",
                                        "expires_at",
                                        "checked_by",
                                        "excerpt",
                                    )
                                ),
                            ),
                        )
                historic = {**tool["facts"][0]["evidence"][0], "id": uid(100)}
                seed.execute(
                    """INSERT INTO evidence(id, fact_id, fact_revision, source_url, source_kind,
                                                     checked_at, expires_at, checked_by, excerpt)
                                VALUES (%s,%s,1,%s,%s,%s,%s,%s,%s)""",
                    (
                        historic["id"],
                        uid(10),
                        *(
                            historic[field]
                            for field in (
                                "source_url",
                                "source_kind",
                                "checked_at",
                                "expires_at",
                                "checked_by",
                                "excerpt",
                            )
                        ),
                    ),
                )
                seed.execute(
                    "INSERT INTO tool_capabilities(tool_id, capability_id, fact_id) "
                    "VALUES (%s,%s,%s)",
                    (uid(5), uid(3), uid(11)),
                )
                seed.execute(
                    sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                        sql.Identifier(database),
                        sql.Identifier(reader),
                    )
                )
                seed.execute(
                    sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(reader))
                )
                seed.execute(
                    sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(
                        sql.Identifier(reader)
                    )
                )
            read_parameters = {**parameters, "user": reader, "password": password}
            yield test_url, make_conninfo(**read_parameters), payload
        finally:
            if created_database:
                connection.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (database,),
                )
                connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            if created_role:
                connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(reader)))


def fingerprint(database_url: str) -> str:
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


def invoke(
    database_url: str, directory: Path, paths: list[Path], *, format: str = "json"
) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "DATABASE_URL": database_url,
        "PYTHONPATH": str(ROOT / "apps/api/src"),
        "LLM_PROVIDER": "unrelated-invalid-provider",
        "PYTHONUTF8": "1",
    }
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_atlas_api.curated_cli",
            "dry-run",
            "--format",
            format,
            *map(str, paths),
        ],
        cwd=directory,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )


def write_payload(tmp_path: Path, payload: dict[str, Any], name: str = "curated.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def assert_redacted(result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    for marker in (
        "private-password-DO-NOT-ECHO",
        "private-reviewer-DO-NOT-ECHO",
        "private-excerpt-DO-NOT-ECHO",
        "private-note-DO-NOT-ECHO",
        "docs.python.org",
    ):
        assert marker not in output


def test_unchanged_reordered_relations_numbers_notes_and_history_are_not_changes(
    dry_run_database: tuple[str, str, dict[str, Any]],
    tmp_path: Path,
) -> None:
    root_url, reader_url, baseline = dry_run_database
    before = fingerprint(root_url)
    payload = copy.deepcopy(baseline)
    tool = payload["tools"][0]
    tool["category_ids"].reverse()
    tool["facts"][3]["value"] = 8.0
    tool["facts"][4]["curation_notes"] = "editorial only"
    tool["curation_notes"] = "editorial only"
    result = invoke(reader_url, tmp_path, [write_payload(tmp_path, payload)])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["summary"] == {"added": 0, "updated": 0, "unchanged": 15}
    assert all(
        row["status"] == "unchanged" and row["changed_fields"] == [] for row in report["changes"]
    )
    assert uid(100) not in {row["id"] for row in report["changes"]}
    assert report["errors"] == []
    assert fingerprint(root_url) == before
    assert_redacted(result)


def test_mixed_add_update_diff_reports_metadata_relations_facts_and_new_evidence_without_writes(
    dry_run_database: tuple[str, str, dict[str, Any]],
    tmp_path: Path,
) -> None:
    root_url, reader_url, baseline = dry_run_database
    before = fingerprint(root_url)
    payload = copy.deepcopy(baseline)
    payload["providers"][0]["website_url"] = "https://www.python.org/about/"
    payload["capabilities"][0]["description"] = "Changed vocabulary description."
    payload["categories"].append(
        {"id": uid(23), "slug": "business-productivity", "name": "Business"}
    )
    tool = payload["tools"][0]
    tool["tags"] = ["changed"]
    tool["category_ids"] = [uid(23), uid(22)]
    tool["facts"][0]["value"] = False
    tool["facts"][0]["evidence"][0]["id"] = uid(210)
    path = write_payload(tmp_path, payload)
    result = invoke(reader_url, tmp_path, [path])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["summary"] == {"added": 2, "updated": 4, "unchanged": 10}
    by_id = {row["id"]: row for row in report["changes"]}
    assert by_id[uid(1)]["changed_fields"] == ["website_url"]
    assert by_id[uid(3)]["changed_fields"] == ["description"]
    assert by_id[uid(5)]["changed_fields"] == ["category_ids", "tags"]
    assert by_id[uid(10)]["changed_fields"] == ["value"]
    assert by_id[uid(10)]["parent_id"] == uid(5)
    assert by_id[uid(210)]["status"] == "added"
    assert by_id[uid(210)]["parent_id"] == uid(10)
    text = invoke(reader_url, tmp_path, [path], format="text")
    assert text.returncode == 0
    assert "added=2 updated=4 unchanged=10" in text.stdout
    assert f"UPDATED facts {uid(10)}" in text.stdout
    assert f"ADDED evidence {uid(210)}" in text.stdout
    assert fingerprint(root_url) == before
    assert_redacted(result)
    assert_redacted(text)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("type", "bool_type"),
        ("publication", "published_requires_verified_identity"),
        ("fk", "unknown_reference"),
        ("credentials", "source_requires_public_https_hostname_without_credentials"),
        ("historical", "evidence_cannot_certify_new_value_or_old_revision"),
        ("changed_value", "evidence_cannot_certify_new_value_or_old_revision"),
        ("false_relation", "relation_requires_verified_true_fresh_fact"),
        ("future", "checked_at_in_future"),
    ],
)
def test_invalid_batch_has_no_diff_no_writes_and_sanitized_errors(
    dry_run_database: tuple[str, str, dict[str, Any]],
    tmp_path: Path,
    mutation: str,
    code: str,
) -> None:
    root_url, reader_url, baseline = dry_run_database
    before = fingerprint(root_url)
    payload = copy.deepcopy(baseline)
    tool = payload["tools"][0]
    fact = tool["facts"][0]
    if mutation == "type":
        fact["value"] = "false"
    elif mutation == "publication":
        tool["publication_status"] = "published"
    elif mutation == "fk":
        tool["category_ids"] = [uid(999)]
    elif mutation == "credentials":
        fact["evidence"][0].update(
            id=uid(210), source_url="https://user:private-password-DO-NOT-ECHO@docs.python.org/3/"
        )
    elif mutation == "historical":
        fact["evidence"][0]["id"] = uid(100)
    elif mutation == "changed_value":
        fact["value"] = False
    elif mutation == "false_relation":
        tool["facts"][1]["value"] = False
        tool["facts"][1]["evidence"][0]["id"] = uid(211)
    else:
        fact["evidence"][0].update(
            id=uid(210), checked_at=(datetime.now(UTC) + timedelta(days=1)).isoformat()
        )
    result = invoke(reader_url, tmp_path, [write_payload(tmp_path, payload)])
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report["status"] == "invalid"
    assert code in {issue["code"] for issue in report["errors"]}
    assert report["changes"] == []
    assert report["summary"] == {"added": 0, "updated": 0, "unchanged": 0}
    assert fingerprint(root_url) == before
    assert_redacted(result)


def test_new_cross_file_references_resolve_in_either_order_with_deterministic_diff(
    dry_run_database: tuple[str, str, dict[str, Any]],
    tmp_path: Path,
) -> None:
    root_url, reader_url, baseline = dry_run_database
    before = fingerprint(root_url)
    payload = copy.deepcopy(baseline)
    payload["models"].append(
        {"id": uid(42), "slug": "fixture-second", "name": "Second model", "provider_id": uid(1)}
    )
    payload["capabilities"].append(
        {
            "id": uid(43),
            "key": "code_generation",
            "name": "Code generation",
            "description": "Synthetic vocabulary.",
        }
    )
    tool = payload["tools"][0]
    tool["model_ids"].append(uid(42))
    tool["capabilities"].append({"capability_id": uid(43), "fact_id": uid(33)})
    for number, key in ((32, "model_usage:fixture-second"), (33, "capability:code_generation")):
        tool["facts"].append(
            {
                "id": uid(number),
                "key": key,
                "value": True,
                "verification_status": "verified",
                "evidence": [source(200 + number, datetime.now(UTC))],
            }
        )
    definitions = {**payload, "tools": []}
    tools = {
        "schema_version": 1,
        "providers": [],
        "models": [],
        "categories": [],
        "capabilities": [],
        "tools": [tool],
    }
    paths = [
        write_payload(tmp_path, tools, "tools.json"),
        write_payload(tmp_path, definitions, "definitions.json"),
    ]
    first = invoke(reader_url, tmp_path, paths)
    second = invoke(reader_url, tmp_path, paths[::-1])
    assert first.returncode == second.returncode == 0
    first_report = json.loads(first.stdout)
    second_report = json.loads(second.stdout)
    assert first_report["summary"] == {"added": 6, "updated": 1, "unchanged": 14}
    assert first_report["changes"] == second_report["changes"]
    assert fingerprint(root_url) == before
    assert_redacted(first)
    assert_redacted(second)


@pytest.mark.parametrize(
    "mutation,entity,identifier,fields",
    [
        ("model_provider", "models", 4, ["provider_id"]),
        ("official_url", "tools", 5, ["official_url"]),
        ("review_date", "tools", 5, ["last_verified_at"]),
        ("fact_status", "facts", 10, ["verification_status"]),
        ("relations", "tools", 5, ["capabilities", "category_ids", "model_ids"]),
    ],
)
def test_non_label_fields_and_relation_removal_are_meaningful_updates(
    dry_run_database: tuple[str, str, dict[str, Any]],
    tmp_path: Path,
    mutation: str,
    entity: str,
    identifier: int,
    fields: list[str],
) -> None:
    root_url, reader_url, baseline = dry_run_database
    before = fingerprint(root_url)
    payload = copy.deepcopy(baseline)
    tool = payload["tools"][0]
    if mutation == "model_provider":
        payload["models"][0]["provider_id"] = None
    elif mutation == "official_url":
        tool["official_url"] = "https://www.python.org/about/"
    elif mutation == "review_date":
        tool["last_verified_at"] = (
            datetime.fromisoformat(tool["last_verified_at"]) + timedelta(hours=1)
        ).isoformat()
    elif mutation == "fact_status":
        tool["facts"][0]["verification_status"] = "unverified"
    else:
        tool.update(category_ids=[], model_ids=[], capabilities=[])
    result = invoke(reader_url, tmp_path, [write_payload(tmp_path, payload)])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["summary"] == {"added": 0, "updated": 1, "unchanged": 14}
    updated = [row for row in report["changes"] if row["status"] == "updated"]
    assert [(row["entity"], row["id"], row["changed_fields"]) for row in updated] == [
        (entity, uid(identifier), fields)
    ]
    assert fingerprint(root_url) == before
    assert_redacted(result)
