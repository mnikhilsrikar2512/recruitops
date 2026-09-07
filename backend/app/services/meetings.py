from fastapi import HTTPException, status
from sqlalchemy import Engine

from app.repositories.meetings import (
    create_meeting,
    find_meeting_by_id,
    list_meetings,
    meeting_client_exists,
    update_meeting,
)
from app.repositories.users import find_user_by_id, location_exists
from app.schemas.meeting import (
    MeetingCreate,
    MeetingListFilters,
    MeetingListResponse,
    MeetingResponse,
    MeetingUpdate,
)
from app.schemas.pagination import PaginationMeta


def _assert_meeting_refs(engine: Engine, payload: MeetingCreate | MeetingUpdate, location_id: int | None = None) -> None:
    payload_location_id = getattr(payload, "location_id", None)
    target_location_id = payload_location_id or location_id
    if payload_location_id is not None and not location_exists(engine, payload_location_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location was not found")

    client_id = getattr(payload, "client_id", None)
    if client_id is not None and not meeting_client_exists(engine, client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client was not found")

    end_client_id = getattr(payload, "end_client_id", None)
    if end_client_id is not None and not meeting_client_exists(engine, end_client_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="End client was not found")

    owner_ids = [
        getattr(payload, "meeting_owner_user_id", None),
        getattr(payload, "follow_up_owner_user_id", None),
    ]
    for user_id in [value for value in owner_ids if value is not None]:
        user = find_user_by_id(engine, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting owner user was not found")
        if target_location_id is not None and user.primary_location_id not in (None, target_location_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting owner must belong to the same location",
            )


def list_meetings_service(engine: Engine, filters: MeetingListFilters) -> MeetingListResponse:
    items, total = list_meetings(engine, filters)
    return MeetingListResponse(
        items=[MeetingResponse.model_validate(item) for item in items],
        meta=PaginationMeta(page=filters.page, page_size=filters.page_size, total=total),
    )


def get_meeting_detail_service(engine: Engine, meeting_id: int) -> MeetingResponse:
    meeting = find_meeting_by_id(engine, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting was not found")
    return MeetingResponse.model_validate(meeting)


def create_meeting_service(engine: Engine, payload: MeetingCreate) -> MeetingResponse:
    _assert_meeting_refs(engine, payload)
    created = create_meeting(engine, payload)
    return MeetingResponse.model_validate(created)


def update_meeting_service(engine: Engine, meeting_id: int, payload: MeetingUpdate) -> MeetingResponse:
    existing = find_meeting_by_id(engine, meeting_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting was not found")
    _assert_meeting_refs(engine, payload, location_id=existing.location_id)
    updated = update_meeting(engine, meeting_id, payload)
    return MeetingResponse.model_validate(updated)
