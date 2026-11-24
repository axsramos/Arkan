import base64
import os
import sqlite3
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from backend.content import ContentError, create_draft, delete_draft, list_drafts, publish_draft, review_draft, update_draft
from backend.database import initialize_schema
from backend.library import list_headers


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        initialize_schema(self.connection)
        network_id, self.member_id = str(uuid4()), str(uuid4())
        signing = Ed25519PrivateKey.generate()
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.connection.execute("INSERT INTO networks VALUES (?, ?, ?)", (network_id, self.member_id, now))
        self.connection.execute("INSERT INTO members VALUES (?, ?, ?, ?, 'GUARDIAO', 'ATIVO', ?, ?)", (self.member_id, network_id, 'a', 'b', base64.b64encode(os.urandom(32)).decode(), now))
        self.identity = {"public_identity": {"network_id": network_id, "member_id": self.member_id}, "signing_private_key": base64.b64encode(signing.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode()}

    def tearDown(self): self.connection.close()

    def test_draft_is_mutable_and_publication_is_immutable_with_version_link(self):
        draft = create_draft(self.connection, self.identity, "ARTIGO", "Título", "Corpo")
        update_draft(self.connection, self.identity, draft["draft_id"], "Título alterado", "Corpo alterado")
        review_draft(self.connection, self.identity, draft["draft_id"])
        first = publish_draft(self.connection, self.identity, draft["draft_id"], True)
        self.assertEqual(first["sequence_number"], 1)
        header = list_headers(self.connection, self.member_id, 'ATIVO')[0]
        self.assertEqual(header["hash"], first["content_hash"])
        self.assertTrue(header["proprio"])
        self.connection.execute("DELETE FROM local_content_control WHERE content_hash = ?", (first["content_hash"],))
        self.connection.execute("DELETE FROM content_headers WHERE content_hash = ?", (first["content_hash"],))
        recovered_header = list_headers(self.connection, self.member_id, 'ATIVO')[0]
        self.assertEqual(recovered_header["hash"], first["content_hash"])
        self.assertTrue(recovered_header["proprio"])
        with self.assertRaises(ContentError): update_draft(self.connection, self.identity, draft["draft_id"], "x", "y")
        version = create_draft(self.connection, self.identity, "ARTIGO", "Título 2", "Corpo 2", previous_hash=first["content_hash"])
        review_draft(self.connection, self.identity, version["draft_id"])
        second = publish_draft(self.connection, self.identity, version["draft_id"], True)
        self.assertEqual(second["sequence_number"], 2)
        self.assertEqual(self.connection.execute("SELECT previous_publication_hash FROM publications WHERE content_hash = ?", (second["content_hash"],)).fetchone()[0], first["content_hash"])

    def test_publication_requires_confirmation_and_comments_require_article(self):
        draft = create_draft(self.connection, self.identity, "ARTIGO", "Título", "Corpo")
        with self.assertRaises(ContentError): publish_draft(self.connection, self.identity, draft["draft_id"], True)
        review_draft(self.connection, self.identity, draft["draft_id"])
        with self.assertRaises(ContentError): publish_draft(self.connection, self.identity, draft["draft_id"], False)
        with self.assertRaises(ContentError): create_draft(self.connection, self.identity, "COMENTARIO", None, "Texto")
        with self.assertRaises(ContentError): delete_draft(self.connection, self.identity, draft["draft_id"])

    def test_review_is_local_read_only_until_returning_to_draft(self):
        draft = create_draft(self.connection, self.identity, "ARTIGO", "Título", "Corpo")
        review_draft(self.connection, self.identity, draft["draft_id"])

        self.assertEqual(list_drafts(self.connection, self.identity)[0]["status"], "EM_REVISAO")
        with self.assertRaises(ContentError): delete_draft(self.connection, self.identity, draft["draft_id"])

        update_draft(self.connection, self.identity, draft["draft_id"], "Título revisado", "Corpo revisado")
        self.assertEqual(list_drafts(self.connection, self.identity)[0]["status"], "RASCUNHO")
        delete_draft(self.connection, self.identity, draft["draft_id"])

    def test_lists_only_local_mutable_drafts(self):
        first = create_draft(self.connection, self.identity, "ARTIGO", "Primeiro", "Corpo")
        second = create_draft(self.connection, self.identity, "ARTIGO", "Segundo", "Outro corpo")

        drafts = list_drafts(self.connection, self.identity)

        self.assertCountEqual([draft["draft_id"] for draft in drafts], [first["draft_id"], second["draft_id"]])
        self.assertCountEqual([draft["title"] for draft in drafts], ["Primeiro", "Segundo"])

