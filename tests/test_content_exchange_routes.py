import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cbor2
from fastapi import HTTPException
from starlette.requests import Request

from backend.arkx import ArkxError
from backend.content import ContentError
from backend.native_dialog import NativeDialogError
from backend.routers import content


class ContentExchangeRouteTests(unittest.TestCase):
    def setUp(self):
        self.request = Request({"type": "http", "method": "POST", "path": "/", "headers": []})

    def test_export_success_records_items_after_saving(self):
        header = cbor2.dumps({"exportacao_id": "exportacao", "modalidade": "COMPLETA", "emitido_em": "2026-01-01"})
        artifact = b"ARKX\x02" + len(header).to_bytes(4, "big") + header
        connection = Mock()
        connection.execute.side_effect = [None, [("publicacao",)], None]
        session = SimpleNamespace(identity={"pseudonym": "Membro"})
        with patch.object(content, "_with_content", side_effect=lambda request, operation: operation(connection, {})), \
             patch.object(content.sessions, "get", return_value=session), \
             patch.object(content, "build_export", return_value=artifact), \
             patch.object(content, "save_export_artifact") as save:
            result = asyncio.run(content.export_content("COMPLETA", content.ExportPayload(), self.request))
        self.assertEqual(result, {"status": "EXPORTACAO_GERADA"})
        save.assert_called_once_with(artifact, "Membro")
        self.assertEqual(connection.execute.call_count, 3)

    def test_export_handles_expected_failures(self):
        for failure, status in [(NativeDialogError(), 409), (ArkxError(), 400), (ContentError(), 400)]:
            with self.subTest(failure=type(failure).__name__), patch.object(content, "_with_content", side_effect=failure):
                with self.assertRaises(HTTPException) as error:
                    asyncio.run(content.export_content("COMPLETA", content.ExportPayload(), self.request))
                self.assertEqual(error.exception.status_code, status)

    def test_import_handles_cancelled_dialog(self):
        with patch("backend.native_dialog.collect_export_artifact", side_effect=NativeDialogError()):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(content.import_content(content.DraftActionPayload(), self.request))
        self.assertEqual(error.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
