from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping


def list_visibility_rules(engine: Engine) -> list[RowMapping]:
    query = text(
        """
        SELECT entity, field_name, label, allowed_role_codes
        FROM dbo.visibility_rules
        ORDER BY entity, field_name;
        """
    )
    with engine.connect() as connection:
        return connection.execute(query).mappings().all()


def upsert_visibility_rule(
    engine_or_connection, entity: str, field_name: str, allowed_role_codes_csv: str, updated_by_user_id: int | None
) -> None:
    query = text(
        """
        UPDATE dbo.visibility_rules
        SET allowed_role_codes = :allowed_role_codes,
            updated_by_user_id = :updated_by_user_id,
            updated_at = SYSUTCDATETIME()
        WHERE entity = :entity AND field_name = :field_name;
        """
    )
    engine_or_connection.execute(
        query,
        {
            "entity": entity,
            "field_name": field_name,
            "allowed_role_codes": allowed_role_codes_csv,
            "updated_by_user_id": updated_by_user_id,
        },
    )


def allowed_role_codes_map(engine: Engine) -> dict[tuple[str, str], set[str]]:
    """{(entity, field_name): {role_code, ...}} for every gated field.
    A field with no row here (shouldn't happen once seeded) is treated
    as visible to everyone — fail open to "not actually gated" rather
    than fail closed and hide data nobody configured a rule for."""
    rows = list_visibility_rules(engine)
    out: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        codes = {c.strip() for c in (row["allowed_role_codes"] or "").split(",") if c.strip()}
        out[(row["entity"], row["field_name"])] = codes
    return out
