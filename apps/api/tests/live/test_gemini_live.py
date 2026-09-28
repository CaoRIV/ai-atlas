import pytest
from pydantic import BaseModel

from ai_atlas_api.config import Settings
from ai_atlas_api.providers.gemini import GeminiProvider


class LivePayload(BaseModel):
    message: str


@pytest.mark.live
def test_gemini_generation_and_embedding_live_smoke() -> None:
    settings = Settings()
    if not settings.run_live_ai_tests:
        pytest.skip("Set RUN_LIVE_AI_TESTS=1 to authorize billed Gemini smoke calls.")

    if settings.gemini_api_key is None:
        pytest.skip("GEMINI_API_KEY is required for the opt-in live smoke test.")

    provider = GeminiProvider.from_settings(settings)
    generation = provider.generate_structured(
        'Return JSON with message exactly "ok".',
        LivePayload,
        max_output_tokens=32,
    )
    embedding = provider.embed(["AI Atlas live smoke test"])

    assert generation.payload.message == "ok"
    assert generation.model == settings.llm_model
    assert generation.usage.total_tokens > 0
    assert embedding.model == settings.embedding_model
    assert embedding.dimension == settings.embedding_dim
    assert len(embedding.vectors) == 1
    print(
        "Gemini live smoke usage: "
        f"generation_model={generation.model}, "
        f"input_tokens={generation.usage.input_tokens}, "
        f"output_tokens={generation.usage.output_tokens}, "
        f"total_tokens={generation.usage.total_tokens}, "
        f"embedding_model={embedding.model}, dimension={embedding.dimension}"
    )
