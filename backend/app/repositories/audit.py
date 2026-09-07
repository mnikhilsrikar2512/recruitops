from __future__ import annotations

import json

from sqlalchemy import Engine, text


def insert_audit_log(
    engine: Engine,
    *,
    actor_user_id: int,
    location_id: int | None,
    entity_type: str,
    entity_id: int,
    action_type: str,
    old_values: dict | None = None,
    new_values: dict | None = None,
) -> None:
    query = text(
        """
        INSERT INTO dbo.audit_logs (
          actor_user_id,
          location_id,
          entity_type,
          entity_id,
          action_type,
          old_values_json,
          new_values_json,
          created_at
        )
        VALUES (
          :actor_user_id,
          :location_id,
          :entity_type,
          :entity_id,
          :action_type,
          :old_values_json,
          :new_values_json,
          SYSUTCDATETIME()
        );
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "actor_user_id": actor_user_id,
                "location_id": location_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action_type": action_type,
                "old_values_json": json.dumps(old_values, default=str) if old_values is not None else None,
                "new_values_json": json.dumps(new_values, default=str) if new_values is not None else None,
            },
        )
