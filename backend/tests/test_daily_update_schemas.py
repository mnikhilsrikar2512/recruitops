from app.schemas.daily_update import DailyUpdateCreate


def test_daily_update_create_normalizes_optional_text() -> None:
    payload = DailyUpdateCreate(
        update_date="2026-08-19",
        requisition_id=1,
        submitted_by_user_id=2,
        summary="  Completed sourcing push  ",
        blockers="  Waiting for feedback  ",
        next_actions="  Send next shortlist  ",
    )

    assert payload.summary == "Completed sourcing push"
    assert payload.blockers == "Waiting for feedback"
    assert payload.next_actions == "Send next shortlist"


def test_daily_update_create_defaults_submission_status() -> None:
    payload = DailyUpdateCreate(
        update_date="2026-08-19",
        requisition_id=1,
        submitted_by_user_id=2,
        summary="Completed sourcing push",
    )

    assert payload.submission_status == "submitted"
