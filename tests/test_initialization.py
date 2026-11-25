import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.activation import ActivationStateError, prepare_activation
from backend.config import storage_is_activated
from backend.main import favicon
import main as launcher
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

    def test_favicon_uses_the_new_ico_asset(self):
        response = favicon()

        self.assertEqual(response.headers["location"], "/static/favicon.ico")

    @patch("main.uvicorn.Server")
    @patch("main.uvicorn.Config")
    def test_legacy_local_server_exposes_clean_shutdown_callback(self, config, server):
        local_app = SimpleNamespace(state=SimpleNamespace())
        local_server = Mock()
        server.return_value = local_server
        with patch.object(launcher, "app", local_app):
            launcher.run_local_server(8765)

        config.assert_called_once_with(local_app, host="127.0.0.1", port=8765, log_level="info")
        local_server.run.assert_called_once_with()
        local_app.state.request_shutdown()
        self.assertTrue(local_server.should_exit)


if __name__ == "__main__":
    unittest.main()
