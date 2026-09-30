import copy
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from ai_atlas_api.curated_models import CuratedCatalog
from ai_atlas_api.curated_validation import (
    CatalogSnapshot,
    CuratedValidationError,
    ReferenceEntity,
    StoredEvidence,
    StoredFact,
    validate_catalog,
)

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def uid(number: int) -> str:
    return f"10000000-0000-4000-8000-{number:012d}"


def source(number: int, *, days: int = 90) -> dict[str, Any]:
    checked = NOW - timedelta(days=1)
    return {
        "id": uid(number),
        "source_url": "https://docs.python.org/3/",
        "source_kind": "official_docs",
        "checked_at": checked.isoformat(),
        "expires_at": (checked + timedelta(days=days)).isoformat(),
        "checked_by": "Synthetic fixture reviewer",
    }


def fact(number: int, key: str, value: object) -> dict[str, Any]:
    return {
        "id": uid(number),
        "key": key,
        "value": value,
        "verification_status": "unknown" if value is None else "verified",
        "evidence": [] if value is None else [source(100 + number)],
    }


def catalog_input() -> dict[str, Any]:
    """Synthetic fixture only; public URLs test syntax, not tool claims/authenticity."""
    tool = {
        "id": uid(5),
        "slug": "synthetic-tool",
        "name": "Synthetic tool",
        "description": "Synthetic fixture, not a curated tool claim.",
        "official_url": "https://www.python.org/",
        "provider_id": uid(1),
        "tags": [],
        "publication_status": "published",
        "last_verified_at": NOW.isoformat(),
        "category_ids": [uid(2)],
        "model_ids": [uid(4)],
        "capabilities": [{"capability_id": uid(3), "fact_id": uid(11)}],
        "facts": [
            fact(
                10,
                "identity",
                {
                    "name": "Synthetic tool",
                    "description": "Synthetic fixture, not a curated tool claim.",
                    "official_url": "https://www.python.org/",
                    "provider_id": uid(1),
                },
            ),
            fact(11, "capability:text_generation", True),
            fact(12, "model_usage:fixture-model", True),
            fact(13, "api_available", True),
            fact(14, "pricing", None),
        ],
    }
    return {
        "schema_version": 1,
        "providers": [{"id": uid(1), "slug": "fixture", "name": "Fixture", "website_url": None}],
        "models": [
            {"id": uid(4), "slug": "fixture-model", "name": "Fixture model", "provider_id": uid(1)}
        ],
        "categories": [{"id": uid(2), "slug": "coding-development", "name": "Coding"}],
        "capabilities": [
            {
                "id": uid(3),
                "key": "text_generation",
                "name": "Text generation",
                "description": "Synthetic vocabulary definition.",
            }
        ],
        "tools": [tool],
    }


def parse(payload: dict[str, Any]) -> CuratedCatalog:
    return CuratedCatalog.model_validate_json(json.dumps(payload))


def set_value(payload: dict[str, Any], path: tuple[str | int, ...], value: object) -> None:
    cursor: Any = payload
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value


def assert_issue(
    payload: dict[str, Any], code: str, *, existing: CatalogSnapshot | None = None
) -> None:
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog([parse(payload)], now=NOW, existing=existing)
    assert code in {issue.code for issue in caught.value.issues}
    assert all(issue.field.startswith("documents[0].") for issue in caught.value.issues)


def test_published_gate_allows_incomplete_draft_then_rejects_publication() -> None:
    payload = catalog_input()
    tool = payload["tools"][0]
    tool.update(
        publication_status="draft",
        last_verified_at=None,
        category_ids=[],
        model_ids=[],
        capabilities=[],
        facts=[],
    )
    validate_catalog([parse(payload)], now=NOW)
    tool["publication_status"] = "published"
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog([parse(payload)], now=NOW)
    assert {issue.code for issue in caught.value.issues} == {
        "published_requires_category",
        "published_requires_review_date",
        "published_requires_verified_identity",
    }


@pytest.mark.parametrize(
    "path",
    [
        ("models", 0, "provider_id"),
        ("tools", 0, "provider_id"),
        ("tools", 0, "category_ids", 0),
        ("tools", 0, "model_ids", 0),
        ("tools", 0, "capabilities", 0, "capability_id"),
        ("tools", 0, "facts", 0, "value", "provider_id"),
    ],
)
def test_missing_reference_is_not_silently_dropped(path: tuple[str | int, ...]) -> None:
    payload = catalog_input()
    set_value(payload, path, uid(999))
    assert_issue(payload, "unknown_reference")


@pytest.mark.parametrize("table", ["providers", "models", "categories", "capabilities", "tools"])
def test_duplicate_entity_ids_and_keys_are_rejected(table: str) -> None:
    payload = catalog_input()
    duplicate = copy.deepcopy(payload[table][0])
    payload[table].append(duplicate)
    assert_issue(payload, "duplicate_id")
    duplicate["id"] = uid(999)
    assert_issue(payload, "duplicate_key")


@pytest.mark.parametrize("relation", ["category_ids", "model_ids", "capabilities"])
def test_duplicate_relations_are_rejected(relation: str) -> None:
    payload = catalog_input()
    values = payload["tools"][0][relation]
    values.append(copy.deepcopy(values[0]))
    assert_issue(payload, "duplicate_relation")


@pytest.mark.parametrize("kind", ["fact_id", "fact_key", "evidence_id"])
def test_fact_and_evidence_uniqueness_is_enforced(kind: str) -> None:
    payload = catalog_input()
    facts = payload["tools"][0]["facts"]
    if kind == "fact_id":
        facts[3]["id"] = facts[1]["id"]
        code = "duplicate_fact_id"
    elif kind == "fact_key":
        facts[3]["key"] = facts[1]["key"]
        code = "duplicate_fact_key"
    else:
        facts[3]["evidence"][0]["id"] = facts[1]["evidence"][0]["id"]
        code = "duplicate_evidence_id"
    assert_issue(payload, code)


@pytest.mark.parametrize("fact_index", [1, 2])
@pytest.mark.parametrize("state", ["false", "unknown", "unverified", "expired", "absent"])
def test_relations_require_affirmative_fresh_evidence(fact_index: int, state: str) -> None:
    payload = catalog_input()
    facts = payload["tools"][0]["facts"]
    target = facts[fact_index]
    if state == "false":
        target["value"] = False
    elif state == "unknown":
        target.update(value=None, verification_status="unknown", evidence=[])
    elif state == "unverified":
        target["verification_status"] = "unverified"
    elif state == "expired":
        target["evidence"][0]["expires_at"] = NOW.isoformat()
    else:
        facts.remove(target)
    code = (
        "capability_fact_must_belong_to_tool"
        if state == "absent" and fact_index == 1
        else "relation_requires_verified_true_fresh_fact"
    )
    assert_issue(payload, code)


def test_capability_relation_cannot_point_at_another_fact_key() -> None:
    payload = catalog_input()
    payload["tools"][0]["capabilities"][0]["fact_id"] = uid(13)
    assert_issue(payload, "capability_fact_key_mismatch")


def test_capability_relation_cannot_point_at_another_tool_fact() -> None:
    payload = catalog_input()
    other = copy.deepcopy(payload["tools"][0])
    other.update(id=uid(20), slug="other-tool", name="Other tool")
    for index, entry in enumerate(other["facts"]):
        entry["id"] = uid(200 + index)
        for evidence in entry["evidence"]:
            evidence["id"] = uid(300 + index)
    other["facts"][0]["value"]["name"] = "Other tool"
    other["capabilities"][0]["fact_id"] = other["facts"][1]["id"]
    payload["tools"].append(other)
    payload["tools"][0]["capabilities"][0]["fact_id"] = other["facts"][1]["id"]
    assert_issue(payload, "capability_fact_must_belong_to_tool")


@pytest.mark.parametrize("index", [1, 2])
def test_fact_namespace_must_reference_known_vocabulary(index: int) -> None:
    payload = catalog_input()
    payload["tools"][0]["facts"][index]["key"] = (
        "capability:invented_capability" if index == 1 else "model_usage:invented-model"
    )
    assert_issue(payload, "unknown_capability_key" if index == 1 else "unknown_model_slug")


@pytest.mark.parametrize("field", ["name", "description", "official_url", "provider_id"])
def test_identity_must_agree_with_tool_metadata(field: str) -> None:
    payload = catalog_input()
    value = "https://docs.python.org/" if field == "official_url" else "Different value"
    if field == "provider_id":
        value = None
    payload["tools"][0]["facts"][0]["value"][field] = value
    assert_issue(payload, "identity_does_not_match_tool")


@pytest.mark.parametrize("state", ["absent", "unknown", "unverified", "expired"])
def test_published_identity_requires_verification_and_freshness(state: str) -> None:
    payload = catalog_input()
    facts = payload["tools"][0]["facts"]
    identity = facts[0]
    if state == "absent":
        facts.remove(identity)
    elif state == "unknown":
        identity.update(value=None, verification_status="unknown", evidence=[])
    elif state == "unverified":
        identity["verification_status"] = "unverified"
    else:
        identity["evidence"][0]["expires_at"] = NOW.isoformat()
    assert_issue(payload, "published_requires_verified_identity")


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/docs",
        "https://127.0.0.1/docs",
        "https://[::1]/docs",
        "https://192.168.1.1/docs",
        "https://example.invalid/docs",
        "https://docs.example.com/docs",
        "https://catalog.test/docs",
        "https://internal.local/docs",
        "https://user:private-password@docs.python.org/3/",
    ],
)
def test_source_url_is_not_a_placeholder_or_credential_bearing_url(url: str) -> None:
    payload = catalog_input()
    payload["tools"][0]["facts"][0]["evidence"][0]["source_url"] = url
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog([parse(payload)], now=NOW)
    assert "source_requires_public_https_hostname_without_credentials" in {
        issue.code for issue in caught.value.issues
    }
    assert "private-password" not in str(caught.value)


@pytest.mark.parametrize("location", ["provider", "tool", "identity"])
def test_public_url_rule_applies_to_entity_metadata(location: str) -> None:
    payload = catalog_input()
    if location == "provider":
        payload["providers"][0]["website_url"] = "https://example.invalid/"
    elif location == "tool":
        payload["tools"][0]["official_url"] = "https://example.invalid/"
    else:
        payload["tools"][0]["facts"][0]["value"]["official_url"] = "https://example.invalid/"
    assert_issue(payload, "source_requires_public_https_hostname_without_credentials")


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("checked_at", NOW + timedelta(microseconds=1), "checked_at_in_future"),
        ("expires_at", NOW - timedelta(days=1), "expires_at_must_follow_checked_at"),
        ("expires_at", NOW + timedelta(days=89, microseconds=1), "evidence_ttl_exceeded"),
        ("expires_at", NOW, "verified_requires_fresh_evidence"),
    ],
)
def test_evidence_time_boundaries(field: str, value: datetime, code: str) -> None:
    payload = catalog_input()
    payload["tools"][0]["facts"][0]["evidence"][0][field] = value.isoformat()
    assert_issue(payload, code)


def test_pricing_has_30_day_ttl_not_the_90_day_fact_ttl() -> None:
    payload = catalog_input()
    pricing = payload["tools"][0]["facts"][4]
    pricing.update(
        value={
            "model": "paid",
            "currency": "USD",
            "monthly_min": 5,
            "billing_basis": "Monthly",
            "usage_limits": None,
            "free_tier": None,
        },
        verification_status="verified",
        evidence=[source(114, days=30)],
    )
    document = parse(payload)
    validate_catalog([document], now=NOW)
    before = document.model_dump_json()
    pricing["evidence"][0]["expires_at"] = (NOW + timedelta(days=29, microseconds=1)).isoformat()
    assert_issue(payload, "evidence_ttl_exceeded")
    assert document.model_dump_json() == before


def test_future_review_date_is_invalid_even_with_fresh_identity() -> None:
    payload = catalog_input()
    payload["tools"][0]["last_verified_at"] = (NOW + timedelta(seconds=1)).isoformat()
    assert_issue(payload, "review_date_in_future")


def test_expired_unverified_fact_and_unknown_fields_remain_explicit_without_mutation() -> None:
    payload = catalog_input()
    api = payload["tools"][0]["facts"][3]
    api["verification_status"] = "unverified"
    api["evidence"][0]["expires_at"] = NOW.isoformat()
    document = parse(payload)
    before = document.model_dump_json()
    validate_catalog([document], now=NOW)
    assert document.model_dump_json() == before
    assert document.tools[0].facts[3].verification_status == "unverified"
    assert document.tools[0].facts[4].value is None


def test_verified_false_is_allowed_without_positive_model_or_capability_relation() -> None:
    payload = catalog_input()
    payload["tools"][0]["facts"][3]["value"] = False
    document = parse(payload)
    validate_catalog([document], now=NOW)
    assert document.tools[0].facts[3].value is False
    assert document.tools[0].facts[3].verification_status == "verified"
    payload["tools"][0]["facts"][3].update(verification_status="unverified", evidence=[])
    assert_issue(payload, "false_requires_evidence")


def test_invalid_secondary_source_is_not_hidden_by_a_fresh_primary_source() -> None:
    payload = catalog_input()
    evidence = payload["tools"][0]["facts"][0]["evidence"]
    second = source(999)
    second["checked_at"] = (NOW + timedelta(days=1)).isoformat()
    evidence.append(second)
    assert_issue(payload, "checked_at_in_future")


def test_multi_document_references_resolve_before_validation_regardless_of_order() -> None:
    payload = catalog_input()
    tools = {
        **copy.deepcopy(payload),
        "providers": [],
        "models": [],
        "categories": [],
        "capabilities": [],
    }
    vocabulary = {**copy.deepcopy(payload), "tools": []}
    documents = [parse(tools), parse(vocabulary)]
    before = [document.model_dump_json() for document in documents]
    validate_catalog(documents, now=NOW)
    validate_catalog(list(reversed(documents)), now=NOW)
    assert [document.model_dump_json() for document in documents] == before
    duplicate = parse(vocabulary)
    with pytest.raises(CuratedValidationError) as caught:
        validate_catalog([*documents, duplicate], now=NOW)
    assert any(
        issue.field.startswith("documents[2].") and issue.code == "duplicate_id"
        for issue in caught.value.issues
    )


def test_integrations_resolve_catalog_targets_but_allow_named_external_targets() -> None:
    payload = catalog_input()
    integration = fact(
        15,
        "integration:external-api",
        {
            "target_tool_id": None,
            "target_name": "External service",
            "mechanism": "API",
            "conditions": [],
        },
    )
    payload["tools"][0]["facts"].append(integration)
    validate_catalog([parse(payload)], now=NOW)
    integration["value"]["target_tool_id"] = uid(999)
    assert_issue(payload, "unknown_reference")
    integration["value"]["target_tool_id"] = uid(5)
    assert_issue(payload, "integration_target_name_mismatch")


def test_snapshot_supports_external_references_and_detects_key_conflicts_without_mutation() -> None:
    payload = catalog_input()
    category = payload["categories"].pop()
    entity = ReferenceEntity(UUID(category["id"]), category["slug"], category["name"])
    snapshot = CatalogSnapshot(categories={entity.id: entity})
    validate_catalog([parse(payload)], now=NOW, existing=snapshot)
    payload["categories"] = [{**category, "id": uid(999)}]
    assert_issue(payload, "duplicate_key", existing=snapshot)
    assert snapshot.categories == {entity.id: entity}
    payload["categories"] = [{**category, "slug": "renamed-category"}]
    document = parse(payload)
    validate_catalog([document], now=NOW, existing=snapshot)
    assert document.categories[0].id == entity.id
    assert snapshot.categories[entity.id].key == "coding-development"


def snapshot_for_api(
    payload: dict[str, Any], *, revision: int = 2, source_revision: int = 2
) -> CatalogSnapshot:
    document = parse(payload)
    api = document.tools[0].facts[3]
    stored = StoredFact(
        api.id, document.tools[0].id, api.key, api.model_dump(mode="json")["value"], revision
    )
    evidence = StoredEvidence(api.id, source_revision, api.evidence[0])
    return CatalogSnapshot(facts={api.id: stored}, evidence={api.evidence[0].id: evidence})


@pytest.mark.parametrize("change", ["owner", "key", "id"])
def test_existing_fact_identity_is_stable(change: str) -> None:
    payload = catalog_input()
    snapshot = snapshot_for_api(payload)
    if change == "owner":
        payload["tools"][0]["id"] = uid(999)
        code = "fact_owner_and_key_are_immutable"
    elif change == "key":
        payload["tools"][0]["facts"][3]["key"] = "offline_supported"
        code = "fact_owner_and_key_are_immutable"
    else:
        payload["tools"][0]["facts"][3]["id"] = uid(999)
        code = "fact_id_must_remain_stable"
    assert_issue(payload, code, existing=snapshot)


@pytest.mark.parametrize("change", ["value", "old_revision", "owner", "source_metadata"])
def test_evidence_is_immutable_and_cannot_recertify_a_different_value(change: str) -> None:
    payload = catalog_input()
    snapshot = snapshot_for_api(payload, source_revision=1 if change == "old_revision" else 2)
    api = payload["tools"][0]["facts"][3]
    if change == "value":
        api["value"] = False
        code = "evidence_cannot_certify_new_value_or_old_revision"
    elif change == "old_revision":
        code = "evidence_cannot_certify_new_value_or_old_revision"
    elif change == "owner":
        api["id"] = uid(999)
        code = "evidence_owner_is_immutable"
    else:
        api["evidence"][0]["checked_by"] = "Different reviewer"
        code = "evidence_content_is_immutable"
    assert_issue(payload, code, existing=snapshot)


def test_reimport_preserves_evidence_but_changed_fact_requires_new_evidence_id() -> None:
    payload = catalog_input()
    snapshot = snapshot_for_api(payload)
    document = parse(payload)
    before = document.model_dump_json()
    validate_catalog([document], now=NOW, existing=snapshot)
    validate_catalog([document], now=NOW, existing=snapshot)
    assert document.model_dump_json() == before
    api = payload["tools"][0]["facts"][3]
    api["value"] = False
    assert_issue(payload, "evidence_cannot_certify_new_value_or_old_revision", existing=snapshot)
    api["evidence"][0]["id"] = uid(999)
    changed = parse(payload)
    validate_catalog([changed], now=NOW, existing=snapshot)
    assert changed.tools[0].facts[3].value is False
    assert snapshot.facts[UUID(uid(13))].value is True


def test_validation_clock_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="validation_clock_requires_timezone"):
        validate_catalog([parse(catalog_input())], now=NOW.replace(tzinfo=None))


def test_checked_at_now_is_valid_but_future_microsecond_is_not() -> None:
    payload = catalog_input()
    evidence = payload["tools"][0]["facts"][0]["evidence"][0]
    evidence["checked_at"] = NOW.isoformat()
    evidence["expires_at"] = (NOW + timedelta(days=90)).isoformat()
    document = parse(payload)
    validate_catalog([document], now=NOW)
    assert document.tools[0].facts[0].evidence[0].checked_at == NOW
    evidence["checked_at"] = (NOW + timedelta(microseconds=1)).isoformat()
    assert_issue(payload, "checked_at_in_future")


def test_numeric_equivalence_does_not_force_evidence_rebinding() -> None:
    payload = catalog_input()
    payload["tools"][0]["facts"].append(fact(15, "min_ram_gb", 8))
    document = parse(payload)
    ram = document.tools[0].facts[-1]
    snapshot = CatalogSnapshot(
        facts={ram.id: StoredFact(ram.id, document.tools[0].id, ram.key, 8, 2)},
        evidence={ram.evidence[0].id: StoredEvidence(ram.id, 2, ram.evidence[0])},
    )
    validate_catalog([document], now=NOW, existing=snapshot)
    assert ram.model_dump(mode="json")["value"] == 8.0
    payload["tools"][0]["facts"][-1]["value"] = 9
    assert_issue(payload, "evidence_cannot_certify_new_value_or_old_revision", existing=snapshot)


def test_json_boolean_is_not_equivalent_to_a_stored_json_number() -> None:
    payload = catalog_input()
    document = parse(payload)
    api = document.tools[0].facts[3]
    snapshot = CatalogSnapshot(
        facts={api.id: StoredFact(api.id, document.tools[0].id, api.key, 1, 2)},
        evidence={api.evidence[0].id: StoredEvidence(api.id, 2, api.evidence[0])},
    )
    assert_issue(payload, "evidence_cannot_certify_new_value_or_old_revision", existing=snapshot)
