"""Governed maintenance paths that the database otherwise forbids.

candidate_stage_history is append-only (scripts/016_metric_buckets.sql,
trg_stage_history_append_only). The one exemption is a session that sets
SESSION_CONTEXT 'recruitops.history_maintenance' = 1 — used by the
governed tenant purge (Phase 5 privacy delete) and by test cleanup.

The flag is cleared before the connection goes back to the pool, so it can
never leak into an ordinary request that later reuses the connection.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Connection

HISTORY_MAINTENANCE_KEY = "recruitops.history_maintenance"


@contextmanager
def history_maintenance(connection: Connection) -> Iterator[Connection]:
    connection.execute(
        text("EXEC sp_set_session_context @key = :key, @value = 1;"),
        {"key": HISTORY_MAINTENANCE_KEY},
    )
    try:
        yield connection
    finally:
        connection.execute(
            text("EXEC sp_set_session_context @key = :key, @value = NULL;"),
            {"key": HISTORY_MAINTENANCE_KEY},
        )
