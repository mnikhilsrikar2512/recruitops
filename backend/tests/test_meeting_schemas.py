import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.schemas.meeting import MeetingCreate, MeetingUpdate


class MeetingSchemaTests(unittest.TestCase):
    def test_meeting_create_normalizes_text_and_type(self) -> None:
        payload = MeetingCreate(
            location_id=1,
            client_id=2,
            meeting_owner_user_id=3,
            title="  Requirement Sync  ",
            meeting_type="Requirement Discussion",
            agenda="  Align on shortlist quality  ",
        )

        self.assertEqual(payload.title, "Requirement Sync")
        self.assertEqual(payload.meeting_type, "requirement_discussion")
        self.assertEqual(payload.agenda, "Align on shortlist quality")

    def test_meeting_update_normalizes_statuses(self) -> None:
        payload = MeetingUpdate(attendance_status="No Show", outcome_status="Follow Up Required")

        self.assertEqual(payload.attendance_status, "no-show")
        self.assertEqual(payload.outcome_status, "follow-up-required")

    def test_meeting_update_requires_one_field(self) -> None:
        with self.assertRaises(ValidationError):
            MeetingUpdate()


if __name__ == "__main__":
    unittest.main()
