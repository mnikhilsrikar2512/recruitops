from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.auth import (
    AuthContext,
    change_password_service,
    forgot_password_service,
    reset_password_service,
    setup_password_service,
)
from tests.stubs import make_login_user_record

from app.schemas.auth import (
    PasswordChangeRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    PasswordSetupRequest,
)


def _auth_context(user_id: int = 22, email: str = "test@example.com", role_code: str = "recruiter") -> AuthContext:
    user = SimpleNamespace(id=user_id, email=email, role_code=role_code, location_id=4)
    return AuthContext(session_id=1, session_token_hash="token", user=user)


def test_change_password_rejects_incorrect_current_password(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.auth.find_user_for_login",
        lambda engine, email: SimpleNamespace(password_hash="sha256:abc"),
    )

    with pytest.raises(HTTPException) as exc_info:
        change_password_service(
            object(),
            _auth_context(),
            PasswordChangeRequest(current_password="wrong", new_password="newpassword123"),
        )

    assert exc_info.value.status_code == 400


def test_change_password_succeeds_with_correct_password(monkeypatch) -> None:
    from app.core.security import sha256_hex

    correct_hash = f"sha256:{sha256_hex('oldpassword')}"
    monkeypatch.setattr(
        "app.services.auth.find_user_for_login",
        lambda engine, email: make_login_user_record(password_hash=correct_hash),
    )
    captured = {}
    monkeypatch.setattr(
        "app.services.auth.update_user_password_state",
        lambda engine, **kwargs: captured.update(kwargs),
    )

    response = change_password_service(
        object(),
        _auth_context(),
        PasswordChangeRequest(current_password="oldpassword", new_password="newpassword123"),
    )

    assert response.message == "Password changed successfully"
    assert captured["force_password_change_on_first_login"] is False
    assert captured["password_setup_status"] == "setup-complete"


def test_setup_password_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.auth.find_valid_password_reset_token",
        lambda engine, token_hash, purpose: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        setup_password_service(
            object(),
            PasswordSetupRequest(token="invalid-token", new_password="newpassword123"),
        )

    assert exc_info.value.status_code == 400


def test_setup_password_succeeds_with_valid_token(monkeypatch) -> None:
    token_record = {"id": 1, "user_id": 22}
    monkeypatch.setattr(
        "app.services.auth.find_valid_password_reset_token",
        lambda engine, token_hash, purpose: token_record,
    )
    captured = {}
    monkeypatch.setattr(
        "app.services.auth.update_user_password_state",
        lambda engine, **kwargs: captured.update(kwargs),
    )
    monkeypatch.setattr(
        "app.services.auth.mark_password_reset_token_used",
        lambda engine, token_id: None,
    )

    response = setup_password_service(
        object(),
        PasswordSetupRequest(token="valid-token", new_password="newpassword123"),
    )

    assert response.message == "Password set successfully"
    assert captured["user_id"] == 22
    assert captured["force_password_change_on_first_login"] is False


def test_forgot_password_always_returns_success_message(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.auth.find_user_by_email",
        lambda engine, email: None,
    )

    response = forgot_password_service(
        object(),
        PasswordForgotRequest(email="nonexistent@example.com"),
    )

    assert "reset link" in response.message.lower()


def test_forgot_password_creates_token_for_existing_user(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.auth.find_user_by_email",
        lambda engine, email: make_login_user_record(),
    )
    captured = {}
    monkeypatch.setattr(
        "app.services.auth.create_password_reset_token",
        lambda engine, **kwargs: captured.update(kwargs),
    )

    response = forgot_password_service(
        object(),
        PasswordForgotRequest(email="test@example.com"),
    )

    assert "reset link" in response.message.lower()
    assert captured["user_id"] == 22
    assert captured["purpose"] == "self-reset"


def test_reset_password_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.auth.find_valid_password_reset_token",
        lambda engine, token_hash, purpose: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        reset_password_service(
            object(),
            PasswordResetRequest(token="invalid-token", new_password="newpassword123"),
        )

    assert exc_info.value.status_code == 400


def test_reset_password_succeeds_with_valid_token(monkeypatch) -> None:
    token_record = {"id": 1, "user_id": 22}
    monkeypatch.setattr(
        "app.services.auth.find_valid_password_reset_token",
        lambda engine, token_hash, purpose: token_record,
    )
    captured = {}
    monkeypatch.setattr(
        "app.services.auth.update_user_password_state",
        lambda engine, **kwargs: captured.update(kwargs),
    )
    monkeypatch.setattr(
        "app.services.auth.mark_password_reset_token_used",
        lambda engine, token_id: None,
    )

    response = reset_password_service(
        object(),
        PasswordResetRequest(token="valid-token", new_password="newpassword123"),
    )

    assert response.message == "Password reset successfully"
    assert captured["user_id"] == 22
