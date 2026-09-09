"""Dump the live database schema (tables + constraints) to backend/db/schema.sql.

Usage:
    .venv/bin/python scripts/dump_schema.py

Reads connection settings from backend/.env, reflects all tables in the
configured database, and writes the DDL in two passes so circular foreign-key
dependencies (e.g. locations <-> roles <-> users) cannot break replay:

  pass 1 — every CREATE TABLE (foreign keys omitted)
  pass 2 — every ALTER TABLE ... ADD CONSTRAINT for the foreign keys
"""

from pathlib import Path

from sqlalchemy import MetaData, create_engine
from sqlalchemy.schema import CreateIndex, CreateTable, ForeignKeyConstraint

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import create_db_engine  # noqa: E402

OUTPUT = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def main() -> None:
    engine = create_db_engine()
    metadata = MetaData()
    metadata.reflect(bind=engine)

    dialect = engine.dialect
    tables = list(metadata.sorted_tables)

    def foreign_keys(table):
        return [c for c in table.constraints if isinstance(c, ForeignKeyConstraint)]

    lines = ["-- RecruitOps schema dump (tables only, no data)", "--",
             "-- Pass 1: tables (FKs deferred to pass 2 so circular dependencies replay)", "--",
             "-- Required SET options for filtered/computed indexes (sqlcmd defaults differ):",
             "SET QUOTED_IDENTIFIER ON;",
             "SET ANSI_NULLS ON;",
             "SET ANSI_PADDING ON;",
             "SET ANSI_WARNINGS ON;",
             "SET ARITHABORT ON;",
             "SET CONCAT_NULL_YIELDS_NULL ON;",
             "SET NUMERIC_ROUNDABORT OFF;",
             ""]
    for table in tables:
        # Clone into a FRESH MetaData: cloning into the reflected metadata is a
        # no-op (name already exists) and stripping would mutate the originals.
        stripped = table.to_metadata(MetaData())
        stripped.constraints = {
            c for c in stripped.constraints if not isinstance(c, ForeignKeyConstraint)
        }
        lines.append(str(CreateTable(stripped).compile(dialect=dialect)).strip() + ";")
        # indexes is a set: sort for deterministic output across runs (hash seed)
        for index in sorted(stripped.indexes, key=lambda i: i.name or ""):
            lines.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
        lines.append("")

    lines.append("")
    lines.append("-- Pass 2: foreign keys (sorted by constraint name for stable diffs)")
    lines.append("")
    fk_count = 0
    # Reflection returns constraints as an unordered set: sort globally by name
    # so consecutive dumps are byte-identical.
    all_fks = sorted(
        ((table, c) for table in tables for c in foreign_keys(table)),
        key=lambda tc: tc[1].name or "",
    )
    for table, constraint in all_fks:
            pairs = [(e.parent.name, e.column.name) for e in constraint.elements]
            columns = ", ".join(f"[{local}]" for local, _ in pairs)
            referred_columns = ", ".join(f"[{remote}]" for _, remote in pairs)
            referred = constraint.referred_table
            name = constraint.name or f"FK_{table.name}_{fk_count}"
            lines.append(
                f"ALTER TABLE [dbo].[{table.name}] ADD CONSTRAINT [{name}] "
                f"FOREIGN KEY ({columns}) REFERENCES [dbo].[{referred.name}] ({referred_columns});"
            )
            fk_count += 1
    lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(tables)} tables and {fk_count} foreign keys to {OUTPUT}")


if __name__ == "__main__":
    main()
