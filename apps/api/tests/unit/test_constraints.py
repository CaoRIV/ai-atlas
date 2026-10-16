from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_atlas_api.constraints import BuilderConstraints, ConstraintDecision


@pytest.mark.parametrize(
    "payload",
    [
        {"ram_gb": "8"},
        {"offline_required": 1},
        {"budget_usd_month": "10"},
        {"deployment": "local"},
        {"unsupported": True},
    ],
)
def test_constraints_reject_coercion_and_unknown_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        BuilderConstraints.model_validate(payload)


def test_execution_context_preserves_boolean_intent() -> None:
    omitted = BuilderConstraints().to_execution_context()
    explicit_null = BuilderConstraints(
        offline_required=None,
        api_required=None,
    ).to_execution_context()
    declared = BuilderConstraints(
        platform="windows",
        ram_gb=8,
        deployment="local_only",
        offline_required=True,
        api_required=False,
    ).to_execution_context()

    assert omitted == explicit_null
    assert omitted.offline_requirement == omitted.api_requirement == "unspecified"
    assert declared.model_dump() == {
        "platform": "windows",
        "available_ram_gb": 8.0,
        "deployment": "local_only",
        "offline_requirement": "required",
        "api_requirement": "not_required",
    }


def test_usage_is_normalized_but_requires_a_budget() -> None:
    constraints = BuilderConstraints(
        budget_usd_month=10,
        monthly_usage="  100 requests  ",
    )
    assert constraints.monthly_usage == "100 requests"

    with pytest.raises(ValidationError, match="monthly_usage_requires_budget"):
        BuilderConstraints(monthly_usage="100 requests")


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        ("pass", "constraint_not_met"),
        ("fail", "fact_missing"),
        ("unknown", "constraint_met"),
    ],
)
def test_decision_rejects_reason_outcome_mismatches(outcome: str, reason: str) -> None:
    with pytest.raises(ValidationError, match="decision_reason_does_not_match_outcome"):
        ConstraintDecision.model_validate(
            {
                "constraint": "platform",
                "outcome": outcome,
                "reason": reason,
                "fact_key": "platforms",
                "evidence_ids": [],
            }
        )


def test_unknown_decision_cannot_claim_verified_evidence() -> None:
    decision = ConstraintDecision(
        constraint="platform",
        outcome="unknown",
        reason="fact_missing",
        fact_key="platforms",
    )
    assert decision.outcome == "unknown"

    with pytest.raises(ValidationError, match="unknown_decision_cannot_claim_evidence"):
        ConstraintDecision(
            constraint="platform",
            outcome="unknown",
            reason="fact_not_verified",
            fact_key="platforms",
            evidence_ids=[uuid4()],
        )
