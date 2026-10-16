from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_atlas_api.catalog_models import Platform

ConstraintName = Literal[
    "platform",
    "ram_gb",
    "deployment",
    "offline_required",
    "api_required",
    "budget_usd_month",
]
DecisionOutcome = Literal["pass", "fail", "unknown"]
DecisionReason = Literal[
    "constraint_met",
    "constraint_not_met",
    "fact_missing",
    "fact_not_verified",
    "pricing_not_comparable",
    "monthly_usage_required",
]
DeploymentConstraint = Literal["cloud_allowed", "local_only"]
RequirementState = Literal["unspecified", "not_required", "required"]

_VALID_DECISION_REASONS: dict[DecisionOutcome, frozenset[DecisionReason]] = {
    "pass": frozenset({"constraint_met"}),
    "fail": frozenset({"constraint_not_met"}),
    "unknown": frozenset(
        {
            "fact_missing",
            "fact_not_verified",
            "pricing_not_comparable",
            "monthly_usage_required",
        }
    ),
}


class _StrictContract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )


class ExecutionContext(_StrictContract):
    """Normalized device and execution requirements for deterministic evaluation."""

    platform: Platform | None
    available_ram_gb: float | None
    deployment: DeploymentConstraint | None
    offline_requirement: RequirementState
    api_requirement: RequirementState


class BuilderConstraints(_StrictContract):
    platform: Platform | None = None
    ram_gb: float | None = Field(default=None, gt=0, le=1024)
    deployment: DeploymentConstraint | None = None
    offline_required: bool | None = None
    api_required: bool | None = None
    budget_usd_month: float | None = Field(default=None, ge=0, le=1_000_000)
    monthly_usage: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def reject_usage_without_budget(self) -> Self:
        if self.monthly_usage is not None and self.budget_usd_month is None:
            raise ValueError("monthly_usage_requires_budget")
        return self

    def to_execution_context(self) -> ExecutionContext:
        return ExecutionContext(
            platform=self.platform,
            available_ram_gb=self.ram_gb,
            deployment=self.deployment,
            offline_requirement=_requirement_state(self.offline_required),
            api_requirement=_requirement_state(self.api_required),
        )


class ConstraintDecision(_StrictContract):
    constraint: ConstraintName
    outcome: DecisionOutcome
    reason: DecisionReason
    fact_key: str | None
    evidence_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_tri_state_reason(self) -> Self:
        if self.reason not in _VALID_DECISION_REASONS[self.outcome]:
            raise ValueError("decision_reason_does_not_match_outcome")
        if self.outcome == "unknown" and self.evidence_ids:
            raise ValueError("unknown_decision_cannot_claim_evidence")
        return self


def _requirement_state(value: bool | None) -> RequirementState:
    if value is None:
        return "unspecified"
    return "required" if value else "not_required"
