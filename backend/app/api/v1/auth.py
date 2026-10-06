from fastapi import APIRouter, Depends, Request
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine
from app.schemas.auth import (
    CurrentSessionResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
    PasswordForgotRequest,
    PasswordForgotResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordSetupRequest,
    PasswordSetupResponse,
    ProfileUpdateRequest,
)
from app.services.auth import (
    AuthContext,
    change_password_service,
    forgot_password_service,
    get_current_session_service,
    login_service,
    logout_service,
    reset_password_service,
    setup_password_service,
    update_own_profile_service,
)

router = APIRouter()


def _resolve_ip_address(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


@router.post("/login", response_model=LoginResponse)
def login_endpoint(
    payload: LoginRequest,
    request: Request,
    engine: Engine = Depends(get_engine),
) -> LoginResponse:
    return login_service(
        engine,
        payload,
        ip_address=_resolve_ip_address(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> LogoutResponse:
    return logout_service(engine, auth_context)


@router.get("/me", response_model=CurrentSessionResponse)
def me_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> CurrentSessionResponse:
    return get_current_session_service(engine, auth_context)


@router.patch("/profile", response_model=CurrentSessionResponse)
def update_profile_endpoint(
    payload: ProfileUpdateRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> CurrentSessionResponse:
    return update_own_profile_service(engine, auth_context, payload)


@router.post("/password/change", response_model=PasswordChangeResponse)
def change_password_endpoint(
    payload: PasswordChangeRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> PasswordChangeResponse:
    return change_password_service(engine, auth_context, payload)


@router.post("/password/setup", response_model=PasswordSetupResponse)
def setup_password_endpoint(
    payload: PasswordSetupRequest,
    engine: Engine = Depends(get_engine),
) -> PasswordSetupResponse:
    return setup_password_service(engine, payload)


@router.post("/password/forgot", response_model=PasswordForgotResponse)
def forgot_password_endpoint(
    payload: PasswordForgotRequest,
    engine: Engine = Depends(get_engine),
) -> PasswordForgotResponse:
    return forgot_password_service(engine, payload)


@router.post("/password/reset", response_model=PasswordResetResponse)
def reset_password_endpoint(
    payload: PasswordResetRequest,
    engine: Engine = Depends(get_engine),
) -> PasswordResetResponse:
    return reset_password_service(engine, payload)
