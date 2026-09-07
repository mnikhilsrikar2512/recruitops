import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.schemas.location import LocationCreate, LocationUpdate


class LocationSchemaTests(unittest.TestCase):
    def test_location_create_normalizes_code_and_name(self) -> None:
        payload = LocationCreate(
            location_name="  Hyderabad  ",
            location_code=" hyd01 ",
            status="active",
        )

        self.assertEqual(payload.location_name, "Hyderabad")
        self.assertEqual(payload.location_code, "HYD01")

    def test_location_update_requires_one_field(self) -> None:
        with self.assertRaises(ValidationError):
            LocationUpdate()


if __name__ == "__main__":
    unittest.main()
