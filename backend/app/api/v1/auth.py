from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from app.api.deps import get_current_auth_context, get_engine
from app.core.config import settings
from app.core.tokens import REFRESH_COOKIE, REFRESH_COOKIE_PATH
from app.schemas.auth import (
    CurrentSessionResponse,
    RefreshResponse,
    SessionListResponse,
    SessionsRevokedResponse,
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
    list_sessions_service,
    login_service,
    logout_service,
    refresh_service,
    revoke_other_sessions_service,
    revoke_own_session_service,
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


def _set_refresh_cookie(response: Response, raw: str) -> None:
    """HttpOnly + SameSite=Strict + scoped to the auth routes: page scripts can't
    read it and other sites can't send it. Secure outside development."""
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, samesite="strict",
                           secure=settings.is_production, httponly=True)


@router.post("/login", response_model=LoginResponse)
def login_endpoint(
    payload: LoginRequest,
    request: Request,
    response: Response,
    engine: Engine = Depends(get_engine),
) -> LoginResponse:
    body, refresh_raw = login_service(
        engine,
        payload,
        ip_address=_resolve_ip_address(request),
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, refresh_raw)
    return body


@router.post("/refresh", response_model=RefreshResponse)
def refresh_endpoint(request: Request, response: Response, engine: Engine = Depends(get_engine)):
    """New access token from the refresh cookie; the cookie rotates each time."""
    try:
        body, refresh_raw = refresh_service(engine, request.cookies.get(REFRESH_COOKIE))
    except HTTPException as exc:
        failed = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        _clear_refresh_cookie(failed)  # a dead refresh token is dropped from the browser
        return failed
    _set_refresh_cookie(response, refresh_raw)
    return RefreshResponse(**body)


@router.post("/logout", response_model=LogoutResponse)
def logout_endpoint(
    response: Response,
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> LogoutResponse:
    _clear_refresh_cookie(response)
    return logout_service(engine, auth_context)


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> SessionListResponse:
    return SessionListResponse(**list_sessions_service(engine, auth_context))


@router.delete("/sessions", response_model=SessionsRevokedResponse)
def revoke_other_sessions_endpoint(
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> SessionsRevokedResponse:
    """Sign out every OTHER device; this one stays signed in."""
    return SessionsRevokedResponse(revoked=revoke_other_sessions_service(engine, auth_context))


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session_endpoint(
    session_id: int = Path(..., ge=1),
    auth_context: AuthContext = Depends(get_current_auth_context),
    engine: Engine = Depends(get_engine),
) -> Response:
    revoke_own_session_service(engine, auth_context, session_id)
    return Response(status_code=204)


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
