import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.schemas.client import ClientContactCreate, ClientCreate, ClientUpdate


class ClientSchemaTests(unittest.TestCase):
    def test_client_create_normalizes_code_and_text(self) -> None:
        payload = ClientCreate(
            client_name="  Acme Corp  ",
            client_code=" acm01 ",
            location_id=1,
            client_owner_user_id=2,
            business_source_owner_user_id=3,
            industry="  Fintech  ",
        )

        self.assertEqual(payload.client_name, "Acme Corp")
        self.assertEqual(payload.client_code, "ACM01")
        self.assertEqual(payload.industry, "Fintech")

    def test_client_update_requires_one_field(self) -> None:
        with self.assertRaises(ValidationError):
            ClientUpdate()

    def test_client_contact_normalizes_email(self) -> None:
        payload = ClientContactCreate(
            contact_name="  John Doe  ",
            email="  JOHN.DOE@example.com ",
        )

        self.assertEqual(payload.contact_name, "John Doe")
        self.assertEqual(payload.email, "john.doe@example.com")


if __name__ == "__main__":
    unittest.main()
