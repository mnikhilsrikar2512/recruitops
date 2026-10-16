"""Field-level visibility rules — which roles can see which commercial
fields (requisition margin/bill rate, client default rate/markup),
company-wide. See scripts/031_visibility_rules.sql."""
from __future__ import annotations

from pydantic import BaseModel, Field


class VisibilityRuleField(BaseModel):
    entity: str
    field_name: str
    label: str
    allowed_role_codes: list[str]


class VisibilityRoleOption(BaseModel):
    code: str
    name: str


class VisibilityRulesResponse(BaseModel):
    fields: list[VisibilityRuleField]
    roles: list[VisibilityRoleOption]


class VisibilityRuleUpdate(BaseModel):
    entity: str
    field_name: str
    allowed_role_codes: list[str] = Field(default_factory=list)


class VisibilityRulesBulkUpdate(BaseModel):
    rules: list[VisibilityRuleUpdate]
