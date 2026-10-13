import unicodedata
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_atlas_api.catalog_models import Platform, ToolSummary

BuilderStatus = Literal["complete", "partial", "no_match", "needs_clarification"]
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


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BuilderConstraints(StrictModel):
    platform: Platform | None = None
    ram_gb: float | None = Field(default=None, gt=0, le=1024)
    deployment: Literal["cloud_allowed", "local_only"] | None = None
    offline_required: bool | None = None
    api_required: bool | None = None
    budget_usd_month: float | None = Field(default=None, ge=0, le=1_000_000)
    monthly_usage: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def reject_usage_without_budget(self) -> Self:
        if self.monthly_usage is not None and self.budget_usd_month is None:
            raise ValueError("monthly_usage_requires_budget")
        return self


class BuilderLiteRequest(StrictModel):
    objective: str = Field(min_length=10, max_length=4000)
    constraints: BuilderConstraints = Field(default_factory=BuilderConstraints)

    @field_validator("objective", mode="before")
    @classmethod
    def normalize_objective(cls, value: object) -> object:
        return unicodedata.normalize("NFC", value.strip()) if isinstance(value, str) else value


class EvidenceReference(StrictModel):
    id: UUID
    fact_key: str
    source_url: str
    checked_at: datetime
    expires_at: datetime


class ConstraintDecision(StrictModel):
    constraint: ConstraintName
    outcome: DecisionOutcome
    reason: DecisionReason
    fact_key: str | None
    evidence_ids: list[UUID] = Field(default_factory=list)


class BuilderCandidate(StrictModel):
    tool: ToolSummary
    decisions: list[ConstraintDecision]
    evidence: list[EvidenceReference]


class ExcludedCandidate(StrictModel):
    tool: ToolSummary
    decisions: list[ConstraintDecision]


class DataGap(StrictModel):
    tool_id: UUID | None
    tool_name: str | None
    constraint: ConstraintName
    reason: DecisionReason


class BuilderLiteResult(StrictModel):
    status: BuilderStatus
    objective_summary: str
    candidates: list[BuilderCandidate] = Field(max_length=30)
    exclusions: list[ExcludedCandidate] = Field(max_length=30)
    data_gaps: list[DataGap] = Field(max_length=180)
    limitations: list[str] = Field(max_length=10)


class BuilderLiteResponse(StrictModel):
    data: BuilderLiteResult
    request_id: UUID
