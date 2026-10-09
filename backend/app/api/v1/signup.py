"""Self-serve signup (Phase 5.2). Public; rate-limited per IP."""
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import Engine

from app.api.deps import get_engine
from app.core import rate_limit
from app.schemas.signup import (
    MfaConfirmRequest,
    MfaConfirmResponse,
    MfaStartResponse,
    ResendRequest,
    SetupTokenRequest,
    SignupAccepted,
    SignupRequest,
    VerifyRequest,
    VerifyResponse,
)
from app.services import signup

router = APIRouter()


@router.post("/", response_model=SignupAccepted, status_code=202)
def signup_endpoint(payload: SignupRequest, request: Request, background: BackgroundTasks,
                    engine: Engine = Depends(get_engine)) -> SignupAccepted:
    rate_limit.enforce("signup:ip", rate_limit.client_ip(request))
    return signup.signup_service(engine, payload, background, rate_limit.client_ip(request),
                                 request.headers.get("user-agent"))


@router.post("/resend", response_model=SignupAccepted, status_code=202)
def resend_endpoint(payload: ResendRequest, request: Request, background: BackgroundTasks,
                    engine: Engine = Depends(get_engine)) -> SignupAccepted:
    rate_limit.enforce("signup:ip", rate_limit.client_ip(request))
    return signup.resend_service(engine, payload.email, background)


@router.post("/verify", response_model=VerifyResponse)
def verify_endpoint(payload: VerifyRequest, request: Request, engine: Engine = Depends(get_engine)) -> VerifyResponse:
    rate_limit.enforce("signup_verify:ip", rate_limit.client_ip(request))
    return signup.verify_service(engine, payload.token)


@router.post("/mfa/start", response_model=MfaStartResponse)
def mfa_start_endpoint(payload: SetupTokenRequest, request: Request, engine: Engine = Depends(get_engine)) -> MfaStartResponse:
    rate_limit.enforce("signup_verify:ip", rate_limit.client_ip(request))
    return signup.mfa_start_service(engine, payload.setup_token)


@router.post("/mfa/confirm", response_model=MfaConfirmResponse)
def mfa_confirm_endpoint(payload: MfaConfirmRequest, request: Request, engine: Engine = Depends(get_engine)) -> MfaConfirmResponse:
    rate_limit.enforce("signup_verify:ip", rate_limit.client_ip(request))
    return signup.mfa_confirm_service(engine, payload.setup_token, payload.code)
