import unittest
from unittest.mock import MagicMock, patch
from app.api.parents.utils import load_data

class LoadDataTestCase(unittest.TestCase):

    @patch('app.api.parents.utils.ParentSchema')
    def test_load_data_single(self, mock_schema_class):
        """Test loading single parent data."""
        mock_parent = MagicMock()
        mock_schema_instance = MagicMock()
        mock_schema_instance.dump.return_value = {"id": 1}
        mock_schema_class.return_value = mock_schema_instance

        result = load_data(mock_parent)

        self.assertEqual(result, {"id": 1})
        mock_schema_instance.dump.assert_called_once_with(mock_parent)

    @patch('app.api.parents.utils.ParentSchema')
    def test_load_data_multiple(self, mock_schema_class):
        """Test loading multiple parents data."""
        mock_parents = [MagicMock(), MagicMock()]
        mock_schema_instance = MagicMock()
        mock_schema_instance.dump.return_value = [{"id": 1}, {"id": 2}]
        mock_schema_class.return_value = mock_schema_instance

        result = load_data(mock_parents, many=True)

        self.assertEqual(result, [{"id": 1}, {"id": 2}])
        mock_schema_instance.dump.assert_called_once_with(mock_parents)

if __name__ == '__main__':
    unittest.main()
