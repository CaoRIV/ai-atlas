from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from ai_atlas_api.catalog import CatalogError, CatalogRepository
from ai_atlas_api.config import Settings
from ai_atlas_api.providers.gemini import (
    EmbeddingBatch,
    GeminiRequestError,
    GeminiResponseError,
)

DOCUMENT_VERSION = 1
RRF_K = 60
RETRIEVAL_POOL_LIMIT = 30
REINDEX_BATCH_SIZE = 32
SEMANTIC_RETRIEVAL_WARNING = "semantic_retrieval_unavailable"


class EmbeddingProvider(Protocol):
    def embed(
        self,
        texts: Sequence[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingBatch: ...


@dataclass(frozen=True)
class EmbeddingProfile:
    provider: str
    model: str
    dimension: int

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("Embedding provider and model are required.")
        if self.dimension != 1536:
            raise ValueError("The current database schema requires 1536-dimensional embeddings.")

    @property
    def model_key(self) -> str:
        return f"{self.provider}:{self.model}:d{self.dimension}:document-v{DOCUMENT_VERSION}"

    @classmethod
    def from_settings(cls, settings: Settings) -> EmbeddingProfile:
        return cls(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            dimension=settings.embedding_dim,
        )


@dataclass(frozen=True)
class EmbeddingDocument:
    tool_id: UUID
    source_revision: int
    content: str
    content_hash: str


@dataclass(frozen=True)
class StoredEmbedding:
    content_hash: str
    source_revision: int


@dataclass(frozen=True)
class ReindexReport:
    total: int
    embedded: int
    stored: int
    unchanged: int
    stale_during_write: int
    batches: int
    model_key: str

    def to_dict(self) -> dict[str, int | str]:
        return {
            "total": self.total,
            "embedded": self.embedded,
            "stored": self.stored,
            "unchanged": self.unchanged,
            "stale_during_write": self.stale_during_write,
            "batches": self.batches,
            "model_key": self.model_key,
        }


@dataclass(frozen=True)
class RetrievalResult:
    tool_ids: tuple[UUID, ...]
    warnings: tuple[str, ...] = ()


def make_embedding_document(
    *,
    tool_id: UUID,
    source_revision: int,
    name: str,
    description: str,
    categories: Sequence[tuple[str, str]],
    capabilities: Sequence[tuple[str, str]],
) -> EmbeddingDocument:
    """Build the stable, public-only document used for both hashing and embedding."""

    payload = {
        "capabilities": sorted({_normalized_pair(key, label) for key, label in capabilities}),
        "categories": sorted({_normalized_pair(slug, label) for slug, label in categories}),
        "description": _normalize_text(description),
        "document_version": DOCUMENT_VERSION,
        "name": _normalize_text(name),
    }
    content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return EmbeddingDocument(
        tool_id=tool_id,
        source_revision=source_revision,
        content=content,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[UUID]],
    *,
    limit: int = RETRIEVAL_POOL_LIMIT,
) -> tuple[UUID, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")

    scores: dict[UUID, float] = {}
    for ranked in ranked_lists:
        seen: set[UUID] = set()
        for rank, tool_id in enumerate(ranked, start=1):
            if tool_id in seen:
                continue
            seen.add(tool_id)
            scores[tool_id] = scores.get(tool_id, 0.0) + 1.0 / (RRF_K + rank)
    return tuple(sorted(scores, key=lambda tool_id: (-scores[tool_id], tool_id.int))[:limit])


class EmbeddingIndex:
    """PostgreSQL boundary for versioned embedding documents and exact vector search."""

    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def documents(
        self,
        connection: psycopg.Connection[dict[str, Any]],
        tool_ids: Sequence[UUID] | None = None,
    ) -> list[EmbeddingDocument]:
        if tool_ids is not None and not tool_ids:
            return []
        restriction = sql.SQL("")
        parameters: list[object] = []
        if tool_ids is not None:
            restriction = sql.SQL(" AND t.id = ANY(%s)")
            parameters.append(list(tool_ids))
        rows = connection.execute(
            sql.SQL(
                """
                SELECT t.id, t.name, t.description, t.revision,
                    COALESCE((
                        SELECT jsonb_agg(jsonb_build_array(c.slug, c.name)
                                         ORDER BY c.slug, c.id)
                        FROM tool_categories tc
                        JOIN categories c ON c.id = tc.category_id
                        WHERE tc.tool_id = t.id
                    ), '[]'::jsonb) AS categories,
                    COALESCE((
                        SELECT jsonb_agg(jsonb_build_array(c.key, c.name)
                                         ORDER BY c.key, c.id)
                        FROM tool_capabilities tc
                        JOIN capabilities c ON c.id = tc.capability_id
                        WHERE tc.tool_id = t.id
                    ), '[]'::jsonb) AS capabilities
                FROM tools t
                WHERE t.publication_status = 'published'{}
                ORDER BY t.id
                """
            ).format(restriction),
            parameters,
        ).fetchall()
        return [
            make_embedding_document(
                tool_id=row["id"],
                source_revision=row["revision"],
                name=row["name"],
                description=row["description"],
                categories=[tuple(item) for item in row["categories"]],
                capabilities=[tuple(item) for item in row["capabilities"]],
            )
            for row in rows
        ]

    def reindex(
        self,
        provider: EmbeddingProvider,
        profile: EmbeddingProfile,
        *,
        batch_size: int = REINDEX_BATCH_SIZE,
    ) -> ReindexReport:
        if batch_size < 1 or batch_size > 100:
            raise ValueError("batch_size must be between 1 and 100")

        with self.repository.connection() as connection:
            documents = self.documents(connection)
            existing = self._stored_embeddings(connection, profile, documents)
        pending = [
            document
            for document in documents
            if existing.get(document.tool_id)
            != StoredEmbedding(document.content_hash, document.source_revision)
        ]

        stored = 0
        batches = 0
        for offset in range(0, len(pending), batch_size):
            batch_documents = pending[offset : offset + batch_size]
            response = provider.embed(
                [document.content for document in batch_documents],
                task_type="RETRIEVAL_DOCUMENT",
            )
            self._validate_batch(response, profile, len(batch_documents))
            stored += self._store_batch(profile, batch_documents, response.vectors)
            batches += 1

        return ReindexReport(
            total=len(documents),
            embedded=len(pending),
            stored=stored,
            unchanged=len(documents) - len(pending),
            stale_during_write=len(pending) - stored,
            batches=batches,
            model_key=profile.model_key,
        )

    def keyword_ranked(
        self,
        connection: psycopg.Connection[dict[str, Any]],
        query: str,
        *,
        limit: int = RETRIEVAL_POOL_LIMIT,
    ) -> tuple[UUID, ...]:
        tokens = list(dict.fromkeys(re.findall(r"[^\W_]{2,}", query.casefold())))[:20]
        exact_match = sql.SQL("lower(t.name) = lower(%s) OR lower(t.slug) = lower(%s)")
        token_matches = [
            sql.SQL("t.search_vector @@ plainto_tsquery('simple', %s)") for _ in tokens
        ]
        conditions = sql.SQL(" OR ").join([exact_match, *token_matches])
        ranks = [
            sql.SQL("ts_rank_cd(t.search_vector, plainto_tsquery('simple', %s))") for _ in tokens
        ]
        rank = sql.SQL(" + ").join(ranks) if ranks else sql.SQL("0")
        parameters: list[object] = [query, query, *tokens, query, query, *tokens, limit]
        rows = connection.execute(
            sql.SQL(
                """
                SELECT t.id FROM tools t
                WHERE t.publication_status = 'published' AND ({})
                ORDER BY (CASE WHEN lower(t.name) = lower(%s)
                          OR lower(t.slug) = lower(%s) THEN 1 ELSE 0 END) DESC,
                         {} DESC, t.id ASC
                LIMIT %s
                """
            ).format(conditions, rank),
            parameters,
        ).fetchall()
        return tuple(row["id"] for row in rows)

    def vector_ranked(
        self,
        connection: psycopg.Connection[dict[str, Any]],
        query_vector: Sequence[float],
        profile: EmbeddingProfile,
        *,
        limit: int = RETRIEVAL_POOL_LIMIT,
    ) -> tuple[UUID, ...]:
        vector = _vector_literal(query_vector, profile.dimension)
        rows = connection.execute(
            """
            SELECT t.id, e.content_hash, e.embedding <=> %s::vector AS distance
            FROM tool_embeddings e
            JOIN tools t ON t.id = e.tool_id
            WHERE t.publication_status = 'published'
              AND e.model_key = %s
              AND e.source_revision = t.revision
            ORDER BY distance ASC, t.id ASC
            """,
            (vector, profile.model_key),
        ).fetchall()
        if not rows:
            return ()
        current = {
            document.tool_id: document
            for document in self.documents(connection, [row["id"] for row in rows])
        }
        valid = [
            row["id"]
            for row in rows
            if row["id"] in current and row["content_hash"] == current[row["id"]].content_hash
        ]
        return tuple(valid[:limit])

    @staticmethod
    def _stored_embeddings(
        connection: psycopg.Connection[dict[str, Any]],
        profile: EmbeddingProfile,
        documents: Sequence[EmbeddingDocument],
    ) -> dict[UUID, StoredEmbedding]:
        if not documents:
            return {}
        return {
            row["tool_id"]: StoredEmbedding(row["content_hash"], row["source_revision"])
            for row in connection.execute(
                """
                SELECT tool_id, content_hash, source_revision
                FROM tool_embeddings
                WHERE model_key = %s AND tool_id = ANY(%s)
                """,
                (profile.model_key, [document.tool_id for document in documents]),
            )
        }

    @staticmethod
    def _validate_batch(
        response: EmbeddingBatch,
        profile: EmbeddingProfile,
        expected_count: int,
    ) -> None:
        if response.model != profile.model or response.dimension != profile.dimension:
            raise GeminiResponseError("Embedding response does not match the configured profile.")
        if len(response.vectors) != expected_count:
            raise GeminiResponseError("Embedding response count does not match the request.")
        for vector in response.vectors:
            _vector_literal(vector, profile.dimension)

    def _store_batch(
        self,
        profile: EmbeddingProfile,
        documents: Sequence[EmbeddingDocument],
        vectors: Sequence[Sequence[float]],
    ) -> int:
        stored = 0
        try:
            with self._write_connection() as connection, connection.transaction():
                connection.execute("SET LOCAL statement_timeout = '5s'")
                for document, vector in zip(documents, vectors, strict=True):
                    row = connection.execute(
                        """
                        INSERT INTO tool_embeddings (
                            tool_id, model_key, content_hash, source_revision,
                            embedding, embedded_at
                        )
                        SELECT t.id, %s, %s, %s, %s::vector, CURRENT_TIMESTAMP
                        FROM tools t
                        WHERE t.id = %s
                          AND t.publication_status = 'published'
                          AND t.revision = %s
                        ON CONFLICT (tool_id, model_key) DO UPDATE SET
                            content_hash = EXCLUDED.content_hash,
                            source_revision = EXCLUDED.source_revision,
                            embedding = EXCLUDED.embedding,
                            embedded_at = EXCLUDED.embedded_at
                        WHERE tool_embeddings.content_hash
                              IS DISTINCT FROM EXCLUDED.content_hash
                           OR tool_embeddings.source_revision
                              IS DISTINCT FROM EXCLUDED.source_revision
                        RETURNING tool_id
                        """,
                        (
                            profile.model_key,
                            document.content_hash,
                            document.source_revision,
                            _vector_literal(vector, profile.dimension),
                            document.tool_id,
                            document.source_revision,
                        ),
                    ).fetchone()
                    stored += int(row is not None)
        except (psycopg.Error, OSError):
            raise CatalogError(503, "CATALOG_UNAVAILABLE", "Catalog hiện chưa sẵn sàng.") from None
        return stored

    @contextmanager
    def _write_connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        if not self.repository.database_url:
            raise CatalogError(503, "CATALOG_UNAVAILABLE", "Catalog hiện chưa sẵn sàng.")
        with psycopg.connect(
            self.repository.database_url,
            connect_timeout=3,
            row_factory=dict_row,
        ) as connection:
            yield connection


class HybridRetriever:
    def __init__(
        self,
        index: EmbeddingIndex,
        profile: EmbeddingProfile,
        provider: EmbeddingProvider | None,
    ) -> None:
        self.index = index
        self.profile = profile
        self.provider = provider

    def retrieve(self, query: str, *, limit: int = RETRIEVAL_POOL_LIMIT) -> RetrievalResult:
        query_vector: Sequence[float] | None = None
        warnings: tuple[str, ...] = ()
        if self.provider is None:
            warnings = (SEMANTIC_RETRIEVAL_WARNING,)
        else:
            try:
                response = self.provider.embed([query], task_type="RETRIEVAL_QUERY")
                EmbeddingIndex._validate_batch(response, self.profile, 1)
                query_vector = response.vectors[0]
            except (GeminiRequestError, GeminiResponseError, ValueError):
                warnings = (SEMANTIC_RETRIEVAL_WARNING,)

        with self.index.repository.connection() as connection:
            keyword = self.index.keyword_ranked(connection, query)
            vector = (
                self.index.vector_ranked(connection, query_vector, self.profile)
                if query_vector is not None
                else ()
            )
        return RetrievalResult(
            tool_ids=reciprocal_rank_fusion([keyword, vector], limit=limit),
            warnings=warnings,
        )


def _normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _normalized_pair(key: str, label: str) -> tuple[str, str]:
    return (_normalize_text(key), _normalize_text(label))


def _vector_literal(values: Sequence[float], dimension: int) -> str:
    if len(values) != dimension:
        raise GeminiResponseError("Embedding vector has an unexpected dimension.")
    normalized = [float(value) for value in values]
    if any(not math.isfinite(value) for value in normalized):
        raise GeminiResponseError("Embedding vector contains a non-finite value.")
    return "[" + ",".join(format(value, ".17g") for value in normalized) + "]"
