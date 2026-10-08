"""Company purge (Phase 5.3, decision D-5c). Irreversible; only run by the
privacy job runner after approval and the 7-day cooling-off.

How it works, in ONE transaction:
1. Candidates this company shares with another company are handed over to
   that company (creator / office / owners re-pointed), so the other
   company keeps working with them.
2. Every row the company owns is marked (#doom), table by table, from the
   tenancy map (app/services/tenant_data.predicate, purpose="purge").
3. Closure over the real foreign keys: a row that must reference a doomed
   row (NOT NULL FK) is doomed too; a nullable reference is cleared. A
   shared table may never be touched — the purge stops if it would be.
4. Audit and legal-acceptance rows are copied to privacy_audit_hold
   (kept until hold_until, default 90 days, PRD §12).
5. Doomed rows are deleted children-first; the company's files are removed;
   the tenants row stays as a tombstone (status archived, purged_at).
The privacy_requests rows are kept: they are the record that this happened.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Connection, Engine, text

from app.core.tenancy import TABLE_TENANCY
from app.db.maintenance import history_maintenance
from app.repositories.versioning import VERSIONED_TABLES
from app.services.tenant_data import predicate, tenant_tables

KEEP = {"privacy_requests", "privacy_audit_hold"}
HOLD_TABLES = ("audit_logs", "legal_acceptances")


class PurgeBlocked(Exception):
    pass


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def _columns(connection: Connection) -> dict[str, set[str]]:
    rows = connection.execute(text(
        "SELECT LOWER(t.name) AS t, LOWER(c.name) AS c FROM sys.tables t JOIN sys.columns c ON c.object_id = t.object_id "
        "WHERE SCHEMA_NAME(t.schema_id) = N'dbo';")).all()
    out: dict[str, set[str]] = {}
    for table, column in rows:
        out.setdefault(table, set()).add(column)
    return out


def _foreign_keys(connection: Connection) -> list[dict]:
    rows = connection.execute(text(
        """
        SELECT LOWER(OBJECT_NAME(fk.parent_object_id)) AS child, LOWER(pc.name) AS col,
               LOWER(OBJECT_NAME(fk.referenced_object_id)) AS parent, pc.is_nullable AS nullable
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.columns pc ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
        WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id) = N'dbo';
        """)).mappings().all()
    return [dict(r) for r in rows]


def _hand_over_shared_candidates(connection: Connection, tenant_id: int) -> int:
    """Candidates this company created/hosts but another company also works
    with: point their creator, office and owners at that other company."""
    shared = connection.execute(text(
        f"""
        SELECT c.id,
               (SELECT TOP (1) ox.owner_user_id FROM dbo.candidate_applications ox
                  JOIN dbo.requisitions orq ON orq.id = ox.requisition_id
                  JOIN dbo.branches ob ON ob.id = orq.branch_id
                 WHERE ox.candidate_id = c.id AND ob.tenant_id <> :tenant ORDER BY ox.id) AS new_owner,
               (SELECT TOP (1) orq.branch_id FROM dbo.candidate_applications ox
                  JOIN dbo.requisitions orq ON orq.id = ox.requisition_id
                  JOIN dbo.branches ob ON ob.id = orq.branch_id
                 WHERE ox.candidate_id = c.id AND ob.tenant_id <> :tenant ORDER BY ox.id) AS new_branch
        FROM dbo.candidates AS c
        WHERE {predicate('candidates', 'c')} AND NOT {predicate('candidates', 'c', purpose='purge')};
        """), {"tenant": tenant_id}).mappings().all()
    users = "(SELECT u.id FROM dbo.users u WHERE u.tenant_id = :tenant)"
    for row in shared:
        connection.execute(text(
            f"""
            UPDATE dbo.candidates
            SET version = version + 1,
                created_by_user_id = CASE WHEN created_by_user_id IN {users} THEN :owner ELSE created_by_user_id END,
                branch_id = CASE WHEN branch_id IN (SELECT b.id FROM dbo.branches b WHERE b.tenant_id = :tenant) THEN :branch ELSE branch_id END,
                primary_owner_user_id = CASE WHEN primary_owner_user_id IN {users} THEN NULL ELSE primary_owner_user_id END,
                source_owner_user_id = CASE WHEN source_owner_user_id IN {users} THEN NULL ELSE source_owner_user_id END,
                updated_at = SYSUTCDATETIME()
            WHERE id = :id;
            """), {"id": row["id"], "owner": row["new_owner"], "branch": row["new_branch"], "tenant": tenant_id})
    return len(shared)


def _assert_nothing_foreign(connection: Connection, tenant_id: int, tables: list[str], columns: dict) -> None:
    """Safety net: no doomed row may belong to another company (or be a
    shared row with a NULL company)."""
    offices = "(SELECT b.id FROM dbo.branches b WHERE b.tenant_id = :tenant)"
    users = "(SELECT u.id FROM dbo.users u WHERE u.tenant_id = :tenant)"
    for table in tables:
        if "id" not in columns[table]:
            continue
        kind, _, rest = TABLE_TENANCY[table].partition(":")
        if kind == "tenant":
            foreign = "(a.tenant_id IS NULL OR a.tenant_id <> :tenant)"
        elif kind == "office":
            foreign = f"(a.{rest} IS NOT NULL AND a.{rest} NOT IN {offices})"
        elif kind == "user":
            foreign = f"(a.{rest} IS NOT NULL AND a.{rest} NOT IN {users})"
        else:
            continue
        count = connection.execute(text(
            f"SELECT COUNT(*) FROM #doom d JOIN dbo.{table} a ON a.id = d.id WHERE d.tbl = N'{table}' AND {foreign};"),
            {"tenant": tenant_id}).scalar_one()
        if count:
            raise PurgeBlocked(f"purge would delete {count} row(s) of {table} that belong to another company")


def purge_company(engine: Engine, tenant_id: int, privacy_request_id: int, hold_days: int | None = None) -> dict:
    report: dict = {"tenant_id": tenant_id, "deleted": {}, "cleared_links": 0}
    with engine.begin() as connection, history_maintenance(connection):
        if hold_days is None:
            hold_days = int(connection.execute(text(
                "SELECT audit_hold_days FROM dbo.tenants WHERE id = :t"), {"t": tenant_id}).scalar_one())
        hold_days = max(hold_days, 1)  # never zero (PRD §12)
        columns = _columns(connection)
        fks = _foreign_keys(connection)
        tables = [t for t in tenant_tables() if t not in KEEP and t in columns]
        report["handed_over_candidates"] = _hand_over_shared_candidates(connection, tenant_id)

        connection.execute(text("CREATE TABLE #doom (tbl NVARCHAR(128) NOT NULL, id BIGINT NOT NULL, PRIMARY KEY (tbl, id));"))
        for table in tables:
            if "id" not in columns[table]:
                continue
            connection.execute(text(
                f"INSERT INTO #doom (tbl, id) SELECT N'{table}', a.id FROM dbo.{table} AS a "
                f"WHERE {predicate(table, 'a', purpose='purge')};"), {"tenant": tenant_id})

        # Closure over NOT NULL foreign keys.
        shared_tables = {t for t, rule in TABLE_TENANCY.items() if rule.startswith("shared:")}
        for _round in range(20):
            added = 0
            for fk in fks:
                if fk["nullable"] or "id" not in columns.get(fk["child"], set()) or fk["child"] in KEEP:
                    continue
                result = connection.execute(text(
                    f"INSERT INTO #doom (tbl, id) SELECT N'{fk['child']}', x.id FROM dbo.{fk['child']} AS x "
                    f"WHERE x.{fk['col']} IN (SELECT id FROM #doom WHERE tbl = N'{fk['parent']}') "
                    f"AND NOT EXISTS (SELECT 1 FROM #doom d WHERE d.tbl = N'{fk['child']}' AND d.id = x.id);"))
                if result.rowcount:
                    if fk["child"] in shared_tables:
                        raise PurgeBlocked(f"purge would delete shared rows in {fk['child']} (via {fk['col']})")
                    added += result.rowcount
                    report.setdefault("closure", {}).setdefault(fk["child"], 0)
                    report["closure"][fk["child"]] += result.rowcount
            if not added:
                break
        else:
            raise PurgeBlocked("foreign-key closure did not settle")

        _assert_nothing_foreign(connection, tenant_id, tables, columns)

        # Hold audit + legal rows before they go.
        hold_until = datetime.now(timezone.utc) + timedelta(days=hold_days)
        for table in HOLD_TABLES:
            rows = connection.execute(text(
                f"SELECT a.* FROM dbo.{table} a WHERE a.id IN (SELECT id FROM #doom WHERE tbl = N'{table}');")).mappings().all()
            for row in rows:
                connection.execute(text(
                    "INSERT INTO dbo.privacy_audit_hold (tenant_id, privacy_request_id, source_table, source_id, row_json, hold_until) "
                    "VALUES (:t, :r, :tbl, :id, :j, :until);"),
                    {"t": tenant_id, "r": privacy_request_id, "tbl": table, "id": row["id"],
                     "j": json.dumps(dict(row), default=_json_default), "until": hold_until})
            report.setdefault("held", {})[table] = len(rows)

        # Clear nullable references to doomed rows (breaks cycles; unlinks others' rows).
        for fk in fks:
            if not fk["nullable"]:
                continue
            bump = ", version = version + 1" if fk["child"] in VERSIONED_TABLES else ""
            result = connection.execute(text(
                f"UPDATE dbo.{fk['child']} SET {fk['col']} = NULL{bump} "
                f"WHERE {fk['col']} IN (SELECT id FROM #doom WHERE tbl = N'{fk['parent']}');"))
            report["cleared_links"] += result.rowcount or 0

        # Tables without an id column: delete by their own rule.
        for table in tables:
            if "id" not in columns[table]:
                result = connection.execute(text(
                    f"DELETE a FROM dbo.{table} AS a WHERE {predicate(table, 'a', purpose='purge')};"), {"tenant": tenant_id})
                report["deleted"][table] = result.rowcount or 0

        # Delete children first: order by NOT NULL foreign keys between doomed tables.
        doomed = {r[0] for r in connection.execute(text("SELECT DISTINCT tbl FROM #doom;")).all()}
        depends = {t: set() for t in doomed}  # parent -> children that must go first
        for fk in fks:
            if not fk["nullable"] and fk["child"] in doomed and fk["parent"] in doomed and fk["child"] != fk["parent"]:
                depends[fk["parent"]].add(fk["child"])
        ordered: list[str] = []
        remaining = set(doomed)
        while remaining:
            ready = sorted(t for t in remaining if not (depends[t] & remaining))
            if not ready:
                raise PurgeBlocked(f"foreign-key cycle between {sorted(remaining)}")
            ordered.extend(ready)
            remaining -= set(ready)
        for table in ordered:
            result = connection.execute(text(
                f"DELETE x FROM dbo.{table} AS x WHERE x.id IN (SELECT id FROM #doom WHERE tbl = N'{table}');"))
            report["deleted"][table] = report["deleted"].get(table, 0) + (result.rowcount or 0)

        connection.execute(text("DROP TABLE #doom;"))
        connection.execute(text(
            "UPDATE dbo.tenants SET status = N'archived', purged_at = SYSUTCDATETIME(), "
            "display_name = N'Deleted company', slug = CONCAT(N'deleted-', id), updated_at = SYSUTCDATETIME() WHERE id = :t;"),
            {"t": tenant_id})

    # Files last: the database is already consistent if this fails.
    try:
        from app.core.file_storage import get_storage

        report["files_deleted"] = get_storage().delete_prefix(f"tenant_{tenant_id}")
    except Exception as exc:  # noqa: BLE001 — reported; the runner retries file cleanup
        report["files_error"] = str(exc)[:500]
    report["deleted"] = {k: v for k, v in report["deleted"].items() if v}
    return report


def release_expired_holds(engine: Engine) -> int:
    with engine.begin() as connection:
        return connection.execute(text("DELETE FROM dbo.privacy_audit_hold WHERE hold_until <= SYSUTCDATETIME();")).rowcount or 0
