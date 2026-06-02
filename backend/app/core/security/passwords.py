"""
Password hashing and verification using Argon2id (argon2-cffi).

C-03: Passwords always hashed with Argon2id. NEVER stored in plaintext.
"""
import hmac
import hashlib
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError


# One shared PasswordHasher instance — the defaults are safe (Argon2id).
_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash *password* using Argon2id.

    Returns an encoded string (algorithm + parameters + salt + hash) suitable
    for storing in the database. Each call produces a different hash (random salt).
    """
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify *plain_password* against a stored *hashed_password*.

    Returns True if they match, False otherwise. Never raises.
    """
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def email_lookup_hash(email: str) -> str:
    """
    Compute a deterministic HMAC-SHA256 hash for email lookup.

    The email is normalized (lowercase + strip) before hashing, so
    'User@Example.COM' and 'user@example.com' produce the same hash.
    The HMAC key is derived from SECRET_KEY, making this resistant to
    rainbow table attacks (unlike a plain SHA-256 of the email).

    Returns a hex digest string (64 characters).
    """
    from app.core.config import Settings
    settings = Settings()
    key = settings.SECRET_KEY.encode("utf-8")
    normalized = email.strip().lower().encode("utf-8")
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()
