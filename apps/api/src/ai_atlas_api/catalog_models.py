import re
import unicodedata
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

PricingModel = Literal["free", "freemium", "paid", "usage_based", "contact", "unknown"]
VerificationStatus = Literal["verified", "unverified", "unknown"]
Platform = Literal["web", "windows", "macos", "linux", "ios", "android"]


class CatalogQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: str = Field(default="", max_length=200)
    category: str | None = Field(
        default=None, max_length=512, description="1-8 slugs, comma-separated"
    )
    platform: Platform | None = None
    pricing_model: PricingModel | None = None
    api_available: bool | None = Field(
        default=None, description="Literal true/false; fresh evidence only"
    )
    open_source: bool | None = Field(
        default=None, description="Literal true/false; fresh evidence only"
    )
    sort: Literal["relevance", "name", "updated"] | None = Field(
        default=None, description="Defaults to relevance with non-empty q, otherwise name"
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("q", "category", "platform", "pricing_model", "sort", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        return unicodedata.normalize("NFC", value.strip()) if isinstance(value, str) else value

    @field_validator("api_available", "open_source", mode="before")
    @classmethod
    def boolean_literal(cls, value: object) -> object:
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip() in ("true", "false"):
            return value.strip() == "true"
        raise ValueError("boolean_must_be_true_or_false")

    @model_validator(mode="after")
    def validate_groups(self) -> Self:
        if self.sort == "relevance" and not self.q:
            raise ValueError("relevance_requires_q")
        if self.category is not None:
            slugs = self.category_slugs
            if not 1 <= len(slugs) <= 8 or any(
                not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs
            ):
                raise ValueError("category_requires_1_to_8_slugs")
        return self

    @property
    def category_slugs(self) -> list[str]:
        return [slug.strip() for slug in self.category.split(",")] if self.category else []

    @property
    def effective_sort(self) -> str:
        return self.sort or ("relevance" if self.q else "name")


class Category(BaseModel):
    id: UUID
    slug: str
    name: str


class PricingSummary(BaseModel):
    model: PricingModel
    verification_status: VerificationStatus


class ToolSummary(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    categories: list[Category]
    pricing: PricingSummary
    last_verified_at: datetime | None


class NamedEntity(BaseModel):
    id: UUID
    name: str


class Fact(BaseModel):
    key: str
    value: JsonValue
    verification_status: VerificationStatus
    evidence_ids: list[UUID]


class Capability(BaseModel):
    key: str
    name: str
    evidence_ids: list[UUID]


class Evidence(BaseModel):
    id: UUID
    fact_key: str
    source_url: str
    checked_at: datetime
    expires_at: datetime


class ToolDetail(ToolSummary):
    official_url: str
    provider: NamedEntity | None
    tags: list[str]
    models: list[NamedEntity]
    capabilities: list[Capability]
    facts: list[Fact]
    evidence: list[Evidence]
    revision: int
    warnings: list[str]


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int


class CategoriesResponse(BaseModel):
    data: list[Category]
    request_id: UUID


class ToolsResponse(BaseModel):
    data: list[ToolSummary]
    pagination: Pagination
    request_id: UUID


class ToolResponse(BaseModel):
    data: ToolDetail
    request_id: UUID


class ErrorDetail(BaseModel):
    field: str
    reason: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: UUID
