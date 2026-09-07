import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.schemas.requisition import (
    RequisitionCreate,
    RequisitionOwnerReassignment,
    RequisitionStatusUpdate,
    RequisitionUpdate,
)


class RequisitionSchemaTests(unittest.TestCase):
    def test_requisition_create_normalizes_skills_and_text(self) -> None:
        payload = RequisitionCreate(
            client_id=1,
            location_id=1,
            title="  Senior Python Developer  ",
            primary_owner_user_id=2,
            openings_count=2,
            target_closure_date=" 2026-09-15 ",
            job_description="  Build APIs  ",
            must_have_skills=[" Python ", " FastAPI ", ""],
            good_to_have_skills=[" SQLAlchemy "],
        )

        self.assertEqual(payload.title, "Senior Python Developer")
        self.assertEqual(payload.target_closure_date, "2026-09-15")
        self.assertEqual(payload.job_description, "Build APIs")
        self.assertEqual(payload.must_have_skills, ["Python", "FastAPI"])
        self.assertEqual(payload.good_to_have_skills, ["SQLAlchemy"])

    def test_requisition_update_requires_one_field(self) -> None:
        with self.assertRaises(ValidationError):
            RequisitionUpdate()

    def test_requisition_owner_reassignment_requires_change(self) -> None:
        with self.assertRaises(ValidationError):
            RequisitionOwnerReassignment(reason="handover")

    def test_requisition_status_update_normalizes_reason(self) -> None:
        payload = RequisitionStatusUpdate(status="closed", reason="  filled  ")

        self.assertEqual(payload.reason, "filled")


if __name__ == "__main__":
    unittest.main()
