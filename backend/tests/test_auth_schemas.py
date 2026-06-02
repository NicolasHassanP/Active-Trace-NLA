"""
Tests for auth Pydantic schemas (extra='forbid', validation, email).
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Task 5.1
"""
import pytest


# ==============================================================================
# LoginRequest
# ==============================================================================

def test_login_request_valid():
    from app.schemas.auth import LoginRequest
    req = LoginRequest(email="user@example.com", password="MyP@ss!")
    assert req.email == "user@example.com"
    assert req.password == "MyP@ss!"


def test_login_request_extra_field_forbidden():
    from pydantic import ValidationError
    from app.schemas.auth import LoginRequest
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password="p", extra_field="bad")


def test_login_request_invalid_email():
    from pydantic import ValidationError
    from app.schemas.auth import LoginRequest
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="p")


# ==============================================================================
# TokenPair
# ==============================================================================

def test_token_pair_valid():
    from app.schemas.auth import TokenPair
    tp = TokenPair(access_token="acc", refresh_token="ref", token_type="bearer")
    assert tp.token_type == "bearer"


def test_token_pair_extra_field_forbidden():
    from pydantic import ValidationError
    from app.schemas.auth import TokenPair
    with pytest.raises(ValidationError):
        TokenPair(access_token="a", refresh_token="r", token_type="bearer", extra="x")


# ==============================================================================
# MfaChallengeResponse
# ==============================================================================

def test_mfa_challenge_response_valid():
    from app.schemas.auth import MfaChallengeResponse
    resp = MfaChallengeResponse(mfa_token="tok", mfa_required=True)
    assert resp.mfa_required is True


def test_mfa_challenge_response_extra_forbidden():
    from pydantic import ValidationError
    from app.schemas.auth import MfaChallengeResponse
    with pytest.raises(ValidationError):
        MfaChallengeResponse(mfa_token="t", mfa_required=True, extra="x")


# ==============================================================================
# MfaVerifyRequest
# ==============================================================================

def test_mfa_verify_request_valid():
    from app.schemas.auth import MfaVerifyRequest
    req = MfaVerifyRequest(mfa_token="tok", code="123456")
    assert req.code == "123456"


# ==============================================================================
# RefreshRequest / LogoutRequest
# ==============================================================================

def test_refresh_request_valid():
    from app.schemas.auth import RefreshRequest
    req = RefreshRequest(refresh_token="mytoken")
    assert req.refresh_token == "mytoken"


def test_logout_request_valid():
    from app.schemas.auth import LogoutRequest
    req = LogoutRequest(refresh_token="mytoken")
    assert req.refresh_token == "mytoken"


# ==============================================================================
# ForgotRequest / ResetRequest
# ==============================================================================

def test_forgot_request_valid():
    from app.schemas.auth import ForgotRequest
    req = ForgotRequest(email="user@example.com")
    assert req.email == "user@example.com"


def test_forgot_request_invalid_email():
    from pydantic import ValidationError
    from app.schemas.auth import ForgotRequest
    with pytest.raises(ValidationError):
        ForgotRequest(email="not-email")


def test_reset_request_valid():
    from app.schemas.auth import ResetRequest
    req = ResetRequest(token="tok", new_password="NewP@ss1!")
    assert req.token == "tok"


def test_reset_request_extra_forbidden():
    from pydantic import ValidationError
    from app.schemas.auth import ResetRequest
    with pytest.raises(ValidationError):
        ResetRequest(token="t", new_password="p", extra="x")


# ==============================================================================
# EnrollResponse / Verify2FARequest
# ==============================================================================

def test_enroll_response_valid():
    from app.schemas.auth import EnrollResponse
    resp = EnrollResponse(secret="base32secret", uri="otpauth://totp/...")
    assert "otpauth" in resp.uri


def test_verify_2fa_request_valid():
    from app.schemas.auth import Verify2FARequest
    req = Verify2FARequest(code="123456")
    assert req.code == "123456"


def test_verify_2fa_request_extra_forbidden():
    from pydantic import ValidationError
    from app.schemas.auth import Verify2FARequest
    with pytest.raises(ValidationError):
        Verify2FARequest(code="123456", extra="bad")
