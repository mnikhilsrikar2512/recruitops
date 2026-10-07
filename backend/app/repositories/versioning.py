"""Optimistic locking (Phase 4.3, scripts/018_row_versions.sql).

Every UPDATE of a versioned table bumps ``version``. An edit that carries
the version the client loaded calls ``check_version`` first, inside the
same transaction: the row is read with UPDLOCK/HOLDLOCK, so two concurrent
writers serialise and the second one sees the first one's bump and gets a
StaleWriteConflict (→ HTTP 409 with the fresh row, app/main.py).

An edit without a version is not checked (older clients, system writes).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

VERSIONED_TABLES = frozenset({"candidates", "requisitions", "candidate_applications"})


class StaleWriteConflict(Exception):
    """The row changed after the client loaded it."""

    def __init__(self, table: str, record_id: int, current_version: int, expected_version: int) -> None:
        super().__init__(f"{table} {record_id} is at version {current_version}, not {expected_version}")
        self.table = table
        self.record_id = record_id
        self.current_version = current_version
        self.expected_version = expected_version
        # The fresh record as the API shows it; the service fills it in.
        self.current: Any = None


def check_version(connection: Connection, table: str, record_id: int, expected_version: int | None) -> None:
    if expected_version is None:
        return
    if table not in VERSIONED_TABLES:
        raise ValueError(f"{table} is not a versioned table")
    current = connection.execute(
        text(f"SELECT version FROM dbo.{table} WITH (UPDLOCK, HOLDLOCK) WHERE id = :id;"),
        {"id": record_id},
    ).scalar_one_or_none()
    if current is not None and int(current) != int(expected_version):
        raise StaleWriteConflict(table, record_id, int(current), int(expected_version))
