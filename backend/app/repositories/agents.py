from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass
class AgentRunRecord:
    id: int
    agent_id: str
    actor_user_id: int
    location_id: int | None
    input_refs: dict
    output_draft: dict
    output_summary: str
    status: str
    decided_by_user_id: int | None
    decided_at: object
    decision_notes: str | None
    created_at: object
    updated_at: object


def create_agent_run(
    engine: Engine,
    *,
    agent_id: str,
    actor_user_id: int,
    location_id: int | None,
    input_refs: dict,
    output_draft: dict,
    output_summary: str,
) -> AgentRunRecord:
    query = text(
        """
        INSERT INTO dbo.agent_runs (
          agent_id, actor_user_id, location_id, input_refs_json, output_draft_json,
          output_summary, status
        )
        OUTPUT INSERTED.id
        VALUES (
          :agent_id, :actor_user_id, :location_id, :input_refs_json, :output_draft_json,
          :output_summary, N'pending'
        );
        """
    )
    with engine.begin() as connection:
        run_id = connection.execute(
            query,
            {
                "agent_id": agent_id,
                "actor_user_id": actor_user_id,
                "location_id": location_id,
                "input_refs_json": json.dumps(input_refs, default=str),
                "output_draft_json": json.dumps(output_draft, default=str),
                "output_summary": output_summary,
            },
        ).scalar_one()
    created = find_agent_run_by_id(engine, int(run_id))
    if created is None:
        raise RuntimeError("Created agent run could not be reloaded")
    return created


def find_agent_run_by_id(engine: Engine, run_id: int) -> AgentRunRecord | None:
    query = text(
        """
        SELECT
          r.id,
          r.agent_id,
          r.actor_user_id,
          r.location_id,
          r.input_refs_json,
          r.output_draft_json,
          r.output_summary,
          r.status,
          r.decided_by_user_id,
          r.decided_at,
          r.decision_notes,
          r.created_at,
          r.updated_at
        FROM dbo.agent_runs AS r
        WHERE r.id = :run_id;
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"run_id": run_id}).mappings().first()
    if row is None:
        return None
    values = dict(row)
    values["input_refs"] = json.loads(values.pop("input_refs_json") or "{}")
    values["output_draft"] = json.loads(values.pop("output_draft_json") or "{}")
    return AgentRunRecord(**values)


def list_agent_runs(
    engine: Engine,
    *,
    actor_user_id: int,
    agent_id: str | None,
    page: int,
    page_size: int,
) -> tuple[list[AgentRunRecord], int]:
    query = text(
        """
        WITH filtered_runs AS (
          SELECT
            r.id,
            r.agent_id,
            r.actor_user_id,
            r.location_id,
            r.input_refs_json,
            r.output_draft_json,
            r.output_summary,
            r.status,
            r.decided_by_user_id,
            r.decided_at,
            r.decision_notes,
            r.created_at,
            r.updated_at
          FROM dbo.agent_runs AS r
          WHERE (:agent_id IS NULL OR r.agent_id = :agent_id)
          AND r.actor_user_id = :actor_user_id
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_runs
        ORDER BY created_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "agent_id": agent_id,
                "actor_user_id": actor_user_id,
                "offset": (page - 1) * page_size,
                "page_size": page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    records: list[AgentRunRecord] = []
    for row in rows:
        values = {key: value for key, value in row.items() if key != "total_count"}
        values["input_refs"] = json.loads(values.pop("input_refs_json") or "{}")
        values["output_draft"] = json.loads(values.pop("output_draft_json") or "{}")
        records.append(AgentRunRecord(**values))
    return records, total


def update_agent_run_decision(
    engine: Engine,
    run_id: int,
    *,
    status: str,
    decided_by_user_id: int,
    decision_notes: str | None,
) -> AgentRunRecord:
    query = text(
        """
        UPDATE dbo.agent_runs
        SET
          status = :status,
          decided_by_user_id = :decided_by_user_id,
          decided_at = SYSUTCDATETIME(),
          decision_notes = :decision_notes,
          updated_at = SYSUTCDATETIME()
        WHERE id = :run_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "status": status,
                "decided_by_user_id": decided_by_user_id,
                "decision_notes": decision_notes,
                "run_id": run_id,
            },
        )
    updated = find_agent_run_by_id(engine, run_id)
    if updated is None:
        raise RuntimeError("Updated agent run could not be reloaded")
    return updated