from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_atlas_api.builder import BuilderLiteService, FactSnapshot, evaluate_constraints
from ai_atlas_api.builder_models import BuilderLiteRequest, EvidenceReference
from ai_atlas_api.catalog import CatalogRepository
from ai_atlas_api.constraints import BuilderConstraints
from ai_atlas_api.retrieval import EmbeddingIndex, EmbeddingProfile, HybridRetriever


def evidence(fact_key: str) -> EvidenceReference:
    now = datetime.now(UTC)
    return EvidenceReference(
        id=uuid4(),
        fact_key=fact_key,
        source_url="https://example.invalid/docs",
        checked_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=1),
    )


def test_request_normalizes_objective_and_rejects_unsupported_fields() -> None:
    request = BuilderLiteRequest(objective="  ho\u0300a công cụ viết nội dung  ")
    assert request.objective == "hòa công cụ viết nội dung"

    with pytest.raises(ValidationError):
        BuilderLiteRequest.model_validate({"objective": "valid objective", "preferences": ["free"]})
    with pytest.raises(ValidationError):
        BuilderLiteRequest.model_validate(
            {
                "objective": "valid objective",
                "constraints": {"monthly_usage": "100 requests"},
            }
        )


def test_hard_constraints_require_current_verified_facts() -> None:
    verified_evidence = evidence("api_available")
    constraints = BuilderConstraints(api_required=True, platform="windows")

    decisions = evaluate_constraints(
        constraints,
        {
            "api_available": FactSnapshot(True, "verified", [verified_evidence]),
            "platforms": FactSnapshot(["windows"], "unverified"),
        },
    )

    assert [(decision.constraint, decision.outcome, decision.reason) for decision in decisions] == [
        ("platform", "unknown", "fact_not_verified"),
        ("api_required", "pass", "constraint_met"),
    ]
    assert decisions[1].evidence_ids == [verified_evidence.id]


def test_budget_only_passes_a_provable_free_plan() -> None:
    free = evaluate_constraints(
        BuilderConstraints(budget_usd_month=0, monthly_usage="100 requests"),
        {"pricing": FactSnapshot({"model": "free"}, "verified", [evidence("pricing")])},
    )[0]
    above_floor = evaluate_constraints(
        BuilderConstraints(budget_usd_month=10, monthly_usage="100 requests"),
        {
            "pricing": FactSnapshot(
                {"model": "paid", "monthly_min": 20, "currency": "USD"},
                "verified",
                [evidence("pricing")],
            )
        },
    )[0]
    ambiguous = evaluate_constraints(
        BuilderConstraints(budget_usd_month=10, monthly_usage="100 requests"),
        {"pricing": FactSnapshot({"model": "paid"}, "verified", [evidence("pricing")])},
    )[0]

    assert (free.outcome, free.reason) == ("pass", "constraint_met")
    assert (above_floor.outcome, above_floor.reason) == ("fail", "constraint_not_met")
    assert (ambiguous.outcome, ambiguous.reason) == ("unknown", "pricing_not_comparable")


def test_budget_without_usage_requests_clarification_before_database_access() -> None:
    repository = CatalogRepository(None)
    retriever = HybridRetriever(
        EmbeddingIndex(repository),
        EmbeddingProfile("google_gemini", "gemini-embedding-2", 1536),
        None,
    )
    service = BuilderLiteService(repository, retriever)
    result = service.build(
        BuilderLiteRequest(
            objective="Find a writing assistant",
            constraints=BuilderConstraints(budget_usd_month=10),
        )
    )

    assert result.status == "needs_clarification"
    assert result.candidates == []
    assert [(gap.constraint, gap.reason) for gap in result.data_gaps] == [
        ("budget_usd_month", "monthly_usage_required")
    ]
