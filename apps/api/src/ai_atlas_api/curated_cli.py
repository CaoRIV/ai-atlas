import argparse
import json
import stat
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings

from ai_atlas_api.catalog import CatalogError
from ai_atlas_api.config import Settings
from ai_atlas_api.curated_diff import CatalogChange, build_catalog_diff
from ai_atlas_api.curated_models import CuratedCatalog
from ai_atlas_api.curated_snapshot import load_catalog_snapshot
from ai_atlas_api.curated_validation import (
    CuratedValidationError,
    ValidationIssue,
    validate_catalog,
)

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_BATCH_BYTES = 32 * 1024 * 1024


class _DatabaseSettings(BaseSettings):
    model_config = Settings.model_config
    database_url: SecretStr | None = None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # argparse's default includes user-supplied values, potentially secrets.
        self.print_usage(sys.stderr)
        self.exit(2, "CLI_ARGS_INVALID\n")


class _DuplicateJSONKey(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey
        result[key] = value
    return result


@dataclass(frozen=True)
class DryRunReport:
    as_of: datetime
    status: Literal["valid", "invalid", "unavailable", "error"]
    changes: tuple[CatalogChange, ...] = ()
    errors: tuple[ValidationIssue, ...] = ()

    @property
    def exit_code(self) -> int:
        return {"valid": 0, "invalid": 2, "unavailable": 3, "error": 4}[self.status]

    def to_dict(self) -> dict[str, Any]:
        summary = {"added": 0, "updated": 0, "unchanged": 0}
        rows = []
        for change in self.changes:
            summary[change.status] += 1
            rows.append(
                {
                    "entity": change.entity,
                    "id": str(change.id),
                    "status": change.status,
                    "changed_fields": list(change.changed_fields),
                    "parent_id": str(change.parent_id) if change.parent_id is not None else None,
                }
            )
        return {
            "command": "dry-run",
            "status": self.status,
            "as_of": self.as_of.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "summary": summary,
            "changes": rows,
            "errors": [{"field": issue.field, "code": issue.code} for issue in self.errors],
        }


def _schema_issues(index: int, error: ValidationError) -> list[ValidationIssue]:
    issues = []
    for detail in error.errors(include_url=False, include_context=False, include_input=False):
        location = detail["loc"]
        if detail["type"] == "extra_forbidden" and location:
            location = (*location[:-1], "unknown_key")
        field = f"documents[{index}]"
        for part in location:
            field += f"[{part}]" if isinstance(part, int) else f".{part}"
        issues.append(ValidationIssue(field, detail["type"]))
    return issues


def _read_documents(paths: Sequence[Path]) -> tuple[list[CuratedCatalog], list[ValidationIssue]]:
    documents = []
    issues = []
    total_bytes = 0
    for index, path in enumerate(paths):
        field = f"documents[{index}]"
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                issues.append(ValidationIssue(field, "input_not_regular_file"))
                continue
            with path.open("rb") as stream:
                content = stream.read(MAX_FILE_BYTES + 1)
        except OSError:
            issues.append(ValidationIssue(field, "input_unreadable"))
            continue
        if len(content) > MAX_FILE_BYTES:
            issues.append(ValidationIssue(field, "input_file_too_large"))
            continue
        total_bytes += len(content)
        if total_bytes > MAX_BATCH_BYTES:
            issues.append(ValidationIssue(field, "input_batch_too_large"))
            break
        try:
            # JSON mode is required by strict UUID/datetime fields. Detect ambiguous
            # duplicate object keys first; Pydantic alone would silently keep the last.
            json.loads(content, object_pairs_hook=_unique_object)
            documents.append(CuratedCatalog.model_validate_json(content))
        except _DuplicateJSONKey:
            issues.append(ValidationIssue(field, "duplicate_json_key"))
        except (json.JSONDecodeError, UnicodeError, RecursionError):
            issues.append(ValidationIssue(field, "json_invalid"))
        except ValidationError as error:
            issues.extend(_schema_issues(index, error))
    return documents, issues


def run_dry_run(paths: Sequence[Path], database_url: str | None, *, now: datetime) -> DryRunReport:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("validation_clock_requires_timezone")
    if not paths:
        return DryRunReport(
            now, "invalid", errors=(ValidationIssue("documents", "input_required"),)
        )
    documents, issues = _read_documents(paths)
    if issues:
        return DryRunReport(now, "invalid", errors=tuple(issues))
    try:
        snapshot = load_catalog_snapshot(database_url)
        validate_catalog(documents, now=now, existing=snapshot)
        return DryRunReport(now, "valid", build_catalog_diff(documents, snapshot))
    except CuratedValidationError as error:
        return DryRunReport(now, "invalid", errors=error.issues)
    except CatalogError as error:
        return DryRunReport(now, "unavailable", errors=(ValidationIssue("existing", error.code),))


def _render_text(report: DryRunReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        f"{report.status.upper()} dry-run as_of={data['as_of']} "
        f"added={summary['added']} updated={summary['updated']} unchanged={summary['unchanged']}"
    ]
    for change in report.changes:
        fields = ",".join(change.changed_fields) or "-"
        parent = f" parent_id={change.parent_id}" if change.parent_id is not None else ""
        lines.append(f"{change.status.upper()} {change.entity} {change.id}{parent} fields={fields}")
    lines.extend(f"ERROR {issue.field} {issue.code}" for issue in report.errors)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _ArgumentParser(description="Preview curated catalog changes; never writes to DB.")
    commands = parser.add_subparsers(dest="command", required=True)
    dry_run = commands.add_parser("dry-run", help="Validate files against the configured database.")
    dry_run.add_argument("files", type=Path, nargs="+")
    dry_run.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    now = datetime.now(UTC)
    try:
        secret = _DatabaseSettings().database_url
        report = run_dry_run(args.files, secret.get_secret_value() if secret else None, now=now)
    except Exception:
        # CLI boundary: operational/programming failures are explicit, never success,
        # and must not print traceback/exception values containing connection secrets.
        report = DryRunReport(now, "error", errors=(ValidationIssue("command", "INTERNAL_ERROR"),))
    print(
        json.dumps(report.to_dict(), ensure_ascii=True)
        if args.format == "json"
        else _render_text(report)
    )
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
