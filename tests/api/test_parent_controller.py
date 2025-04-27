import unittest
from unittest.mock import patch
from flask import url_for
from flask_jwt_extended import create_access_token
from app import create_app, db

class ParentControllerTestCase(unittest.TestCase):
    def setUp(self):
        """Set up the test client and tokens."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.client = self.app.test_client()

        self.TEST_ADMIN_ACCESS_TOKEN = create_access_token(identity=1, additional_claims={"role": "admin"})
        self.TEST_PARENT_ACCESS_TOKEN = create_access_token(identity=2, additional_claims={"role": "parent"})

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('app.api.parents.service.ParentService.get_all_parents')
    def test_get_all_parents_admin_success(self, mock_get_all):
        """Test admin can get all parents."""
        mock_get_all.return_value = ({"status": True, "message": "Success", "parents": []}, 200)

        response = self.client.get(
            url_for('api.parents_parent_list'),
            headers={'Authorization': f'Bearer {self.TEST_ADMIN_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 200)
        mock_get_all.assert_called_once()

    @patch('app.api.parents.service.ParentService.create_parent')
    def test_create_parent_admin_success(self, mock_create):
        """Test admin can create parent."""
        mock_create.return_value = ({"status": True, "message": "Created"}, 201)
        data = {
            "email": "test@example.com",
            "password": "secure123",
            "phone_number": "+1234567890"
        }

        response = self.client.post(
            url_for('api.parents_parent_list'),
            json=data,
            headers={'Authorization': f'Bearer {self.TEST_ADMIN_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 201)

    @patch('app.api.parents.service.ParentService.get_parent_data')
    def test_get_parent_by_id_admin_success(self, mock_get):
        """Test admin can get any parent."""
        mock_get.return_value = ({"status": True, "message": "Success", "parent": {}}, 200)

        response = self.client.get(
            url_for('api.parents_parent_resource', parent_id=1),
            headers={'Authorization': f'Bearer {self.TEST_ADMIN_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 200)

    @patch('app.api.parents.service.ParentService.get_parent_data')
    def test_get_parent_by_id_self_success(self, mock_get):
        """Test parent can get their own data."""
        mock_get.return_value = ({"status": True, "message": "Success", "parent": {}}, 200)

        response = self.client.get(
            url_for('api.parents_parent_resource', parent_id=2),
            headers={'Authorization': f'Bearer {self.TEST_PARENT_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 200)

    @patch('app.api.parents.service.ParentService.update_parent_by_admin')
    def test_update_parent_admin_success(self, mock_update):
        """Test admin can update parent."""
        mock_update.return_value = ({"status": True, "message": "Updated"}, 200)
        data = {"first_name": "Updated"}

        response = self.client.put(
            url_for('api.parents_parent_resource', parent_id=1),
            json=data,
            headers={'Authorization': f'Bearer {self.TEST_ADMIN_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 200)

    @patch('app.api.parents.service.ParentService.update_own_profile')
    def test_update_own_profile_success(self, mock_update):
        """Test parent can update their own profile."""
        mock_update.return_value = ({"status": True, "message": "Updated"}, 200)
        data = {"first_name": "Updated"}

        response = self.client.put(
            url_for('api.parents_parent_profile'),
            json=data,
            headers={'Authorization': f'Bearer {self.TEST_PARENT_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 200)

    @patch('app.api.parents.service.ParentService.delete_parent')
    def test_delete_parent_admin_success(self, mock_delete):
        """Test admin can delete parent."""
        mock_delete.return_value = (None, 204)

        response = self.client.delete(
            url_for('api.parents_parent_resource', parent_id=1),
            headers={'Authorization': f'Bearer {self.TEST_ADMIN_ACCESS_TOKEN}'}
        )

        self.assertEqual(response.status_code, 204)

if __name__ == '__main__':
    unittest.main()
