"""
Auth DTOs — Pydantic schemas for request/response validation.

C-03: All schemas use extra='forbid' to reject undeclared fields.
No business logic here — pure data validation.
"""
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------------------------------------------------------------------------
# Base with extra='forbid' — all auth schemas inherit this
# ---------------------------------------------------------------------------

class _AuthBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginRequest(_AuthBase):
    """Credentials for the login endpoint."""
    email: EmailStr
    password: str


class TokenPair(_AuthBase):
    """Access token response returned after successful authentication.

    The refresh token is no longer in the body — it travels as an httpOnly
    cookie set by the server (transport change, C-03).
    """
    access_token: str
    token_type: str = "bearer"


# Alias for clarity at the router level
LoginResponse = TokenPair
AccessTokenResponse = TokenPair


# ---------------------------------------------------------------------------
# 2FA challenge (gate between credentials and session issuance)
# ---------------------------------------------------------------------------

class MfaChallengeResponse(_AuthBase):
    """Returned when a user with totp_enabled=True presents valid credentials."""
    mfa_token: str
    mfa_required: bool = True


class MfaVerifyRequest(_AuthBase):
    """Client sends the mfa_token (from challenge) + TOTP code."""
    mfa_token: str
    code: str


# ---------------------------------------------------------------------------
# Password recovery
# ---------------------------------------------------------------------------

class ForgotRequest(_AuthBase):
    """Email address for password recovery request."""
    email: EmailStr


class ResetRequest(_AuthBase):
    """Recovery token + new password for the reset endpoint."""
    token: str
    new_password: str


# ---------------------------------------------------------------------------
# 2FA enrolment
# ---------------------------------------------------------------------------

class EnrollResponse(_AuthBase):
    """Returned after enrolment — includes the secret and QR URI."""
    secret: str
    uri: str


class Verify2FARequest(_AuthBase):
    """TOTP code sent to activate 2FA after enrolment."""
    code: str


# ---------------------------------------------------------------------------
# Generic message response (uniform responses for forgot, logout, etc.)
# ---------------------------------------------------------------------------

class MessageResponse(_AuthBase):
    """Generic success message — used for endpoints with uniform responses."""
    message: str
