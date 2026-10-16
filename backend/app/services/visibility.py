"""Field-level visibility rules: the admin-facing matrix (visibility.py
API) plus the masking helper every commercial-field response route
calls before returning data. See scripts/031_visibility_rules.sql."""
from __future__ import annotations

import json

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import Engine, text

from app.repositories.visibility import allowed_role_codes_map, list_visibility_rules, upsert_visibility_rule
from app.schemas.visibility import (
    VisibilityRoleOption,
    VisibilityRuleField,
    VisibilityRulesBulkUpdate,
    VisibilityRulesResponse,
)

# The only fields this feature knows how to gate. Adding a new gated
# field means: a migration row (scripts/0NN_*.sql) + listing it here +
# calling mask_single/mask_list at that field's response call site(s).
GATED_FIELDS = {
    "requisition": {"margin_percent", "bill_rate"},
    "client": {"default_bill_rate", "markup_percent"},
}


def _role_catalog(engine: Engine) -> list[VisibilityRoleOption]:
    query = text("SELECT code, name FROM dbo.roles WHERE status = N'active' ORDER BY name;")
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [VisibilityRoleOption(code=row["code"], name=row["name"]) for row in rows]


def get_visibility_rules_service(engine: Engine) -> VisibilityRulesResponse:
    rows = list_visibility_rules(engine)
    fields = [
        VisibilityRuleField(
            entity=row["entity"],
            field_name=row["field_name"],
            label=row["label"],
            allowed_role_codes=[c.strip() for c in (row["allowed_role_codes"] or "").split(",") if c.strip()],
        )
        for row in rows
    ]
    return VisibilityRulesResponse(fields=fields, roles=_role_catalog(engine))


def update_visibility_rules_service(
    engine: Engine, payload: VisibilityRulesBulkUpdate, updated_by_user_id: int | None
) -> VisibilityRulesResponse:
    for rule in payload.rules:
        if rule.entity not in GATED_FIELDS or rule.field_name not in GATED_FIELDS[rule.entity]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown visibility field: {rule.entity}.{rule.field_name}",
            )
    with engine.begin() as connection:
        for rule in payload.rules:
            codes_csv = ",".join(sorted({c.strip() for c in rule.allowed_role_codes if c.strip()}))
            upsert_visibility_rule(connection, rule.entity, rule.field_name, codes_csv, updated_by_user_id)
    return get_visibility_rules_service(engine)


def _hidden_fields_for_role(engine: Engine, entity: str, role_code: str) -> set[str]:
    """Which of this entity's gated fields this role cannot see. A field
    the matrix doesn't mention yet is left visible (fail open) rather
    than silently hidden from everyone before an admin configures it."""
    rules = allowed_role_codes_map(engine)
    hidden: set[str] = set()
    for field_name in GATED_FIELDS.get(entity, set()):
        allowed = rules.get((entity, field_name))
        if allowed is not None and role_code not in allowed:
            hidden.add(field_name)
    return hidden


def mask_single(entity: str, response: BaseModel, role_code: str, engine: Engine):
    """A single detail/create/update response: returns the Pydantic
    object unchanged when nothing needs hiding, or a JSONResponse with
    the hidden fields genuinely absent (not null) from the JSON body —
    returning a Response bypasses FastAPI's response_model
    re-serialization, which would otherwise put nulled-out fields back."""
    hidden = _hidden_fields_for_role(engine, entity, role_code)
    if not hidden:
        return response
    content = json.loads(response.model_dump_json(exclude=hidden))
    return JSONResponse(content=content)


def mask_list(entity: str, list_response: BaseModel, role_code: str, engine: Engine):
    """A *ListResponse with an .items list of per-entity response
    objects plus a .meta block; hides the same fields on every item."""
    hidden = _hidden_fields_for_role(engine, entity, role_code)
    if not hidden:
        return list_response
    content = json.loads(list_response.model_dump_json())
    content["items"] = [
        {k: v for k, v in json.loads(item_model.model_dump_json(exclude=hidden)).items()}
        for item_model in list_response.items
    ]
    return JSONResponse(content=content)
