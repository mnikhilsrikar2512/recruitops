"""Stage label -> metric bucket map (Phase 4.5, scripts/016_metric_buckets.sql).

Resolution lives in SQL (dbo.fn_metric_bucket) so reports, history
snapshots and this admin view can never disagree. This module only reads
the resolved state and writes a company's own overrides.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text

METRIC_BUCKETS: tuple[str, ...] = (
    "sourced", "screened", "submitted", "interview", "offer", "joined", "rejected", "withdrawn",
)


def stage_key(label: str) -> str:
    """Python twin of dbo.fn_stage_key: lower-case, '-' for spaces and '_'."""
    return label.strip().replace("_", "-").replace(" ", "-").lower()


@dataclass
class MetricBucketRecord:
    code: str
    label: str
    sort_order: int
    is_terminal: bool


@dataclass
class StageBucketRecord:
    stage_key: str
    example_label: str | None
    metric_bucket: str
    source: str  # company | platform | inferred
    platform_bucket: str | None
    applications: int


def list_metric_buckets(engine: Engine) -> list[MetricBucketRecord]:
    query = text("SELECT code, label, sort_order, is_terminal FROM dbo.metric_buckets ORDER BY sort_order;")
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [MetricBucketRecord(code=r["code"], label=r["label"], sort_order=int(r["sort_order"]),
                               is_terminal=bool(r["is_terminal"])) for r in rows]


def list_stage_buckets(engine: Engine, tenant_id: int | None) -> list[StageBucketRecord]:
    """Every stage label the company uses (current stages + history) plus every
    mapped label, with the bucket it resolves to and where that came from."""
    query = text(
        """
        WITH used AS (
            SELECT dbo.fn_stage_key(ca.current_stage) AS stage_key, ca.current_stage AS label, ca.id AS application_id
            FROM dbo.candidate_applications AS ca
            INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
            INNER JOIN dbo.branches AS b ON b.id = r.branch_id
            WHERE (:tenant_id IS NULL OR b.tenant_id = :tenant_id)
            UNION ALL
            SELECT dbo.fn_stage_key(h.to_stage), h.to_stage, NULL
            FROM dbo.candidate_stage_history AS h
            INNER JOIN dbo.candidate_applications AS ca ON ca.id = h.candidate_application_id
            INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
            INNER JOIN dbo.branches AS b ON b.id = r.branch_id
            WHERE (:tenant_id IS NULL OR b.tenant_id = :tenant_id)
            UNION ALL
            SELECT m.stage_key, NULL, NULL
            FROM dbo.stage_bucket_map AS m
            WHERE m.tenant_id IS NULL OR m.tenant_id = :tenant_id
        ),
        keys AS (
            SELECT stage_key, MAX(label) AS example_label, COUNT(DISTINCT application_id) AS applications
            FROM used
            WHERE stage_key IS NOT NULL AND stage_key <> N''
            GROUP BY stage_key
        )
        SELECT
            k.stage_key,
            k.example_label,
            dbo.fn_metric_bucket(NULL, :tenant_id, k.stage_key) AS metric_bucket,
            CASE
                WHEN tm.metric_bucket IS NOT NULL THEN N'company'
                WHEN pm.metric_bucket IS NOT NULL THEN N'platform'
                ELSE N'inferred'
            END AS source,
            pm.metric_bucket AS platform_bucket,
            k.applications
        FROM keys AS k
        LEFT JOIN dbo.stage_bucket_map AS tm ON tm.tenant_id = :tenant_id AND tm.stage_key = k.stage_key
        LEFT JOIN dbo.stage_bucket_map AS pm ON pm.tenant_id IS NULL AND pm.stage_key = k.stage_key
        ORDER BY k.applications DESC, k.stage_key ASC;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"tenant_id": tenant_id}).mappings().all()
    return [
        StageBucketRecord(
            stage_key=r["stage_key"],
            example_label=r["example_label"],
            metric_bucket=r["metric_bucket"],
            source=r["source"],
            platform_bucket=r["platform_bucket"],
            applications=int(r["applications"] or 0),
        )
        for r in rows
    ]


def resolve_bucket(engine: Engine, tenant_id: int | None, label: str) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT dbo.fn_metric_bucket(NULL, :tenant_id, :label);"),
            {"tenant_id": tenant_id, "label": label},
        ).scalar_one()


def find_tenant_mapping(engine: Engine, tenant_id: int, key: str) -> str | None:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT metric_bucket FROM dbo.stage_bucket_map WHERE tenant_id = :tenant_id AND stage_key = :key;"),
            {"tenant_id": tenant_id, "key": key},
        ).scalar_one_or_none()


def upsert_tenant_mapping(engine: Engine, tenant_id: int, key: str, bucket: str, user_id: int) -> None:
    query = text(
        """
        MERGE dbo.stage_bucket_map WITH (HOLDLOCK) AS t
        USING (SELECT :tenant_id AS tenant_id, :key AS stage_key) AS s
        ON t.tenant_id = s.tenant_id AND t.stage_key = s.stage_key
        WHEN MATCHED THEN UPDATE SET metric_bucket = :bucket, updated_by_user_id = :user_id, updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT (tenant_id, stage_key, metric_bucket, updated_by_user_id)
            VALUES (:tenant_id, :key, :bucket, :user_id);
        """
    )
    with engine.begin() as connection:
        connection.execute(query, {"tenant_id": tenant_id, "key": key, "bucket": bucket, "user_id": user_id})


def delete_tenant_mapping(engine: Engine, tenant_id: int, key: str) -> bool:
    with engine.begin() as connection:
        result = connection.execute(
            text("DELETE FROM dbo.stage_bucket_map WHERE tenant_id = :tenant_id AND stage_key = :key;"),
            {"tenant_id": tenant_id, "key": key},
        )
    return result.rowcount > 0
