import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError
from marshmallow import ValidationError
from flask import Flask
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.api.parents.service import ParentService
from app.models import Parent

class ParentServiceTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test variables."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.parent_data = {
            "email": "test@example.com",
            "password": "secure123",
            "phone_number": "+1234567890",
            "first_name": "Test",
            "last_name": "User"
        }

    def tearDown(self):
        """Tear down test variables."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('app.api.parents.service.load_data')
    @patch('app.models.Parent.query')
    def test_get_parent_data_success(self, mock_query, mock_load):
        """Test getting parent data successfully."""
        mock_parent = MagicMock()
        mock_parent.id = 1
        mock_query.get.return_value = mock_parent
        mock_load.return_value = {"id": 1}

        response, status = ParentService.get_parent_data(1, 1, "parent")

        self.assertEqual(status, 200)
        self.assertTrue(response["status"])

    @patch('app.models.Parent.query')
    def test_get_parent_data_not_found(self, mock_query):
        """Test parent not found."""
        mock_query.get.return_value = None

        response, status = ParentService.get_parent_data(999, 1, "parent")

        self.assertEqual(status, 404)
        self.assertFalse(response["status"])

    @patch('app.models.Parent.query')
    def test_get_all_parents_admin_success(self, mock_query):
        """Test admin getting all parents."""
        mock_parent = MagicMock()
        mock_query.all.return_value = [mock_parent]
        mock_query.filter.return_value.order_by.return_value.order_by.return_value = mock_query

        response, status = ParentService.get_all_parents(current_user_role="admin")

        self.assertEqual(status, 200)
        self.assertTrue(response["status"])

    @patch('app.api.parents.service.parent_create_schema.load')
    @patch('app.api.parents.service.db.session')
    def test_create_parent_success(self, mock_db_session, mock_schema_load):
        """Test creating parent successfully."""
        mock_schema_load.return_value = self.parent_data

        response, status = ParentService.create_parent(self.parent_data, "admin")

        self.assertEqual(status, 201)
        self.assertTrue(response["status"])
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @patch('app.api.parents.service.parent_create_schema.load')
    def test_create_parent_validation_error(self, mock_schema_load):
        """Test validation error when creating parent."""
        mock_schema_load.side_effect = ValidationError({"email": ["Invalid email"]})

        response, status = ParentService.create_parent({}, "admin")

        self.assertEqual(status, 400)
        self.assertFalse(response["status"])

    @patch('app.models.Parent.query')
    @patch('app.api.parents.service.parent_admin_update_schema.load')
    @patch('app.api.parents.service.db.session')
    def test_update_parent_by_admin_success(self, mock_db_session, mock_schema_load, mock_query):
        """Test admin updating parent successfully."""
        mock_parent = MagicMock()
        mock_query.get.return_value = mock_parent
        mock_schema_load.return_value = {"first_name": "Updated"}

        response, status = ParentService.update_parent_by_admin(1, {}, "admin")

        self.assertEqual(status, 200)
        self.assertTrue(response["status"])
        mock_db_session.commit.assert_called_once()

    @patch('app.models.Parent.query')
    @patch('app.api.parents.service.parent_self_update_schema.load')
    @patch('app.api.parents.service.db.session')
    def test_update_own_profile_success(self, mock_db_session, mock_schema_load, mock_query):
        """Test parent updating own profile successfully."""
        mock_parent = MagicMock()
        mock_query.get.return_value = mock_parent
        mock_schema_load.return_value = {"first_name": "Updated"}

        response, status = ParentService.update_own_profile(1, {})

        self.assertEqual(status, 200)
        self.assertTrue(response["status"])
        mock_db_session.commit.assert_called_once()

    @patch('app.models.Parent.query')
    @patch('app.api.parents.service.db.session')
    def test_delete_parent_success(self, mock_db_session, mock_query):
        """Test admin deleting parent successfully."""
        mock_parent = MagicMock()
        mock_query.get.return_value = mock_parent

        response, status = ParentService.delete_parent(1, "admin")

        self.assertEqual(status, 204)
        mock_db_session.delete.assert_called_once_with(mock_parent)
        mock_db_session.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
