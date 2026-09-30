from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql
from pydantic import JsonValue, ValidationError

from ai_atlas_api.catalog import CatalogRepository
from ai_atlas_api.curated_models import CuratedEvidence
from ai_atlas_api.curated_validation import (
    CatalogSnapshot,
    CuratedValidationError,
    ReferenceEntity,
    StoredEvidence,
    StoredFact,
    ValidationIssue,
)

ENTITY_COLUMNS = {
    "providers": ("id", "slug", "name", "website_url"),
    "models": ("id", "slug", "name", "provider_id"),
    "categories": ("id", "slug", "name"),
    "capabilities": ("id", "key", "name", "description"),
    "tools": (
        "id",
        "slug",
        "name",
        "description",
        "official_url",
        "provider_id",
        "tags",
        "publication_status",
        "last_verified_at",
    ),
}


def load_catalog_snapshot(database_url: str | None) -> CatalogSnapshot:
    """Read identities, import-owned content and evidence history in one read-only snapshot."""
    with CatalogRepository(database_url).connection() as connection:
        return _read_catalog_snapshot(connection)


def load_catalog_snapshot_from_connection(
    connection: psycopg.Connection[dict[str, Any]],
) -> CatalogSnapshot:
    """Read a catalog snapshot from the caller-owned transaction."""
    return _read_catalog_snapshot(connection)


def _read_catalog_snapshot(
    connection: psycopg.Connection[dict[str, Any]],
) -> CatalogSnapshot:
    entities: dict[str, dict[UUID, ReferenceEntity]] = {}
    records: dict[str, dict[UUID, dict[str, JsonValue]]] = {}
    for table, columns in ENTITY_COLUMNS.items():
        entities[table] = {}
        records[table] = {}
        for row in connection.execute(
            sql.SQL("SELECT {} FROM {}").format(
                sql.SQL(", ").join(map(sql.Identifier, columns)), sql.Identifier(table)
            )
        ):
            identifier = row["id"]
            key = row["key"] if table == "capabilities" else row["slug"]
            entities[table][identifier] = ReferenceEntity(identifier, key, row["name"])
            records[table][identifier] = {
                field: (
                    str(value)
                    if isinstance(value, UUID)
                    else value.astimezone(UTC).isoformat().replace("+00:00", "Z")
                    if isinstance(value, datetime)
                    else value
                )
                for field, value in row.items()
            }
    for record in records["tools"].values():
        record.update(category_ids=[], model_ids=[], capabilities=[])
    for table, target, field in (
        ("tool_categories", "category_id", "category_ids"),
        ("tool_models", "model_id", "model_ids"),
    ):
        for row in connection.execute(
            sql.SQL("SELECT tool_id, {} FROM {} ORDER BY tool_id, {}").format(
                sql.Identifier(target), sql.Identifier(table), sql.Identifier(target)
            )
        ):
            values = records["tools"][row["tool_id"]][field]
            assert isinstance(values, list)
            values.append(str(row[target]))
    for row in connection.execute(
        "SELECT tool_id, capability_id, fact_id FROM tool_capabilities "
        "ORDER BY tool_id, capability_id, fact_id"
    ):
        relations = records["tools"][row["tool_id"]]["capabilities"]
        assert isinstance(relations, list)
        relations.append(
            {"capability_id": str(row["capability_id"]), "fact_id": str(row["fact_id"])}
        )
    facts = {}
    records["facts"] = {}
    for row in connection.execute(
        "SELECT id, tool_id, key, value, verification_status, revision FROM tool_facts"
    ):
        facts[row["id"]] = StoredFact(
            id=row["id"],
            tool_id=row["tool_id"],
            key=row["key"],
            value=row["value"],
            revision=row["revision"],
        )
        records["facts"][row["id"]] = {
            "id": str(row["id"]),
            "tool_id": str(row["tool_id"]),
            "key": row["key"],
            "value": row["value"],
            "verification_status": row["verification_status"],
        }
    evidence = {}
    records["evidence"] = {}
    for row in connection.execute(
        """SELECT id, fact_id, fact_revision, source_url, source_kind,
                  checked_at, expires_at, checked_by, excerpt FROM evidence"""
    ):
        fact_id = row.pop("fact_id")
        fact_revision = row.pop("fact_revision")
        try:
            source = CuratedEvidence.model_validate(row)
        except ValidationError:
            raise CuratedValidationError(
                [
                    ValidationIssue(
                        f"existing.evidence[{row['id']}]", "stored_evidence_shape_invalid"
                    )
                ]
            ) from None
        evidence[row["id"]] = StoredEvidence(
            fact_id=fact_id, fact_revision=fact_revision, source=source
        )
        records["evidence"][row["id"]] = {
            **source.model_dump(mode="json"),
            "fact_id": str(fact_id),
        }
    return CatalogSnapshot(
        providers=entities["providers"],
        models=entities["models"],
        categories=entities["categories"],
        capabilities=entities["capabilities"],
        tools=entities["tools"],
        facts=facts,
        evidence=evidence,
        records=records,
    )
