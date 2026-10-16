from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping


def list_visibility_rules(engine: Engine, tenant_id: int | None) -> list[RowMapping]:
    """One row per gated field: the caller's own company override when
    they have saved one, else the shared platform default (tenant_id
    IS NULL). Never returns another company's override."""
    query = text(
        """
        SELECT entity, field_name, label, allowed_role_codes, tenant_id
        FROM dbo.visibility_rules
        WHERE tenant_id = :tenant_id OR tenant_id IS NULL
        ORDER BY entity, field_name;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"tenant_id": tenant_id}).mappings().all()

    picked: dict[tuple[str, str], RowMapping] = {}
    for row in rows:
        key = (row["entity"], row["field_name"])
        if key not in picked or row["tenant_id"] is not None:
            picked[key] = row
    return sorted(picked.values(), key=lambda r: (r["entity"], r["field_name"]))


def upsert_visibility_rule(
    connection,
    tenant_id: int,
    entity: str,
    field_name: str,
    label: str,
    allowed_role_codes_csv: str,
    updated_by_user_id: int | None,
) -> None:
    """Upserts the CALLER'S company's own override row — never the
    shared platform-default row (tenant_id IS NULL), which only the
    seed migration writes. ``connection`` is an open transaction
    (``engine.begin()``), not the Engine itself."""
    update_query = text(
        """
        UPDATE dbo.visibility_rules
        SET allowed_role_codes = :allowed_role_codes,
            updated_by_user_id = :updated_by_user_id,
            updated_at = SYSUTCDATETIME()
        WHERE tenant_id = :tenant_id AND entity = :entity AND field_name = :field_name;
        """
    )
    params = {
        "tenant_id": tenant_id,
        "entity": entity,
        "field_name": field_name,
        "allowed_role_codes": allowed_role_codes_csv,
        "updated_by_user_id": updated_by_user_id,
    }
    result = connection.execute(update_query, params)
    if result.rowcount == 0:
        insert_query = text(
            """
            INSERT INTO dbo.visibility_rules
                (tenant_id, entity, field_name, label, allowed_role_codes, updated_by_user_id)
            VALUES
                (:tenant_id, :entity, :field_name, :label, :allowed_role_codes, :updated_by_user_id);
            """
        )
        connection.execute(insert_query, {**params, "label": label})


def allowed_role_codes_map(engine: Engine, tenant_id: int | None) -> dict[tuple[str, str], set[str]]:
    """{(entity, field_name): {role_code, ...}} for every gated field,
    scoped to the caller's own company (falling back to the platform
    default). A field with no row at all (shouldn't happen once seeded)
    is treated as visible to everyone — fail open to "not actually
    gated" rather than fail closed and hide data nobody configured a
    rule for."""
    rows = list_visibility_rules(engine, tenant_id)
    out: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        codes = {c.strip() for c in (row["allowed_role_codes"] or "").split(",") if c.strip()}
        out[(row["entity"], row["field_name"])] = codes
    return out
