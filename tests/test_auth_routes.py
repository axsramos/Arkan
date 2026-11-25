import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from starlette.requests import Request
from starlette.responses import Response
from backend.main import require_local_origin_for_mutations
from backend.routers import auth
from backend.routers import content, members
from backend.session import IDLE_TIMEOUT_SECONDS, LocalSessionStore, SessionError


class AuthenticationRouteTests(unittest.TestCase):
    def test_http_models_do_not_include_pin_or_private_credential(self):
        self.assertEqual(set(auth.SetupPayload.model_fields), {"pseudonym"})
        self.assertEqual(set(auth.JoinPayload.model_fields), {"pseudonym"})
        self.assertEqual(set(auth.RecoverPayload.model_fields), {"pseudonym"})
        self.assertFalse(hasattr(auth, "UnlockPayload"))
        self.assertNotIn("pin", content.DraftPayload.model_fields)
        self.assertNotIn("pin", content.DraftUpdatePayload.model_fields)
        self.assertNotIn("pin", content.DraftActionPayload.model_fields)
        self.assertNotIn("pin", members.GuardianSessionPayload.model_fields)
        self.assertNotIn("pin", members.IdentifierPayload.model_fields)

    def test_session_expires_after_two_hours_of_inactivity(self):
        clock = [0.0]
        store = LocalSessionStore(clock=lambda: clock[0])
        token = store.create(b"dado", {"pseudonym": "Membro"})
        self.assertEqual(store.get(token).identity["pseudonym"], "Membro")
        clock[0] = IDLE_TIMEOUT_SECONDS - 1
        store.get(token, renew=True)
        clock[0] += IDLE_TIMEOUT_SECONDS
        with self.assertRaises(SessionError):
            store.get(token)

    def test_exit_requests_clean_shutdown_for_an_active_local_session(self):
        token = auth.sessions.create(b"dado", {"pseudonym": "Membro"})
        shutdown = Mock()
        request = Request({"type": "http", "method": "POST", "path": "/api/v1/application/exit", "scheme": "http", "app": SimpleNamespace(state=SimpleNamespace(request_shutdown=shutdown)), "headers": [(b"cookie", f"{auth.SESSION_COOKIE}={token}".encode())]})
        try:
            result = asyncio.run(auth.exit_application(request))
        finally:
            auth.sessions.destroy(token)
        shutdown.assert_called_once_with()
        self.assertEqual(result["status"], "ENCERRANDO")

    def test_exit_rejects_missing_local_session(self):
        request = Request({"type": "http", "method": "POST", "path": "/api/v1/application/exit", "scheme": "http", "app": SimpleNamespace(state=SimpleNamespace(request_shutdown=Mock())), "headers": []})

        with self.assertRaises(auth.HTTPException) as error:
            asyncio.run(auth.exit_application(request))

        self.assertEqual(error.exception.status_code, 401)

    def test_mutation_rejects_missing_or_foreign_origin(self):
        async def next_handler(_): return Response(status_code=204)
        def request(origin=None):
            headers = [(b"host", b"127.0.0.1:8765")]
            if origin: headers.append((b"origin", origin.encode()))
            return Request({"type": "http", "method": "POST", "path": "/api/v1/application/exit", "scheme": "http", "headers": headers})
        self.assertEqual(asyncio.run(require_local_origin_for_mutations(request(), next_handler)).status_code, 403)
        self.assertEqual(asyncio.run(require_local_origin_for_mutations(request("http://127.0.0.1:8765"), next_handler)).status_code, 204)

    def test_storage_usage_preserves_fraction_below_one_percent(self):
        token = auth.sessions.create(b"dado", {"pseudonym": "Membro"})
        request = Request({"type": "http", "method": "GET", "path": "/api/v1/node/storage", "scheme": "http", "headers": [(b"cookie", f"{auth.SESSION_COOKIE}={token}".encode())]})
        try:
            with patch.object(auth, "disk_usage", return_value=SimpleNamespace(used=125, total=100000)):
                result = asyncio.run(auth.storage_usage(request))
        finally:
            auth.sessions.destroy(token)
        self.assertEqual(result["percentual_usado"], 0.12)

    def test_session_creation_derives_the_data_key_once(self):
        data_key = b"d" * 32
        identity = {"pseudonym": "Membro", "public_identity": {"member_id": "membro"}}
        with patch.object(auth, "load_vault", return_value={}), patch.object(auth, "data_key_with_pin", return_value=data_key) as derive, patch.object(auth, "identity_with_data_key", return_value=identity) as open_identity, patch.object(auth, "_session_summary", return_value={"pseudonym": "Membro", "role": "MEMBRO"}):
            token, _ = auth._create_session_from_pin(object())
        try:
            derive.assert_called_once()
            open_identity.assert_called_once_with({}, data_key)
        finally:
            auth.sessions.destroy(token)


if __name__ == "__main__":
    unittest.main()
