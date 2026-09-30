import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_atlas_api.curated_cli import (
    MAX_BATCH_BYTES,
    MAX_FILE_BYTES,
    main,
    run_dry_run,
    run_import,
)

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)
EMPTY = {
    "schema_version": 1,
    "providers": [],
    "models": [],
    "categories": [],
    "capabilities": [],
    "tools": [],
}


@pytest.mark.parametrize(
    "content,code",
    [
        (b"{", "json_invalid"),
        (b"\xff", "json_invalid"),
        (b"\xef\xbb\xbf" + json.dumps(EMPTY).encode(), "json_invalid"),
        (json.dumps({**EMPTY, "schema_version": "1"}).encode(), "value_error"),
        (b'{"schema_version":1}', "missing"),
        ((json.dumps(EMPTY)[:-1] + ',"schema_version":1}').encode(), "duplicate_json_key"),
        (
            json.dumps({**EMPTY, "private-password-DO-NOT-ECHO": "sensitive"}).encode(),
            "extra_forbidden",
        ),
    ],
)
def test_invalid_files_fail_before_db_access_without_echoing_raw_data(
    tmp_path: Path,
    content: bytes,
    code: str,
) -> None:
    path = tmp_path / "curated.json"
    path.write_bytes(content)
    report = run_dry_run([path], None, now=NOW)
    assert report.exit_code == 2
    assert report.status == "invalid"
    assert code in {issue.code for issue in report.errors}
    assert report.changes == ()
    assert "private-password-DO-NOT-ECHO" not in json.dumps(report.to_dict())
    assert "sensitive" not in json.dumps(report.to_dict())


@pytest.mark.parametrize(
    "kind,code",
    [
        ("missing", "input_unreadable"),
        ("directory", "input_not_regular_file"),
    ],
)
def test_unreadable_or_non_file_input(tmp_path: Path, kind: str, code: str) -> None:
    path = tmp_path if kind == "directory" else tmp_path / "missing.json"
    report = run_dry_run([path], None, now=NOW)
    assert report.exit_code == 2
    assert [(issue.field, issue.code) for issue in report.errors] == [("documents[0]", code)]


def test_valid_input_requires_target_db_without_empty_catalog_fallback(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps(EMPTY), encoding="utf-8")
    report = run_dry_run([path], None, now=NOW)
    assert report.exit_code == 3
    assert report.status == "unavailable"
    assert [(issue.field, issue.code) for issue in report.errors] == [
        ("existing", "CATALOG_UNAVAILABLE")
    ]
    assert report.changes == ()


def test_bad_database_connection_is_sanitized(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text(json.dumps(EMPTY), encoding="utf-8")
    report = run_dry_run([path], "invalid-connection-secret-DO-NOT-ECHO", now=NOW)
    assert report.exit_code == 3
    assert report.errors[0].code == "CATALOG_UNAVAILABLE"
    assert "invalid-connection-secret" not in json.dumps(report.to_dict())


def test_exact_file_size_limit_is_accepted_then_one_byte_more_rejected(tmp_path: Path) -> None:
    content = json.dumps(EMPTY).encode()
    path = tmp_path / "bounded.json"
    path.write_bytes(content + b" " * (MAX_FILE_BYTES - len(content)))
    assert (
        run_dry_run([path], None, now=NOW).exit_code == 3
    )  # Reaches missing DB, not size failure.
    with path.open("ab") as stream:
        stream.write(b" ")
    report = run_dry_run([path], None, now=NOW)
    assert report.exit_code == 2
    assert report.errors[0].code == "input_file_too_large"


def test_batch_limit_rejects_combined_files_even_when_each_file_is_valid(tmp_path: Path) -> None:
    content = json.dumps(EMPTY).encode()
    paths = []
    for index in range(MAX_BATCH_BYTES // MAX_FILE_BYTES):
        path = tmp_path / f"bounded-{index}.json"
        path.write_bytes(content + b" " * (MAX_FILE_BYTES - len(content)))
        paths.append(path)
    assert run_dry_run(paths, None, now=NOW).exit_code == 3
    final = tmp_path / "extra.json"
    final.write_bytes(content)
    report = run_dry_run([*paths, final], None, now=NOW)
    assert report.exit_code == 2
    assert report.errors[0].code == "input_batch_too_large"


def test_bad_second_file_reports_original_document_index_and_no_partial_diff(
    tmp_path: Path,
) -> None:
    first = tmp_path / "valid.json"
    first.write_text(json.dumps(EMPTY), encoding="utf-8")
    second = tmp_path / "invalid.json"
    second.write_text("{", encoding="utf-8")
    report = run_dry_run([first, second], None, now=NOW)
    assert report.exit_code == 2
    assert [(issue.field, issue.code) for issue in report.errors] == [
        ("documents[1]", "json_invalid")
    ]
    assert report.changes == ()


def test_import_reuses_bounded_parser_and_requires_database_after_valid_parse(
    tmp_path: Path,
) -> None:
    path = tmp_path / "catalog.json"
    path.write_text("{", encoding="utf-8")
    invalid = run_import([path], None, now=NOW)
    assert invalid.command == "import"
    assert invalid.exit_code == 2
    assert invalid.errors[0].code == "json_invalid"
    path.write_text(json.dumps(EMPTY), encoding="utf-8")
    unavailable = run_import([path], None, now=NOW)
    assert unavailable.command == "import"
    assert unavailable.exit_code == 3
    assert unavailable.errors[0].code == "CATALOG_UNAVAILABLE"


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["write", "private-password-DO-NOT-ECHO"],
        ["dry-run"],
        ["dry-run", "--format", "private-password-DO-NOT-ECHO", "file.json"],
        ["dry-run", "--database-url", "postgresql://user:private-password-DO-NOT-ECHO@host/db"],
    ],
)
def test_argument_errors_have_exit_two_without_echoing_values(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        main(arguments)
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "CLI_ARGS_INVALID" in output.err
    assert "private-password-DO-NOT-ECHO" not in output.err
