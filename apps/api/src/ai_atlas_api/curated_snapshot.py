from psycopg import sql
from pydantic import ValidationError

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


def load_catalog_snapshot(database_url: str | None) -> CatalogSnapshot:
    """Read reference identities and evidence history in one read-only repeatable-read snapshot."""
    with CatalogRepository(database_url).connection() as connection:
        entities = {}
        for table, key in (
            ("providers", "slug"),
            ("models", "slug"),
            ("categories", "slug"),
            ("capabilities", "key"),
            ("tools", "slug"),
        ):
            entities[table] = {
                row["id"]: ReferenceEntity(row["id"], row["key"], row["name"])
                for row in connection.execute(
                    sql.SQL("SELECT id, {} AS key, name FROM {}").format(
                        sql.Identifier(key), sql.Identifier(table)
                    )
                )
            }
        facts = {
            row["id"]: StoredFact(
                id=row["id"],
                tool_id=row["tool_id"],
                key=row["key"],
                value=row["value"],
                revision=row["revision"],
            )
            for row in connection.execute(
                "SELECT id, tool_id, key, value, revision FROM tool_facts"
            )
        }
        evidence = {}
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
        return CatalogSnapshot(
            providers=entities["providers"],
            models=entities["models"],
            categories=entities["categories"],
            capabilities=entities["capabilities"],
            tools=entities["tools"],
            facts=facts,
            evidence=evidence,
        )
