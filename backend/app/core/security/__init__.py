"""
security package — public API for all security helpers.

C-02 exports (AES-256, EncryptedString) and C-03 exports (Argon2id, JWT, TOTP)
are all available at this level for backwards-compatible imports:

    from app.core.security import encrypt, decrypt, EncryptedString
    from app.core.security import hash_password, verify_password
    from app.core.security import encode_access_token, decode_access_token
    from app.core.security import generate_totp_secret, verify_totp
    ...
"""
# C-02 — AES-256 encryption (unchanged)
from app.core.security.crypto import (  # noqa: F401
    encrypt,
    decrypt,
    EncryptedString,
)

# C-03 — Password hashing (Argon2id) and email lookup hash
from app.core.security.passwords import (  # noqa: F401
    hash_password,
    verify_password,
    email_lookup_hash,
)

# C-03 — JWT tokens (access + MFA) and opaque tokens (refresh/recovery)
from app.core.security.tokens import (  # noqa: F401
    encode_access_token,
    decode_access_token,
    encode_mfa_token,
    decode_mfa_token,
    generate_opaque_token,
    hash_opaque_token,
)

# C-03 — TOTP 2FA helpers
from app.core.security.totp import (  # noqa: F401
    generate_totp_secret,
    build_totp_uri,
    verify_totp,
)
