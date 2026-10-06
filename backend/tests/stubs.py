"""Shared user/role stub factories for service-layer tests.

Monkeypatched repository calls return these instead of ad-hoc
``SimpleNamespace`` records. They mirror the real ``UserRecord`` /
``RoleRecord`` shapes, so a guard reading ``primary_role_code`` or any
other field keeps working as tests evolve — new fields show up as
factory parameters, not as AttributeError surprises in unrelated tests.
"""
from types import SimpleNamespace


def make_user_record(
    *,
    user_id: int = 22,
    full_name: str = "Test User",
    email: str = "test.user@example.com",
    phone: str | None = "+91-90000-00000",
    employee_code: str | None = "EMP1001",
    status: str = "active",
    business_title: str | None = "Senior Recruiter",
    primary_location_id: int | None = 4,
    primary_location_name: str | None = "Hyderabad Branch",
    primary_role_id: int = 7,
    primary_role_name: str = "Recruiter",
    primary_role_code: str = "recruiter",
    reporting_manager_user_id: int | None = None,
    reporting_manager_name: str | None = None,
    password_setup_status: str = "active",
    force_password_change_on_first_login: bool = False,
    **overrides,
) -> SimpleNamespace:
    """Mirror of repositories.users.UserRecord for stubbing find_user_by_id & co."""
    fields = dict(
        id=user_id,
        full_name=full_name,
        email=email,
        phone=phone,
        employee_code=employee_code,
        status=status,
        business_title=business_title,
        primary_location_id=primary_location_id,
        primary_location_name=primary_location_name,
        primary_role_id=primary_role_id,
        primary_role_name=primary_role_name,
        primary_role_code=primary_role_code,
        reporting_manager_user_id=reporting_manager_user_id,
        reporting_manager_name=reporting_manager_name,
        password_setup_status=password_setup_status,
        force_password_change_on_first_login=force_password_change_on_first_login,
        created_at=None,
        updated_at=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def make_login_user_record(
    *,
    user_id: int = 22,
    full_name: str = "Test User",
    email: str = "test.user@example.com",
    phone: str | None = "+91-90000-00000",
    employee_code: str | None = "EMP1001",
    password_hash: str = "bcrypt:$2b$12$stubhashstubhashstubha",
    status: str = "active",
    business_title: str | None = "Senior Recruiter",
    force_password_change_on_first_login: bool = False,
    location_id: int | None = 4,
    location_code: str | None = "HYD01",
    location_name: str | None = "Hyderabad Branch",
    role_id: int = 7,
    role_code: str = "recruiter",
    role_name: str = "Recruiter",
    **overrides,
) -> SimpleNamespace:
    """Mirror of repositories.auth.LoginUserRecord for stubbing
    find_user_for_login / find_user_by_email."""
    fields = dict(
        id=user_id,
        tenant_id=None,
        tenant_status="active",
        employee_code=employee_code,
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=password_hash,
        status=status,
        business_title=business_title,
        force_password_change_on_first_login=force_password_change_on_first_login,
        location_id=location_id,
        role_id=role_id,
        role_code=role_code,
        role_name=role_name,
        location_code=location_code,
        location_name=location_name,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def make_role_record(
    *,
    role_id: int = 2,
    code: str = "recruiter",
    name: str = "Recruiter",
    description: str | None = None,
    is_system_role: bool = False,
    status: str = "active",
    created_by_user_id: int | None = None,
    **overrides,
) -> SimpleNamespace:
    """Mirror of repositories.roles.RoleRecord for stubbing find_role_by_id & co."""
    fields = dict(
        id=role_id,
        code=code,
        name=name,
        description=description,
        is_system_role=is_system_role,
        status=status,
        created_by_user_id=created_by_user_id,
        created_at=None,
        updated_at=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)
