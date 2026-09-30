from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import JsonValue

from ai_atlas_api.curated_models import CuratedCatalog
from ai_atlas_api.curated_validation import (
    CatalogSnapshot,
    CuratedValidationError,
    ValidationIssue,
    same_json_value,
)


@dataclass(frozen=True)
class CatalogChange:
    entity: str
    id: UUID
    status: Literal["added", "updated", "unchanged"]
    changed_fields: tuple[str, ...]
    parent_id: UUID | None = None


def build_catalog_diff(
    documents: Sequence[CuratedCatalog], existing: CatalogSnapshot
) -> tuple[CatalogChange, ...]:
    """Compare validated input rows, not deletions or server-owned revision/projection fields."""
    proposed: dict[str, dict[UUID, tuple[dict[str, JsonValue], UUID | None]]] = {
        table: {}
        for table in (
            "providers",
            "models",
            "categories",
            "capabilities",
            "tools",
            "facts",
            "evidence",
        )
    }
    known: dict[str, Mapping[UUID, object]] = {
        "providers": existing.providers,
        "models": existing.models,
        "categories": existing.categories,
        "capabilities": existing.capabilities,
        "tools": existing.tools,
        "facts": existing.facts,
        "evidence": existing.evidence,
    }
    for document in documents:
        for table in ("providers", "models", "categories", "capabilities"):
            for entity in getattr(document, table):
                proposed[table][entity.id] = (entity.model_dump(mode="json"), None)
        for tool in document.tools:
            record = tool.model_dump(mode="json", exclude={"facts", "curation_notes"})
            record["category_ids"] = sorted(record["category_ids"])
            record["model_ids"] = sorted(record["model_ids"])
            record["capabilities"] = sorted(
                record["capabilities"],
                key=lambda relation: (relation["capability_id"], relation["fact_id"]),
            )
            proposed["tools"][tool.id] = (record, None)
            for fact in tool.facts:
                proposed["facts"][fact.id] = (
                    {
                        **fact.model_dump(mode="json", exclude={"evidence", "curation_notes"}),
                        "tool_id": str(tool.id),
                    },
                    tool.id,
                )
                for evidence in fact.evidence:
                    proposed["evidence"][evidence.id] = (
                        {**evidence.model_dump(mode="json"), "fact_id": str(fact.id)},
                        fact.id,
                    )
    changes = []
    for table, records in proposed.items():
        for identifier, (record, parent) in sorted(records.items()):
            stored = existing.records.get(table, {}).get(identifier)
            if identifier in known[table] and (stored is None or stored.keys() != record.keys()):
                raise CuratedValidationError(
                    [
                        ValidationIssue(
                            f"existing.{table}[{identifier}]", "snapshot_content_incomplete"
                        )
                    ]
                )
            changed_fields = tuple(
                field
                for field in sorted(record)
                if field != "id"
                and (stored is None or not same_json_value(record[field], stored[field]))
            )
            status: Literal["added", "updated", "unchanged"] = (
                "added" if stored is None else "updated" if changed_fields else "unchanged"
            )
            changes.append(CatalogChange(table, identifier, status, changed_fields, parent))
    return tuple(changes)
