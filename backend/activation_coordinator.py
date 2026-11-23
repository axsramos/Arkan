"""Confirma a ativação local sem expor segredos fora do backend."""

from backend.activation import ActivationPreparation
from backend.database import register_initial_guardian
from backend.data_store import create_data_store
from backend.vault import ActivationMaterial, write_vault
from backend.protocol import artifact_hash, encode_artifact_v2
import base64


def confirm_initial_guardian(
    preparation: ActivationPreparation, material: ActivationMaterial
) -> None:
    """Confirma cofre e metadados públicos juntos, apenas após confirmação nativa."""
    def initialize(directory, connection) -> None:
        write_vault(directory, material.vault)
        register_initial_guardian(connection, material.public_identity)

    create_data_store(preparation, material.data_key, initialize)


def confirm_joined_member_v2(preparation: ActivationPreparation, material: ActivationMaterial, invitation: dict) -> None:
    """Confirma Membro já ativo no `ARKI v2`, sem confirmação posterior ao Guardião."""
    def initialize(directory, connection) -> None:
        write_vault(directory, material.vault)
        authorization = invitation["arka"]
        created_at = material.public_identity["created_at"]
        connection.execute("INSERT INTO installations(installation_id, activated_at) VALUES (?, ?)", (material.public_identity["installation_id"], created_at))
        connection.execute("INSERT INTO networks(network_id, guardian_member_id, created_at) VALUES (?, ?, ?)", (invitation["rede_id"], invitation["guardiao_id"], created_at))
        for member in authorization["membros"]:
            connection.execute(
                "INSERT INTO members(member_id, network_id, signing_public_key, encryption_public_key, role, status, activation_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (member["membro_id"], invitation["rede_id"], base64.b64encode(member["chave_assinatura"]).decode(), base64.b64encode(member["chave_cifragem"]).decode(), member["papel"], member["status"], base64.b64encode(member["ativacao_hash"]).decode(), member["efetivo_em"]),
            )
        artifact = encode_artifact_v2(authorization)
        state_hash = artifact_hash(authorization)
        connection.execute("INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)", (invitation["rede_id"], authorization["sequencia"], state_hash, artifact, created_at))
        connection.execute("INSERT INTO consumed_invitations(invitation_id, consumed_at) VALUES (?, ?)", (invitation["ingresso_id"], created_at))
        connection.execute("INSERT INTO local_memberships(member_id, network_id, copy_id, invitation_id, activation_status, created_at) VALUES (?, ?, ?, ?, 'ATIVO', ?)", (invitation["membro_id"], invitation["rede_id"], invitation["copia_id"], invitation["ingresso_id"], created_at))
    create_data_store(preparation, material.data_key, initialize)


def confirm_recovered_member(preparation: ActivationPreparation, material: ActivationMaterial) -> None:
    """Restaura um Membro em cópia nova com a âncora pública do `ARKR v2`."""
    authorization = material.recovery_authorization
    invitation_id = material.recovery_invitation_id
    if authorization is None or invitation_id is None:
        confirm_initial_guardian(preparation, material)
        return

    def initialize(directory, connection) -> None:
        write_vault(directory, material.vault)
        public = material.public_identity
        connection.execute("INSERT INTO installations(installation_id, activated_at) VALUES (?, ?)", (public["installation_id"], public["created_at"]))
        connection.execute("INSERT INTO networks(network_id, guardian_member_id, created_at) VALUES (?, ?, ?)", (authorization["rede_id"], authorization["guardiao_id"], public["created_at"]))
        for member in authorization["membros"]:
            connection.execute(
                "INSERT INTO members(member_id, network_id, signing_public_key, encryption_public_key, role, status, activation_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (member["membro_id"], authorization["rede_id"], base64.b64encode(member["chave_assinatura"]).decode(), base64.b64encode(member["chave_cifragem"]).decode(), member["papel"], member["status"], base64.b64encode(member["ativacao_hash"]).decode(), member["efetivo_em"]),
            )
        artifact = encode_artifact_v2(authorization)
        connection.execute("INSERT INTO authorization_anchors(network_id, sequence_number, state_hash, state_artifact, anchored_at) VALUES (?, ?, ?, ?, ?)", (authorization["rede_id"], authorization["sequencia"], artifact_hash(authorization), artifact, public["created_at"]))
        connection.execute("INSERT INTO consumed_invitations(invitation_id, consumed_at) VALUES (?, ?)", (invitation_id, public["created_at"]))
        connection.execute("INSERT INTO local_memberships(member_id, network_id, copy_id, invitation_id, activation_status, created_at) VALUES (?, ?, ?, ?, 'ATIVO', ?)", (public["member_id"], authorization["rede_id"], public["installation_id"], invitation_id, public["created_at"]))

    create_data_store(preparation, material.data_key, initialize)
