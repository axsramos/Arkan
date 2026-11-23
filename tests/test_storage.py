import os
import json
import tempfile
import unittest
from pathlib import Path

from backend.activation import prepare_activation
from backend.database import initialize_schema
from backend.data_store import DATABASE_NAME, FORMAT_VERSION, DataStoreError, create_data_store, migrate_data_store, open_data_store
from backend.arkx import migrate_exports


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temporary_directory.name) / "data"
        self.key = os.urandom(32)
        create_data_store(prepare_activation(self.storage_dir), self.key)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_database_is_encrypted_and_requires_the_opening_key(self):
        raw_database = (self.storage_dir / DATABASE_NAME).read_bytes()
        self.assertNotEqual(raw_database[:16], b"SQLite format 3\x00")
        connection = open_data_store(self.storage_dir, self.key)
        connection.execute("CREATE TABLE protected_item (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.close()
        with self.assertRaises(DataStoreError):
            open_data_store(self.storage_dir, os.urandom(32))

    def test_minimal_schema_is_created_without_p2p_or_governance(self):
        connection = open_data_store(self.storage_dir, self.key)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        connection.close()
        self.assertTrue({"installations", "networks", "members", "content_headers", "local_content_control"} <= tables)
        self.assertFalse(any("govern" in table or "vote" in table or "p2p" in table for table in tables))

    def test_failed_migration_preserves_a_recoverable_copy(self):
        original_database = (self.storage_dir / DATABASE_NAME).read_bytes()

        def fail_after_write(connection):
            connection.execute("CREATE TABLE interrupted_migration (id INTEGER)")
            raise RuntimeError("interrupção simulada")

        with self.assertRaises(DataStoreError):
            migrate_data_store(self.storage_dir, self.key, FORMAT_VERSION + 1, fail_after_write)
        backup = self.storage_dir / f"{DATABASE_NAME}.backup-v{FORMAT_VERSION}"
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), original_database)

    def test_local_classification_migration_preserves_backup(self):
        manifest_path = self.storage_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["format_version"] = 8
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        migrate_data_store(self.storage_dir, self.key, FORMAT_VERSION, lambda connection: migrate_exports(connection, 8))

        connection = open_data_store(self.storage_dir, self.key)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        connection.close()
        self.assertTrue({"local_article_categories", "local_article_badges"} <= tables)
        self.assertTrue((self.storage_dir / f"{DATABASE_NAME}.backup-v8").is_file())


if __name__ == "__main__":
    unittest.main()
