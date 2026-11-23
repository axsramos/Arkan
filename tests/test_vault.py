import secrets
import tempfile
import unittest
from pathlib import Path

from backend.activation import prepare_activation
from backend.activation_coordinator import confirm_initial_guardian
from backend.data_store import open_data_store
from backend.vault import (
    VaultError,
    create_activation_material,
    create_recovery_activation_material,
    open_with_pin,
)


class VaultTests(unittest.TestCase):
    def test_activation_material_uses_separate_public_keys_and_opens_with_pin(self):
        pin = str(secrets.randbelow(900000) + 100000)
        invalid_pin = str((int(pin) + 1) % 1_000_000).zfill(6)
        material = create_activation_material("Guardião", pin)
        public = material.public_identity

        self.assertNotEqual(public["signing_public_key"], public["encryption_public_key"])
        self.assertNotIn(pin, str(material.vault))
        self.assertNotIn(pin.encode("utf-8"), material.recovery_artifact)
        open_with_pin(material.vault, pin)
        with self.assertRaises(VaultError):
            open_with_pin(material.vault, invalid_pin)

    def test_recovery_credential_restores_same_public_identity_in_new_vault(self):
        pin = str(secrets.randbelow(900000) + 100000)
        new_pin = str(secrets.randbelow(900000) + 100000)
        material = create_activation_material("Membro", pin)
        restored = create_recovery_activation_material(material.recovery_artifact, "Membro", new_pin)

        self.assertEqual(restored.public_identity["signing_public_key"], material.public_identity["signing_public_key"])
        self.assertEqual(restored.public_identity["encryption_public_key"], material.public_identity["encryption_public_key"])
        open_with_pin(restored.vault, new_pin)
        with self.assertRaises(VaultError):
            create_recovery_activation_material(material.recovery_artifact, "Outro", new_pin)

    def test_confirmation_persists_only_public_identity_and_encrypted_vault(self):
        pin = str(secrets.randbelow(900000) + 100000)
        material = create_activation_material("Guardião", pin)
        with tempfile.TemporaryDirectory() as temporary_directory:
            storage_dir = Path(temporary_directory) / "data"
            confirm_initial_guardian(prepare_activation(storage_dir), material)

            database = open_data_store(storage_dir, material.data_key)
            row = database.execute(
                "SELECT signing_public_key, encryption_public_key FROM members"
            ).fetchone()
            database.close()
            persisted_vault = (storage_dir / "vault.json").read_text(encoding="utf-8")

        self.assertEqual(tuple(row), (material.public_identity["signing_public_key"], material.public_identity["encryption_public_key"]))
        self.assertNotIn(pin, persisted_vault)


if __name__ == "__main__":
    unittest.main()
