import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import asyncio

from backend.routers import settings as settings_router
from backend.settings import DEFAULT_THEME, load_settings, migrate_legacy_settings, save_theme


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "settings.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_defaults_to_dark_when_no_preference_exists(self):
        settings = load_settings(self.path)

        self.assertEqual(settings["format_version"], 1)
        self.assertEqual(settings["appearance"]["theme"], DEFAULT_THEME)

    def test_persists_theme_in_versioned_json_with_backup(self):
        save_theme(self.path, "DARK")
        saved = save_theme(self.path, "LIGHT")

        self.assertEqual(saved["appearance"]["theme"], "LIGHT")
        self.assertEqual(load_settings(self.path)["appearance"]["theme"], "LIGHT")
        self.assertEqual(load_settings(self.path.with_suffix(".json.backup"))["appearance"]["theme"], "DARK")

    def test_malformed_or_unknown_preferences_fall_back_to_dark(self):
        self.path.write_text('{"format_version": 9, "appearance": {"theme": "BLUE"}}', encoding="utf-8")

        self.assertEqual(load_settings(self.path)["appearance"]["theme"], DEFAULT_THEME)

    def test_rejects_unknown_theme(self):
        with self.assertRaises(ValueError):
            save_theme(self.path, "BLUE")

    def test_migrates_valid_legacy_preference_without_removing_it(self):
        legacy_path = Path(self.temporary_directory.name) / "settings.json"
        destination_path = Path(self.temporary_directory.name) / "data" / "settings.json"
        save_theme(legacy_path, "DARK")
        save_theme(legacy_path, "LIGHT")

        migrate_legacy_settings(legacy_path, destination_path)

        self.assertEqual(load_settings(destination_path)["appearance"]["theme"], "LIGHT")
        self.assertTrue(legacy_path.is_file())
        self.assertTrue(legacy_path.with_suffix(".json.backup").is_file())
        self.assertTrue(destination_path.with_suffix(".json.backup").is_file())

    def test_does_not_migrate_invalid_legacy_preference(self):
        legacy_path = Path(self.temporary_directory.name) / "settings.json"
        destination_path = Path(self.temporary_directory.name) / "data" / "settings.json"
        legacy_path.write_text('{"format_version": 99}', encoding="utf-8")

        migrate_legacy_settings(legacy_path, destination_path)

        self.assertFalse(destination_path.exists())

    def test_local_routes_return_and_update_the_theme(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy-settings.json"
        with patch.object(settings_router, "SETTINGS_PATH", self.path), patch.object(settings_router, "LEGACY_SETTINGS_PATH", legacy_path):
            result = asyncio.run(settings_router.update_theme(settings_router.ThemePayload(theme="LIGHT")))
            current = asyncio.run(settings_router.get_settings())

        self.assertEqual(result["appearance"]["theme"], "LIGHT")
        self.assertEqual(current["appearance"]["theme"], "LIGHT")


if __name__ == "__main__":
    unittest.main()
