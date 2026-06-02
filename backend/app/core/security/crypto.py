"""
AES-256 (AESGCM) encryption helpers and EncryptedString TypeDecorator.

C-02: PII encryption in reposo. NEVER text plano en logs.
"""
import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator


# ---------------------------------------------------------------------------
# Key derivation — loaded once from settings, validated at startup.
# ---------------------------------------------------------------------------

def _get_key() -> bytes:
    """Return the 32-byte AES-256 key from ENCRYPTION_KEY env/settings."""
    from app.core.config import Settings  # avoid circular import at module level

    settings = Settings()
    return settings.ENCRYPTION_KEY.encode("utf-8")


# ---------------------------------------------------------------------------
# Low-level helpers: encrypt / decrypt
# ---------------------------------------------------------------------------

_NONCE_SIZE = 12  # 96-bit nonce — recommended for AESGCM


def encrypt(plaintext: str) -> str:
    """
    Encrypt *plaintext* with AES-256-GCM.

    Output format: base64url(nonce || ciphertext), no padding.
    A fresh 12-byte nonce is generated per call (non-deterministic).
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    combined = nonce + ciphertext
    return base64.urlsafe_b64encode(combined).rstrip(b"=").decode("ascii")


def decrypt(token: str) -> str:
    """
    Decrypt *token* produced by :func:`encrypt`.

    Raises :class:`cryptography.exceptions.InvalidTag` (or subclass) if the
    token has been tampered with.
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    padded = token + "=="
    combined = base64.urlsafe_b64decode(padded)
    nonce = combined[:_NONCE_SIZE]
    ciphertext = combined[_NONCE_SIZE:]
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator — transparent encryption at the column level
# ---------------------------------------------------------------------------

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy column type that transparently encrypts on write and decrypts on
    read using AES-256-GCM.

    Usage::

        class AlumnoModel(Base, TenantScopedBase):
            dni: Mapped[str] = mapped_column(EncryptedString, nullable=False)

    The value in the database column is always encrypted. The ORM layer always
    sees plaintext. Searching by value equality is intentionally unsupported
    (use a separate deterministic hash column — C-03+).
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """Encrypt the value before persisting it to the database."""
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[str]:
        """Decrypt the raw value read from the database."""
        if value is None:
            return None
        return decrypt(value)

    def __repr__(self) -> str:  # pragma: no cover
        return "EncryptedString()"
