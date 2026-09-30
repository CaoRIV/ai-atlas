from datetime import UTC, datetime
from pathlib import Path

from ai_atlas_api.curated_models import CuratedCatalog
from ai_atlas_api.curated_validation import validate_catalog

ROOT = Path(__file__).resolve().parents[4]
NOW = datetime(2026, 9, 30, 16, tzinfo=UTC)
UNKNOWN_KEYS = {
    "pricing",
    "platforms",
    "api_available",
    "open_source",
    "deployment_modes",
    "offline_supported",
}


def load_seed() -> tuple[CuratedCatalog, CuratedCatalog]:
    taxonomy = CuratedCatalog.model_validate_json(
        (ROOT / "data/curated/taxonomy.json").read_bytes()
    )
    tools = CuratedCatalog.model_validate_json((ROOT / "data/curated/tools.json").read_bytes())
    return taxonomy, tools


def test_seed_is_a_valid_fifteen_tool_published_batch() -> None:
    taxonomy, tools = load_seed()
    validate_catalog([taxonomy, tools], now=NOW)
    assert len(tools.tools) == 15
    assert len(tools.providers) == 14
    assert all(tool.publication_status == "published" for tool in tools.tools)
    assert all(tool.last_verified_at is not None for tool in tools.tools)
    assert {category_id for tool in tools.tools for category_id in tool.category_ids} == {
        category.id for category in taxonomy.categories
    }


def test_each_seed_tool_has_verified_identity_capability_and_explicit_unknowns() -> None:
    _, seed = load_seed()
    for tool in seed.tools:
        facts = {fact.key: fact for fact in tool.facts}
        identity = facts["identity"]
        assert identity.verification_status == "verified"
        assert len(identity.evidence) == 1
        assert len(tool.capabilities) >= 1
        for relation in tool.capabilities:
            capability = next(fact for fact in tool.facts if fact.id == relation.fact_id)
            assert capability.value is True
            assert capability.verification_status == "verified"
            assert len(capability.evidence) == 1
        assert facts.keys() >= UNKNOWN_KEYS
        for key in UNKNOWN_KEYS:
            assert facts[key].value is None
            assert facts[key].verification_status == "unknown"
            assert facts[key].evidence == []


def test_seed_contains_no_synthetic_fixture_content() -> None:
    content = (ROOT / "data/curated/tools.json").read_text(encoding="utf-8").lower()
    assert "synthetic" not in content
    assert "example.com" not in content
    assert "localhost" not in content
