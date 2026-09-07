import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.schemas.role import RoleCreate, RolePermissionsUpdate, RoleUpdate


class RoleSchemaTests(unittest.TestCase):
    def test_role_create_normalizes_code_and_text(self) -> None:
        payload = RoleCreate(
            name="  Account Manager  ",
            code=" AM_ROLE ",
            description="  manages requisitions  ",
        )

        self.assertEqual(payload.name, "Account Manager")
        self.assertEqual(payload.code, "am_role")
        self.assertEqual(payload.description, "manages requisitions")

    def test_role_update_requires_one_field(self) -> None:
        with self.assertRaises(ValidationError):
            RoleUpdate()

    def test_permissions_update_deduplicates_and_normalizes(self) -> None:
        payload = RolePermissionsUpdate(
            permission_codes=[" role.read ", "role.read", "role.update "],
            scope_rules={" requisition ": " location ", " ": "ignored"},
        )

        self.assertEqual(payload.permission_codes, ["role.read", "role.update"])
        self.assertEqual(payload.scope_rules, {"requisition": "location"})


if __name__ == "__main__":
    unittest.main()
