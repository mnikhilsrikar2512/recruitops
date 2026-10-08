from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Engine, text
from sqlalchemy.engine import RowMapping

from app.schemas.meeting import MeetingCreate, MeetingListFilters, MeetingUpdate


def meeting_client_exists(engine: Engine, client_id: int) -> bool:
    query = text("SELECT 1 FROM dbo.clients WHERE id = :client_id;")
    with engine.connect() as connection:
        return connection.execute(query, {"client_id": client_id}).first() is not None


@dataclass
class MeetingAttendeeRecord:
    id: int
    meeting_id: int
    attendee_type: str
    user_id: int | None
    user_name: str | None
    client_contact_id: int | None
    client_contact_name: str | None
    attendance_status: str
    notes: str | None
    created_at: object
    updated_at: object


@dataclass
class MeetingRecord:
    id: int
    location_id: int
    location_name: str | None
    client_id: int
    client_name: str | None
    end_client_id: int | None
    end_client_name: str | None
    meeting_owner_user_id: int
    meeting_owner_name: str | None
    title: str
    meeting_type: str
    scheduled_at: object | None
    attendance_status: str
    outcome_status: str
    agenda: str | None
    minutes_of_meeting: str | None
    decision_summary: str | None
    next_steps: str | None
    follow_up_owner_user_id: int | None
    follow_up_owner_name: str | None
    follow_up_due_date: object | None
    created_at: object
    updated_at: object
    attendees: list[MeetingAttendeeRecord] = field(default_factory=list)


def _map_meeting(row: RowMapping) -> MeetingRecord:
    return MeetingRecord(
        id=row["id"],
        location_id=row["location_id"],
        location_name=row["location_name"],
        client_id=row["client_id"],
        client_name=row["client_name"],
        end_client_id=row["end_client_id"],
        end_client_name=row["end_client_name"],
        meeting_owner_user_id=row["meeting_owner_user_id"],
        meeting_owner_name=row["meeting_owner_name"],
        title=row["title"],
        meeting_type=row["meeting_type"],
        scheduled_at=row["scheduled_at"],
        attendance_status=row["attendance_status"],
        outcome_status=row["outcome_status"],
        agenda=row["agenda"],
        minutes_of_meeting=row["minutes_of_meeting"],
        decision_summary=row["decision_summary"],
        next_steps=row["next_steps"],
        follow_up_owner_user_id=row["follow_up_owner_user_id"],
        follow_up_owner_name=row["follow_up_owner_name"],
        follow_up_due_date=row["follow_up_due_date"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _map_attendee(row: RowMapping) -> MeetingAttendeeRecord:
    return MeetingAttendeeRecord(
        id=row["id"],
        meeting_id=row["meeting_id"],
        attendee_type=row["attendee_type"],
        user_id=row["user_id"],
        user_name=row["user_name"],
        client_contact_id=row["client_contact_id"],
        client_contact_name=row["client_contact_name"],
        attendance_status=row["attendance_status"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _meeting_select_sql() -> str:
    return """
      SELECT
        m.id,
        m.location_id,
        l.name AS location_name,
        m.client_id,
        client.name AS client_name,
        m.end_client_id,
        end_client.name AS end_client_name,
        m.meeting_owner_user_id,
        owner.full_name AS meeting_owner_name,
        m.title,
        LOWER(REPLACE(m.meeting_type, N' ', N'_')) AS meeting_type,
        m.scheduled_at,
        m.attendance_status,
        m.outcome_status,
        m.agenda,
        m.minutes_of_meeting,
        m.decision_summary,
        m.next_steps,
        m.follow_up_owner_user_id,
        follow_up_owner.full_name AS follow_up_owner_name,
        m.follow_up_due_date,
        m.created_at,
        m.updated_at
      FROM dbo.meetings AS m
      LEFT JOIN dbo.locations AS l
        ON l.id = m.location_id
      LEFT JOIN dbo.clients AS client
        ON client.id = m.client_id
      LEFT JOIN dbo.clients AS end_client
        ON end_client.id = m.end_client_id
      LEFT JOIN dbo.users AS owner
        ON owner.id = m.meeting_owner_user_id
      LEFT JOIN dbo.users AS follow_up_owner
        ON follow_up_owner.id = m.follow_up_owner_user_id
    """


def list_meetings(engine: Engine, filters: MeetingListFilters) -> tuple[list[MeetingRecord], int]:
    query = text(
        f"""
        WITH filtered_meetings AS (
          {_meeting_select_sql()}
          WHERE (:location_id IS NULL OR m.location_id = :location_id)
          AND (:tenant_id IS NULL OR m.location_id IN (SELECT tb.id FROM dbo.branches AS tb WHERE tb.tenant_id = :tenant_id))
          AND (:client_id IS NULL OR m.client_id = :client_id OR m.end_client_id = :client_id)
          AND (:meeting_owner_user_id IS NULL OR m.meeting_owner_user_id = :meeting_owner_user_id)
          AND (:attendance_status IS NULL OR m.attendance_status = :attendance_status)
          AND (:outcome_status IS NULL OR m.outcome_status = :outcome_status)
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM filtered_meetings
        ORDER BY scheduled_at DESC, id DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {
                "location_id": filters.location_id,
                "tenant_id": filters.tenant_id,
                "client_id": filters.client_id,
                "meeting_owner_user_id": filters.meeting_owner_user_id,
                "attendance_status": filters.attendance_status,
                "outcome_status": filters.outcome_status,
                "offset": (filters.page - 1) * filters.page_size,
                "page_size": filters.page_size,
            },
        ).mappings().all()
    total = rows[0]["total_count"] if rows else 0
    meetings = [_map_meeting(row) for row in rows]
    attach_meeting_attendees(engine, meetings)
    return meetings, total


def find_meeting_by_id(engine: Engine, meeting_id: int) -> MeetingRecord | None:
    query = text(f"{_meeting_select_sql()} WHERE m.id = :meeting_id;")
    with engine.connect() as connection:
        row = connection.execute(query, {"meeting_id": meeting_id}).mappings().first()
    if row is None:
        return None
    meeting = _map_meeting(row)
    attach_meeting_attendees(engine, [meeting])
    return meeting


def attach_meeting_attendees(engine: Engine, meetings: list[MeetingRecord]) -> None:
    meeting_ids = [meeting.id for meeting in meetings]
    if not meeting_ids:
        return
    bind_names = [f"meeting_id_{index}" for index, _ in enumerate(meeting_ids)]
    placeholders = ", ".join(f":{name}" for name in bind_names)
    query = text(
        f"""
        SELECT
          ma.id,
          ma.meeting_id,
          ma.attendee_type,
          ma.user_id,
          attendee_user.full_name AS user_name,
          ma.client_contact_id,
          contact.full_name AS client_contact_name,
          ma.attendance_status,
          ma.notes,
          ma.created_at,
          ma.updated_at
        FROM dbo.meeting_attendees AS ma
        LEFT JOIN dbo.users AS attendee_user
          ON attendee_user.id = ma.user_id
        LEFT JOIN dbo.client_contacts AS contact
          ON contact.id = ma.client_contact_id
        WHERE ma.meeting_id IN ({placeholders})
        ORDER BY ma.id;
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, dict(zip(bind_names, meeting_ids, strict=True))).mappings().all()

    attendees_by_meeting: dict[int, list[MeetingAttendeeRecord]] = {}
    for row in rows:
        attendees_by_meeting.setdefault(row["meeting_id"], []).append(_map_attendee(row))
    for meeting in meetings:
        meeting.attendees = attendees_by_meeting.get(meeting.id, [])


def create_meeting(engine: Engine, payload: MeetingCreate) -> MeetingRecord:
    query = text(
        """
        INSERT INTO dbo.meetings (
          location_id,
          client_id,
          end_client_id,
          meeting_owner_user_id,
          title,
          meeting_type,
          scheduled_at,
          agenda,
          follow_up_owner_user_id,
          follow_up_due_date
        )
        OUTPUT INSERTED.id
        VALUES (
          :location_id,
          :client_id,
          :end_client_id,
          :meeting_owner_user_id,
          :title,
          :meeting_type,
          :scheduled_at,
          :agenda,
          :follow_up_owner_user_id,
          :follow_up_due_date
        );
        """
    )
    with engine.begin() as connection:
        meeting_id = connection.execute(query, payload.model_dump()).scalar_one()
    created = find_meeting_by_id(engine, int(meeting_id))
    if created is None:
        raise RuntimeError("Created meeting could not be reloaded")
    return created


def update_meeting(engine: Engine, meeting_id: int, payload: MeetingUpdate) -> MeetingRecord:
    fields = payload.model_dump(exclude_unset=True)
    query = text(
        """
        UPDATE dbo.meetings
        SET
          attendance_status = COALESCE(:attendance_status, attendance_status),
          outcome_status = COALESCE(:outcome_status, outcome_status),
          minutes_of_meeting = CASE WHEN :has_minutes = 1 THEN :minutes_of_meeting ELSE minutes_of_meeting END,
          decision_summary = CASE WHEN :has_decision = 1 THEN :decision_summary ELSE decision_summary END,
          next_steps = CASE WHEN :has_next_steps = 1 THEN :next_steps ELSE next_steps END,
          follow_up_owner_user_id = CASE WHEN :has_follow_up_owner = 1 THEN :follow_up_owner_user_id ELSE follow_up_owner_user_id END,
          follow_up_due_date = CASE WHEN :has_follow_up_due_date = 1 THEN :follow_up_due_date ELSE follow_up_due_date END,
          updated_at = SYSUTCDATETIME()
        WHERE id = :meeting_id;
        """
    )
    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "meeting_id": meeting_id,
                "attendance_status": fields.get("attendance_status"),
                "outcome_status": fields.get("outcome_status"),
                "minutes_of_meeting": fields.get("minutes_of_meeting"),
                "decision_summary": fields.get("decision_summary"),
                "next_steps": fields.get("next_steps"),
                "follow_up_owner_user_id": fields.get("follow_up_owner_user_id"),
                "follow_up_due_date": fields.get("follow_up_due_date"),
                "has_minutes": 1 if "minutes_of_meeting" in fields else 0,
                "has_decision": 1 if "decision_summary" in fields else 0,
                "has_next_steps": 1 if "next_steps" in fields else 0,
                "has_follow_up_owner": 1 if "follow_up_owner_user_id" in fields else 0,
                "has_follow_up_due_date": 1 if "follow_up_due_date" in fields else 0,
            },
        )
    updated = find_meeting_by_id(engine, meeting_id)
    if updated is None:
        raise RuntimeError("Updated meeting could not be reloaded")
    return updated
