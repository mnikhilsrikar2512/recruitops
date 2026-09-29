"""Per-branch human display IDs (Badge-Based Visual ID, scripts/008_display_ids.sql).

Format stays fixed: REQ-101, CND-1001. The numeric sequence is scoped per
branch (HYD's REQ-101 and MUM's REQ-101 are distinct rows; the branch badge
resolves the visual context), so allocation must always happen inside the
caller's transaction against the same connection that inserts the entity row.
"""

from __future__ import annotations

from sqlalchemy import Connection, text

ENTITY_REQUISITION = "REQ"
ENTITY_CANDIDATE = "CND"

_PREFIXES: dict[str, str] = {
    ENTITY_REQUISITION: "REQ",
    ENTITY_CANDIDATE: "CND",
}

_START_VALUES: dict[str, int] = {
    ENTITY_REQUISITION: 101,
    ENTITY_CANDIDATE: 1001,
}


def format_display_id(entity: str, value: int) -> str:
    """Render a sequence value as the stable display-ID string."""
    try:
        prefix = _PREFIXES[entity]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown display-ID entity: {entity}") from exc
    return f"{prefix}-{value}"


def _seed_sequence_row(connection: Connection, entity: str, branch_id: int) -> None:
    """Ensure the branch has a sequence row at or past its start value.

    Branches created after scripts/008_display_ids.sql ran get seeded lazily
    here; a row that somehow sits below its start value (partial backfill) is
    bumped up so allocation never emits a code the backfill already used.
    """
    start_value = _START_VALUES[entity]
    connection.execute(
        text(
            """
            UPDATE dbo.display_id_sequences
            SET next_value = :start_value
            WHERE entity = :entity
              AND branch_id = :branch_id
              AND tenant_scope = N'DEFAULT'
              AND next_value < :start_value;
            """
        ),
        {"entity": entity, "branch_id": branch_id, "start_value": start_value},
    )
    connection.execute(
        text(
            """
            INSERT INTO dbo.display_id_sequences (entity, branch_id, tenant_scope, next_value)
            SELECT :entity, :branch_id, N'DEFAULT', :start_value
            WHERE NOT EXISTS (
              SELECT 1 FROM dbo.display_id_sequences
              WHERE entity = :entity
                AND branch_id = :branch_id
                AND tenant_scope = N'DEFAULT'
            );
            """
        ),
        {"entity": entity, "branch_id": branch_id, "start_value": start_value},
    )


def allocate_display_id(connection: Connection, entity: str, branch_id: int) -> str:
    """Atomically reserve and return the next display ID for (entity, branch).

    Runs the single-statement counter increment (UPDATE ... OUTPUT) inside the
    caller's transaction, so concurrent creates serialize on the sequence row
    and never receive the same value.
    """
    if branch_id is None:
        raise ValueError(f"A branch is required to allocate a {entity} display ID")
    _seed_sequence_row(connection, entity, branch_id)
    # Single-statement atomic increment: the row lock taken by the UPDATE
    # (with explicit UPDLOCK/ROWLOCK hints as documentation of intent)
    # serializes concurrent creators; each commits its own value inside the
    # caller's transaction, so no two requests can observe the same value.
    allocated = connection.execute(
        text(
            """
            UPDATE dbo.display_id_sequences WITH (UPDLOCK, ROWLOCK)
            SET next_value += 1
            OUTPUT deleted.next_value AS allocated_value
            WHERE entity = :entity
              AND branch_id = :branch_id
              AND tenant_scope = N'DEFAULT';
            """
        ),
        {"entity": entity, "branch_id": branch_id},
    ).mappings().one()
    return format_display_id(entity, int(allocated["allocated_value"]))
