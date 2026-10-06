"""DB-backed tests for the Badge-Based Visual ID system (scripts/008_display_ids.sql).

These run real SQL against the configured database and skip when it is
unreachable, matching the convention in test_agent_runs_db.py. They pin the
three data-integrity rules the PRD calls out: fixed display-ID format,
per-branch sequence allocation, and write-once immutability of an assigned
code (branch moves never rewrite it).
"""
import re

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_engine
from app.repositories.display_ids import ENTITY_CANDIDATE, ENTITY_REQUISITION, allocate_display_id
from tests.test_rbac_chain_integration import _db_reachable


@pytest.fixture(scope="module")
def engine():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    return get_engine()


def _branch_id(engine, code: str) -> int:
    with engine.connect() as connection:
        return int(
            connection.execute(
                text("SELECT id FROM dbo.branches WHERE code = :code"), {"code": code}
            ).scalar_one()
        )


def _next_value(engine, entity: str, branch_id: int) -> int:
    with engine.connect() as connection:
        return int(
            connection.execute(
                text(
                    "SELECT next_value FROM dbo.display_id_sequences "
                    "WHERE entity = :entity AND branch_id = :branch_id AND tenant_scope = N'DEFAULT'"
                ),
                {"entity": entity, "branch_id": branch_id},
            ).scalar_one()
        )


class TestBackfillFormat:
    def test_all_requisition_codes_match_format(self, engine) -> None:
        with engine.connect() as connection:
            codes = connection.execute(
                text("SELECT requisition_code FROM dbo.requisitions WHERE requisition_code IS NOT NULL")
            ).scalars().all()
        assert codes, "expected the display-ID backfill to have run"
        assert all(re.fullmatch(r"REQ-\d{3,}", code) for code in codes)

    def test_all_candidate_codes_match_format(self, engine) -> None:
        with engine.connect() as connection:
            codes = connection.execute(
                text("SELECT candidate_code FROM dbo.candidates WHERE candidate_code IS NOT NULL")
            ).scalars().all()
        assert codes, "expected the display-ID backfill to have run"
        assert all(re.fullmatch(r"CND-\d{4,}", code) for code in codes)

    def test_codes_are_unique_per_branch(self, engine) -> None:
        with engine.connect() as connection:
            req_dupes = connection.execute(
                text(
                    "SELECT branch_id, requisition_code FROM dbo.requisitions "
                    "WHERE requisition_code IS NOT NULL "
                    "GROUP BY branch_id, requisition_code HAVING COUNT(*) > 1"
                )
            ).all()
            cand_dupes = connection.execute(
                text(
                    "SELECT branch_id, candidate_code FROM dbo.candidates "
                    "WHERE candidate_code IS NOT NULL "
                    "GROUP BY branch_id, candidate_code HAVING COUNT(*) > 1"
                )
            ).all()
        assert not req_dupes
        assert not cand_dupes


class TestPerBranchAllocation:
    def test_allocation_increments_then_rolls_back_clean(self, engine) -> None:
        branch_id = _branch_id(engine, "HYD01")
        before = _next_value(engine, ENTITY_REQUISITION, branch_id)
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                first = allocate_display_id(connection, ENTITY_REQUISITION, branch_id)
                second = allocate_display_id(connection, ENTITY_REQUISITION, branch_id)
                first_value = int(first.split("-")[1])
                second_value = int(second.split("-")[1])
                assert first_value == before and second_value == before + 1
            finally:
                transaction.rollback()
        assert _next_value(engine, ENTITY_REQUISITION, branch_id) == before

    def test_all_branches_have_sequence_rows(self, engine) -> None:
        """Every branch must be seedable — the allocator seeds missing rows
        lazily, so assert post-allocation state rather than pre-seeded rows
        (fixture branches created by other test modules may not have run the
        allocator yet)."""
        with engine.connect() as connection:
            branch_ids = connection.execute(text("SELECT id FROM dbo.branches")).scalars().all()
        for branch_id in branch_ids:
            with engine.connect() as connection:
                transaction = connection.begin()
                try:
                    allocate_display_id(connection, ENTITY_REQUISITION, int(branch_id))
                    seeded = connection.execute(
                        text(
                            "SELECT COUNT(*) FROM dbo.display_id_sequences "
                            "WHERE entity = :entity AND branch_id = :branch_id AND tenant_scope = N'DEFAULT'"
                        ),
                        {"entity": ENTITY_REQUISITION, "branch_id": int(branch_id)},
                    ).scalar_one()
                finally:
                    transaction.rollback()
            assert seeded == 1, f"branch {branch_id} sequence row missing after allocation"

    def test_new_branch_sequence_starts_at_configured_start(self, engine) -> None:
        with engine.connect() as connection:
            min_next = connection.execute(
                text("SELECT MIN(next_value) FROM dbo.display_id_sequences WHERE entity = :entity"),
                {"entity": ENTITY_REQUISITION},
            ).scalar_one()
        assert min_next >= 101


class TestConcurrentAllocation:
    """High-concurrency rule: parallel creators must never receive the same ID.

    Spawns real concurrent transactions against the live database — the same
    contention shape as multiple recruiters hitting POST /candidates at once.
    """

    def test_parallel_allocations_never_collide(self, engine) -> None:
        from concurrent.futures import ThreadPoolExecutor

        branch_id = _branch_id(engine, "HYD01")
        entity = ENTITY_CANDIDATE
        workers = 8
        attempts_per_worker = 5
        before = _next_value(engine, entity, branch_id)
        results: list[str] = []
        errors: list[Exception] = []

        def allocate_batch(worker_index: int) -> list[str]:
            allocated: list[str] = []
            for _ in range(attempts_per_worker):
                with engine.connect() as connection:
                    transaction = connection.begin()
                    try:
                        allocated.append(allocate_display_id(connection, entity, branch_id))
                        transaction.commit()
                    except Exception:  # noqa: BLE001 - recorded and asserted below
                        transaction.rollback()
                        raise
            return allocated

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(allocate_batch, i) for i in range(workers)]
            for future in futures:
                try:
                    results.extend(future.result())
                except Exception as exc:  # noqa: BLE001 - surfaced below
                    errors.append(exc)

        assert not errors, f"concurrent allocation raised: {errors!r}"
        assert len(results) == workers * attempts_per_worker
        assert len(set(results)) == len(results), "duplicate display IDs under concurrency"
        # Every allocation is strictly sequential with no gaps or repeats.
        values = sorted(int(code.split("-")[1]) for code in results)
        assert values == list(range(before, before + len(values)))


class TestWriteOnceImmutability:
    def test_reassigning_an_assigned_code_throws(self, engine) -> None:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with pytest.raises(SQLAlchemyError):
                    connection.execute(
                        text(
                            "UPDATE dbo.requisitions SET requisition_code = N'REQ-000000' "
                            "WHERE id = (SELECT TOP 1 id FROM dbo.requisitions WHERE requisition_code IS NOT NULL)"
                        )
                    )
            finally:
                transaction.rollback()

    def test_candidate_code_reassignment_throws(self, engine) -> None:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with pytest.raises(SQLAlchemyError):
                    connection.execute(
                        text(
                            "UPDATE dbo.candidates SET candidate_code = N'CND-000000' "
                            "WHERE id = (SELECT TOP 1 id FROM dbo.candidates WHERE candidate_code IS NOT NULL)"
                        )
                    )
            finally:
                transaction.rollback()

    def test_non_code_update_still_succeeds(self, engine) -> None:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(
                    text(
                        "UPDATE dbo.requisitions SET updated_at = SYSUTCDATETIME() "
                        "WHERE id = (SELECT TOP 1 id FROM dbo.requisitions WHERE requisition_code IS NOT NULL)"
                    )
                )
            finally:
                transaction.rollback()
