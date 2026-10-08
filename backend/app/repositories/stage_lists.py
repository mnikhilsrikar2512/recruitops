"""Client stage lists (Phase 4.10, scripts/025_client_stage_lists.sql).

Per client only (D-4.10): a client has ONE stage list and every requisition
for that client uses it. Internal hiring, and clients without a list of
their own, use the company default; with neither, the platform stages.

A list is stored as a pipeline_templates row (tenant_id, client_company_id)
plus its pipeline_template_stages. Requisitions point at the list through
requisitions.pipeline_template_id, which the SQL bucket resolver already
reads, so every report keeps working.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, Engine, text

from app.core.stage_buckets import TERMINAL_BUCKETS, stage_key

PLATFORM_DEFAULT_STAGES: list[tuple[str, str]] = [
    ("Sourced", "sourced"),
    ("Screening", "screened"),
    ("Submitted to Client", "submitted"),
    ("Client Interview", "interview"),
    ("Offer", "offer"),
    ("Joined", "joined"),
    ("Rejected", "rejected"),
    ("Withdrawn", "withdrawn"),
]
# Every list needs a way to close a candidate out; missing ones are added.
REQUIRED_CLOSING = [("Joined", "joined"), ("Rejected", "rejected"), ("Withdrawn", "withdrawn")]


@dataclass
class StageDef:
    name: str
    bucket: str
    allows_rejection: bool = True

    @property
    def code(self) -> str:
        return stage_key(self.name)


@dataclass
class StageList:
    template_id: int | None
    source: str  # "client" | "company" | "platform"
    client_company_id: int | None
    stages: list[dict] = field(default_factory=list)
    version: int | None = None


class StageRemapRequired(Exception):
    """Active candidates sit in stages the new list drops."""

    def __init__(self, unmapped: list[dict], allowed: list[str]) -> None:
        super().__init__("Some candidates are in stages that the new list removes")
        self.unmapped = unmapped
        self.allowed = allowed


def normalise_stages(stages: list[StageDef]) -> list[StageDef]:
    """Pure: de-duplicate by key, keep order, add any missing closing stage."""
    seen: set[str] = set()
    result: list[StageDef] = []
    for stage in stages:
        name = (stage.name or "").strip()
        if not name or stage_key(name) in seen:
            continue
        seen.add(stage_key(name))
        result.append(StageDef(name=name, bucket=stage.bucket, allows_rejection=stage.allows_rejection))
    present = {stage.bucket for stage in result}
    for name, bucket in REQUIRED_CLOSING:
        if bucket not in present and stage_key(name) not in seen:
            result.append(StageDef(name=name, bucket=bucket))
            seen.add(stage_key(name))
    return result


def _stage_rows(connection: Connection, template_id: int) -> list[dict]:
    rows = connection.execute(
        text(
            """
            SELECT stage_code, stage_name, stage_order, metric_bucket, allows_rejection, is_terminal
            FROM dbo.pipeline_template_stages
            WHERE pipeline_template_id = :t
            ORDER BY stage_order, id;
            """
        ),
        {"t": template_id},
    ).mappings().all()
    return [
        {
            "code": row["stage_code"],
            "name": row["stage_name"],
            "order": int(row["stage_order"]),
            "bucket": row["metric_bucket"],
            "allows_rejection": bool(row["allows_rejection"]),
            "is_terminal": bool(row["is_terminal"]),
        }
        for row in rows
    ]


def _find_template(connection: Connection, tenant_id: int, client_company_id: int | None, lock: bool = False):
    hint = "WITH (UPDLOCK, HOLDLOCK)" if lock else ""
    if client_company_id is None:
        sql = (f"SELECT TOP (1) id, version FROM dbo.pipeline_templates {hint} WHERE tenant_id = :tenant "
               "AND client_company_id IS NULL AND stage_scope = N'company' AND status = N'active';")
    else:
        sql = (f"SELECT TOP (1) id, version FROM dbo.pipeline_templates {hint} WHERE tenant_id = :tenant "
               "AND client_company_id = :client AND status = N'active';")
    return connection.execute(text(sql), {"tenant": tenant_id, "client": client_company_id}).mappings().first()


def platform_list() -> StageList:
    return StageList(
        template_id=None,
        source="platform",
        client_company_id=None,
        stages=[
            {"code": stage_key(name), "name": name, "order": (i + 1) * 10, "bucket": bucket,
             "allows_rejection": True, "is_terminal": bucket in TERMINAL_BUCKETS}
            for i, (name, bucket) in enumerate(PLATFORM_DEFAULT_STAGES)
        ],
    )


def get_stage_list(engine: Engine, tenant_id: int, client_company_id: int | None) -> StageList:
    """The list that applies: the client's own, else the company default,
    else the platform stages."""
    with engine.connect() as connection:
        if client_company_id is not None:
            row = _find_template(connection, tenant_id, client_company_id)
            if row:
                return StageList(int(row["id"]), "client", client_company_id, _stage_rows(connection, int(row["id"])), int(row["version"]))
        row = _find_template(connection, tenant_id, None)
        if row:
            return StageList(int(row["id"]), "company", None, _stage_rows(connection, int(row["id"])), int(row["version"]))
    return platform_list()


def list_client_stage_lists(engine: Engine, tenant_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT c.id AS client_id, c.name AS client_name, t.id AS template_id,
                       (SELECT COUNT(*) FROM dbo.pipeline_template_stages s WHERE s.pipeline_template_id = t.id) AS stage_count
                FROM dbo.client_companies AS c
                INNER JOIN dbo.branches AS b ON b.id = c.branch_id
                LEFT JOIN dbo.pipeline_templates AS t
                  ON t.client_company_id = c.id AND t.status = N'active'
                WHERE b.tenant_id = :tenant AND c.archived_at IS NULL
                ORDER BY c.name;
                """
            ),
            {"tenant": tenant_id},
        ).mappings().all()
    return [
        {"client_id": int(r["client_id"]), "client_name": r["client_name"],
         "template_id": int(r["template_id"]) if r["template_id"] else None,
         "has_own_list": r["template_id"] is not None, "stage_count": int(r["stage_count"] or 0)}
        for r in rows
    ]


def _affected_requisitions_sql(client_company_id: int | None) -> str:
    """Requisitions governed by this list."""
    if client_company_id is not None:
        return """
            SELECT r.id FROM dbo.requisitions AS r
            INNER JOIN dbo.branches AS b ON b.id = r.branch_id
            WHERE b.tenant_id = :tenant AND r.client_company_id = :client
        """
    return """
        SELECT r.id FROM dbo.requisitions AS r
        INNER JOIN dbo.branches AS b ON b.id = r.branch_id
        WHERE b.tenant_id = :tenant
          AND (r.client_company_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM dbo.pipeline_templates AS ct
            WHERE ct.client_company_id = r.client_company_id AND ct.status = N'active'))
    """


def save_stage_list(
    engine: Engine,
    *,
    tenant_id: int,
    client_company_id: int | None,
    stages: list[StageDef],
    remap: dict[str, str],
    user_id: int,
    location_id: int | None,
) -> int:
    """Create or replace the list in one transaction. Active candidates in a
    stage the new list drops must be remapped (StageRemapRequired lists
    them); remapped moves are written to the stage history."""
    stages = normalise_stages(stages)
    keys = {stage.code: stage for stage in stages}
    for stage in stages:
        keys.setdefault(stage_key(stage.name), stage)
    affected = _affected_requisitions_sql(client_company_id)
    params = {"tenant": tenant_id, "client": client_company_id}
    remap_keys = {stage_key(old): stage_key(new) for old, new in (remap or {}).items()}
    with engine.begin() as connection:
        existing = _find_template(connection, tenant_id, client_company_id, lock=True)
        in_use = connection.execute(
            text(
                f"""
                SELECT ca.current_stage, COUNT(*) AS n
                FROM dbo.candidate_applications AS ca
                WHERE ca.requisition_id IN ({affected}) AND ca.application_status = N'active'
                GROUP BY ca.current_stage;
                """
            ),
            params,
        ).mappings().all()
        unmapped = []
        moves: list[tuple[str, StageDef]] = []
        for row in in_use:
            key = stage_key(row["current_stage"])
            if key in keys:
                continue
            target_key = remap_keys.get(key)
            if not target_key or target_key not in keys or keys[target_key].bucket in TERMINAL_BUCKETS:
                unmapped.append({"stage": row["current_stage"], "candidates": int(row["n"])})
                continue
            moves.append((row["current_stage"], keys[target_key]))
        if unmapped:
            raise StageRemapRequired(
                unmapped, [s.name for s in stages if s.bucket not in TERMINAL_BUCKETS]
            )

        if existing:
            template_id = int(existing["id"])
            connection.execute(
                text("UPDATE dbo.pipeline_templates SET version = version + 1, updated_at = SYSUTCDATETIME() WHERE id = :t;"),
                {"t": template_id},
            )
            connection.execute(text("DELETE FROM dbo.pipeline_template_stages WHERE pipeline_template_id = :t;"), {"t": template_id})
        else:
            template_id = int(connection.execute(
                text(
                    """
                    INSERT INTO dbo.pipeline_templates
                      (tenant_id, client_company_id, location_id, template_name, stage_scope, status, created_by_user_id)
                    OUTPUT INSERTED.id
                    VALUES (:tenant, :client, :location, :name, :scope, N'active', :u);
                    """
                ),
                {"tenant": tenant_id, "client": client_company_id, "location": location_id,
                 "name": "Client stages" if client_company_id else "Company default stages",
                 "scope": "client" if client_company_id else "company", "u": user_id},
            ).scalar_one())
        for index, stage in enumerate(stages):
            connection.execute(
                text(
                    """
                    INSERT INTO dbo.pipeline_template_stages
                      (pipeline_template_id, stage_code, stage_name, stage_order, stage_type, allows_rejection,
                       metric_bucket, is_terminal)
                    VALUES (:t, :code, :name, :ord, :type, :rej, :bucket, :terminal);
                    """
                ),
                {"t": template_id, "code": stage.code[:50], "name": stage.name[:150], "ord": (index + 1) * 10,
                 "type": "rejection" if stage.bucket == "rejected" else "joining" if stage.bucket == "joined" else "normal",
                 "rej": 1 if stage.allows_rejection else 0, "bucket": stage.bucket,
                 "terminal": 1 if stage.bucket in TERMINAL_BUCKETS else 0},
            )

        # Point the governed requisitions at the list; drop any per-application
        # pointer so the client's list is the one that applies.
        connection.execute(
            text(
                f"""
                UPDATE dbo.requisitions
                SET pipeline_template_id = :t, version = version + 1, updated_at = SYSUTCDATETIME()
                WHERE id IN ({affected}) AND (pipeline_template_id IS NULL OR pipeline_template_id <> :t);
                """
            ),
            {**params, "t": template_id},
        )
        connection.execute(
            text(
                f"""
                UPDATE dbo.candidate_applications
                SET pipeline_template_id = NULL, version = version + 1, updated_at = SYSUTCDATETIME()
                WHERE requisition_id IN ({affected}) AND pipeline_template_id IS NOT NULL;
                """
            ),
            params,
        )
        for old_label, target in moves:
            ids = connection.execute(
                text(
                    f"""
                    SELECT ca.id FROM dbo.candidate_applications AS ca
                    WHERE ca.requisition_id IN ({affected}) AND ca.application_status = N'active'
                      AND ca.current_stage = :old;
                    """
                ),
                {**params, "old": old_label},
            ).scalars().all()
            for application_id in ids:
                connection.execute(
                    text(
                        """
                        UPDATE dbo.candidate_applications
                        SET current_stage = :new, version = version + 1,
                            stage_updated_at = SYSUTCDATETIME(), updated_at = SYSUTCDATETIME()
                        WHERE id = :a;
                        """
                    ),
                    {"a": application_id, "new": target.name},
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO dbo.candidate_stage_history
                          (candidate_application_id, from_stage, to_stage, change_reason, changed_by_user_id,
                           changed_at, source_type)
                        VALUES (:a, :old, :new, :reason, :u, SYSUTCDATETIME(), N'stage-list-change');
                        """
                    ),
                    {"a": application_id, "old": old_label, "new": target.name, "u": user_id,
                     "reason": f"Stage list changed: '{old_label}' is now '{target.name}'"},
                )
    return template_id


def point_requisition_at_list(engine: Engine, requisition_id: int) -> None:
    """New requisition: use its client's list, else the company default."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE r
                SET pipeline_template_id = COALESCE(
                      (SELECT TOP (1) ct.id FROM dbo.pipeline_templates AS ct
                       WHERE ct.client_company_id = r.client_company_id AND ct.status = N'active'),
                      (SELECT TOP (1) dt.id FROM dbo.pipeline_templates AS dt
                       WHERE dt.tenant_id = b.tenant_id AND dt.client_company_id IS NULL
                         AND dt.stage_scope = N'company' AND dt.status = N'active')),
                    version = version + 1
                FROM dbo.requisitions AS r
                INNER JOIN dbo.branches AS b ON b.id = r.branch_id
                WHERE r.id = :r;
                """
            ),
            {"r": requisition_id},
        )


def stage_options_for_application(engine: Engine, application_id: int) -> StageList:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT COALESCE(ca.pipeline_template_id, r.pipeline_template_id) AS template_id,
                       r.client_company_id, t.client_company_id AS list_client
                FROM dbo.candidate_applications AS ca
                INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
                LEFT JOIN dbo.pipeline_templates AS t ON t.id = COALESCE(ca.pipeline_template_id, r.pipeline_template_id)
                WHERE ca.id = :a;
                """
            ),
            {"a": application_id},
        ).mappings().first()
        if row and row["template_id"]:
            template_id = int(row["template_id"])
            source = "client" if row["list_client"] else "company"
            return StageList(template_id, source, row["client_company_id"], _stage_rows(connection, template_id))
    return platform_list()
