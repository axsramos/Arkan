import base64
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from backend.database import initialize_schema
from backend.member_management import MemberManagementError, issue_invitation, revoke_member
from backend.protocol import decode_artifact, verify_invitation_v2
from backend.activation import prepare_activation
from backend.activation_coordinator import confirm_recovered_member
from backend.data_store import open_data_store
from backend.vault import create_invited_member_activation_material, create_recovery_activation_material


def _public_x25519() -> bytes:
    return X25519PrivateKey.generate().public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )


class MemberManagementTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        initialize_schema(self.connection)
        self.network_id = str(uuid4())
        self.guardian_id = str(uuid4())
        self.signing_key = Ed25519PrivateKey.generate()
        signing_public = self.signing_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.identity = {
            "public_identity": {
                "network_id": self.network_id, "member_id": self.guardian_id,
                "signing_public_key": base64.b64encode(signing_public).decode(),
                "encryption_public_key": base64.b64encode(_public_x25519()).decode(),
                "activation_hash": base64.b64encode(os.urandom(32)).decode(), "created_at": now,
            },
            "signing_private_key": base64.b64encode(self.signing_key.private_bytes(
                serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
            )).decode(),
            "pseudonym": "Guardião",
        }
        self.connection.execute("INSERT INTO networks(network_id, guardian_member_id, created_at) VALUES (?, ?, ?)", (self.network_id, self.guardian_id, now))
        self.connection.execute(
            "INSERT INTO members(member_id, network_id, signing_public_key, encryption_public_key, role, status, activation_hash, created_at) VALUES (?, ?, ?, ?, 'GUARDIAO', 'ATIVO', ?, ?)",
            (self.guardian_id, self.network_id, self.identity["public_identity"]["signing_public_key"], self.identity["public_identity"]["encryption_public_key"], self.identity["public_identity"]["activation_hash"], now),
        )

    def tearDown(self):
        self.connection.close()

    def test_guardian_issues_immediate_active_invitation(self):
        invitation = decode_artifact(issue_invitation(self.connection, self.identity, "Membro"))
        self.assertEqual(invitation["pseudonimo"], "Membro")
        member = verify_invitation_v2(invitation)
        self.assertEqual(member["status"], "ATIVO")
        self.assertEqual(member["membro_id"], invitation["membro_id"])

    def test_guardian_can_revoke_certified_member_but_not_self(self):
        invitation = decode_artifact(issue_invitation(self.connection, self.identity, "Membro"))
        state = decode_artifact(revoke_member(self.connection, self.identity, invitation["membro_id"]))
        self.assertEqual(state["membros"][-1]["status"], "REVOGADO")
        with self.assertRaises(MemberManagementError):
            revoke_member(self.connection, self.identity, self.guardian_id)

    def test_member_recovery_restores_anchor_and_active_membership(self):
        invitation = decode_artifact(issue_invitation(self.connection, self.identity, "Membro"))
        material = create_invited_member_activation_material(invitation, "123456")
        restored = create_recovery_activation_material(material.recovery_artifact, "Membro", "654321")
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_dir = Path(temporary_directory) / "data"
            confirm_recovered_member(prepare_activation(storage_dir), restored)
            database = open_data_store(storage_dir, restored.data_key)
            membership = database.execute("SELECT activation_status FROM local_memberships").fetchone()
            anchor = database.execute("SELECT sequence_number FROM authorization_anchors").fetchone()
            database.close()
        self.assertEqual(membership[0], "ATIVO")
        self.assertEqual(anchor[0], invitation["arka"]["sequencia"])

