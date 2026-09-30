from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ai_atlas_api.catalog_models import (
    Capability,
    CatalogQuery,
    Category,
    Evidence,
    Fact,
    NamedEntity,
    PricingSummary,
    ToolDetail,
    ToolSummary,
)

# One transaction timestamp and snapshot govern both filtering and public projections.
EFFECTIVE_FACTS = """
    WITH effective_facts AS NOT MATERIALIZED (
        SELECT f.*,
            CASE WHEN f.value = 'null'::jsonb OR f.verification_status = 'unknown'
                 THEN 'unknown'
                 WHEN f.verification_status = 'verified' AND EXISTS (
                     SELECT 1 FROM evidence e
                     WHERE e.fact_id = f.id AND e.fact_revision = f.revision
                       AND e.checked_at <= CURRENT_TIMESTAMP
                       AND CURRENT_TIMESTAMP < e.expires_at
                 ) THEN 'verified' ELSE 'unverified' END AS effective_status
        FROM tool_facts f
    )
"""
PRICING_MODEL = """
    CASE WHEN f.effective_status = 'verified'
          AND f.value->>'model' IN ('free','freemium','paid','usage_based','contact')
         THEN f.value->>'model' ELSE 'unknown' END
"""


class CatalogError(Exception):
    def __init__(self, status: int, code: str, message: str, field: str | None = None) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.field = field
        super().__init__(code)


class CatalogRepository:
    def __init__(self, database_url: str | None) -> None:
        self.database_url = database_url

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        if not self.database_url:
            raise CatalogError(503, "CATALOG_UNAVAILABLE", "Catalog hiện chưa sẵn sàng.")
        try:
            with psycopg.connect(
                self.database_url, connect_timeout=3, row_factory=dict_row
            ) as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                connection.execute("SET LOCAL statement_timeout = '5s'")
                yield connection
        except (psycopg.Error, OSError):
            raise CatalogError(503, "CATALOG_UNAVAILABLE", "Catalog hiện chưa sẵn sàng.") from None

    def categories(self) -> list[Category]:
        with self.connection() as connection:
            return [
                Category.model_validate(row)
                for row in connection.execute(
                    "SELECT id, slug, name FROM categories ORDER BY name, id"
                )
            ]

    def tools(self, query: CatalogQuery) -> tuple[list[ToolSummary], int]:
        with self.connection() as connection:
            conditions: list[sql.Composable] = [sql.SQL("t.publication_status = 'published'")]
            parameters: list[object] = []
            if query.category is not None:
                slugs = query.category_slugs
                known = {
                    row["slug"]
                    for row in connection.execute(
                        "SELECT slug FROM categories WHERE slug = ANY(%s)", (slugs,)
                    )
                }
                if set(slugs) - known:
                    raise CatalogError(
                        422, "VALIDATION_ERROR", "Category không tồn tại.", "category"
                    )
                conditions.append(
                    sql.SQL("""
                    EXISTS (SELECT 1 FROM tool_categories tc JOIN categories c
                        ON c.id = tc.category_id
                        WHERE tc.tool_id = t.id AND c.slug = ANY(%s))
                """)
                )
                parameters.append(slugs)
            if query.q:
                conditions.append(
                    sql.SQL("""
                    (t.search_vector @@ plainto_tsquery('simple', %s)
                     OR lower(t.name) = lower(%s) OR lower(t.slug) = lower(%s))
                """)
                )
                parameters.extend([query.q, query.q, query.q])
            for key, value, predicate in (
                ("platforms", query.platform, "f.value @> %s::jsonb"),
                ("api_available", query.api_available, "f.value = %s::jsonb"),
                ("open_source", query.open_source, "f.value->'status' = %s::jsonb"),
            ):
                if value is None:
                    continue
                conditions.append(
                    sql.SQL("""
                    EXISTS (SELECT 1 FROM effective_facts f
                        WHERE f.tool_id = t.id AND f.key = %s
                          AND f.effective_status = 'verified' AND {})
                """).format(sql.SQL(predicate))
                )
                parameters.extend([key, Jsonb([value] if key == "platforms" else value)])
            if query.pricing_model is not None:
                conditions.append(
                    sql.SQL("""
                    COALESCE((SELECT {} FROM effective_facts f
                        WHERE f.tool_id = t.id AND f.key = 'pricing'), 'unknown') = %s
                """).format(sql.SQL(PRICING_MODEL))
                )
                parameters.append(query.pricing_model)
            where = sql.SQL(" AND ").join(conditions)
            count = connection.execute(
                sql.SQL(EFFECTIVE_FACTS + "SELECT count(*) AS total FROM tools t WHERE {}").format(
                    where
                ),
                parameters,
            ).fetchone()
            assert count is not None
            total = int(count["total"])
            offset = (query.page - 1) * query.page_size
            if offset >= total:
                return [], total
            order = {
                "name": "lower(t.name) ASC, t.id ASC",
                "updated": "t.updated_at DESC, t.id ASC",
                "relevance": """(CASE WHEN lower(t.name) = lower(%s)
                        OR lower(t.slug) = lower(%s) THEN 1 ELSE 0 END) DESC,
                    ts_rank_cd(t.search_vector, plainto_tsquery('simple', %s)) DESC,
                    t.id ASC""",
            }[query.effective_sort]
            if query.effective_sort == "relevance":
                parameters.extend([query.q, query.q, query.q])
            parameters.extend([query.page_size, offset])
            rows = connection.execute(
                sql.SQL(
                    EFFECTIVE_FACTS + "SELECT t.* FROM tools t WHERE {} ORDER BY {} "
                    "LIMIT %s OFFSET %s"
                ).format(where, sql.SQL(order)),
                parameters,
            ).fetchall()
            return self.summaries(connection, rows), total

    def summaries(
        self, connection: psycopg.Connection[dict[str, Any]], rows: list[dict[str, Any]]
    ) -> list[ToolSummary]:
        ids = [row["id"] for row in rows]
        categories: dict[UUID, list[Category]] = {tool_id: [] for tool_id in ids}
        for row in connection.execute(
            """SELECT tc.tool_id, c.id, c.slug, c.name FROM tool_categories tc
               JOIN categories c ON c.id = tc.category_id
               WHERE tc.tool_id = ANY(%s) ORDER BY c.name, c.id""",
            (ids,),
        ):
            categories[row["tool_id"]].append(Category.model_validate(row))
        pricing = {
            row["tool_id"]: PricingSummary(
                model=row["model"], verification_status=row["effective_status"]
            )
            for row in connection.execute(
                EFFECTIVE_FACTS
                + f"""SELECT f.tool_id, {PRICING_MODEL} AS model,
                    f.effective_status FROM effective_facts f
                    WHERE f.key = 'pricing' AND f.tool_id = ANY(%s)""",
                (ids,),
            )
        }
        return [
            ToolSummary(
                **{
                    key: row[key]
                    for key in ("id", "slug", "name", "description", "last_verified_at")
                },
                categories=categories[row["id"]],
                pricing=pricing.get(
                    row["id"], PricingSummary(model="unknown", verification_status="unknown")
                ),
            )
            for row in rows
        ]

    def tool(self, tool_id: UUID) -> ToolDetail:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM tools WHERE id = %s AND publication_status = 'published'",
                (tool_id,),
            ).fetchone()
            if row is None:
                raise CatalogError(404, "NOT_FOUND", "Không tìm thấy tool.")
            summary = self.summaries(connection, [row])[0]
            fact_rows = connection.execute(
                EFFECTIVE_FACTS + "SELECT * FROM effective_facts WHERE tool_id = %s ORDER BY key",
                (tool_id,),
            ).fetchall()
            evidence_rows = connection.execute(
                """SELECT e.id, f.key AS fact_key, e.source_url, e.checked_at, e.expires_at,
                          (e.checked_at <= CURRENT_TIMESTAMP
                           AND CURRENT_TIMESTAMP < e.expires_at) AS fresh
                   FROM evidence e JOIN tool_facts f ON f.id = e.fact_id
                   WHERE f.tool_id = %s AND e.fact_revision = f.revision
                   ORDER BY f.key, e.checked_at DESC, e.id""",
                (tool_id,),
            ).fetchall()
            evidence_ids: dict[str, list[UUID]] = {}
            for source in evidence_rows:
                if source["fresh"]:
                    evidence_ids.setdefault(source["fact_key"], []).append(source["id"])
            facts = [
                Fact(
                    key=f["key"],
                    value=f["value"],
                    verification_status=f["effective_status"],
                    evidence_ids=evidence_ids.get(f["key"], [])
                    if f["effective_status"] == "verified"
                    else [],
                )
                for f in fact_rows
            ]
            by_key = {fact.key: fact for fact in facts}
            capabilities = []
            for capability in connection.execute(
                """SELECT c.key, c.name, f.key AS fact_key FROM tool_capabilities tc
                   JOIN capabilities c ON c.id = tc.capability_id
                   JOIN tool_facts f ON f.id = tc.fact_id
                   WHERE tc.tool_id = %s ORDER BY c.key""",
                (tool_id,),
            ):
                fact = by_key.get("capability:" + capability["key"])
                if (
                    fact
                    and capability["fact_key"] == fact.key
                    and fact.verification_status == "verified"
                    and fact.value is True
                ):
                    capabilities.append(
                        Capability(
                            key=capability["key"],
                            name=capability["name"],
                            evidence_ids=fact.evidence_ids,
                        )
                    )
            provider_row = connection.execute(
                "SELECT id, name FROM providers WHERE id = %s", (row["provider_id"],)
            ).fetchone()
            models = []
            for model in connection.execute(
                """SELECT m.id, m.name, m.slug FROM tool_models tm
                   JOIN models m ON m.id = tm.model_id WHERE tm.tool_id = %s
                   ORDER BY m.name, m.id""",
                (tool_id,),
            ):
                fact = by_key.get("model_usage:" + model["slug"])
                if fact and fact.verification_status == "verified" and fact.value is True:
                    models.append(NamedEntity.model_validate(model))
            return ToolDetail(
                **summary.model_dump(),
                official_url=row["official_url"],
                tags=row["tags"],
                provider=NamedEntity.model_validate(provider_row) if provider_row else None,
                models=models,
                capabilities=capabilities,
                facts=facts,
                evidence=[Evidence.model_validate(source) for source in evidence_rows],
                revision=row["revision"],
                warnings=[
                    f"fact_{fact.verification_status}:{fact.key}"
                    for fact in facts
                    if fact.verification_status != "verified"
                ],
            )
