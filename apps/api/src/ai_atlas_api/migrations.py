from __future__ import annotations

import argparse
import hashlib
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import psycopg

MigrationDirection = Literal["up", "down"]
DatabaseConnection = psycopg.Connection[tuple[Any, ...]]
DEFAULT_MIGRATIONS_DIRECTORY = Path(__file__).resolve().parents[4] / "infra" / "db" / "migrations"
MIGRATION_FILENAME = re.compile(
    r"^(?P<version>[0-9]{4})_(?P<name>[a-z0-9_]+)\.(?P<direction>up|down)\.sql$"
)
MIGRATION_LOCK_KEY = 2_026_090_003


class MigrationError(RuntimeError):
    """Raised when migration files or database history are inconsistent."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    up_sql: str
    down_sql: str
    up_checksum: str
    down_checksum: str


@dataclass(frozen=True)
class AppliedMigration:
    version: int
    name: str
    up_checksum: str
    down_checksum: str


@dataclass(frozen=True)
class MigrationStatus:
    version: int
    name: str
    applied: bool


def load_migrations(directory: Path = DEFAULT_MIGRATIONS_DIRECTORY) -> tuple[Migration, ...]:
    """Load ordered, paired up/down SQL migrations from disk."""

    if not directory.is_dir():
        raise MigrationError(f"Migration directory does not exist: {directory}")

    files_by_version: dict[int, dict[MigrationDirection, Path]] = {}
    names_by_version: dict[int, str] = {}
    sql_files = sorted(directory.glob("*.sql"))
    if not sql_files:
        raise MigrationError(f"No SQL migrations found in: {directory}")

    for path in sql_files:
        match = MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {path.name}")

        version = int(match.group("version"))
        name = match.group("name")
        direction = cast(MigrationDirection, match.group("direction"))
        existing_name = names_by_version.setdefault(version, name)
        if existing_name != name:
            raise MigrationError(
                f"Migration version {version:04d} has multiple names: {existing_name}, {name}"
            )

        version_files = files_by_version.setdefault(version, {})
        if direction in version_files:
            raise MigrationError(f"Migration {version:04d}_{name} has multiple {direction} files")
        version_files[direction] = path

    migrations: list[Migration] = []
    for version in sorted(files_by_version):
        name = names_by_version[version]
        version_files = files_by_version[version]
        missing = {"up", "down"} - set(version_files)
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise MigrationError(f"Migration {version:04d}_{name} is missing: {missing_list}")

        up_bytes = version_files["up"].read_bytes()
        down_bytes = version_files["down"].read_bytes()
        if not up_bytes.strip() or not down_bytes.strip():
            raise MigrationError(f"Migration {version:04d}_{name} contains empty SQL")

        migrations.append(
            Migration(
                version=version,
                name=name,
                up_sql=up_bytes.decode("utf-8"),
                down_sql=down_bytes.decode("utf-8"),
                up_checksum=hashlib.sha256(up_bytes).hexdigest(),
                down_checksum=hashlib.sha256(down_bytes).hexdigest(),
            )
        )

    return tuple(migrations)


def upgrade(
    database_url: str,
    *,
    target_version: int | None = None,
    directory: Path = DEFAULT_MIGRATIONS_DIRECTORY,
) -> tuple[Migration, ...]:
    """Apply pending migrations through target_version, or all migrations by default."""

    migrations = load_migrations(directory)
    target = _resolve_target(migrations, target_version)
    applied_now: list[Migration] = []

    with psycopg.connect(database_url, autocommit=True, connect_timeout=5) as connection:
        _initialize_migration_store(connection)
        applied = _read_applied(connection)
        _validate_applied(migrations, applied)
        if applied and max(applied) > target:
            raise MigrationError(
                f"Database is at version {max(applied):04d}; use down before targeting {target:04d}"
            )

        for migration in migrations:
            if migration.version > target:
                break

            with connection.transaction():
                _acquire_lock(connection)
                current = _read_applied(connection)
                _validate_applied(migrations, current)
                if migration.version in current:
                    continue

                connection.execute(migration.up_sql)
                connection.execute(
                    """
                    INSERT INTO schema_migrations (
                        version,
                        name,
                        up_checksum,
                        down_checksum
                    ) VALUES (%s, %s, %s, %s)
                    """,
                    (
                        migration.version,
                        migration.name,
                        migration.up_checksum,
                        migration.down_checksum,
                    ),
                )
                applied_now.append(migration)

    return tuple(applied_now)


def downgrade(
    database_url: str,
    *,
    target_version: int,
    directory: Path = DEFAULT_MIGRATIONS_DIRECTORY,
) -> tuple[Migration, ...]:
    """Roll back applied migrations until target_version remains applied."""

    migrations = load_migrations(directory)
    target = _resolve_target(migrations, target_version, allow_zero=True)
    rolled_back: list[Migration] = []

    with psycopg.connect(database_url, autocommit=True, connect_timeout=5) as connection:
        _initialize_migration_store(connection)
        applied = _read_applied(connection)
        _validate_applied(migrations, applied)
        current_version = max(applied, default=0)
        if target > current_version:
            raise MigrationError(
                f"Database is at version {current_version:04d}; use up before targeting "
                f"{target:04d}"
            )

        for migration in reversed(migrations):
            if migration.version <= target:
                break

            with connection.transaction():
                _acquire_lock(connection)
                current = _read_applied(connection)
                _validate_applied(migrations, current)
                if migration.version not in current:
                    continue

                connection.execute(migration.down_sql)
                connection.execute(
                    "DELETE FROM schema_migrations WHERE version = %s",
                    (migration.version,),
                )
                rolled_back.append(migration)

    return tuple(rolled_back)


def get_status(
    database_url: str,
    *,
    directory: Path = DEFAULT_MIGRATIONS_DIRECTORY,
) -> tuple[MigrationStatus, ...]:
    """Return the ordered local migration list and database application state."""

    migrations = load_migrations(directory)
    with psycopg.connect(database_url, autocommit=True, connect_timeout=5) as connection:
        _initialize_migration_store(connection)
        applied = _read_applied(connection)
        _validate_applied(migrations, applied)

    return tuple(
        MigrationStatus(
            version=migration.version,
            name=migration.name,
            applied=migration.version in applied,
        )
        for migration in migrations
    )


def _resolve_target(
    migrations: tuple[Migration, ...],
    target_version: int | None,
    *,
    allow_zero: bool = False,
) -> int:
    if target_version is None:
        return migrations[-1].version
    if allow_zero and target_version == 0:
        return 0
    if target_version not in {migration.version for migration in migrations}:
        raise MigrationError(f"Unknown migration target: {target_version:04d}")
    return target_version


def _initialize_migration_store(connection: DatabaseConnection) -> None:
    with connection.transaction():
        _acquire_lock(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version integer PRIMARY KEY,
                name text NOT NULL,
                up_checksum text NOT NULL,
                down_checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _acquire_lock(connection: DatabaseConnection) -> None:
    connection.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_KEY,))


def _read_applied(connection: DatabaseConnection) -> dict[int, AppliedMigration]:
    rows = connection.execute(
        """
        SELECT version, name, up_checksum, down_checksum
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()
    return {
        int(row[0]): AppliedMigration(
            version=int(row[0]),
            name=str(row[1]),
            up_checksum=str(row[2]),
            down_checksum=str(row[3]),
        )
        for row in rows
    }


def _validate_applied(
    migrations: tuple[Migration, ...],
    applied: dict[int, AppliedMigration],
) -> None:
    local_by_version = {migration.version: migration for migration in migrations}
    unknown_versions = sorted(set(applied) - set(local_by_version))
    if unknown_versions:
        formatted = ", ".join(f"{version:04d}" for version in unknown_versions)
        raise MigrationError(f"Database contains unknown migration versions: {formatted}")

    expected_prefix = [migration.version for migration in migrations[: len(applied)]]
    if sorted(applied) != expected_prefix:
        raise MigrationError("Applied migrations are not a contiguous prefix of local migrations")

    for version, applied_migration in applied.items():
        local = local_by_version[version]
        if applied_migration.name != local.name:
            raise MigrationError(f"Migration {version:04d} name differs from database history")
        if applied_migration.up_checksum != local.up_checksum:
            raise MigrationError(f"Applied up migration {version:04d}_{local.name} was modified")
        if applied_migration.down_checksum != local.down_checksum:
            raise MigrationError(f"Applied down migration {version:04d}_{local.name} was modified")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage AI Atlas PostgreSQL migrations.")
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string; defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=DEFAULT_MIGRATIONS_DIRECTORY,
        help="Directory containing paired *.up.sql and *.down.sql files.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    up_parser = commands.add_parser("up", help="Apply pending migrations.")
    up_parser.add_argument("--to", dest="target_version", type=int)

    down_parser = commands.add_parser("down", help="Roll back to a migration version.")
    down_parser.add_argument("--to", dest="target_version", type=int, required=True)

    commands.add_parser("status", help="Show migration status.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    database_url = cast(str | None, args.database_url) or os.getenv("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL or --database-url is required")

    directory = cast(Path, args.migrations_dir)
    command = cast(str, args.command)
    try:
        if command == "up":
            applied = upgrade(
                database_url,
                target_version=cast(int | None, args.target_version),
                directory=directory,
            )
            if applied:
                for migration in applied:
                    print(f"applied {migration.version:04d}_{migration.name}")
            else:
                print("database already up to date")
            return 0

        if command == "down":
            rolled_back = downgrade(
                database_url,
                target_version=cast(int, args.target_version),
                directory=directory,
            )
            if rolled_back:
                for migration in rolled_back:
                    print(f"rolled back {migration.version:04d}_{migration.name}")
            else:
                print("database already at target")
            return 0

        for status in get_status(database_url, directory=directory):
            state = "applied" if status.applied else "pending"
            print(f"{status.version:04d}_{status.name}: {state}")
        return 0
    except (MigrationError, psycopg.Error, OSError, UnicodeError) as error:
        parser.exit(1, f"migration failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
