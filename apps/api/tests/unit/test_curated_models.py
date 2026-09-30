import json
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from ai_atlas_api.curated_models import (
    BooleanFact,
    CapabilityFact,
    CuratedCatalog,
    CuratedFact,
    DeploymentModesFact,
    IdentityFact,
    IntegrationFact,
    MinRamFact,
    ModelUsageFact,
    OpenSourceFact,
    PlatformsFact,
    PricingFact,
)

FACT_ID = "10000000-0000-4000-8000-000000000001"
TOOL_ID = "10000000-0000-4000-8000-000000000002"
EVIDENCE_ID = "20000000-0000-4000-8000-000000000001"
FACT_ADAPTER = TypeAdapter(CuratedFact)


def fact_input(key: str, value: object, state: str = "verified") -> dict[str, Any]:
    return {
        "id": FACT_ID,
        "key": key,
        "value": value,
        "verification_status": state,
        "evidence": [
            {
                "id": EVIDENCE_ID,
                "source_url": "https://example.invalid/docs",
                "source_kind": "official_docs",
                "checked_at": "2026-09-01T07:00:00+07:00",
                "expires_at": "2026-10-01T07:00:00+07:00",
                "checked_by": "Synthetic reviewer",
            }
        ],
    }


def catalog_input() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "providers": [],
        "models": [],
        "categories": [],
        "capabilities": [],
        "tools": [
            {
                "id": TOOL_ID,
                "slug": "synthetic-tool",
                "name": "  ho\u0300a  ",
                "description": "Synthetic fixture, not curated catalog data.",
                "official_url": "https://example.invalid/tool",
                "provider_id": None,
                "tags": ["  ho\u0300a  "],
                "publication_status": "draft",
                "last_verified_at": None,
                "category_ids": [],
                "model_ids": [],
                "capabilities": [],
                "facts": [fact_input("api_available", False)],
            }
        ],
    }


@pytest.mark.parametrize(
    ("value", "state"), [(True, "verified"), (False, "verified"), (None, "unknown")]
)
def test_boolean_fact_preserves_three_states(value: bool | None, state: str) -> None:
    fact = FACT_ADAPTER.validate_json(json.dumps(fact_input("api_available", value, state)))
    assert isinstance(fact, BooleanFact)
    assert fact.value is value
    assert fact.verification_status == state
    assert fact.model_dump(mode="json")["value"] is value


@pytest.mark.parametrize("value", [0, 1, 1.0, "true", "false", [], {}])
def test_boolean_fact_does_not_coerce_other_json_types(value: object) -> None:
    with pytest.raises(ValidationError):
        FACT_ADAPTER.validate_json(json.dumps(fact_input("api_available", value)))


@pytest.mark.parametrize(
    ("value", "state"), [(None, "verified"), (None, "unverified"), (False, "unknown")]
)
def test_unknown_status_requires_json_null(value: object, state: str) -> None:
    with pytest.raises(ValidationError):
        FACT_ADAPTER.validate_json(json.dumps(fact_input("api_available", value, state)))


@pytest.mark.parametrize(
    ("key", "value", "expected_class"),
    [
        ("platforms", ["web", "windows"], PlatformsFact),
        ("offline_supported", False, BooleanFact),
        ("open_source", {"status": None, "license": None}, OpenSourceFact),
        ("deployment_modes", ["cloud", "local"], DeploymentModesFact),
        ("min_ram_gb", 8, MinRamFact),
        ("capability:pdf_extraction", True, CapabilityFact),
        ("model_usage:fixture-model", False, ModelUsageFact),
        (
            "identity",
            {
                "name": "Synthetic",
                "description": "Synthetic fixture",
                "official_url": "https://example.invalid/tool",
                "provider_id": None,
            },
            IdentityFact,
        ),
        (
            "integration:external-api",
            {
                "target_tool_id": None,
                "target_name": "External fixture",
                "mechanism": "API",
                "conditions": None,
            },
            IntegrationFact,
        ),
        (
            "pricing",
            {
                "model": "usage_based",
                "currency": "USD",
                "monthly_min": None,
                "billing_basis": "Usage-based",
                "usage_limits": None,
                "free_tier": None,
            },
            PricingFact,
        ),
    ],
)
def test_fact_key_selects_its_value_schema(
    key: str, value: object, expected_class: type[object]
) -> None:
    fact = FACT_ADAPTER.validate_json(json.dumps(fact_input(key, value)))
    assert isinstance(fact, expected_class)
    if isinstance(fact, MinRamFact):
        assert fact.value == 8.0
    elif isinstance(fact, ModelUsageFact):
        assert fact.value is False
    elif isinstance(fact, PricingFact):
        assert fact.value is not None
        assert fact.value.monthly_min is None
        assert fact.value.free_tier is None
    elif isinstance(fact, OpenSourceFact):
        assert fact.value is not None
        assert fact.value.status is None
    elif isinstance(fact, IntegrationFact):
        assert fact.value is not None
        assert fact.value.target_tool_id is None
        assert fact.value.conditions is None


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("platforms", "web"),
        ("platforms", ["desktop"]),
        ("deployment_modes", ["windows"]),
        ("open_source", True),
        ("open_source", {"status": "false", "license": None}),
        ("open_source", {"status": False, "license": None, "hidden": True}),
        ("min_ram_gb", True),
        ("min_ram_gb", "8"),
        ("min_ram_gb", -1),
        ("min_ram_gb", float("inf")),
        ("min_ram_gb", float("nan")),
        ("capability:pdf-extraction", True),
        ("capability:PDF_EXTRACTION", True),
        ("model_usage:fixture_model", True),
        ("model_usage:fixture-model", {"status": True}),
        ("integration:", {}),
        ("unsupported_fact", True),
    ],
)
def test_fact_rejects_wrong_shape_or_namespace(key: str, value: object) -> None:
    with pytest.raises(ValidationError):
        FACT_ADAPTER.validate_json(json.dumps(fact_input(key, value)))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("monthly_min", -1),
        ("monthly_min", "0"),
        ("monthly_min", True),
        ("currency", "usd"),
        ("free_tier", "false"),
        ("usage_limits", {"tokens": 100}),
    ],
)
def test_pricing_rejects_coercion_and_invalid_numeric_values(field: str, value: object) -> None:
    pricing: dict[str, object] = {
        "model": "paid",
        "currency": "USD",
        "monthly_min": 0,
        "billing_basis": None,
        "usage_limits": None,
        "free_tier": None,
    }
    pricing[field] = value
    with pytest.raises(ValidationError):
        FACT_ADAPTER.validate_json(json.dumps(fact_input("pricing", pricing)))


def test_catalog_normalizes_text_and_aware_timestamps_without_changing_ids() -> None:
    catalog = CuratedCatalog.model_validate_json(json.dumps(catalog_input()))
    tool = catalog.tools[0]
    assert str(tool.id) == TOOL_ID
    assert tool.name == "hòa"
    assert tool.tags == ["hòa"]
    evidence = tool.facts[0].evidence[0]
    assert str(evidence.id) == EVIDENCE_ID
    assert evidence.checked_at == datetime(2026, 9, 1, tzinfo=UTC)
    assert evidence.expires_at == datetime(2026, 10, 1, tzinfo=UTC)
    serialized = catalog.model_dump_json()
    restored = CuratedCatalog.model_validate_json(serialized)
    assert restored.tools[0].facts[0].model_dump(mode="json")["value"] is False
    assert restored.tools[0].facts[0].evidence[0].checked_at.tzinfo == UTC


@pytest.mark.parametrize("version", [True, 1.0, "1", 2])
def test_catalog_rejects_non_integer_or_unsupported_version(version: object) -> None:
    payload = catalog_input()
    payload["schema_version"] = version
    with pytest.raises(ValidationError):
        CuratedCatalog.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("checked_at", "2026-09-01T00:00:00"),
        ("expires_at", "2026-10-01"),
        ("checked_at", 1788220800),
        ("source_url", "http://example.invalid/docs"),
        ("source_kind", "community_blog"),
        ("fact_revision", 1),
    ],
)
def test_evidence_rejects_wrong_types_and_importer_owned_fields(field: str, value: object) -> None:
    payload = fact_input("api_available", False)
    payload["evidence"][0][field] = value
    with pytest.raises(ValidationError):
        FACT_ADAPTER.validate_json(json.dumps(payload))


@pytest.mark.parametrize("level", ["catalog", "tool", "fact"])
def test_unknown_keys_cannot_override_importer_metadata(level: str) -> None:
    payload = catalog_input()
    if level == "catalog":
        payload["unexpected"] = True
    elif level == "tool":
        payload["tools"][0]["search_vector"] = "trusted?"
    else:
        payload["tools"][0]["facts"][0]["revision"] = 1
    with pytest.raises(ValidationError):
        CuratedCatalog.model_validate_json(json.dumps(payload))
