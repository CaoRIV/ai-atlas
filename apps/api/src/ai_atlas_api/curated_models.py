import unicodedata
from datetime import UTC, datetime
from typing import Annotated, Literal, Self, TypeAlias
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    UrlConstraints,
    field_validator,
    model_validator,
)

from ai_atlas_api.catalog_models import Platform, PricingModel, VerificationStatus


def normalize_text(value: object) -> object:
    return unicodedata.normalize("NFC", value.strip()) if isinstance(value, str) else value


ShortText = Annotated[str, BeforeValidator(normalize_text), Field(min_length=1, max_length=200)]
LongText = Annotated[str, BeforeValidator(normalize_text), Field(min_length=1, max_length=4000)]
Slug = Annotated[
    str,
    BeforeValidator(normalize_text),
    Field(min_length=1, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
]
CapabilityKey = Annotated[
    str,
    BeforeValidator(normalize_text),
    Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"),
]
HttpsUrl = Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"], max_length=2048)]
NonNegativeNumber = Annotated[float, Field(ge=0)]


class CuratedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @field_validator("*", mode="after")
    @classmethod
    def timestamps_in_utc(cls, value: object) -> object:
        return value.astimezone(UTC) if isinstance(value, datetime) else value


class CuratedProvider(CuratedModel):
    id: UUID
    slug: Slug
    name: ShortText
    website_url: HttpsUrl | None


class CuratedModelEntity(CuratedModel):
    id: UUID
    slug: Slug
    name: ShortText
    provider_id: UUID | None


class CuratedCategory(CuratedModel):
    id: UUID
    slug: Slug
    name: ShortText


class CuratedCapability(CuratedModel):
    id: UUID
    key: CapabilityKey
    name: ShortText
    description: LongText


class CuratedEvidence(CuratedModel):
    id: UUID
    source_url: HttpsUrl
    source_kind: Literal["official_docs", "official_pricing", "official_site"]
    checked_at: AwareDatetime
    expires_at: AwareDatetime
    checked_by: ShortText
    excerpt: Annotated[str, BeforeValidator(normalize_text), Field(max_length=1000)] | None = None


class PricingValue(CuratedModel):
    model: PricingModel
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None
    monthly_min: NonNegativeNumber | None
    billing_basis: LongText | None
    usage_limits: LongText | None
    free_tier: bool | None


class OpenSourceValue(CuratedModel):
    status: bool | None
    license: ShortText | None


class IdentityValue(CuratedModel):
    name: ShortText
    description: LongText
    official_url: HttpsUrl
    provider_id: UUID | None


class IntegrationValue(CuratedModel):
    target_tool_id: UUID | None
    target_name: ShortText
    mechanism: LongText | None
    conditions: list[LongText] | None


class CuratedFactBase(CuratedModel):
    id: UUID
    verification_status: VerificationStatus
    value: object
    evidence: list[CuratedEvidence]
    curation_notes: (
        Annotated[str, BeforeValidator(normalize_text), Field(max_length=2000)] | None
    ) = None

    @model_validator(mode="after")
    def unknown_requires_null(self) -> Self:
        if (self.value is None) != (self.verification_status == "unknown"):
            raise ValueError("null_value_requires_unknown_status_and_unknown_requires_null")
        return self


class PricingFact(CuratedFactBase):
    key: Literal["pricing"]
    value: PricingValue | None


class PlatformsFact(CuratedFactBase):
    key: Literal["platforms"]
    value: list[Platform] | None


class BooleanFact(CuratedFactBase):
    key: Literal["api_available", "offline_supported"]
    value: bool | None


class OpenSourceFact(CuratedFactBase):
    key: Literal["open_source"]
    value: OpenSourceValue | None


class DeploymentModesFact(CuratedFactBase):
    key: Literal["deployment_modes"]
    value: list[Literal["cloud", "local"]] | None


class MinRamFact(CuratedFactBase):
    key: Literal["min_ram_gb"]
    value: NonNegativeNumber | None


class IdentityFact(CuratedFactBase):
    key: Literal["identity"]
    value: IdentityValue | None


class CapabilityFact(CuratedFactBase):
    key: Annotated[
        str,
        BeforeValidator(normalize_text),
        Field(max_length=111, pattern=r"^capability:[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"),
    ]
    value: bool | None


class ModelUsageFact(CuratedFactBase):
    key: Annotated[
        str,
        BeforeValidator(normalize_text),
        Field(max_length=112, pattern=r"^model_usage:[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ]
    value: bool | None


class IntegrationFact(CuratedFactBase):
    key: Annotated[
        str,
        BeforeValidator(normalize_text),
        Field(max_length=112, pattern=r"^integration:[a-z0-9]+(?:[-_][a-z0-9]+)*$"),
    ]
    value: IntegrationValue | None


CuratedFact: TypeAlias = Annotated[
    PricingFact
    | PlatformsFact
    | BooleanFact
    | OpenSourceFact
    | DeploymentModesFact
    | MinRamFact
    | IdentityFact
    | CapabilityFact
    | ModelUsageFact
    | IntegrationFact,
    Field(union_mode="left_to_right"),
]


class CuratedToolCapability(CuratedModel):
    capability_id: UUID
    fact_id: UUID


class CuratedTool(CuratedModel):
    id: UUID
    slug: Slug
    name: ShortText
    description: LongText
    official_url: HttpsUrl
    provider_id: UUID | None
    tags: list[ShortText]
    publication_status: Literal["draft", "published", "archived"]
    last_verified_at: AwareDatetime | None
    category_ids: list[UUID]
    model_ids: list[UUID]
    capabilities: list[CuratedToolCapability]
    facts: list[CuratedFact]
    curation_notes: (
        Annotated[str, BeforeValidator(normalize_text), Field(max_length=2000)] | None
    ) = None


class CuratedCatalog(CuratedModel):
    schema_version: Literal[1]
    providers: list[CuratedProvider]
    models: list[CuratedModelEntity]
    categories: list[CuratedCategory]
    capabilities: list[CuratedCapability]
    tools: list[CuratedTool]

    @field_validator("schema_version", mode="before")
    @classmethod
    def version_is_integer(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version_must_be_integer")
        return value
