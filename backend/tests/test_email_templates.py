from app.core.email import build_password_reset_email, build_password_setup_email, build_notification_email


def test_build_password_setup_email_contains_token() -> None:
    subject, html_body, text_body = build_password_setup_email("test-token-123")

    assert "Set Up Your Password" in subject
    assert "test-token-123" in html_body
    assert "test-token-123" in text_body
    assert "24 hours" in html_body


def test_build_password_reset_email_contains_token() -> None:
    subject, html_body, text_body = build_password_reset_email("reset-token-456")

    assert "Reset Your Password" in subject
    assert "reset-token-456" in html_body
    assert "reset-token-456" in text_body
    assert "24 hours" in html_body


def test_build_notification_email_with_action_url() -> None:
    subject, html_body, text_body = build_notification_email(
        user_name="John",
        event_type="pipeline_stage_changed",
        message="Candidate moved to interview",
        action_url="/pipeline/applications/100",
    )

    assert "Notification" in subject
    assert "John" in html_body
    assert "Candidate moved to interview" in html_body
    assert "/pipeline/applications/100" in html_body


def test_build_notification_email_without_action_url() -> None:
    subject, html_body, text_body = build_notification_email(
        user_name="John",
        event_type="daily_reminder",
        message="Daily update reminder",
    )

    assert "John" in html_body
    assert "Daily update reminder" in html_body
    assert "View Details" not in html_body
