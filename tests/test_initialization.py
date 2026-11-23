import socket
import tempfile
import unittest
from pathlib import Path

from backend.activation import ActivationStateError, prepare_activation
from backend.config import storage_is_activated
from main import find_free_port


class InitializationTests(unittest.TestCase):
    def test_unconfigured_storage_is_not_created_by_queries_or_preparation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_dir = Path(temporary_directory) / "data"

            self.assertFalse(storage_is_activated(storage_dir))
            preparation = prepare_activation(storage_dir)

            self.assertEqual(preparation.storage_dir, storage_dir)
            self.assertFalse(storage_dir.exists())

    def test_confirmed_storage_cannot_be_prepared_again(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_dir = Path(temporary_directory) / "data"
            storage_dir.mkdir()
            (storage_dir / "manifest.json").write_text("{}", encoding="utf-8")

            self.assertTrue(storage_is_activated(storage_dir))
            with self.assertRaises(ActivationStateError):
                prepare_activation(storage_dir)

    def test_free_port_is_bound_to_loopback(self):
        port = find_free_port()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", port))


if __name__ == "__main__":
    unittest.main()
