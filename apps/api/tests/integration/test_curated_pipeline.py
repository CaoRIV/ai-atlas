"""Real curated files, CLI subprocesses, temporary PostgreSQL and live HTTP.

Uses real freshness clocks: expired curated evidence must be reviewed by a curator.
Never fetches sources, refreshes timestamps or calls an AI provider.
"""

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from ai_atlas_api.migrations import upgrade

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[4]
TAXONOMY = ROOT / "data/curated/taxonomy.json"
TOOLS = ROOT / "data/curated/tools.json"
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
COUNTS = {
    "providers": 14,
    "models": 0,
    "categories": 8,
    "capabilities": 15,
    "tools": 15,
    "tool_facts": 120,
    "evidence": 30,
    "tool_embeddings": 0,
}


@pytest.fixture
def pipeline_database() -> Iterator[str]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required; the test creates a separate temporary database.")
    name = f"ai_atlas_pipeline_{uuid4().hex}"
    parameters = conninfo_to_dict(base_url)
    parameters["dbname"] = name
    test_url = make_conninfo(**parameters)
    with psycopg.connect(base_url, autocommit=True, connect_timeout=3) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        upgrade(test_url)
        yield test_url
    finally:
        with psycopg.connect(base_url, autocommit=True, connect_timeout=3) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (name,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def fingerprint(database_url: str) -> str:
    """Includes every column, timestamp, revision, join and evidence row."""
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


def environment(database_url: str) -> dict[str, str]:
    return {
        **os.environ,
        "DATABASE_URL": database_url,
        "PYTHONPATH": str(ROOT / "apps/api/src"),
        "PYTHONUTF8": "1",
        "RUN_LIVE_AI_TESTS": "0",
        "GEMINI_API_KEY": "",
    }


def cli(database_url: str, action: str, *paths: Path, exit_code: int = 0) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_atlas_api.curated_cli",
            action,
            "--format",
            "json",
            *(str(path) for path in (paths or (TAXONOMY, TOOLS))),
        ],
        cwd=ROOT,
        env=environment(database_url),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    report = json.loads(result.stdout)
    if exit_code == 0:
        assert report["status"] == "valid" and report["errors"] == []
    else:
        assert report["changes"] == [] and report["errors"]
        assert report["summary"] == {"added": 0, "updated": 0, "unchanged": 0}
    return report


@pytest.fixture
def live_api(pipeline_database: str, tmp_path: Path) -> Iterator[httpx.Client]:
    # Bind an ephemeral loopback port; startup fails explicitly if another process wins it.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with (tmp_path / "uvicorn.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "ai_atlas_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            cwd=ROOT,
            env=environment(pipeline_database),
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False
            ) as client:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    assert process.poll() is None, "Uvicorn exited before readiness."
                    try:
                        if client.get("/health/ready").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("Uvicorn did not become ready within 30 seconds.")
                yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def get(client: httpx.Client, path: str, status: int = 200, **params: Any) -> dict[str, Any]:
    response = client.get(path, params=params)
    assert response.status_code == status, response.text
    body = response.json()
    assert body["request_id"] == response.headers["X-Request-ID"]
    return body


def test_curated_seed_cli_database_http_end_to_end(
    pipeline_database: str,
    live_api: httpx.Client,
) -> None:
    seed = json.loads(TOOLS.read_bytes())
    taxonomy = json.loads(TAXONOMY.read_bytes())
    before = fingerprint(pipeline_database)
    assert cli(pipeline_database, "dry-run")["summary"] == {
        "added": 202,
        "updated": 0,
        "unchanged": 0,
    }
    assert fingerprint(pipeline_database) == before
    assert get(live_api, "/api/v1/tools")["data"] == []
    print("dry-run: added=202 updated=0 unchanged=0; database unchanged")

    assert cli(pipeline_database, "import")["summary"] == {
        "added": 202,
        "updated": 0,
        "unchanged": 0,
    }
    with psycopg.connect(pipeline_database) as connection:
        counts = {
            table: connection.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            ).fetchone()[0]
            for table in COUNTS
        }
        assert counts == COUNTS
        assert connection.execute(
            "SELECT count(*) FROM tools WHERE publication_status = 'published'"
        ).fetchone() == (15,)
        assert connection.execute(
            "SELECT count(*) FROM tool_facts WHERE verification_status = 'unknown' "
            "AND value = 'null'::jsonb"
        ).fetchone() == (90,)
        assert connection.execute(
            "SELECT count(DISTINCT capability_id) FROM tool_capabilities"
        ).fetchone() == (10,)
    print("import counts: " + json.dumps(counts, sort_keys=True))
    imported = fingerprint(pipeline_database)
    for action in ("import", "dry-run"):
        assert cli(pipeline_database, action)["summary"] == {
            "added": 0,
            "updated": 0,
            "unchanged": 202,
        }
        assert fingerprint(pipeline_database) == imported
    print("re-import: added=0 updated=0 unchanged=202; exact catalog fingerprint unchanged")

    categories = get(live_api, "/api/v1/categories")["data"]
    assert {item["id"] for item in categories} == {item["id"] for item in taxonomy["categories"]}
    expected_ids = {tool["id"] for tool in seed["tools"]}
    listed = []
    for page in range(1, 4):
        result = get(live_api, "/api/v1/tools", page=page, page_size=5)
        assert result["pagination"] == {"page": page, "page_size": 5, "total": 15}
        assert len(result["data"]) == 5
        listed.extend(result["data"])
    assert len({item["id"] for item in listed}) == 15
    assert {item["id"] for item in listed} == expected_ids
    assert [item["name"].lower() for item in listed] == sorted(
        tool["name"].lower() for tool in seed["tools"]
    )
    assert get(live_api, "/api/v1/tools", page=4, page_size=5)["data"] == []
    assert get(live_api, "/api/v1/tools", q="no-such-tool-0056")["data"] == []
    chatgpt = next(tool for tool in seed["tools"] if tool["slug"] == "chatgpt")
    assert get(live_api, "/api/v1/tools", q="ChatGPT")["data"][0]["id"] == chatgpt["id"]
    for category in taxonomy["categories"]:
        result = get(live_api, "/api/v1/tools", category=category["slug"], pricing_model="unknown")
        assert {item["id"] for item in result["data"]} == {
            tool["id"] for tool in seed["tools"] if category["id"] in tool["category_ids"]
        }
    for key in ("api_available", "open_source"):
        for value in ("true", "false"):
            assert get(live_api, "/api/v1/tools", **{key: value})["pagination"]["total"] == 0
    for params in ({"pricing_model": "free"}, {"platform": "web"}):
        assert get(live_api, "/api/v1/tools", **params)["data"] == []
    for params in ({"category": "not-a-category"}, {"page": 0}, {"unsupported": "true"}):
        assert (
            get(live_api, "/api/v1/tools", status=422, **params)["error"]["code"]
            == "VALIDATION_ERROR"
        )

    for tool in seed["tools"]:
        detail = get(live_api, f"/api/v1/tools/{tool['id']}")["data"]
        assert detail["official_url"] == tool["official_url"]
        assert datetime.fromisoformat(detail["last_verified_at"]) == datetime.fromisoformat(
            tool["last_verified_at"]
        )
        assert detail["pricing"] == {"model": "unknown", "verification_status": "unknown"}
        assert detail["revision"] == 1 and detail["models"] == []
        facts = {fact["key"]: fact for fact in detail["facts"]}
        sources = {source["id"]: source for source in detail["evidence"]}
        expected_sources = {source["id"] for fact in tool["facts"] for source in fact["evidence"]}
        assert set(sources) == expected_sources
        for fact in tool["facts"]:
            actual = facts[fact["key"]]
            assert actual["value"] == fact["value"]
            assert actual["verification_status"] == fact["verification_status"]
            assert set(actual["evidence_ids"]) == {source["id"] for source in fact["evidence"]}
            if fact["value"] is None:
                assert "fact_unknown:" + fact["key"] in detail["warnings"]
            for source in fact["evidence"]:
                actual_source = sources[source["id"]]
                assert actual_source["source_url"] == source["source_url"]
                assert actual_source["fact_key"] == fact["key"]
                for field in ("checked_at", "expires_at"):
                    assert datetime.fromisoformat(actual_source[field]) == datetime.fromisoformat(
                        source[field]
                    )
                assert "checked_by" not in actual_source and "excerpt" not in actual_source
        assert len(detail["capabilities"]) == len(tool["capabilities"])

    # Synthetic records exist only in this disposable DB and are never published.
    sentinels = []
    with psycopg.connect(pipeline_database) as connection:
        for state in ("draft", "archived"):
            identifier = uuid4()
            sentinels.append(identifier)
            connection.execute(
                "INSERT INTO tools (id, slug, name, description, official_url, publication_status) "
                "VALUES (%s, %s, 'Synthetic sentinel', 'Fixture only', "
                "'https://example.invalid', %s)",
                (identifier, f"synthetic-{state}", state),
            )
    assert {item["id"] for item in get(live_api, "/api/v1/tools")["data"]} == expected_ids
    assert get(live_api, "/api/v1/tools", q="Synthetic sentinel")["data"] == []
    for identifier in sentinels:
        get(live_api, f"/api/v1/tools/{identifier}", status=404)
    print(
        "HTTP: categories=8; pages=3x5; search/filters/empty/422 pass; "
        "details=15; provenance/unknown pass; draft/archived hidden"
    )


@pytest.mark.parametrize("populated", [False, True], ids=["clean", "seeded"])
@pytest.mark.parametrize("defect", ["fk", "source", "fact_type"])
def test_invalid_batch_leaves_no_partial_records(
    pipeline_database: str,
    tmp_path: Path,
    populated: bool,
    defect: str,
) -> None:
    if populated:
        cli(pipeline_database, "import")
    before = fingerprint(pipeline_database)
    payload = copy.deepcopy(json.loads(TOOLS.read_bytes()))
    # Valid earlier work must not survive a later invalid record.
    payload["providers"][0]["name"] += " pending change"
    tool = payload["tools"][-1]
    if defect == "fk":
        tool["category_ids"].append(str(uuid4()))
    elif defect == "source":
        tool["facts"][0]["evidence"][0]["source_url"] = "https://localhost/private"
    else:
        fact = next(fact for fact in tool["facts"] if fact["key"] == "api_available")
        fact["value"] = "false"
    bad_path = tmp_path / "invalid.json"
    bad_path.write_text(json.dumps(payload), encoding="utf-8")
    report = cli(pipeline_database, "import", TAXONOMY, bad_path, exit_code=2)
    assert report["status"] == "invalid"
    if defect == "fk":
        assert any(error["code"] == "unknown_reference" for error in report["errors"])
    elif defect == "source":
        assert any(
            error["code"] == "source_requires_public_https_hostname_without_credentials"
            for error in report["errors"]
        )
    else:
        assert any(error["code"] == "bool_type" for error in report["errors"])
    assert fingerprint(pipeline_database) == before
    print(f"invalid {defect} ({'seeded' if populated else 'clean'}): exit=2; catalog unchanged")


@pytest.mark.parametrize("populated", [False, True], ids=["clean", "seeded"])
def test_mid_transaction_database_failure_rolls_back_all_writes(
    pipeline_database: str,
    tmp_path: Path,
    populated: bool,
) -> None:
    if populated:
        cli(pipeline_database, "import")
    before = fingerprint(pipeline_database)
    payload = json.loads(TOOLS.read_bytes())
    payload["providers"][0]["name"] += " pending change"
    payload["tools"][0]["tags"].append("pending-change")
    path = tmp_path / "rollback.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with psycopg.connect(pipeline_database) as connection:
        # Tool writes occur after provider/taxonomy writes in the actual importer.
        # nextval survives rollback and proves the trigger saw the earlier write.
        connection.execute("CREATE SEQUENCE rollback_witness")
        connection.execute("""CREATE FUNCTION fail_pipeline_write() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
            IF EXISTS (SELECT 1 FROM providers WHERE name LIKE '% pending change') THEN
                PERFORM nextval('rollback_witness');
            END IF;
            RAISE EXCEPTION 'private-trigger-marker'; END $$""")
        connection.execute("""CREATE TRIGGER fail_pipeline_write BEFORE INSERT OR UPDATE ON tools
            FOR EACH ROW EXECUTE FUNCTION fail_pipeline_write()""")
    report = cli(pipeline_database, "import", TAXONOMY, path, exit_code=3)
    assert report["status"] == "unavailable"
    assert report["errors"] == [{"field": "existing", "code": "CATALOG_UNAVAILABLE"}]
    assert "private-trigger-marker" not in json.dumps(report)
    with psycopg.connect(pipeline_database) as connection:
        assert connection.execute("SELECT is_called FROM rollback_witness").fetchone() == (True,)
    assert fingerprint(pipeline_database) == before
    print(
        f"mid-transaction failure ({'seeded' if populated else 'clean'}): "
        "exit=3; all earlier writes rolled back"
    )
