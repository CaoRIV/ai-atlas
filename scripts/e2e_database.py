from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import sql

_DATABASE_NAME = re.compile(r"ai_atlas_e2e_[0-9a-f]{16}")
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _configuration() -> tuple[str, str]:
    admin_url = os.getenv("E2E_DATABASE_ADMIN_URL", "")
    database_name = os.getenv("E2E_DATABASE_NAME", "")
    parsed = urlparse(admin_url)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in _LOCAL_HOSTS:
        raise ValueError("E2E_DATABASE_ADMIN_URL_MUST_BE_LOCAL")
    if _DATABASE_NAME.fullmatch(database_name) is None:
        raise ValueError("E2E_DATABASE_NAME_INVALID")
    return admin_url, database_name


def _create(admin_url: str, database_name: str) -> None:
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
        existing = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
        ).fetchone()
        if existing is not None:
            raise ValueError("E2E_DATABASE_ALREADY_EXISTS")
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))


def _drop(admin_url: str, database_name: str) -> None:
    with psycopg.connect(admin_url, autocommit=True, connect_timeout=5) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (database_name,),
        )
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name))
        )


def _seed_fixtures(admin_url: str, database_name: str) -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "e2e/fixtures/archived-tool.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    # Override the admin URL's database; fixtures must never touch the development catalog.
    with psycopg.connect(admin_url, dbname=database_name, connect_timeout=5) as connection:
        connection.execute(
            "INSERT INTO tools "
            "(id, slug, name, description, official_url, publication_status, search_vector) "
            "VALUES (%s, %s, %s, %s, %s, 'archived', to_tsvector('simple', %s))",
            (
                fixture["id"],
                fixture["slug"],
                fixture["name"],
                fixture["description"],
                fixture["official_url"],
                fixture["name"],
            ),
        )
        stored = connection.execute(
            "SELECT publication_status FROM tools WHERE id = %s", (fixture["id"],)
        ).fetchone()
        if stored != ("archived",):
            raise ValueError("E2E_ARCHIVED_FIXTURE_MISSING")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage an isolated local Discover E2E database.")
    parser.add_argument("action", choices=("create", "drop", "seed-fixtures"))
    arguments = parser.parse_args(argv)
    try:
        admin_url, database_name = _configuration()
        if arguments.action == "create":
            _create(admin_url, database_name)
        elif arguments.action == "seed-fixtures":
            _seed_fixtures(admin_url, database_name)
        else:
            _drop(admin_url, database_name)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (psycopg.Error, OSError):
        print("E2E_DATABASE_UNAVAILABLE", file=sys.stderr)
        return 3
    print(f"{arguments.action}: isolated Discover E2E database ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
