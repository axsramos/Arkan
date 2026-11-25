import unittest
from pathlib import Path
from unittest.mock import patch

from backend import config
from backend.config import STORAGE_DIR


class ConfigurationTests(unittest.TestCase):
    def test_storage_is_in_project_data_directory(self):
        project_root = Path(__file__).resolve().parents[1]
        self.assertEqual(STORAGE_DIR, project_root / "data")

    def test_frozen_application_uses_the_executable_directory_for_storage(self):
        executable = Path("C:/Teste/Arkan/Arkan.exe")
        with patch.object(config.sys, "frozen", True, create=True), patch.object(config.sys, "executable", executable):
            self.assertEqual(config.application_root(), executable.parent)


if __name__ == "__main__":
    unittest.main()
