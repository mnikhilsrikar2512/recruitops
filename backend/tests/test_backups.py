"""Phase 6.6: backup retention, restore-drill verification, job schedules."""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


backup_db = _load("backup_db")
restore_drill = _load("restore_drill")
scheduler = _load("scheduler")


def _daily(days: int, now: datetime) -> list[dict]:
    return [{"key": f"b/{i}.json", "at": now - timedelta(days=i)} for i in range(days)]


def test_retention_keeps_recent_days_and_one_per_month():
    now = datetime(2026, 11, 2, 21, tzinfo=timezone.utc)
    backups = _daily(400, now)
    doomed = {b["key"] for b in backup_db.to_delete(backups, now, keep_days=35, keep_months=12)}
    kept = [b for b in backups if b["key"] not in doomed]
    assert all(b["key"] not in doomed for b in backups if b["at"] >= now - timedelta(days=35))
    old_kept = [b for b in kept if b["at"] < now - timedelta(days=35)]
    months = {b["at"].strftime("%Y-%m") for b in old_kept}
    assert len(old_kept) == len(months) and len(months) <= 12  # one per month, at most a year back
    assert backup_db.to_delete([], now, 35, 12) == []


def test_retention_never_deletes_the_newest_backup():
    now = datetime(2026, 11, 2, tzinfo=timezone.utc)
    only = [{"key": "b/old.json", "at": now - timedelta(days=500)}]
    assert backup_db.to_delete(only, now, keep_days=35, keep_months=0) == []


def test_drill_accepts_counts_inside_the_export_window_only():
    manifest = {"row_counts_before": {"dbo.a": 10, "dbo.b": 5}, "row_counts_after": {"dbo.a": 12, "dbo.b": 5}}
    assert restore_drill.compare_counts(manifest, {"dbo.a": 11, "dbo.b": 5}) == []
    problems = restore_drill.compare_counts(manifest, {"dbo.a": 13, "dbo.b": 4})
    assert any("dbo.a: 13 rows, expected 10..12" in p for p in problems)
    assert any("dbo.b: 4 rows, expected 5" in p for p in problems)
    assert restore_drill.compare_counts(manifest, {"dbo.a": 10}) == ["dbo.b: missing after restore"]
    assert "not in the backup" in restore_drill.compare_counts(manifest, {"dbo.a": 10, "dbo.b": 5, "dbo.c": 1})[0]


def test_monthly_drill_runs_on_the_first_at_the_set_time():
    job = scheduler.JOBS["restore_drill"]
    assert job.next_after(datetime(2026, 11, 2, 9, tzinfo=timezone.utc)) == datetime(2026, 12, 1, 22, 30, tzinfo=timezone.utc)
    assert job.next_after(datetime(2026, 12, 1, 8, tzinfo=timezone.utc)) == datetime(2026, 12, 1, 22, 30, tzinfo=timezone.utc)
    daily = scheduler.JOBS["db_backup"]
    assert daily.next_after(datetime(2026, 11, 2, 21, tzinfo=timezone.utc)) == datetime(2026, 11, 3, 20, 30, tzinfo=timezone.utc)


def test_backup_jobs_need_the_ops_image_and_audit_retention_is_opt_in(monkeypatch):
    assert scheduler.JOBS["db_backup"].needs_ops_image and scheduler.JOBS["restore_drill"].needs_ops_image
    monkeypatch.delenv("AUDIT_RETENTION_DAYS", raising=False)
    assert "skipped" in scheduler.job_audit_retention(object())
    monkeypatch.setenv("AUDIT_RETENTION_DAYS", "30")
    import pytest
    with pytest.raises(RuntimeError, match="below 365"):
        scheduler.job_audit_retention(object())
