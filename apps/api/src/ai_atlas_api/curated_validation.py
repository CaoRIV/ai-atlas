import ipaddress
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypeAlias
from uuid import UUID

from pydantic import HttpUrl, JsonValue

from ai_atlas_api.curated_models import (
    CapabilityFact,
    CuratedCapability,
    CuratedCatalog,
    CuratedCategory,
    CuratedEvidence,
    CuratedFact,
    CuratedModelEntity,
    CuratedProvider,
    CuratedTool,
    IdentityFact,
    IntegrationFact,
    ModelUsageFact,
    OpenSourceFact,
)


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    code: str


class CuratedValidationError(ValueError):
    def __init__(self, issues: Sequence[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.field}: {issue.code}" for issue in self.issues))


@dataclass(frozen=True)
class ReferenceEntity:
    id: UUID
    key: str
    name: str


@dataclass(frozen=True)
class StoredFact:
    id: UUID
    tool_id: UUID
    key: str
    value: JsonValue
    revision: int


@dataclass(frozen=True)
class StoredEvidence:
    fact_id: UUID
    fact_revision: int
    source: CuratedEvidence


@dataclass(frozen=True)
class CatalogSnapshot:
    providers: Mapping[UUID, ReferenceEntity] = field(default_factory=dict)
    models: Mapping[UUID, ReferenceEntity] = field(default_factory=dict)
    categories: Mapping[UUID, ReferenceEntity] = field(default_factory=dict)
    capabilities: Mapping[UUID, ReferenceEntity] = field(default_factory=dict)
    tools: Mapping[UUID, ReferenceEntity] = field(default_factory=dict)
    facts: Mapping[UUID, StoredFact] = field(default_factory=dict)
    evidence: Mapping[UUID, StoredEvidence] = field(default_factory=dict)
    # Import-owned content; validation-only snapshots may omit it, diff must not.
    records: Mapping[str, Mapping[UUID, Mapping[str, JsonValue]]] = field(default_factory=dict)


Entity: TypeAlias = (
    CuratedProvider | CuratedModelEntity | CuratedCategory | CuratedCapability | CuratedTool
)


def same_json_value(left: JsonValue, right: JsonValue) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            same_json_value(value, right[key]) for key, value in left.items()
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            same_json_value(a, b) for a, b in zip(left, right, strict=True)
        )
    return type(left) is type(right) and left == right


def _source_is_public_https(url: HttpUrl) -> bool:
    if url.scheme != "https" or url.username is not None or url.password is not None:
        return False
    host = (url.host or "").rstrip(".").lower()
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        return False
    labels = host.split(".")
    if len(labels) < 2 or any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels
    ):
        return False
    if labels[-1] in ("localhost", "local", "internal", "invalid", "test", "example"):
        return False
    return not any(
        host == reserved or host.endswith("." + reserved)
        for reserved in ("example.com", "example.net", "example.org")
    )


class _CatalogValidation:
    def __init__(self, existing: CatalogSnapshot, now: datetime) -> None:
        self.existing = existing
        self.now = now
        self.issues: list[ValidationIssue] = []
        self.entities: dict[str, dict[UUID, ReferenceEntity]] = {
            "providers": dict(existing.providers),
            "models": dict(existing.models),
            "categories": dict(existing.categories),
            "capabilities": dict(existing.capabilities),
            "tools": dict(existing.tools),
        }
        self.by_key: dict[str, dict[str, ReferenceEntity]] = {}
        self.fact_ids: set[UUID] = set()
        self.evidence_ids: set[UUID] = set()
        self.stored_fact_keys = {
            (fact.tool_id, fact.key): fact.id for fact in existing.facts.values()
        }

    def error(self, path: str, code: str) -> None:
        self.issues.append(ValidationIssue(path, code))

    def source(self, url: HttpUrl, path: str) -> bool:
        valid = _source_is_public_https(url)
        if not valid:
            self.error(path, "source_requires_public_https_hostname_without_credentials")
        return valid

    def reference(self, identifier: UUID | None, table: str, path: str) -> bool:
        if identifier is not None and identifier not in self.entities[table]:
            self.error(path, "unknown_reference")
            return False
        return True

    def references(self, identifiers: Sequence[UUID], table: str, path: str) -> None:
        seen: set[UUID] = set()
        for index, identifier in enumerate(identifiers):
            location = f"{path}[{index}]"
            if identifier in seen:
                self.error(location, "duplicate_relation")
            seen.add(identifier)
            self.reference(identifier, table, location)

    def index(self, documents: Sequence[CuratedCatalog]) -> None:
        seen: dict[str, set[UUID]] = {table: set() for table in self.entities}
        locations: dict[tuple[str, UUID], str] = {}
        for document_index, document in enumerate(documents):
            collections: tuple[tuple[str, Sequence[Entity]], ...] = (
                ("providers", document.providers),
                ("models", document.models),
                ("categories", document.categories),
                ("capabilities", document.capabilities),
                ("tools", document.tools),
            )
            for table, entities in collections:
                for index, entity in enumerate(entities):
                    path = f"documents[{document_index}].{table}[{index}]"
                    if entity.id in seen[table]:
                        self.error(path + ".id", "duplicate_id")
                        continue
                    seen[table].add(entity.id)
                    key = entity.key if isinstance(entity, CuratedCapability) else entity.slug
                    self.entities[table][entity.id] = ReferenceEntity(entity.id, key, entity.name)
                    locations[table, entity.id] = path
        for table, indexed_entities in self.entities.items():
            by_key: dict[str, ReferenceEntity] = {}
            for reference_entity in indexed_entities.values():
                if reference_entity.key in by_key:
                    other = by_key[reference_entity.key]
                    location = locations.get((table, reference_entity.id)) or locations.get(
                        (table, other.id)
                    )
                    suffix = ".key" if table == "capabilities" else ".slug"
                    self.error((location or f"existing.{table}") + suffix, "duplicate_key")
                by_key[reference_entity.key] = reference_entity
            self.by_key[table] = by_key

    def evidence(self, fact: CuratedFact, source: CuratedEvidence, path: str) -> bool:
        valid = self.source(source.source_url, path + ".source_url")
        if source.id in self.evidence_ids:
            self.error(path + ".id", "duplicate_evidence_id")
            valid = False
        self.evidence_ids.add(source.id)
        window = source.expires_at - source.checked_at
        ttl = timedelta(days=30 if fact.key == "pricing" else 90)
        if window <= timedelta(0):
            self.error(path + ".expires_at", "expires_at_must_follow_checked_at")
            valid = False
        elif window > ttl:
            self.error(path + ".expires_at", "evidence_ttl_exceeded")
            valid = False
        if source.checked_at > self.now:
            self.error(path + ".checked_at", "checked_at_in_future")
            valid = False
        stored_source = self.existing.evidence.get(source.id)
        if stored_source is not None:
            stored_fact = self.existing.facts.get(fact.id)
            if stored_source.fact_id != fact.id:
                self.error(path + ".id", "evidence_owner_is_immutable")
                valid = False
            elif (
                stored_fact is None
                or stored_source.fact_revision != stored_fact.revision
                or not same_json_value(stored_fact.value, fact.model_dump(mode="json")["value"])
            ):
                self.error(path + ".id", "evidence_cannot_certify_new_value_or_old_revision")
                valid = False
            if source != stored_source.source:
                self.error(path + ".id", "evidence_content_is_immutable")
                valid = False
        return valid and source.checked_at <= self.now < source.expires_at

    def fact(self, tool: CuratedTool, fact: CuratedFact, path: str) -> bool:
        if fact.id in self.fact_ids:
            self.error(path + ".id", "duplicate_fact_id")
        self.fact_ids.add(fact.id)
        stored_fact = self.existing.facts.get(fact.id)
        if stored_fact is not None and (
            stored_fact.tool_id != tool.id or stored_fact.key != fact.key
        ):
            self.error(path + ".id", "fact_owner_and_key_are_immutable")
        stored_id = self.stored_fact_keys.get((tool.id, fact.key))
        if stored_id is not None and stored_id != fact.id:
            self.error(path + ".id", "fact_id_must_remain_stable")
        fresh = False
        for index, source in enumerate(fact.evidence):
            # Validate every source, not just the first fresh one.
            usable = self.evidence(fact, source, f"{path}.evidence[{index}]")
            fresh = fresh or usable
        verified = fact.verification_status == "verified" and fresh
        if fact.verification_status == "verified" and not fresh:
            self.error(path + ".verification_status", "verified_requires_fresh_evidence")
        negative = fact.value is False or (
            isinstance(fact, OpenSourceFact)
            and fact.value is not None
            and fact.value.status is False
        )
        if negative and not fact.evidence:
            self.error(path + ".evidence", "false_requires_evidence")
        if isinstance(fact, CapabilityFact):
            if fact.key.removeprefix("capability:") not in self.by_key["capabilities"]:
                self.error(path + ".key", "unknown_capability_key")
        elif isinstance(fact, ModelUsageFact):
            if fact.key.removeprefix("model_usage:") not in self.by_key["models"]:
                self.error(path + ".key", "unknown_model_slug")
        elif isinstance(fact, IdentityFact) and fact.value is not None:
            identity_value = fact.value
            self.source(identity_value.official_url, path + ".value.official_url")
            self.reference(identity_value.provider_id, "providers", path + ".value.provider_id")
            if (
                identity_value.name != tool.name
                or identity_value.description != tool.description
                or identity_value.official_url != tool.official_url
                or identity_value.provider_id != tool.provider_id
            ):
                self.error(path + ".value", "identity_does_not_match_tool")
        elif isinstance(fact, IntegrationFact) and fact.value is not None:
            integration_value = fact.value
            if (
                self.reference(
                    integration_value.target_tool_id, "tools", path + ".value.target_tool_id"
                )
                and integration_value.target_tool_id is not None
                and self.entities["tools"][integration_value.target_tool_id].name
                != integration_value.target_name
            ):
                self.error(path + ".value.target_name", "integration_target_name_mismatch")
        return verified

    def tool(self, tool: CuratedTool, path: str) -> None:
        self.source(tool.official_url, path + ".official_url")
        self.reference(tool.provider_id, "providers", path + ".provider_id")
        self.references(tool.category_ids, "categories", path + ".category_ids")
        self.references(tool.model_ids, "models", path + ".model_ids")
        if tool.last_verified_at is not None and tool.last_verified_at > self.now:
            self.error(path + ".last_verified_at", "review_date_in_future")
        by_key: dict[str, CuratedFact] = {}
        by_id: dict[UUID, CuratedFact] = {}
        verified: dict[UUID, bool] = {}
        for index, fact in enumerate(tool.facts):
            location = f"{path}.facts[{index}]"
            if fact.key in by_key:
                self.error(location + ".key", "duplicate_fact_key")
            by_key[fact.key] = fact
            by_id[fact.id] = fact
            verified[fact.id] = self.fact(tool, fact, location)
        if tool.publication_status == "published":
            if not tool.category_ids:
                self.error(path + ".category_ids", "published_requires_category")
            if tool.last_verified_at is None:
                self.error(path + ".last_verified_at", "published_requires_review_date")
            identity = by_key.get("identity")
            if identity is None or not verified.get(identity.id, False):
                self.error(path + ".facts", "published_requires_verified_identity")
        seen_capabilities: set[UUID] = set()
        for index, relation in enumerate(tool.capabilities):
            location = f"{path}.capabilities[{index}]"
            if relation.capability_id in seen_capabilities:
                self.error(location + ".capability_id", "duplicate_relation")
            seen_capabilities.add(relation.capability_id)
            known = self.reference(
                relation.capability_id, "capabilities", location + ".capability_id"
            )
            capability_fact = by_id.get(relation.fact_id)
            if capability_fact is None:
                self.error(location + ".fact_id", "capability_fact_must_belong_to_tool")
            elif known:
                key = "capability:" + self.entities["capabilities"][relation.capability_id].key
                if not isinstance(capability_fact, CapabilityFact) or capability_fact.key != key:
                    self.error(location + ".fact_id", "capability_fact_key_mismatch")
                elif capability_fact.value is not True or not verified[capability_fact.id]:
                    self.error(location + ".fact_id", "relation_requires_verified_true_fresh_fact")
        for index, model_id in enumerate(tool.model_ids):
            model = self.entities["models"].get(model_id)
            if model is None:
                continue
            model_fact = by_key.get("model_usage:" + model.key)
            if (
                model_fact is None
                or model_fact.value is not True
                or not verified.get(model_fact.id, False)
            ):
                self.error(
                    f"{path}.model_ids[{index}]", "relation_requires_verified_true_fresh_fact"
                )


def validate_catalog(
    documents: Sequence[CuratedCatalog],
    *,
    now: datetime,
    existing: CatalogSnapshot | None = None,
) -> None:
    """Validate a proposed catalog against one clock and optional read-only DB snapshot."""
    if now.utcoffset() is None:
        raise ValueError("validation_clock_requires_timezone")
    validation = _CatalogValidation(existing or CatalogSnapshot(), now)
    validation.index(documents)
    for document_index, document in enumerate(documents):
        prefix = f"documents[{document_index}]"
        for index, provider in enumerate(document.providers):
            if provider.website_url is not None:
                validation.source(provider.website_url, f"{prefix}.providers[{index}].website_url")
        for index, model in enumerate(document.models):
            validation.reference(
                model.provider_id, "providers", f"{prefix}.models[{index}].provider_id"
            )
        for index, tool in enumerate(document.tools):
            validation.tool(tool, f"{prefix}.tools[{index}]")
    if validation.issues:
        raise CuratedValidationError(validation.issues)
