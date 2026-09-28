from decimal import Decimal
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded only on the server side."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    database_url: SecretStr | None = None

    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: SecretStr | None = None
    session_secret: SecretStr | None = None

    llm_provider: Literal["google_gemini"] = "google_gemini"
    llm_model: str = "gemini-3.5-flash-lite"
    embedding_provider: Literal["google_gemini"] = "google_gemini"
    embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = Field(default=1536, gt=0)
    gemini_api_key: SecretStr | None = None
    gemini_request_timeout_ms: int = Field(default=20_000, ge=1, le=30_000)
    gemini_max_output_tokens: int = Field(default=2048, ge=1)
    run_live_ai_tests: bool = False
    ai_monthly_budget_usd: Decimal | None = Field(default=None, ge=0)

    def database_url_value(self) -> str | None:
        if self.database_url is None:
            return None
        return self.database_url.get_secret_value()
