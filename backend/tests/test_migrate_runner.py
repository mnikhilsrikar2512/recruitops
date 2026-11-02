"""scripts/migrate.py planning rules (the DB part runs in CI/compose)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "migrate.py"
spec = importlib.util.spec_from_file_location("migrate", SCRIPT)
migrate = importlib.util.module_from_spec(spec)
sys.modules["migrate"] = migrate  # dataclasses look their module up here
spec.loader.exec_module(migrate)


def test_discovers_repo_migrations_in_order_and_skips_folded_ones():
    found = migrate.discover()
    numbers = [m.version[:3] for m in found]
    assert numbers == sorted(numbers) and len(numbers) == len(set(numbers))
    assert not {"005", "006", "007"} & set(numbers)
    assert numbers[0] == "008" and "032" in numbers


def test_duplicate_numbers_are_refused(tmp_path):
    (tmp_path / "040_a.sql").write_text("SELECT 1")
    (tmp_path / "040_b.sql").write_text("SELECT 2")
    with pytest.raises(SystemExit, match="share number 040"):
        migrate.discover(tmp_path)


def test_plan_returns_pending_and_refuses_edited_history(tmp_path):
    (tmp_path / "040_a.sql").write_text("SELECT 1")
    (tmp_path / "041_b.sql").write_text("SELECT 2")
    found = migrate.discover(tmp_path)
    applied = {"040_a": found[0].checksum}
    assert [m.version for m in migrate.plan(applied, found)] == ["041_b"]
    with pytest.raises(SystemExit, match="edited since they ran"):
        migrate.plan({"040_a": "0" * 64}, found)
    assert [m.version for m in migrate.plan({"040_a": "0" * 64}, found, allow_changed=True)] == ["041_b"]


def test_checksums_ignore_windows_line_endings():
    assert migrate.sha256_text("A\r\nB") == migrate.sha256_text("A\nB")
