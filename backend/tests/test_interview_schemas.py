import pytest
from pydantic import ValidationError

from app.schemas.interview import InterviewCreate, InterviewFeedbackUpdate, InterviewListFilters


def test_interview_create_normalizes_codes_and_text() -> None:
    payload = InterviewCreate(
        candidate_application_id=501,
        round_type=" Manager ",
        round_name="  L1 Manager Review  ",
        status="No Show",
        created_by_user_id=7,
    )

    assert payload.round_type == "manager"
    assert payload.round_name == "L1 Manager Review"
    assert payload.status == "no-show"


def test_interview_feedback_normalizes_decision() -> None:
    payload = InterviewFeedbackUpdate(
        status="Completed",
        feedback_status="Received",
        decision="Strong Yes",
        feedback_notes="  Excellent system design discussion.  ",
    )

    assert payload.status == "completed"
    assert payload.feedback_status == "received"
    assert payload.decision == "strong-yes"
    assert payload.feedback_notes == "Excellent system design discussion."


def test_interview_feedback_requires_decision_or_notes() -> None:
    with pytest.raises(ValidationError):
        InterviewFeedbackUpdate()


def test_interview_filters_normalize_status() -> None:
    filters = InterviewListFilters(status="No Show")

    assert filters.status == "no-show"
