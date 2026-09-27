from __future__ import annotations

from pydantic import BaseModel


class PermissionRecord(BaseModel):
    code: str
    module_name: str
    action_name: str


class PermissionCatalogResponse(BaseModel):
    items: list[PermissionRecord]
