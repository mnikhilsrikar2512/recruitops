from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.roles import (
    count_permissions_by_codes,
    create_role,
    find_role_by_code,
    find_role_by_id,
    list_all_permission_codes,
    list_permission_catalog,
    list_permission_codes_for_role,
    list_roles,
    list_scope_rules_for_role,
    replace_role_permissions,
    update_role,
)
from app.schemas.permission_catalog import PermissionCatalogResponse
from app.schemas.pagination import PaginationMeta
from app.schemas.role import (
    RoleCreate,
    RoleListFilters,
    RoleListResponse,
    RolePermissionsResponse,
    RolePermissionsUpdate,
    RoleResponse,
    RoleUpdate,
)


def list_permission_catalog_service(engine: Engine) -> PermissionCatalogResponse:
    return PermissionCatalogResponse(
        items=[
            {
                "code": item.code,
                "module_name": item.module_name,
                "action_name": item.action_name,
            }
            for item in list_permission_catalog(engine)
        ]
    )


def list_roles_service(engine: Engine, filters: RoleListFilters) -> RoleListResponse:
    items, total = list_roles(engine, filters)
    return RoleListResponse(
        items=[RoleResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_role_detail_service(engine: Engine, role_id: int) -> RoleResponse:
    existing = find_role_by_id(engine, role_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role was not found",
        )
    return RoleResponse.model_validate(existing)


def get_role_permissions_service(engine: Engine, role_id: int) -> RolePermissionsResponse:
    existing = find_role_by_id(engine, role_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role was not found",
        )
    return RolePermissionsResponse(
        role_id=role_id,
        permission_codes=list_permission_codes_for_role(engine, role_id),
        scope_rules=list_scope_rules_for_role(engine, role_id),
    )


def create_role_service(engine: Engine, payload: RoleCreate) -> RoleResponse:
    existing = find_role_by_code(engine, payload.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Role code already exists",
        )

    created = create_role(engine, payload)
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role could not be created",
        )

    return RoleResponse.model_validate(created)


def update_role_service(engine: Engine, role_id: int, payload: RoleUpdate) -> RoleResponse:
    existing = find_role_by_id(engine, role_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role was not found",
        )

    updated = update_role(engine, role_id, payload)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role could not be updated",
        )

    return RoleResponse.model_validate(updated)


def assign_role_permissions_service(
    engine: Engine,
    role_id: int,
    payload: RolePermissionsUpdate,
) -> RolePermissionsResponse:
    existing = find_role_by_id(engine, role_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role was not found",
        )

    # The admin role is the anchor of the permission bypass — stripping its
    # permission rows corrupts seeds and any code that reads them, even though
    # role_code-based bypass keeps working. Keep it all-access by definition.
    if existing.code == "admin" and set(payload.permission_codes) != set(
        list_all_permission_codes(engine)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The admin role must keep full access; its permissions cannot be changed",
        )

    permission_count = count_permissions_by_codes(engine, payload.permission_codes)
    if permission_count != len(payload.permission_codes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more permission codes are invalid",
        )

    replace_role_permissions(engine, role_id, payload.permission_codes, payload.scope_rules)

    return RolePermissionsResponse(
        role_id=role_id,
        permission_codes=list_permission_codes_for_role(engine, role_id),
        scope_rules=list_scope_rules_for_role(engine, role_id),
    )

