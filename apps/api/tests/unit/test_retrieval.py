from uuid import UUID

import pytest

from ai_atlas_api.retrieval import (
    EmbeddingProfile,
    make_embedding_document,
    reciprocal_rank_fusion,
)


def uid(number: int) -> UUID:
    return UUID(f"80000000-0000-4000-8000-{number:012d}")


def test_embedding_document_is_canonical_and_public_only() -> None:
    first = make_embedding_document(
        tool_id=uid(1),
        source_revision=3,
        name="  Công cụ  Alpha ",
        description="Viết   nội dung\nđa ngôn ngữ",
        categories=[("writing", "Writing"), ("coding", "Coding")],
        capabilities=[("text_generation", "Text generation"), ("chat", "Chat")],
    )
    reordered = make_embedding_document(
        tool_id=uid(1),
        source_revision=3,
        name="Công cụ Alpha",
        description="Viết nội dung đa ngôn ngữ",
        categories=[("coding", "Coding"), ("writing", "Writing")],
        capabilities=[("chat", "Chat"), ("text_generation", "Text generation")],
    )

    assert first.content == reordered.content
    assert first.content_hash == reordered.content_hash
    assert first.source_revision == 3
    assert "document_version" in first.content
    assert "pricing" not in first.content


def test_embedding_document_hash_changes_with_semantic_content() -> None:
    baseline = make_embedding_document(
        tool_id=uid(1),
        source_revision=1,
        name="Alpha",
        description="Writing assistant",
        categories=[],
        capabilities=[],
    )
    changed = make_embedding_document(
        tool_id=uid(1),
        source_revision=2,
        name="Alpha",
        description="Coding assistant",
        categories=[],
        capabilities=[],
    )

    assert baseline.content_hash != changed.content_hash


def test_rrf_is_deterministic_deduplicated_and_uuid_tiebroken() -> None:
    low = uid(1)
    high = uid(2)
    third = uid(3)

    fused = reciprocal_rank_fusion(
        [[high, low, low], [low, high, third]],
        limit=3,
    )

    assert fused == (low, high, third)
    assert reciprocal_rank_fusion([[high], [low]], limit=1) == (low,)


def test_profile_pins_storage_dimension_and_versions_model_key() -> None:
    profile = EmbeddingProfile("google_gemini", "gemini-embedding-2", 1536)

    assert profile.model_key == "google_gemini:gemini-embedding-2:d1536:document-v1"
    with pytest.raises(ValueError, match="1536-dimensional"):
        EmbeddingProfile("google_gemini", "gemini-embedding-2", 768)
