"""Phase 4.3: every UPDATE of a versioned table bumps its version, so a
client holding an old version is always caught (scripts/018_row_versions.sql)."""
import re
from pathlib import Path

from app.repositories.versioning import VERSIONED_TABLES

APP = Path(__file__).resolve().parents[1] / "app"
UPDATE = re.compile(r"UPDATE\s+(?:dbo\.)?\[?(\w+)\]?\s+SET\b(.*?)(?:\bWHERE\b|;|\"\"\")", re.S | re.I)


def test_every_versioned_update_bumps_version() -> None:
    offenders = []
    for path in APP.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for match in UPDATE.finditer(source):
            table, set_clause = match.group(1).lower(), match.group(2)
            if table in VERSIONED_TABLES and not re.search(r"version\s*=\s*version\s*\+\s*1", set_clause):
                line = source[: match.start()].count("\n") + 1
                offenders.append(f"{path.relative_to(APP.parent)}:{line} ({table})")
    assert not offenders, "UPDATE without version bump: " + ", ".join(offenders)
