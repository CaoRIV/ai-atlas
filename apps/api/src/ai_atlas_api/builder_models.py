import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_atlas_api.catalog_models import ToolSummary
from ai_atlas_api.constraints import BuilderConstraints as _BuilderConstraints
from ai_atlas_api.constraints import ConstraintDecision as _ConstraintDecision
from ai_atlas_api.constraints import ConstraintName as _ConstraintName
from ai_atlas_api.constraints import DecisionReason as _DecisionReason

BuilderStatus = Literal["complete", "partial", "no_match", "needs_clarification"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BuilderLiteRequest(StrictModel):
    objective: str = Field(min_length=10, max_length=4000)
    constraints: _BuilderConstraints = Field(default_factory=_BuilderConstraints)

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


class BuilderCandidate(StrictModel):
    tool: ToolSummary
    decisions: list[_ConstraintDecision]
    evidence: list[EvidenceReference]


class ExcludedCandidate(StrictModel):
    tool: ToolSummary
    decisions: list[_ConstraintDecision]


class DataGap(StrictModel):
    tool_id: UUID | None
    tool_name: str | None
    constraint: _ConstraintName
    reason: _DecisionReason


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
