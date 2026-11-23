"""Esquema mínimo da primeira versão, sem transporte ou governança."""

from typing import Any


SCHEMA_VERSION = 1


def initialize_schema(connection: Any) -> None:
    """Cria apenas estruturas locais necessárias aos planos aprovados."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_metadata (
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS installations (
            installation_id TEXT PRIMARY KEY,
            activated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS networks (
            network_id TEXT PRIMARY KEY,
            guardian_member_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS members (
            member_id TEXT PRIMARY KEY,
            network_id TEXT NOT NULL REFERENCES networks(network_id),
            signing_public_key TEXT NOT NULL UNIQUE,
            encryption_public_key TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL CHECK (role IN ('GUARDIAO', 'MEMBRO')),
            status TEXT NOT NULL CHECK (status IN ('ATIVO', 'REVOGADO')),
            activation_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS content_headers (
            content_hash TEXT PRIMARY KEY,
            author_member_id TEXT NOT NULL REFERENCES members(member_id),
            sequence_number INTEGER NOT NULL,
            content_type TEXT NOT NULL CHECK (content_type IN ('ARTIGO', 'COMENTARIO', 'ANEXO')),
            parent_hash TEXT,
            previous_version_hash TEXT,
            title TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(author_member_id, sequence_number)
        );
        CREATE TABLE IF NOT EXISTS local_content_control (
            content_hash TEXT PRIMARY KEY REFERENCES content_headers(content_hash),
            exported_at TEXT,
            removed_locally INTEGER NOT NULL DEFAULT 0 CHECK (removed_locally IN (0, 1))
        );
        CREATE TABLE IF NOT EXISTS consumed_invitations (
            invitation_id TEXT PRIMARY KEY,
            consumed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS authorization_anchors (
            network_id TEXT PRIMARY KEY REFERENCES networks(network_id),
            sequence_number INTEGER NOT NULL,
            state_hash BLOB NOT NULL,
            state_artifact BLOB NOT NULL,
            anchored_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS local_memberships (
            member_id TEXT PRIMARY KEY,
            network_id TEXT NOT NULL REFERENCES networks(network_id),
            copy_id TEXT NOT NULL UNIQUE,
            invitation_id TEXT NOT NULL UNIQUE REFERENCES consumed_invitations(invitation_id),
            activation_status TEXT NOT NULL CHECK (activation_status = 'ATIVO'),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS authorization_states (
            network_id TEXT NOT NULL REFERENCES networks(network_id),
            sequence_number INTEGER NOT NULL,
            state_hash BLOB NOT NULL UNIQUE,
            state_artifact BLOB NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (network_id, sequence_number)
        );
        CREATE TABLE IF NOT EXISTS content_drafts (
            draft_id TEXT PRIMARY KEY,
            author_member_id TEXT NOT NULL REFERENCES members(member_id),
            content_type TEXT NOT NULL CHECK (content_type IN ('ARTIGO', 'COMENTARIO')),
            article_id TEXT,
            title TEXT,
            body TEXT NOT NULL,
            previous_publication_hash TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS publications (
            content_hash TEXT PRIMARY KEY,
            author_member_id TEXT NOT NULL REFERENCES members(member_id),
            sequence_number INTEGER NOT NULL,
            content_type TEXT NOT NULL CHECK (content_type IN ('ARTIGO', 'COMENTARIO')),
            article_id TEXT,
            title TEXT,
            body TEXT NOT NULL,
            previous_publication_hash TEXT,
            signature BLOB NOT NULL,
            header_signature BLOB NOT NULL,
            created_at TEXT NOT NULL,
            publication_status TEXT NOT NULL CHECK (publication_status = 'PUBLICADO'),
            UNIQUE(author_member_id, sequence_number)
        );
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id TEXT PRIMARY KEY,
            article_hash TEXT NOT NULL REFERENCES publications(content_hash),
            author_member_id TEXT NOT NULL REFERENCES members(member_id),
            sequence_number INTEGER NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            media_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 10485760),
            storage_name TEXT NOT NULL UNIQUE,
            nonce BLOB NOT NULL UNIQUE,
            signature BLOB NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS export_records (
            export_id TEXT PRIMARY KEY, mode TEXT NOT NULL, exported_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS export_items (
            export_id TEXT NOT NULL REFERENCES export_records(export_id), content_hash TEXT NOT NULL,
            PRIMARY KEY (export_id, content_hash)
        );
        CREATE TABLE IF NOT EXISTS local_article_categories (
            article_hash TEXT PRIMARY KEY REFERENCES content_headers(content_hash),
            category TEXT NOT NULL CHECK (length(category) BETWEEN 1 AND 80)
        );
        CREATE TABLE IF NOT EXISTS local_article_badges (
            article_hash TEXT NOT NULL REFERENCES content_headers(content_hash),
            label TEXT NOT NULL CHECK (length(label) BETWEEN 1 AND 40),
            PRIMARY KEY (article_hash, label)
        );
        CREATE INDEX IF NOT EXISTS idx_content_author_sequence
            ON content_headers(author_member_id, sequence_number);
        CREATE INDEX IF NOT EXISTS idx_content_hash
            ON content_headers(content_hash);
        """
    )
    connection.execute(
        "INSERT OR REPLACE INTO schema_metadata(name, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    connection.commit()


def migrate_member_management_schema(connection: Any) -> None:
    """Acrescenta o histórico de autorização sem substituir dados existentes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS authorization_states (
            network_id TEXT NOT NULL REFERENCES networks(network_id),
            sequence_number INTEGER NOT NULL,
            state_hash BLOB NOT NULL UNIQUE,
            state_artifact BLOB NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (network_id, sequence_number)
        );
        """
    )


def migrate_content_schema(connection: Any) -> None:
    """Acrescenta rascunhos e publicações sem modificar itens existentes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_drafts (
            draft_id TEXT PRIMARY KEY,
            author_member_id TEXT NOT NULL REFERENCES members(member_id),
            content_type TEXT NOT NULL CHECK (content_type IN ('ARTIGO', 'COMENTARIO')),
            article_id TEXT,
            title TEXT,
            body TEXT NOT NULL,
            previous_publication_hash TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS publications (
            content_hash TEXT PRIMARY KEY,
            author_member_id TEXT NOT NULL REFERENCES members(member_id),
            sequence_number INTEGER NOT NULL,
            content_type TEXT NOT NULL CHECK (content_type IN ('ARTIGO', 'COMENTARIO')),
            article_id TEXT,
            title TEXT,
            body TEXT NOT NULL,
            previous_publication_hash TEXT,
            signature BLOB NOT NULL,
            created_at TEXT NOT NULL,
            certification_status TEXT NOT NULL CHECK (certification_status IN ('PENDENTE_CERTIFICACAO')),
            UNIQUE(author_member_id, sequence_number)
        );
        """
    )


def migrate_attachment_schema(connection: Any) -> None:
    """Acrescenta metadados de anexo sem tocar em conteúdo persistido."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS attachments (
            attachment_id TEXT PRIMARY KEY, article_hash TEXT NOT NULL REFERENCES publications(content_hash),
            author_member_id TEXT NOT NULL REFERENCES members(member_id), content_hash TEXT NOT NULL UNIQUE,
            media_type TEXT NOT NULL, size_bytes INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 10485760),
            storage_name TEXT NOT NULL UNIQUE, nonce BLOB NOT NULL UNIQUE, created_at TEXT NOT NULL)"""
    )


def migrate_export_schema(connection: Any) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS export_records (export_id TEXT PRIMARY KEY, mode TEXT NOT NULL, exported_at TEXT NOT NULL)")


def migrate_export_items_schema(connection: Any) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS export_items (export_id TEXT NOT NULL REFERENCES export_records(export_id), content_hash TEXT NOT NULL, PRIMARY KEY (export_id, content_hash))")


def migrate_local_classification_schema(connection: Any) -> None:
    """Acrescenta classificações estritamente locais sem alterar publicações."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS local_article_categories (
            article_hash TEXT PRIMARY KEY REFERENCES content_headers(content_hash),
            category TEXT NOT NULL CHECK (length(category) BETWEEN 1 AND 80)
        );
        CREATE TABLE IF NOT EXISTS local_article_badges (
            article_hash TEXT NOT NULL REFERENCES content_headers(content_hash),
            label TEXT NOT NULL CHECK (length(label) BETWEEN 1 AND 40),
            PRIMARY KEY (article_hash, label)
        );
        """
    )


def register_initial_guardian(connection: Any, public_identity: dict[str, str]) -> None:
    """Persiste somente dados públicos do primeiro membro da rede local."""
    required = {
        "network_id",
        "installation_id",
        "member_id",
        "signing_public_key",
        "encryption_public_key",
        "activation_hash",
    }
    if not required <= public_identity.keys():
        raise ValueError("Identidade pública incompleta.")
    connection.execute(
        "INSERT INTO installations(installation_id, activated_at) VALUES (?, ?)",
        (public_identity["installation_id"], public_identity["created_at"]),
    )
    connection.execute(
        "INSERT INTO networks(network_id, guardian_member_id, created_at) VALUES (?, ?, ?)",
        (
            public_identity["network_id"],
            public_identity["member_id"],
            public_identity["created_at"],
        ),
    )

    connection.execute(
        """INSERT INTO members(
            member_id, network_id, signing_public_key, encryption_public_key,
            role, status, activation_hash, created_at
        ) VALUES (?, ?, ?, ?, 'GUARDIAO', 'ATIVO', ?, ?)""",
        (
            public_identity["member_id"],
            public_identity["network_id"],
            public_identity["signing_public_key"],
            public_identity["encryption_public_key"],
            public_identity["activation_hash"],
            public_identity["created_at"],
        ),
    )


__all__ = ["initialize_schema", "register_initial_guardian"]
