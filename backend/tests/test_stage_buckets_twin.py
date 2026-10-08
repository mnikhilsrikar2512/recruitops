"""The Python stage-bucket twin must match the SQL seed in 016."""
import re
from pathlib import Path

from app.core.stage_buckets import BUCKET_ORDER, PLATFORM_STAGE_BUCKETS, TERMINAL_BUCKETS, bucket_for_label

SQL = (Path(__file__).resolve().parents[2] / "scripts" / "016_metric_buckets.sql").read_text(encoding="utf-8")


def test_platform_map_matches_sql_seed() -> None:
    block = SQL.split("MERGE dbo.stage_bucket_map AS t")[1].split(") AS s (stage_key, metric_bucket)")[0]
    seeded = dict(re.findall(r"\(N'([^']+)', N'([^']+)'\)", block))
    assert seeded == PLATFORM_STAGE_BUCKETS


def test_bucket_enum_matches_sql_seed() -> None:
    block = SQL.split("MERGE dbo.metric_buckets AS t")[1].split(") AS s (code, label, sort_order, is_terminal)")[0]
    rows = re.findall(r"\(N'([^']+)',\s*N'[^']+',\s*(\d+),\s*([01])\)", block)
    assert {code: int(order) for code, order, _ in rows} == BUCKET_ORDER
    assert {code for code, _, terminal in rows if terminal == "1"} == TERMINAL_BUCKETS


def test_heuristic_examples() -> None:
    assert bucket_for_label("Executive Review") == "interview"
    assert bucket_for_label("Onboarding") == "joined"
    assert bucket_for_label("Candidate Pulled Out") == "withdrawn"
    assert bucket_for_label("Offer Declined") == "rejected"
    assert bucket_for_label("some-untemplated-stage") == "interview"
