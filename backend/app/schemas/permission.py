from pydantic import BaseModel


class PermissionScopePayload(BaseModel):
    clients: str
    requisitions: str
    candidates: str
    locations: str
    location_ids: list[int] | None


class ResolvedPermissionsResponse(BaseModel):
    role_code: str
    permissions: list[str]
    scopes: PermissionScopePayload
    allowed_pages: list[str]
