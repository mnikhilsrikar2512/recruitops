from __future__ import annotations

import pytest

from app.repositories.display_ids import (
    ENTITY_CANDIDATE,
    ENTITY_REQUISITION,
    allocate_display_id,
    format_display_id,
)


class _FakeResult:
    """Mimics the slice of SQLAlchemy's CursorResult that the allocator uses."""

    def __init__(self, row: dict | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def one(self) -> dict:
        assert isinstance(self._row, dict), "expected a single mapping row"
        return self._row


class _FakeConnection:
    """Records executed statements and replays scripted results in order."""

    def __init__(self, results: list[dict | None]) -> None:
        self._results = list(results)
        self.statements: list[str] = []
        self.params: list[dict] = []

    def execute(self, statement, params=None):  # noqa: ANN001 - duck-typed like SQLAlchemy
        self.statements.append(str(statement))
        self.params.append(dict(params or {}))
        return _FakeResult(self._results.pop(0) if self._results else None)


def test_format_display_id_matches_prd_format() -> None:
    assert format_display_id(ENTITY_REQUISITION, 101) == "REQ-101"
    assert format_display_id(ENTITY_REQUISITION, 156) == "REQ-156"
    assert format_display_id(ENTITY_CANDIDATE, 1001) == "CND-1001"


def test_format_display_id_rejects_unknown_entity() -> None:
    with pytest.raises(ValueError):
        format_display_id("OFFER", 1)


def test_allocate_requisition_id_increments_sequence_row() -> None:
    connection = _FakeConnection([None, None, {"allocated_value": 101}])

    assert allocate_display_id(connection, ENTITY_REQUISITION, 1) == "REQ-101"

    assert len(connection.statements) == 3
    assert connection.params[-1] == {"entity": "REQ", "branch_id": 1}


def test_allocate_candidate_id_increments_sequence_row() -> None:
    connection = _FakeConnection([None, None, {"allocated_value": 1001}])

    assert allocate_display_id(connection, ENTITY_CANDIDATE, 6) == "CND-1001"

    assert len(connection.statements) == 3
    assert connection.params[-1] == {"entity": "CND", "branch_id": 6}


def test_allocate_is_single_atomic_counter_statement() -> None:
    connection = _FakeConnection([None, None, {"allocated_value": 157}])

    allocate_display_id(connection, ENTITY_REQUISITION, 2)

    allocation_statement = connection.statements[-1]
    assert "UPDATE dbo.display_id_sequences" in allocation_statement
    assert "OUTPUT deleted.next_value" in allocation_statement


def test_allocate_requires_branch() -> None:
    with pytest.raises(ValueError):
        allocate_display_id(_FakeConnection([]), ENTITY_REQUISITION, None)  # type: ignore[arg-type]
