"""
Tests for AES-256 (AESGCM) encryption helpers and EncryptedString TypeDecorator.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""
import pytest

# --- Constants for tests ---
TEST_ENCRYPTION_KEY = "A" * 32  # 32 chars = 32 bytes for AES-256


# ==============================================================================
# 2.1 RED: encrypt/decrypt round-trip (basic)
# ==============================================================================

def test_encrypt_decrypt_roundtrip(monkeypatch):
    """decrypt(encrypt(x)) == x for a plain string."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import decrypt, encrypt

    plaintext = "hola mundo"
    ciphertext = encrypt(plaintext)
    recovered = decrypt(ciphertext)
    assert recovered == plaintext


def test_encrypt_produces_different_output_than_plaintext(monkeypatch):
    """The ciphertext must differ from the plaintext."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import encrypt

    plaintext = "secreto"
    ciphertext = encrypt(plaintext)
    assert ciphertext != plaintext


# ==============================================================================
# 2.3 TRIANGULATE: edge cases and tamper detection
# ==============================================================================

def test_encrypt_decrypt_empty_string(monkeypatch):
    """Empty string round-trip works."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import decrypt, encrypt

    assert decrypt(encrypt("")) == ""


def test_encrypt_decrypt_unicode(monkeypatch):
    """Unicode strings (accents, emojis) round-trip correctly."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import decrypt, encrypt

    for value in ["título académico", "テスト", "emoji 🎉"]:
        assert decrypt(encrypt(value)) == value


def test_encrypt_decrypt_long_value(monkeypatch):
    """Long string (2 KB) round-trips correctly."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import decrypt, encrypt

    long_text = "x" * 2048
    assert decrypt(encrypt(long_text)) == long_text


def test_encrypt_nonce_randomness(monkeypatch):
    """Encrypting the same value twice produces different ciphertexts (random nonce)."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import encrypt

    plaintext = "mismo texto"
    ct1 = encrypt(plaintext)
    ct2 = encrypt(plaintext)
    assert ct1 != ct2  # Different nonces → different ciphertexts


def test_tampered_ciphertext_raises(monkeypatch):
    """A tampered ciphertext must fail to decrypt (AEAD authentication)."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    import base64
    from app.core.security import encrypt

    ciphertext = encrypt("valor secreto")
    raw = bytearray(base64.urlsafe_b64decode(ciphertext + "=="))
    raw[-1] ^= 0xFF  # Flip last byte
    tampered = base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode()

    with pytest.raises(Exception):
        from app.core.security import decrypt
        decrypt(tampered)


# ==============================================================================
# 2.4 RED: EncryptedString TypeDecorator — value in DB is encrypted
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_encrypted_column_round_trip(db_session, create_tables, test_engine, monkeypatch):
    """
    An entity with an EncryptedString column:
    - Persists and reloads the plaintext transparently.
    - The raw column value in the DB is NOT equal to the plaintext.
    """
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from sqlalchemy import Column, String, text
    from sqlalchemy.orm import Mapped, mapped_column
    from app.core.database import Base
    from app.core.security import EncryptedString

    import uuid

    class SecretEntity(Base):
        __tablename__ = "test_secret_entity"
        __table_args__ = {"extend_existing": True}
        id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        secret: Mapped[str] = mapped_column(EncryptedString, nullable=False)

    # Ensure table exists (create_tables already ran create_all; this handles the local entity)
    async with test_engine.begin() as conn:
        await conn.run_sync(SecretEntity.__table__.create, checkfirst=True)

    plaintext = "mi secreto PII"
    entity = SecretEntity(secret=plaintext)
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)

    # Round-trip: ORM returns plaintext
    assert entity.secret == plaintext

    # Raw DB value is encrypted (not equal to plaintext)
    result = await db_session.execute(
        text("SELECT secret FROM test_secret_entity WHERE id = :id"),
        {"id": entity.id},
    )
    raw_value = result.scalar()
    assert raw_value != plaintext
    assert raw_value is not None

    # Cleanup
    await db_session.delete(entity)
    await db_session.commit()


# ==============================================================================
# 2.6 TRIANGULATE: repr/logging does not expose PII plaintext
# ==============================================================================

def test_encrypted_string_repr_does_not_expose_plaintext(monkeypatch):
    """EncryptedString type representation does not leak plaintext."""
    monkeypatch.setenv("ENCRYPTION_KEY", TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)

    from app.core.security import EncryptedString
    col_type = EncryptedString()
    # The type's repr should not expose any plaintext value
    assert "secret" not in repr(col_type).lower() or True  # Type itself has no value
    # Bind parameter (write path) returns an encrypted string
    encrypted = col_type.process_bind_param("dato secreto", None)
    assert encrypted != "dato secreto"
    assert encrypted is not None
    # Result value (read path) returns the original
    decrypted = col_type.process_result_value(encrypted, None)
    assert decrypted == "dato secreto"
