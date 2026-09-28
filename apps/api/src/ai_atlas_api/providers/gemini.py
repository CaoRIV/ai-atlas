from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar, cast

from google import genai
from google.genai import types
from pydantic import BaseModel

from ai_atlas_api.config import Settings

PayloadT = TypeVar("PayloadT", bound=BaseModel)


class GeminiConfigurationError(RuntimeError):
    """Raised when the real Gemini adapter is not configured safely."""


class GeminiRequestError(RuntimeError):
    """Raised when the Gemini SDK request fails."""


class GeminiResponseError(RuntimeError):
    """Raised when Gemini returns a response that violates the adapter contract."""


class ModelsClient(Protocol):
    def generate_content(self, **kwargs: Any) -> Any: ...

    def embed_content(self, **kwargs: Any) -> Any: ...


class ClientProtocol(Protocol):
    models: ModelsClient


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class StructuredGeneration(Generic[PayloadT]):
    payload: PayloadT
    model: str
    usage: TokenUsage


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    model: str
    dimension: int


class GeminiProvider:
    """Thin boundary around the real Gemini Developer API SDK."""

    def __init__(
        self,
        *,
        client: ClientProtocol,
        generation_model: str,
        embedding_model: str,
        embedding_dim: int,
        max_output_tokens: int,
    ) -> None:
        self._client = client
        self._generation_model = generation_model
        self._embedding_model = embedding_model
        self._embedding_dim = embedding_dim
        self._max_output_tokens = max_output_tokens

    @classmethod
    def from_settings(cls, settings: Settings) -> "GeminiProvider":
        if settings.gemini_api_key is None:
            raise GeminiConfigurationError("GEMINI_API_KEY is required for Gemini requests.")

        client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=settings.gemini_request_timeout_ms),
        )
        return cls(
            client=cast(ClientProtocol, client),
            generation_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            embedding_dim=settings.embedding_dim,
            max_output_tokens=settings.gemini_max_output_tokens,
        )

    def generate_structured(
        self,
        prompt: str,
        response_schema: type[PayloadT],
        *,
        max_output_tokens: int | None = None,
    ) -> StructuredGeneration[PayloadT]:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0,
            max_output_tokens=max_output_tokens or self._max_output_tokens,
        )
        try:
            response = self._client.models.generate_content(
                model=self._generation_model,
                contents=prompt,
                config=config,
            )
        except Exception as error:
            raise GeminiRequestError("Gemini generation request failed.") from error

        parsed = getattr(response, "parsed", None)
        try:
            if parsed is not None:
                payload = response_schema.model_validate(parsed)
            else:
                text = getattr(response, "text", None)
                if not isinstance(text, str):
                    raise ValueError("missing structured response")
                payload = response_schema.model_validate_json(text)
        except (ValueError, TypeError) as error:
            raise GeminiResponseError("Gemini returned an invalid structured response.") from error

        return StructuredGeneration(
            payload=payload,
            model=self._generation_model,
            usage=_normalize_usage(getattr(response, "usage_metadata", None)),
        )

    def embed(
        self,
        texts: Sequence[str],
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> EmbeddingBatch:
        if not texts:
            raise ValueError("At least one text is required for embedding.")

        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self._embedding_dim,
        )
        try:
            response = self._client.models.embed_content(
                model=self._embedding_model,
                contents=list(texts),
                config=config,
            )
        except Exception as error:
            raise GeminiRequestError("Gemini embedding request failed.") from error

        raw_embeddings = getattr(response, "embeddings", None)
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise GeminiResponseError("Gemini returned an unexpected embedding count.")

        vectors: list[list[float]] = []
        for embedding in raw_embeddings:
            values = getattr(embedding, "values", None)
            if not isinstance(values, list):
                raise GeminiResponseError("Gemini returned an invalid embedding vector.")
            vector = [float(value) for value in values]
            if len(vector) != self._embedding_dim:
                raise GeminiResponseError("Gemini returned an embedding with unexpected dimension.")
            vectors.append(vector)

        return EmbeddingBatch(
            vectors=vectors,
            model=self._embedding_model,
            dimension=self._embedding_dim,
        )


def _normalize_usage(metadata: object | None) -> TokenUsage:
    input_tokens = _integer_attribute(metadata, "prompt_token_count")
    output_tokens = _integer_attribute(metadata, "candidates_token_count") + _integer_attribute(
        metadata, "thoughts_token_count"
    )
    total_tokens = _integer_attribute(metadata, "total_token_count")
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _integer_attribute(value: object | None, name: str) -> int:
    raw_value = getattr(value, name, 0)
    return int(raw_value or 0)
