import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.schemas.user import UserCreate, UserDeactivateRequest, UserMoveRequest, UserUpdate


class UserSchemaTests(unittest.TestCase):
    def test_user_create_normalizes_email_and_text(self) -> None:
        payload = UserCreate(
            full_name="  Priya Nair  ",
            email="  PRIYA.NAIR@example.com ",
            employee_code=" EMP1001 ",
            primary_location_id=1,
            primary_role_id=2,
        )

        self.assertEqual(payload.full_name, "Priya Nair")
        self.assertEqual(str(payload.email), "priya.nair@example.com")
        self.assertEqual(payload.employee_code, "EMP1001")

    def test_user_update_requires_one_field(self) -> None:
        with self.assertRaises(ValidationError):
            UserUpdate()

    def test_user_deactivate_request_normalizes_reason(self) -> None:
        payload = UserDeactivateRequest(reason="  leaving company  ")

        self.assertEqual(payload.reason, "leaving company")

    def test_user_move_request_normalizes_reason(self) -> None:
        payload = UserMoveRequest(new_primary_role_id=3, reason="  role correction  ")

        self.assertEqual(payload.reason, "role correction")

    def test_user_move_request_requires_target(self) -> None:
        with self.assertRaises(ValidationError):
            UserMoveRequest(reason="transfer")


if __name__ == "__main__":
    unittest.main()
