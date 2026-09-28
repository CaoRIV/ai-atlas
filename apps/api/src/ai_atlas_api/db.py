from dataclasses import dataclass
from typing import Literal

import psycopg
from anyio import to_thread

DatabaseState = Literal["ok", "not_configured", "unavailable"]
VectorState = Literal["ok", "missing", "not_checked"]


@dataclass(frozen=True)
class DatabaseReadiness:
    database: DatabaseState
    vector: VectorState

    @property
    def ready(self) -> bool:
        return self.database == "ok" and self.vector == "ok"


async def check_database_readiness(database_url: str | None) -> DatabaseReadiness:
    """Check connectivity and the pgvector extension without exposing error details."""

    if not database_url:
        return DatabaseReadiness(database="not_configured", vector="not_checked")

    return await to_thread.run_sync(_check_database_readiness_sync, database_url)


def _check_database_readiness_sync(database_url: str) -> DatabaseReadiness:
    try:
        with (
            psycopg.connect(database_url, connect_timeout=3) as connection,
            connection.cursor() as cursor,
        ):
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            row = cursor.fetchone()
    except (psycopg.Error, OSError):
        return DatabaseReadiness(database="unavailable", vector="not_checked")

    vector_enabled = bool(row and row[0])
    return DatabaseReadiness(database="ok", vector="ok" if vector_enabled else "missing")
