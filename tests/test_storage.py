import os
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.activation import prepare_activation
from backend.database import initialize_schema
from backend.data_store import DATABASE_NAME, FORMAT_VERSION, DataStoreError, create_data_store, migrate_data_store, open_data_store
from backend.arkx import migrate_storage_schema
from backend.content import create_draft


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temporary_directory.name) / "data"
        self.key = os.urandom(32)
        create_data_store(prepare_activation(self.storage_dir), self.key)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_windows_does_not_enable_sqlcipher_memory_security(self):
        connection = Mock()
        with patch("backend.data_store.sqlcipher.connect", return_value=connection), patch.object(sys, "platform", "win32"):
            from backend.data_store import _connect

            _connect(Path("teste.db"), os.urandom(32))

        executed = [call.args[0] for call in connection.execute.call_args_list]
        self.assertFalse(any("cipher_memory_security" in statement for statement in executed))
        connection.close.assert_not_called()

    def test_database_is_encrypted_and_requires_the_opening_key(self):
        raw_database = (self.storage_dir / DATABASE_NAME).read_bytes()
        self.assertNotEqual(raw_database[:16], b"SQLite format 3\x00")
        connection = open_data_store(self.storage_dir, self.key)
        connection.execute("CREATE TABLE protected_item (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.close()
        with self.assertRaises(DataStoreError):
            open_data_store(self.storage_dir, os.urandom(32))

    def test_minimal_schema_is_created_without_p2p_governance_or_attachments(self):
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
        self.assertNotIn("attachments", tables)

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

        migrate_data_store(self.storage_dir, self.key, FORMAT_VERSION, lambda connection: migrate_storage_schema(connection, 8))

        connection = open_data_store(self.storage_dir, self.key)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        connection.close()
        self.assertTrue({"local_article_categories", "local_article_badges"} <= tables)
        self.assertTrue((self.storage_dir / f"{DATABASE_NAME}.backup-v8").is_file())

    def test_attachment_migration_removes_legacy_table_after_backup(self):
        connection = open_data_store(self.storage_dir, self.key)
        connection.execute("CREATE TABLE attachments (attachment_id TEXT PRIMARY KEY)")
        connection.commit()
        connection.close()
        manifest_path = self.storage_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["format_version"] = 9
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        migrate_data_store(self.storage_dir, self.key, FORMAT_VERSION, lambda connection: migrate_storage_schema(connection, 9))

        connection = open_data_store(self.storage_dir, self.key)
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        connection.close()
        self.assertNotIn("attachments", tables)
        self.assertTrue((self.storage_dir / f"{DATABASE_NAME}.backup-v9").is_file())

    def test_draft_review_migration_preserves_backup(self):
        manifest_path = self.storage_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["format_version"] = 10
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        migrate_data_store(self.storage_dir, self.key, FORMAT_VERSION, lambda connection: migrate_storage_schema(connection, 10))

        connection = open_data_store(self.storage_dir, self.key)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(content_drafts)")}
        connection.close()
        self.assertIn("review_status", columns)
        self.assertTrue((self.storage_dir / f"{DATABASE_NAME}.backup-v10").is_file())

    def test_migrated_drafts_accept_a_new_draft(self):
        connection = open_data_store(self.storage_dir, self.key)
        connection.execute("DROP TABLE content_drafts")
        connection.execute(
            """CREATE TABLE content_drafts (
                draft_id TEXT PRIMARY KEY, author_member_id TEXT NOT NULL,
                content_type TEXT NOT NULL, article_id TEXT, title TEXT, body TEXT NOT NULL,
                previous_publication_hash TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )"""
        )
        connection.commit()
        connection.close()
        manifest_path = self.storage_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["format_version"] = 10
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        migrate_data_store(self.storage_dir, self.key, FORMAT_VERSION, lambda store: migrate_storage_schema(store, 10))

        connection = open_data_store(self.storage_dir, self.key)
        network_id, member_id = "rede", "membro"
        connection.execute("INSERT INTO networks VALUES (?, ?, ?)", (network_id, member_id, "agora"))
        connection.execute("INSERT INTO members VALUES (?, ?, ?, ?, 'MEMBRO', 'ATIVO', ?, ?)", (member_id, network_id, "assinatura", "cifragem", "ativacao", "agora"))
        identity = {"public_identity": {"network_id": network_id, "member_id": member_id}}

        draft = create_draft(connection, identity, "ARTIGO", "Título", "Corpo")

        self.assertEqual(connection.execute("SELECT review_status FROM content_drafts WHERE draft_id=?", (draft["draft_id"],)).fetchone()[0], "RASCUNHO")
        connection.close()


if __name__ == "__main__":
    unittest.main()
