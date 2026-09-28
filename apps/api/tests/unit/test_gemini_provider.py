from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from ai_atlas_api.config import Settings
from ai_atlas_api.providers.gemini import (
    GeminiProvider,
    GeminiRequestError,
    GeminiResponseError,
)


class ExamplePayload(BaseModel):
    answer: str


class StubModels:
    def __init__(self) -> None:
        self.generate_calls: list[dict[str, Any]] = []
        self.embed_calls: list[dict[str, Any]] = []
        self.generation_response: Any = SimpleNamespace(
            parsed={"answer": "grounded"},
            text='{"answer":"grounded"}',
            usage_metadata=SimpleNamespace(
                prompt_token_count=11,
                candidates_token_count=5,
                thoughts_token_count=2,
                total_token_count=18,
            ),
        )
        self.embedding_response: Any = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])]
        )

    def generate_content(self, **kwargs: Any) -> Any:
        self.generate_calls.append(kwargs)
        if isinstance(self.generation_response, Exception):
            raise self.generation_response
        return self.generation_response

    def embed_content(self, **kwargs: Any) -> Any:
        self.embed_calls.append(kwargs)
        if isinstance(self.embedding_response, Exception):
            raise self.embedding_response
        return self.embedding_response


class StubClient:
    def __init__(self) -> None:
        self.models = StubModels()


def make_provider(client: StubClient, *, dimension: int = 3) -> GeminiProvider:
    return GeminiProvider(
        client=client,
        generation_model="gemini-3.5-flash-lite",
        embedding_model="gemini-embedding-2",
        embedding_dim=dimension,
        max_output_tokens=128,
    )


def test_generate_structured_uses_configured_model_schema_and_usage() -> None:
    client = StubClient()
    provider = make_provider(client)

    result = provider.generate_structured("Return a small answer.", ExamplePayload)

    assert result.payload == ExamplePayload(answer="grounded")
    assert result.model == "gemini-3.5-flash-lite"
    assert result.usage.input_tokens == 11
    assert result.usage.output_tokens == 7
    assert result.usage.total_tokens == 18
    call = client.models.generate_calls[0]
    assert call["model"] == "gemini-3.5-flash-lite"
    assert call["contents"] == "Return a small answer."
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_schema is ExamplePayload
    assert call["config"].temperature == 0
    assert call["config"].max_output_tokens == 128


def test_generation_can_apply_a_smaller_output_cap() -> None:
    client = StubClient()
    provider = make_provider(client)

    provider.generate_structured("Return a small answer.", ExamplePayload, max_output_tokens=32)

    assert client.models.generate_calls[0]["config"].max_output_tokens == 32


def test_production_factory_sets_a_bounded_request_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    client = StubClient()

    def client_factory(**kwargs: Any) -> StubClient:
        captured.update(kwargs)
        return client

    monkeypatch.setattr("ai_atlas_api.providers.gemini.genai.Client", client_factory)
    settings = Settings(
        _env_file=None,
        gemini_api_key="test-key",
        gemini_request_timeout_ms=12_000,
        gemini_max_output_tokens=256,
    )

    provider = GeminiProvider.from_settings(settings)
    provider.generate_structured("Return a small answer.", ExamplePayload)

    assert captured["http_options"].timeout == 12_000
    assert client.models.generate_calls[0]["config"].max_output_tokens == 256


def test_embed_uses_configured_model_dimension_and_task_type() -> None:
    client = StubClient()
    provider = make_provider(client)

    result = provider.embed(["catalog document"], task_type="RETRIEVAL_DOCUMENT")

    assert result.model == "gemini-embedding-2"
    assert result.dimension == 3
    assert result.vectors == [[0.1, 0.2, 0.3]]
    call = client.models.embed_calls[0]
    assert call["model"] == "gemini-embedding-2"
    assert call["contents"] == ["catalog document"]
    assert call["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert call["config"].output_dimensionality == 3


def test_embed_rejects_an_unexpected_vector_dimension() -> None:
    client = StubClient()
    provider = make_provider(client, dimension=1536)

    with pytest.raises(GeminiResponseError, match="unexpected dimension"):
        provider.embed(["catalog document"])


def test_provider_wraps_sdk_errors_without_exposing_the_original_message() -> None:
    client = StubClient()
    client.models.generation_response = RuntimeError("secret upstream payload")
    provider = make_provider(client)

    with pytest.raises(GeminiRequestError) as captured:
        provider.generate_structured("prompt", ExamplePayload)

    assert str(captured.value) == "Gemini generation request failed."
    assert "secret upstream payload" not in str(captured.value)
