from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import JsonValue

from ai_atlas_api.catalog import CatalogError
from ai_atlas_api.curated_diff import CatalogChange, build_catalog_diff
from ai_atlas_api.curated_models import CuratedCatalog
from ai_atlas_api.curated_snapshot import load_catalog_snapshot_from_connection
from ai_atlas_api.curated_validation import (
    CatalogSnapshot,
    CuratedValidationError,
    ValidationIssue,
    validate_catalog,
)

IMPORT_LOCK_KEY = 2_026_090_054


def import_catalog(
    database_url: str | None,
    documents: Sequence[CuratedCatalog],
    *,
    now: datetime,
) -> tuple[CatalogChange, ...]:
    """Validate and apply one curated batch atomically against its locked snapshot."""
    if not database_url:
        raise CatalogError(503, "CATALOG_UNAVAILABLE", "Catalog hiện chưa sẵn sàng.")
    try:
        with (
            psycopg.connect(database_url, connect_timeout=3, row_factory=dict_row) as connection,
            connection.transaction(),
        ):
            connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            connection.execute("SET LOCAL lock_timeout = '5s'")
            connection.execute("SET LOCAL statement_timeout = '15s'")
            connection.execute("SELECT pg_advisory_xact_lock(%s)", (IMPORT_LOCK_KEY,))
            snapshot = load_catalog_snapshot_from_connection(connection)
            validate_catalog(documents, now=now, existing=snapshot)
            changes = build_catalog_diff(documents, snapshot)
            _validate_import_transitions(documents, snapshot, changes)
            _apply_catalog(connection, documents, snapshot, changes)
        return changes
    except CuratedValidationError:
        raise
    except (psycopg.Error, OSError):
        raise CatalogError(503, "CATALOG_UNAVAILABLE", "Catalog hiện chưa sẵn sàng.") from None


def _change_map(changes: Sequence[CatalogChange]) -> dict[tuple[str, UUID], CatalogChange]:
    return {(change.entity, change.id): change for change in changes}


def _changed(
    change_by_id: Mapping[tuple[str, UUID], CatalogChange], entity: str, identifier: UUID
) -> bool:
    return change_by_id[entity, identifier].status != "unchanged"


def _validate_import_transitions(
    documents: Sequence[CuratedCatalog],
    snapshot: CatalogSnapshot,
    changes: Sequence[CatalogChange],
) -> None:
    change_by_id = _change_map(changes)
    issues = []
    for document_index, document in enumerate(documents):
        for tool_index, tool in enumerate(document.tools):
            for fact_index, fact in enumerate(tool.facts):
                stored_record = snapshot.records.get("facts", {}).get(fact.id)
                if (
                    stored_record is not None
                    and fact.verification_status == "verified"
                    and _changed(change_by_id, "facts", fact.id)
                    and "verification_status" in change_by_id["facts", fact.id].changed_fields
                    and not any(evidence.id not in snapshot.evidence for evidence in fact.evidence)
                ):
                    issues.append(
                        ValidationIssue(
                            f"documents[{document_index}].tools[{tool_index}].facts[{fact_index}].evidence",
                            "verified_transition_requires_new_evidence",
                        )
                    )
        for capability_index, capability in enumerate(document.capabilities):
            stored = snapshot.records.get("capabilities", {}).get(capability.id)
            if (
                stored is not None
                and stored["key"] != capability.key
                and _capability_is_referenced(snapshot, capability.id)
            ):
                issues.append(
                    ValidationIssue(
                        f"documents[{document_index}].capabilities[{capability_index}].key",
                        "referenced_capability_key_is_immutable",
                    )
                )
        for model_index, model in enumerate(document.models):
            stored = snapshot.records.get("models", {}).get(model.id)
            if (
                stored is not None
                and stored["slug"] != model.slug
                and any(
                    record["key"] == f"model_usage:{stored['slug']}"
                    for record in snapshot.records.get("facts", {}).values()
                )
            ):
                issues.append(
                    ValidationIssue(
                        f"documents[{document_index}].models[{model_index}].slug",
                        "referenced_model_slug_is_immutable",
                    )
                )
    if issues:
        raise CuratedValidationError(issues)


def _capability_is_referenced(snapshot: CatalogSnapshot, capability_id: UUID) -> bool:
    for record in snapshot.records.get("tools", {}).values():
        relations = cast(list[JsonValue], record["capabilities"])
        if any(
            isinstance(relation, dict) and relation.get("capability_id") == str(capability_id)
            for relation in relations
        ):
            return True
    return False


def _execute_many(
    connection: psycopg.Connection[dict[str, Any]],
    statement: str,
    rows: Iterable[Sequence[object]],
) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(statement, rows)


def _apply_catalog(
    connection: psycopg.Connection[dict[str, Any]],
    documents: Sequence[CuratedCatalog],
    snapshot: CatalogSnapshot,
    changes: Sequence[CatalogChange],
) -> None:
    change_by_id = _change_map(changes)
    providers = [entity for document in documents for entity in document.providers]
    models = [entity for document in documents for entity in document.models]
    categories = [entity for document in documents for entity in document.categories]
    capabilities = [entity for document in documents for entity in document.capabilities]
    tools = [tool for document in documents for tool in document.tools]

    _execute_many(
        connection,
        """INSERT INTO providers(id, slug, name, website_url) VALUES (%s,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET slug=EXCLUDED.slug, name=EXCLUDED.name,
             website_url=EXCLUDED.website_url, updated_at=CURRENT_TIMESTAMP""",
        (
            (
                entity.id,
                entity.slug,
                entity.name,
                str(entity.website_url) if entity.website_url else None,
            )
            for entity in providers
            if _changed(change_by_id, "providers", entity.id)
        ),
    )
    _execute_many(
        connection,
        """INSERT INTO categories(id, slug, name) VALUES (%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET slug=EXCLUDED.slug, name=EXCLUDED.name,
             updated_at=CURRENT_TIMESTAMP""",
        (
            (entity.id, entity.slug, entity.name)
            for entity in categories
            if _changed(change_by_id, "categories", entity.id)
        ),
    )
    _execute_many(
        connection,
        """INSERT INTO capabilities(id, key, name, description) VALUES (%s,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET key=EXCLUDED.key, name=EXCLUDED.name,
             description=EXCLUDED.description, updated_at=CURRENT_TIMESTAMP""",
        (
            (entity.id, entity.key, entity.name, entity.description)
            for entity in capabilities
            if _changed(change_by_id, "capabilities", entity.id)
        ),
    )
    _execute_many(
        connection,
        """INSERT INTO models(id, slug, name, provider_id) VALUES (%s,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET slug=EXCLUDED.slug, name=EXCLUDED.name,
             provider_id=EXCLUDED.provider_id, updated_at=CURRENT_TIMESTAMP""",
        (
            (entity.id, entity.slug, entity.name, entity.provider_id)
            for entity in models
            if _changed(change_by_id, "models", entity.id)
        ),
    )
    _execute_many(
        connection,
        """INSERT INTO tools(id, slug, name, description, official_url, provider_id, tags,
                             publication_status, last_verified_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET slug=EXCLUDED.slug, name=EXCLUDED.name,
             description=EXCLUDED.description, official_url=EXCLUDED.official_url,
             provider_id=EXCLUDED.provider_id, tags=EXCLUDED.tags,
             publication_status=EXCLUDED.publication_status,
             last_verified_at=EXCLUDED.last_verified_at, updated_at=CURRENT_TIMESTAMP""",
        (
            (
                tool.id,
                tool.slug,
                tool.name,
                tool.description,
                str(tool.official_url),
                tool.provider_id,
                tool.tags,
                tool.publication_status,
                tool.last_verified_at,
            )
            for tool in tools
            if _changed(change_by_id, "tools", tool.id)
        ),
    )

    target_fact_revision: dict[UUID, int] = {}
    facts = [(tool.id, fact) for tool in tools for fact in tool.facts]
    for _, fact in facts:
        stored = snapshot.facts.get(fact.id)
        target_fact_revision[fact.id] = (
            1
            if stored is None
            else stored.revision + 1
            if _changed(change_by_id, "facts", fact.id)
            else stored.revision
        )
    _execute_many(
        connection,
        """INSERT INTO tool_facts(id, tool_id, key, value, verification_status, revision)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET value=EXCLUDED.value,
             verification_status=EXCLUDED.verification_status,
             revision=EXCLUDED.revision, updated_at=CURRENT_TIMESTAMP""",
        (
            (
                fact.id,
                tool_id,
                fact.key,
                Jsonb(fact.model_dump(mode="json")["value"]),
                fact.verification_status,
                target_fact_revision[fact.id],
            )
            for tool_id, fact in facts
            if _changed(change_by_id, "facts", fact.id)
        ),
    )
    _execute_many(
        connection,
        """INSERT INTO evidence(id, fact_id, fact_revision, source_url, source_kind,
                                checked_at, expires_at, checked_by, excerpt)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            (
                evidence.id,
                fact.id,
                target_fact_revision[fact.id],
                str(evidence.source_url),
                evidence.source_kind,
                evidence.checked_at,
                evidence.expires_at,
                evidence.checked_by,
                evidence.excerpt,
            )
            for _, fact in facts
            for evidence in fact.evidence
            if change_by_id["evidence", evidence.id].status == "added"
        ),
    )

    relation_tools = [
        tool
        for tool in tools
        if change_by_id["tools", tool.id].status == "added"
        or set(change_by_id["tools", tool.id].changed_fields)
        & {"category_ids", "model_ids", "capabilities"}
    ]
    relation_ids = [tool.id for tool in relation_tools]
    if relation_ids:
        connection.execute("DELETE FROM tool_capabilities WHERE tool_id = ANY(%s)", (relation_ids,))
        connection.execute("DELETE FROM tool_models WHERE tool_id = ANY(%s)", (relation_ids,))
        connection.execute("DELETE FROM tool_categories WHERE tool_id = ANY(%s)", (relation_ids,))
        _execute_many(
            connection,
            "INSERT INTO tool_categories(tool_id, category_id) VALUES (%s,%s)",
            (
                (tool.id, category_id)
                for tool in relation_tools
                for category_id in tool.category_ids
            ),
        )
        _execute_many(
            connection,
            "INSERT INTO tool_models(tool_id, model_id) VALUES (%s,%s)",
            ((tool.id, model_id) for tool in relation_tools for model_id in tool.model_ids),
        )
        _execute_many(
            connection,
            "INSERT INTO tool_capabilities(tool_id, capability_id, fact_id) VALUES (%s,%s,%s)",
            (
                (tool.id, relation.capability_id, relation.fact_id)
                for tool in relation_tools
                for relation in tool.capabilities
            ),
        )

    projection_ids = _projection_tool_ids(documents, snapshot, changes)
    existing_projection_ids = sorted(
        identifier for identifier in projection_ids if identifier in snapshot.tools
    )
    if existing_projection_ids:
        connection.execute(
            """UPDATE tools SET revision=revision+1, updated_at=CURRENT_TIMESTAMP
               WHERE id = ANY(%s)""",
            (existing_projection_ids,),
        )
    if projection_ids:
        ordered_projection_ids = sorted(projection_ids)
        connection.execute(
            "DELETE FROM tool_embeddings WHERE tool_id = ANY(%s)",
            (ordered_projection_ids,),
        )
        _reindex_tools(connection, ordered_projection_ids)


def _projection_tool_ids(
    documents: Sequence[CuratedCatalog],
    snapshot: CatalogSnapshot,
    changes: Sequence[CatalogChange],
) -> set[UUID]:
    changed_categories = {
        change.id
        for change in changes
        if change.entity == "categories"
        and change.status == "updated"
        and set(change.changed_fields) & {"slug", "name"}
    }
    changed_capabilities = {
        change.id
        for change in changes
        if change.entity == "capabilities"
        and change.status == "updated"
        and set(change.changed_fields) & {"key", "name"}
    }
    affected = {
        change.id for change in changes if change.entity == "tools" and change.status != "unchanged"
    }
    for identifier, record in snapshot.records.get("tools", {}).items():
        stored_categories = cast(list[JsonValue], record["category_ids"])
        stored_capabilities = cast(list[JsonValue], record["capabilities"])
        category_ids = {UUID(cast(str, value)) for value in stored_categories}
        capability_ids = {
            UUID(cast(str, relation["capability_id"]))
            for item in stored_capabilities
            if isinstance(item, dict)
            for relation in (item,)
        }
        if category_ids & changed_categories or capability_ids & changed_capabilities:
            affected.add(identifier)
    for document in documents:
        for tool in document.tools:
            if (
                set(tool.category_ids) & changed_categories
                or {relation.capability_id for relation in tool.capabilities} & changed_capabilities
            ):
                affected.add(tool.id)
    return affected


def _reindex_tools(
    connection: psycopg.Connection[dict[str, Any]], tool_ids: Sequence[UUID]
) -> None:
    connection.execute(
        """UPDATE tools AS t SET search_vector =
             setweight(to_tsvector('simple', coalesce(t.name, '')), 'A') ||
             setweight(to_tsvector('simple', coalesce(t.description, '')), 'B') ||
             setweight(to_tsvector('simple', coalesce(array_to_string(t.tags, ' '), '')), 'B') ||
             setweight(to_tsvector('simple', coalesce((
               SELECT string_agg(c.slug || ' ' || c.name, ' ' ORDER BY c.id)
               FROM tool_categories tc JOIN categories c ON c.id = tc.category_id
               WHERE tc.tool_id = t.id
             ), '')), 'C') ||
             setweight(to_tsvector('simple', coalesce((
               SELECT string_agg(c.key || ' ' || c.name, ' ' ORDER BY c.id)
               FROM tool_capabilities tc JOIN capabilities c ON c.id = tc.capability_id
               WHERE tc.tool_id = t.id
             ), '')), 'C')
           WHERE t.id = ANY(%s)""",
        (list(tool_ids),),
    )
