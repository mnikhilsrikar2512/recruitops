"""Plan 2.3: every table is tenant-scoped or explicitly shared (app/core/tenancy.py)."""
import re
from pathlib import Path

from app.core.tenancy import TABLE_TENANCY

BACKEND = Path(__file__).resolve().parents[1]
SQL_FILES = [BACKEND / "db" / "schema.sql", *sorted((BACKEND.parent / "scripts").glob("*.sql"))]
CREATE = re.compile(r"CREATE TABLE\s+(?:dbo\.|\[dbo\]\.)?\[?(\w+)\]?\s*\((.*?)\n\s*\);", re.S | re.I)
ADD_COLUMN = re.compile(r"ALTER TABLE\s+dbo\.(\w+)\s+ADD\s+(\w+)\s", re.I)


def _tables() -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for path in SQL_FILES:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, body in CREATE.findall(text):
            cols = {m.lower() for m in re.findall(r"^\s*\[?(\w+)\]?\s+[A-Z]", body, re.M)}
            tables.setdefault(name.lower(), set()).update(cols)
        for table, column in ADD_COLUMN.findall(text):
            tables.setdefault(table.lower(), set()).add(column.lower())
    return tables


def test_every_table_has_a_tenancy_line() -> None:
    missing = sorted(set(_tables()) - set(TABLE_TENANCY))
    assert not missing, f"add these tables to app/core/tenancy.py: {missing}"


def test_named_columns_exist() -> None:
    tables = _tables()
    problems = []
    for table, rule in TABLE_TENANCY.items():
        if table not in tables:
            problems.append(f"{table}: not in any schema file")
            continue
        kind, _, rest = rule.partition(":")
        if kind == "tenant":
            if "tenant_id" not in tables[table]:
                problems.append(f"{table}: no tenant_id column")
        elif kind in ("office", "user"):
            if rest.lower() not in tables[table]:
                problems.append(f"{table}: no column {rest}")
        elif kind == "parent":
            column, _, parent = rest.partition("->")
            if column.lower() not in tables[table] or parent not in TABLE_TENANCY:
                problems.append(f"{table}: bad parent rule {rest}")
        elif kind != "shared":
            problems.append(f"{table}: unknown rule {rule}")
    assert not problems, problems
