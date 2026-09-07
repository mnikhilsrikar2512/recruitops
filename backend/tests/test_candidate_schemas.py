import pytest
from pydantic import ValidationError

from app.schemas.candidate import (
    CandidateCreate,
    CandidateDocumentCreate,
    CandidateFinalizePayload,
    CandidateOwnerReassignment,
    CandidateUpdate,
)


def test_candidate_create_normalizes_values() -> None:
    payload = CandidateCreate(
        full_name="  Jane Doe  ",
        email="  JANE@EXAMPLE.COM  ",
        phone=" 1234567890 ",
        source_type=" Referral ",
        source_detail=" Internal ",
        current_company=" Acme ",
        current_designation=" Recruiter ",
        primary_owner_user_id=1,
    )

    assert payload.full_name == "Jane Doe"
    assert payload.email == "jane@example.com"
    assert payload.phone == "1234567890"
    assert payload.source_type == "Referral"


def test_candidate_update_requires_one_field() -> None:
    with pytest.raises(ValidationError):
        CandidateUpdate()


def test_candidate_owner_reassignment_normalizes_reason() -> None:
    payload = CandidateOwnerReassignment(new_primary_owner_user_id=2, reason="  workload transfer  ")

    assert payload.reason == "workload transfer"


def test_candidate_document_create_normalizes_file_fields() -> None:
    payload = CandidateDocumentCreate(file_name=" resume.pdf ", file_path=" /files/resume.pdf ")

    assert payload.file_name == "resume.pdf"
    assert payload.file_path == "/files/resume.pdf"


def test_candidate_finalize_payload_normalizes_stage() -> None:
    payload = CandidateFinalizePayload(requisition_id=10, initial_stage=" submitted ", owner_user_id=2)

    assert payload.initial_stage == "submitted"
