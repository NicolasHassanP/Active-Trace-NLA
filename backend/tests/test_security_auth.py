"""
Tests for auth-specific security helpers added in C-03.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Covers: hash_password/verify_password, email_lookup_hash,
        encode/decode_access_token, encode/decode_mfa_token,
        generate_opaque_token/hash_opaque_token, TOTP helpers.
"""
import time
import uuid
import pytest


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://localhost/test",
    "SECRET_KEY": "supersecretkeyforjwttesting1234567",
    "ENCRYPTION_KEY": "E" * 32,
}


def setup_env(monkeypatch):
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)


# ==============================================================================
# 2.2 hash_password / verify_password (Argon2id)
# ==============================================================================

def test_hash_password_not_plaintext(monkeypatch):
    """hash_password returns something different from plaintext."""
    setup_env(monkeypatch)
    from app.core.security import hash_password
    h = hash_password("mysecret")
    assert h != "mysecret"
    assert len(h) > 20


def test_verify_password_correct(monkeypatch):
    """verify_password returns True for matching password."""
    setup_env(monkeypatch)
    from app.core.security import hash_password, verify_password
    h = hash_password("correct_password")
    assert verify_password("correct_password", h) is True


def test_verify_password_wrong(monkeypatch):
    """verify_password returns False for wrong password."""
    setup_env(monkeypatch)
    from app.core.security import hash_password, verify_password
    h = hash_password("correct_password")
    assert verify_password("wrong_password", h) is False


def test_hash_password_different_salts(monkeypatch):
    """Hashing same password twice produces different hashes (different salts)."""
    setup_env(monkeypatch)
    from app.core.security import hash_password
    h1 = hash_password("same_password")
    h2 = hash_password("same_password")
    assert h1 != h2


# ==============================================================================
# 2.3 email_lookup_hash (HMAC-SHA256, deterministic)
# ==============================================================================

def test_email_lookup_hash_deterministic(monkeypatch):
    """Same email always produces same hash."""
    setup_env(monkeypatch)
    from app.core.security import email_lookup_hash
    h1 = email_lookup_hash("user@example.com")
    h2 = email_lookup_hash("user@example.com")
    assert h1 == h2


def test_email_lookup_hash_case_insensitive(monkeypatch):
    """email_lookup_hash normalizes email to lowercase+trim."""
    setup_env(monkeypatch)
    from app.core.security import email_lookup_hash
    assert email_lookup_hash("User@Example.COM") == email_lookup_hash("user@example.com")
    assert email_lookup_hash("  user@example.com  ") == email_lookup_hash("user@example.com")


def test_email_lookup_hash_different_emails_differ(monkeypatch):
    """Different emails produce different hashes."""
    setup_env(monkeypatch)
    from app.core.security import email_lookup_hash
    h1 = email_lookup_hash("user1@example.com")
    h2 = email_lookup_hash("user2@example.com")
    assert h1 != h2


# ==============================================================================
# 2.4 encode_access_token / decode_access_token
# ==============================================================================

def test_access_token_round_trip(monkeypatch):
    """Access token encodes and decodes claims correctly."""
    setup_env(monkeypatch)
    from app.core.security import encode_access_token, decode_access_token
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    roles = ["ADMIN"]
    token = encode_access_token(user_id=user_id, tenant_id=tenant_id, roles=roles)
    claims = decode_access_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["tenant_id"] == str(tenant_id)
    assert claims["roles"] == roles
    assert claims["type"] == "access"
    assert "exp" in claims
    assert "iat" in claims


def test_access_token_tampered_signature_raises(monkeypatch):
    """A tampered access token raises an exception."""
    setup_env(monkeypatch)
    from app.core.security import encode_access_token, decode_access_token
    token = encode_access_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=[])
    # Tamper: change last char
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(Exception):
        decode_access_token(tampered)


def test_access_token_expiry_respected(monkeypatch):
    """Decode fails if token is expired (by using expires_minutes=0 and sleeping)."""
    setup_env(monkeypatch)
    from app.core.security import encode_access_token, decode_access_token
    import time
    # Use -1 minutes to create an already-expired token
    token = encode_access_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=[], expires_minutes=-1)
    with pytest.raises(Exception):
        decode_access_token(token)


def test_access_token_wrong_type_rejected(monkeypatch):
    """Decode rejects tokens with type != 'access'."""
    setup_env(monkeypatch)
    from app.core.security import encode_mfa_token, decode_access_token
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    mfa_token = encode_mfa_token(user_id=user_id, tenant_id=tenant_id)
    with pytest.raises(Exception):
        decode_access_token(mfa_token)


# ==============================================================================
# 2.5 encode_mfa_token / decode_mfa_token
# ==============================================================================

def test_mfa_token_round_trip(monkeypatch):
    """MFA token encodes and decodes correctly."""
    setup_env(monkeypatch)
    from app.core.security import encode_mfa_token, decode_mfa_token
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_mfa_token(user_id=user_id, tenant_id=tenant_id)
    claims = decode_mfa_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["tenant_id"] == str(tenant_id)
    assert claims["type"] == "mfa"


def test_mfa_token_expired_raises(monkeypatch):
    """Expired MFA token raises exception on decode."""
    setup_env(monkeypatch)
    from app.core.security import encode_mfa_token, decode_mfa_token
    token = encode_mfa_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), expires_minutes=-1)
    with pytest.raises(Exception):
        decode_mfa_token(token)


def test_mfa_token_rejected_as_access(monkeypatch):
    """MFA token cannot be decoded as an access token."""
    setup_env(monkeypatch)
    from app.core.security import encode_mfa_token, decode_access_token
    token = encode_mfa_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    with pytest.raises(Exception):
        decode_access_token(token)


# ==============================================================================
# 2.6 generate_opaque_token / hash_opaque_token
# ==============================================================================

def test_opaque_token_not_equal_to_hash(monkeypatch):
    """The token and its hash are different values."""
    setup_env(monkeypatch)
    from app.core.security import generate_opaque_token, hash_opaque_token
    token = generate_opaque_token()
    h = hash_opaque_token(token)
    assert token != h


def test_opaque_token_hash_deterministic(monkeypatch):
    """Hashing the same token twice produces the same hash."""
    setup_env(monkeypatch)
    from app.core.security import generate_opaque_token, hash_opaque_token
    token = generate_opaque_token()
    assert hash_opaque_token(token) == hash_opaque_token(token)


def test_opaque_tokens_unique(monkeypatch):
    """Two calls to generate_opaque_token produce different tokens."""
    setup_env(monkeypatch)
    from app.core.security import generate_opaque_token
    t1 = generate_opaque_token()
    t2 = generate_opaque_token()
    assert t1 != t2


# ==============================================================================
# 2.7 TOTP helpers
# ==============================================================================

def test_generate_totp_secret_not_empty(monkeypatch):
    """generate_totp_secret returns a non-empty string."""
    setup_env(monkeypatch)
    from app.core.security import generate_totp_secret
    secret = generate_totp_secret()
    assert isinstance(secret, str)
    assert len(secret) > 10


def test_verify_totp_current_code_valid(monkeypatch):
    """Current TOTP code is valid."""
    setup_env(monkeypatch)
    import pyotp
    from app.core.security import generate_totp_secret, verify_totp
    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    assert verify_totp(secret, current_code) is True


def test_verify_totp_wrong_code_invalid(monkeypatch):
    """A wrong TOTP code is rejected."""
    setup_env(monkeypatch)
    from app.core.security import generate_totp_secret, verify_totp
    secret = generate_totp_secret()
    assert verify_totp(secret, "000000") is False or verify_totp(secret, "999999") is False


def test_build_totp_uri_format(monkeypatch):
    """build_totp_uri returns a proper otpauth:// URI."""
    setup_env(monkeypatch)
    from app.core.security import generate_totp_secret, build_totp_uri
    secret = generate_totp_secret()
    uri = build_totp_uri(secret=secret, account_name="user@test.com", issuer="activia-trace")
    assert uri.startswith("otpauth://totp/")
    assert "secret=" in uri
