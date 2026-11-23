import unittest
from pathlib import Path

from backend.config import STORAGE_DIR


class ConfigurationTests(unittest.TestCase):
    def test_storage_is_in_project_data_directory(self):
        project_root = Path(__file__).resolve().parents[1]
        self.assertEqual(STORAGE_DIR, project_root / "data")


if __name__ == "__main__":
    unittest.main()
