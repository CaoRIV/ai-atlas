from pydantic import SecretStr

from ai_atlas_api.config import Settings
from ai_atlas_api.providers.gemini import GeminiConfigurationError, GeminiProvider


def test_settings_can_start_without_a_gemini_key() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "google_gemini"
    assert settings.embedding_provider == "google_gemini"
    assert settings.embedding_dim == 1536
    assert settings.gemini_request_timeout_ms == 20_000
    assert settings.gemini_max_output_tokens == 2048
    assert settings.gemini_api_key is None


def test_settings_masks_the_gemini_key() -> None:
    settings = Settings(_env_file=None, gemini_api_key=SecretStr("super-secret"))

    assert "super-secret" not in repr(settings)
    assert "super-secret" not in str(settings)


def test_settings_masks_database_credentials() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://ai_atlas:database-secret@127.0.0.1:5432/ai_atlas",
    )

    assert "database-secret" not in repr(settings)
    assert "database-secret" not in settings.model_dump_json()


def test_production_provider_factory_requires_a_gemini_key() -> None:
    settings = Settings(_env_file=None, gemini_api_key=None)

    try:
        GeminiProvider.from_settings(settings)
    except GeminiConfigurationError as error:
        assert str(error) == "GEMINI_API_KEY is required for Gemini requests."
    else:
        raise AssertionError("Expected missing Gemini credentials to fail closed")


def test_example_environment_accepts_an_unset_optional_budget() -> None:
    settings = Settings(_env_file=".env.example")

    assert settings.ai_monthly_budget_usd is None
