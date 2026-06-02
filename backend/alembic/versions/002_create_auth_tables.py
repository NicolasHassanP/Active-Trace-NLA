"""002 — create auth tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-02

C-03: Auth identity, refresh sessions, and password recovery tokens.
Three tables in one migration (single schema-change unit for all of auth C-03).

Tables created:
    auth_identities         — encrypted email, HMAC email hash, Argon2id password,
                              TOTP secret (encrypted), roles JSONB, active flag.
    refresh_sessions        — opaque refresh tokens stored by SHA-256 hash,
                              rotation family tracking.
    password_recovery_tokens — single-use recovery tokens stored by SHA-256 hash.

Unique constraint: (tenant_id, email_hash) on auth_identities.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # auth_identities — minimum identity for authentication (auth-owned, not Usuario)
    op.execute("""
        CREATE TABLE auth_identities (
            id                     UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id              UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            email_encrypted        TEXT        NOT NULL,
            email_hash             VARCHAR(64) NOT NULL,
            password_hash          VARCHAR(256) NOT NULL,
            roles                  JSONB       NOT NULL DEFAULT '[]',
            is_active              BOOLEAN     NOT NULL DEFAULT TRUE,
            totp_secret_encrypted  TEXT,
            totp_enabled           BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at             TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    # Unique email per tenant (deterministic hash for lookup)
    op.create_unique_constraint(
        "uq_auth_identity_tenant_email",
        "auth_identities",
        ["tenant_id", "email_hash"],
    )
    # Index on tenant_id (FKs are not automatically indexed in PostgreSQL)
    op.create_index("ix_auth_identities_tenant_id", "auth_identities", ["tenant_id"])
    # Index on email_hash for fast lookup
    op.create_index("ix_auth_identities_email_hash", "auth_identities", ["email_hash"])
    op.create_index("ix_auth_identities_deleted_at", "auth_identities", ["deleted_at"])

    # refresh_sessions — stateful refresh token store (opaque tokens by SHA-256 hash)
    op.execute("""
        CREATE TABLE refresh_sessions (
            id                 UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id          UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            auth_identity_id   UUID        NOT NULL REFERENCES auth_identities(id) ON DELETE CASCADE,
            token_hash         VARCHAR(64) NOT NULL,
            family_id          UUID        NOT NULL,
            expires_at         TIMESTAMPTZ NOT NULL,
            revoked_at         TIMESTAMPTZ,
            rotated_at         TIMESTAMPTZ,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at         TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_unique_constraint(
        "uq_refresh_session_token_hash",
        "refresh_sessions",
        ["token_hash"],
    )
    op.create_index("ix_refresh_sessions_tenant_id", "refresh_sessions", ["tenant_id"])
    op.create_index("ix_refresh_sessions_auth_identity_id", "refresh_sessions", ["auth_identity_id"])
    op.create_index("ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"])
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])
    op.create_index("ix_refresh_sessions_deleted_at", "refresh_sessions", ["deleted_at"])

    # password_recovery_tokens — single-use recovery tokens by SHA-256 hash
    op.execute("""
        CREATE TABLE password_recovery_tokens (
            id                 UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id          UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            auth_identity_id   UUID        NOT NULL REFERENCES auth_identities(id) ON DELETE CASCADE,
            token_hash         VARCHAR(64) NOT NULL,
            expires_at         TIMESTAMPTZ NOT NULL,
            used_at            TIMESTAMPTZ,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at         TIMESTAMPTZ,
            PRIMARY KEY (id)
        )
    """)
    op.create_unique_constraint(
        "uq_recovery_token_hash",
        "password_recovery_tokens",
        ["token_hash"],
    )
    op.create_index("ix_recovery_tokens_tenant_id", "password_recovery_tokens", ["tenant_id"])
    op.create_index("ix_recovery_tokens_auth_identity_id", "password_recovery_tokens", ["auth_identity_id"])
    op.create_index("ix_recovery_tokens_token_hash", "password_recovery_tokens", ["token_hash"])
    op.create_index("ix_recovery_tokens_deleted_at", "password_recovery_tokens", ["deleted_at"])


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_index("ix_recovery_tokens_deleted_at", table_name="password_recovery_tokens")
    op.drop_index("ix_recovery_tokens_token_hash", table_name="password_recovery_tokens")
    op.drop_index("ix_recovery_tokens_auth_identity_id", table_name="password_recovery_tokens")
    op.drop_index("ix_recovery_tokens_tenant_id", table_name="password_recovery_tokens")
    op.drop_constraint("uq_recovery_token_hash", "password_recovery_tokens", type_="unique")
    op.drop_table("password_recovery_tokens")

    op.drop_index("ix_refresh_sessions_deleted_at", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_family_id", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_token_hash", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_auth_identity_id", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_tenant_id", table_name="refresh_sessions")
    op.drop_constraint("uq_refresh_session_token_hash", "refresh_sessions", type_="unique")
    op.drop_table("refresh_sessions")

    op.drop_index("ix_auth_identities_deleted_at", table_name="auth_identities")
    op.drop_index("ix_auth_identities_email_hash", table_name="auth_identities")
    op.drop_index("ix_auth_identities_tenant_id", table_name="auth_identities")
    op.drop_constraint("uq_auth_identity_tenant_email", "auth_identities", type_="unique")
    op.drop_table("auth_identities")
