from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Never

from ai_atlas_api.catalog import CatalogError, CatalogRepository
from ai_atlas_api.config import Settings
from ai_atlas_api.providers.gemini import (
    GeminiConfigurationError,
    GeminiProvider,
    GeminiRequestError,
    GeminiResponseError,
)
from ai_atlas_api.retrieval import (
    EmbeddingIndex,
    EmbeddingProfile,
    EmbeddingProvider,
    ReindexReport,
)

ReindexStatus = Literal["ok", "unavailable", "error"]


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        del message
        self.exit(2, "CLI_ARGS_INVALID\n")


@dataclass(frozen=True)
class ReindexCommandResult:
    status: ReindexStatus
    report: ReindexReport | None = None
    error_code: str | None = None

    @property
    def exit_code(self) -> int:
        return {"ok": 0, "unavailable": 3, "error": 4}[self.status]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "report": self.report.to_dict() if self.report is not None else None,
            "error": self.error_code,
        }


def run_reindex(
    settings: Settings,
    *,
    batch_size: int = 32,
    provider: EmbeddingProvider | None = None,
) -> ReindexCommandResult:
    try:
        profile = EmbeddingProfile.from_settings(settings)
        active_provider = provider or GeminiProvider.from_settings(settings)
        index = EmbeddingIndex(CatalogRepository(settings.database_url_value()))
        return ReindexCommandResult(
            status="ok",
            report=index.reindex(active_provider, profile, batch_size=batch_size),
        )
    except (GeminiConfigurationError, GeminiRequestError, GeminiResponseError) as error:
        code = (
            "EMBEDDING_NOT_CONFIGURED"
            if isinstance(error, GeminiConfigurationError)
            else "EMBEDDING_UNAVAILABLE"
        )
        return ReindexCommandResult(status="unavailable", error_code=code)
    except CatalogError as error:
        return ReindexCommandResult(status="unavailable", error_code=error.code)
    except (ValueError, TypeError):
        return ReindexCommandResult(status="error", error_code="REINDEX_CONFIG_INVALID")


def _render_text(result: ReindexCommandResult) -> str:
    if result.report is None:
        return f"{result.status.upper()} reindex error={result.error_code}"
    report = result.report
    return (
        "OK reindex "
        f"total={report.total} embedded={report.embedded} stored={report.stored} "
        f"unchanged={report.unchanged} stale_during_write={report.stale_during_write} "
        f"batches={report.batches} model_key={report.model_key}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _ArgumentParser(description="Incrementally rebuild catalog embeddings.")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        result = run_reindex(Settings(), batch_size=args.batch_size)
    except Exception:
        result = ReindexCommandResult(status="error", error_code="INTERNAL_ERROR")
    print(
        json.dumps(result.to_dict(), ensure_ascii=True)
        if args.format == "json"
        else _render_text(result)
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
