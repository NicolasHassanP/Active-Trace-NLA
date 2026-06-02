"""
TOTP (Time-based One-Time Password) helpers using pyotp.

C-03: Optional 2FA via TOTP. Secrets are generated here and stored encrypted
(AES-256 via EncryptedString) in the auth_identity table.
"""
import pyotp


def generate_totp_secret() -> str:
    """
    Generate a random base32-encoded TOTP secret.

    This secret is returned to the user once (for QR enrollment) and stored
    encrypted in the database. It must NEVER appear in logs.
    """
    return pyotp.random_base32()


def build_totp_uri(*, secret: str, account_name: str, issuer: str) -> str:
    """
    Build the otpauth:// URI for QR code display.

    Parameters
    ----------
    secret:
        The base32-encoded TOTP secret.
    account_name:
        Typically the user's email address.
    issuer:
        The application/tenant name shown in the authenticator app.

    Returns
    -------
    str
        An otpauth://totp/ URI suitable for encoding as a QR code.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account_name, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a TOTP code against the stored secret.

    Allows a tolerance of ±1 window (30s) to accommodate clock drift.
    Returns True if the code is valid, False otherwise.
    """
    totp = pyotp.TOTP(secret)
    # valid_window=1 allows the previous and next 30s window
    return totp.verify(code, valid_window=1)
