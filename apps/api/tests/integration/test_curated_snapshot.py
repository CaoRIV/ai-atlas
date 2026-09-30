import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from ai_atlas_api.curated_models import CuratedCatalog
from ai_atlas_api.curated_snapshot import load_catalog_snapshot
from ai_atlas_api.curated_validation import CuratedValidationError, validate_catalog
from ai_atlas_api.migrations import upgrade

pytestmark = pytest.mark.integration
NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def uid(number: int) -> UUID:
    return UUID(f"40000000-0000-4000-8000-{number:012d}")


@pytest.fixture(scope="module")
def validation_database() -> Iterator[str]:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is required for curated validation integration tests.")
    database_name = f"ai_atlas_validation_{uuid4().hex}"
    parameters = conninfo_to_dict(base_url)
    parameters["dbname"] = database_name
    test_url = make_conninfo(**parameters)
    with psycopg.connect(base_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    try:
        upgrade(test_url)
        with psycopg.connect(test_url) as connection:
            connection.execute(
                "INSERT INTO categories(id, slug, name) VALUES (%s, 'fixture-category', 'Fixture')",
                (uid(2),),
            )
            connection.execute(
                """INSERT INTO tools(id, slug, name, description, official_url)
                   VALUES (%s, 'fixture-tool', 'Fixture tool', 'Synthetic integration fixture.',
                           'https://www.python.org/')""",
                (uid(5),),
            )
            connection.execute(
                """INSERT INTO tool_facts(id, tool_id, key, value, verification_status, revision)
                   VALUES (%s, %s, 'api_available', 'true'::jsonb, 'verified', 2)""",
                (uid(13), uid(5)),
            )
            for evidence_id, revision in ((uid(113), 2), (uid(112), 1)):
                connection.execute(
                    """INSERT INTO evidence(id, fact_id, fact_revision, source_url, source_kind,
                                            checked_at, expires_at, checked_by)
                       VALUES (%s, %s, %s, 'https://docs.python.org/3/', 'official_docs',
                               %s, %s, 'Synthetic fixture reviewer')""",
                    (
                        evidence_id,
                        uid(13),
                        revision,
                        NOW - timedelta(days=1),
                        NOW + timedelta(days=89),
                    ),
                )
        yield test_url
    finally:
        with psycopg.connect(base_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))


def proposed_catalog() -> dict[str, Any]:
    evidence = {
        "id": str(uid(113)),
        "source_url": "https://docs.python.org/3/",
        "source_kind": "official_docs",
        "checked_at": (NOW - timedelta(days=1)).isoformat(),
        "expires_at": (NOW + timedelta(days=89)).isoformat(),
        "checked_by": "Synthetic fixture reviewer",
    }
    return {
        "schema_version": 1,
        "providers": [],
        "models": [],
        "categories": [],
        "capabilities": [],
        "tools": [
            {
                "id": str(uid(5)),
                "slug": "fixture-tool",
                "name": "Fixture tool",
                "description": "Synthetic integration fixture.",
                "official_url": "https://www.python.org/",
                "provider_id": None,
                "publication_status": "published",
                "tags": [],
                "last_verified_at": NOW.isoformat(),
                "category_ids": [str(uid(2))],
                "model_ids": [],
                "capabilities": [],
                "facts": [
                    {
                        "id": str(uid(10)),
                        "key": "identity",
                        "verification_status": "verified",
                        "value": {
                            "name": "Fixture tool",
                            "description": "Synthetic integration fixture.",
                            "official_url": "https://www.python.org/",
                            "provider_id": None,
                        },
                        "evidence": [{**evidence, "id": str(uid(110))}],
                    },
                    {
                        "id": str(uid(13)),
                        "key": "api_available",
                        "value": True,
                        "verification_status": "verified",
                        "evidence": [evidence],
                    },
                ],
            }
        ],
    }


@pytest.mark.parametrize(
    "change", ["changed_value", "old_revision", "stolen_source", "changed_source"]
)
def test_real_db_snapshot_prevents_evidence_rebinding(
    validation_database: str, change: str
) -> None:
    snapshot = load_catalog_snapshot(validation_database)
    payload = proposed_catalog()
    initial = CuratedCatalog.model_validate_json(json.dumps(payload))
    validate_catalog([initial], now=NOW, existing=snapshot)
    api = payload["tools"][0]["facts"][1]
    if change == "changed_value":
        api["value"] = False
        expected = "evidence_cannot_certify_new_value_or_old_revision"
    elif change == "old_revision":
        api["evidence"][0]["id"] = str(uid(112))
        expected = "evidence_cannot_certify_new_value_or_old_revision"
    elif change == "stolen_source":
        payload["tools"][0]["facts"][0]["evidence"][0]["id"] = str(uid(113))
        expected = "evidence_owner_is_immutable"
    else:
        api["evidence"][0]["checked_by"] = "Different reviewer"
        expected = "evidence_content_is_immutable"
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog(
            [CuratedCatalog.model_validate_json(json.dumps(payload))], now=NOW, existing=snapshot
        )
    assert expected in {issue.code for issue in caught.value.issues}
    unchanged = load_catalog_snapshot(validation_database)
    assert unchanged.facts[uid(13)].value is True
    assert unchanged.facts[uid(13)].revision == 2
    assert unchanged.evidence[uid(113)].fact_id == uid(13)
    assert unchanged.evidence[uid(113)].fact_revision == 2
    if change == "changed_value":
        api["evidence"][0]["id"] = str(uid(999))
        revised = CuratedCatalog.model_validate_json(json.dumps(payload))
        validate_catalog([revised], now=NOW, existing=snapshot)
        assert revised.tools[0].facts[1].value is False


def test_real_db_snapshot_checks_reference_key_conflicts(validation_database: str) -> None:
    snapshot = load_catalog_snapshot(validation_database)
    payload = proposed_catalog()
    payload["categories"] = [{"id": str(uid(999)), "slug": "fixture-category", "name": "Conflict"}]
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog(
            [CuratedCatalog.model_validate_json(json.dumps(payload))], now=NOW, existing=snapshot
        )
    assert any(
        issue.code == "duplicate_key" and issue.field.endswith(".slug")
        for issue in caught.value.issues
    )
    payload["categories"] = []
    payload["tools"][0]["category_ids"] = [str(uid(999))]
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog(
            [CuratedCatalog.model_validate_json(json.dumps(payload))], now=NOW, existing=snapshot
        )
    assert any(
        issue.code == "unknown_reference" and ".category_ids[0]" in issue.field
        for issue in caught.value.issues
    )


def test_invalid_persisted_evidence_is_rejected_without_exposing_raw_source(
    validation_database: str,
) -> None:
    try:
        with psycopg.connect(validation_database) as connection:
            connection.execute(
                "UPDATE evidence SET source_url = %s WHERE id = %s",
                ("http://private-user:private-password@docs.python.org/3/", uid(113)),
            )
        with pytest.raises(CuratedValidationError) as caught:
            load_catalog_snapshot(validation_database)
        assert [(issue.field, issue.code) for issue in caught.value.issues] == [
            (f"existing.evidence[{uid(113)}]", "stored_evidence_shape_invalid")
        ]
        assert "private-password" not in str(caught.value)
        assert "private-user" not in str(caught.value)
    finally:
        with psycopg.connect(validation_database) as connection:
            connection.execute(
                "UPDATE evidence SET source_url = 'https://docs.python.org/3/' WHERE id = %s",
                (uid(113),),
            )
