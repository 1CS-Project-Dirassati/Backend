# tests/test_parent_model.py  (or appropriate path)

from typing import Dict, Any
import unittest
import json
from datetime import datetime, timezone, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

# Assuming your app structure allows these imports
from app.models import Parent

# Assuming a ParentSchema exists similar to UserSchema
from app.models import ParentSchema

from tests.utils.base import BaseTestCase  # Use the same base class


class TestParentModel(BaseTestCase):

    def test_parent_creation_required_fields(self):
        """Test creating a Parent with only the required fields."""
        hashed_password = generate_password_hash("securepassword123")
        p = Parent(
            email="testparent@example.com",
            password=hashed_password,  # Pass the hash directly
            phone_number="1234567890",
        )
        self.assertEqual(p.email, "testparent@example.com")
        self.assertEqual(p.password, hashed_password)  # Stored password is the hash
        self.assertEqual(p.phone_number, "1234567890")
        self.assertIsNone(p.first_name)
        self.assertIsNone(p.last_name)
        self.assertIsNone(p.address)

    def test_parent_creation_all_fields(self):
        """Test creating a Parent with all optional fields provided."""
        hashed_password = generate_password_hash("anotherpassword")
        parent = {
            "email": "janedoe@example.com",
            "password": hashed_password,
            "phone_number": "0987654321",
            "first_name": "Jane",
            "last_name": "Doe",
            "address": "123 Main St"
        }
        p = ParentSchema().load(parent)
       
        

        self.assertEqual(p.email, "janedoe@example.com")
        self.assertEqual(p.password, hashed_password)
        self.assertEqual(p.phone_number, "0987654321")
        self.assertEqual(p.first_name, "Jane")
        self.assertEqual(p.last_name, "Doe")
        self.assertEqual(p.address, "123 Main St")

    def test_parent_defaults(self):
        """Test the default values for Parent attributes."""
        hashed_password = generate_password_hash("defaultpass")
        p = Parent(
            email="default@example.com",
            password=hashed_password,
            phone_number="5555555555",
        )
        self.assertFalse(p.is_email_verified)
        self.assertFalse(p.is_phone_verified)
        self.assertEqual(p.profile_picture, None)
        # Check timestamps are set (exact match can be tricky)
        
       

    def test_verify_password_correct(self):
        """Test the verify_password method with the correct password."""
        original_password = "correct_password"
        hashed_password = generate_password_hash(original_password)
        p = Parent(
            email="verify@example.com",
            password=hashed_password,
            phone_number="1112223333",
        )
        self.assertTrue(p.verify_password(original_password))

    def test_verify_password_incorrect(self):
        """Test the verify_password method with an incorrect password."""
        original_password = "correct_password"
        hashed_password = generate_password_hash(original_password)
        p = Parent(
            email="verify_fail@example.com",
            password=hashed_password,
            phone_number="4445556666",
        )
        self.assertFalse(p.verify_password("incorrect_password"))

    def test_repr(self):
        """Test the __repr__ method."""
        hashed_password = generate_password_hash("reprpass")
        p = Parent(
            email="repr_test@example.com",
            password=hashed_password,
            phone_number="7778889999",
        )
        # Assuming id is None before being added to a session and flushed/committed
        expected_repr_no_id = "<Parent id=None email=repr_test@example.com>"
        self.assertEqual(repr(p), expected_repr_no_id)

        # If BaseTestCase handles adding to session and assigning an ID:
        # db.session.add(p)
        # db.session.flush() # Assigns an ID without committing
        # self.assertIsNotNone(p.id)
        # expected_repr_with_id = f"<Parent id={p.id} email=repr_test@example.com>"
        # self.assertEqual(repr(p), expected_repr_with_id)
        # db.session.rollback() # Rollback changes if needed

    # --- Schema Test (Requires ParentSchema) ---
    def test_schema_dump(self):
        """Test dumping a Parent instance using ParentSchema."""
        # Ensure ParentSchema is imported correctly
        try:
            from app.models import ParentSchema
        except ImportError:
            self.skipTest("ParentSchema not found or could not be imported.")

        hashed_password = generate_password_hash("schemapass")
        p = Parent(
            email="schema_user@example.com",
            password=hashed_password,
            phone_number="1231231234",
            first_name="Schema",
            last_name="Test",
        )
        p.id = 1  # Manually set ID for testing dump, as it might be None otherwise

        parent_schema = ParentSchema()
        parent_dump = parent_schema.dumps(p)

        print("debugging parent_dump")
        print(parent_dump)  # For debugging purposes

        parent_data = json.loads(parent_dump)  # Ensure it's valid JSON
        # Assert expected fields are present
        self.assertEqual(parent_data.get("email"), "schema_user@example.com")
        self.assertEqual(parent_data.get("first_name"), "Schema")
        self.assertEqual(parent_data.get("last_name"), "Test")
        self.assertEqual(parent_data.get("phone_number"), "1231231234")
        self.assertEqual(parent_data.get("id"), 1)
        self.assertFalse(parent_data.get("is_email_verified"))  # Check defaults in dump
        print ("debugging parent_data")
        print (parent_data.get("password"))
        # Assert sensitive fields (like password hash) are NOT present
        self.assertIsNone(
        parent_data.get("password"),
        msg="Password hash should not be in the schema dump"
        )

    # Potential future tests (might be better as integration tests):
    # def test_email_uniqueness(self): ... # Requires DB interaction
    # def test_relationships(self): ... # Requires creating related objects (Student, Fee, etc.)
    # def test_onupdate_timestamp(self): ... # Requires DB interaction and modification


# Allows running tests directly
if __name__ == "__main__":
    unittest.main()
