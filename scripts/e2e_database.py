from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage an isolated local Discover E2E database.")
    parser.add_argument("action", choices=("create", "drop"))
    arguments = parser.parse_args(argv)
    try:
        admin_url, database_name = _configuration()
        if arguments.action == "create":
            _create(admin_url, database_name)
        else:
            _drop(admin_url, database_name)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (psycopg.Error, OSError):
        print("E2E_DATABASE_UNAVAILABLE", file=sys.stderr)
        return 3
    print(f"{arguments.action}d isolated Discover E2E database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
