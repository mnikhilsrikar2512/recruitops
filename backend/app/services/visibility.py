"""Field-level visibility rules: the admin-facing matrix (visibility.py
API) plus the masking helper every commercial-field response route
calls before returning data. Scoped per company (tenant) — see
scripts/031_visibility_rules.sql and app/core/tenancy.py."""
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
# field means: a migration row (scripts/0NN_*.sql) + listing it here
# (with its label) + calling mask_single/mask_list at that field's
# response call site(s).
GATED_FIELDS = {
    "requisition": {"margin_percent", "bill_rate"},
    "client": {"default_bill_rate", "markup_percent"},
}

FIELD_LABELS = {
    ("requisition", "margin_percent"): "Margin %",
    ("requisition", "bill_rate"): "Bill Rate",
    ("client", "default_bill_rate"): "Default Bill Rate",
    ("client", "markup_percent"): "Markup %",
}


def _role_catalog(engine: Engine) -> list[VisibilityRoleOption]:
    query = text("SELECT code, name FROM dbo.roles WHERE status = N'active' ORDER BY name;")
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [VisibilityRoleOption(code=row["code"], name=row["name"]) for row in rows]


def get_visibility_rules_service(engine: Engine, tenant_id: int | None) -> VisibilityRulesResponse:
    rows = list_visibility_rules(engine, tenant_id)
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
    engine: Engine, payload: VisibilityRulesBulkUpdate, tenant_id: int | None, updated_by_user_id: int | None
) -> VisibilityRulesResponse:
    if tenant_id is None:
        # Every real session carries a tenant (users.tenant_id is NOT
        # NULL since 010_tenants.sql); refuse rather than silently write
        # into the shared platform-default row every company falls back
        # to, which only the seed migration may touch.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visibility rules require a company context.",
        )
    for rule in payload.rules:
        if rule.entity not in GATED_FIELDS or rule.field_name not in GATED_FIELDS[rule.entity]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown visibility field: {rule.entity}.{rule.field_name}",
            )
    with engine.begin() as connection:
        for rule in payload.rules:
            codes_csv = ",".join(sorted({c.strip() for c in rule.allowed_role_codes if c.strip()}))
            label = FIELD_LABELS[(rule.entity, rule.field_name)]
            upsert_visibility_rule(connection, tenant_id, rule.entity, rule.field_name, label, codes_csv, updated_by_user_id)
    return get_visibility_rules_service(engine, tenant_id)


def _hidden_fields_for_role(engine: Engine, entity: str, role_code: str, tenant_id: int | None) -> set[str]:
    """Which of this entity's gated fields this role cannot see, under
    this company's own rules (or the platform default if the company
    hasn't saved any yet). A field the matrix doesn't mention at all is
    left visible (fail open) rather than silently hidden from everyone
    before an admin configures it."""
    rules = allowed_role_codes_map(engine, tenant_id)
    hidden: set[str] = set()
    for field_name in GATED_FIELDS.get(entity, set()):
        allowed = rules.get((entity, field_name))
        if allowed is not None and role_code not in allowed:
            hidden.add(field_name)
    return hidden


def mask_single(entity: str, response: BaseModel, role_code: str, engine: Engine, tenant_id: int | None):
    """A single detail/create/update response: returns the Pydantic
    object unchanged when nothing needs hiding, or a JSONResponse with
    the hidden fields genuinely absent (not null) from the JSON body —
    returning a Response bypasses FastAPI's response_model
    re-serialization, which would otherwise put nulled-out fields back."""
    hidden = _hidden_fields_for_role(engine, entity, role_code, tenant_id)
    if not hidden:
        return response
    content = json.loads(response.model_dump_json(exclude=hidden))
    return JSONResponse(content=content)


def mask_list(entity: str, list_response: BaseModel, role_code: str, engine: Engine, tenant_id: int | None):
    """A *ListResponse with an .items list of per-entity response
    objects plus a .meta block; hides the same fields on every item."""
    hidden = _hidden_fields_for_role(engine, entity, role_code, tenant_id)
    if not hidden:
        return list_response
    content = json.loads(list_response.model_dump_json())
    content["items"] = [
        {k: v for k, v in json.loads(item_model.model_dump_json(exclude=hidden)).items()}
        for item_model in list_response.items
    ]
    return JSONResponse(content=content)
