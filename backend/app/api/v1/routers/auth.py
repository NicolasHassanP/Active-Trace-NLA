"""
Auth router — HTTP interface for authentication endpoints.

C-03: All business logic delegated to AuthService. This router:
    - Extracts request data and resolves the tenant from the public context.
    - Calls AuthService methods.
    - Maps domain exceptions to HTTP status codes.
    - NEVER contains business logic.

Public endpoints (no session required):
    POST /api/v1/auth/login
    POST /api/v1/auth/refresh
    POST /api/v1/auth/logout
    POST /api/v1/auth/forgot
    POST /api/v1/auth/reset

Protected endpoints (require valid access token):
    POST /api/v1/auth/2fa/enroll
    POST /api/v1/auth/2fa/verify
    POST /api/v1/auth/mfa/complete

Tenant resolution for public endpoints:
    Reads `X-Tenant` header (UUID of the tenant). MVP uses header;
    production will also support subdomain resolution.
"""
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.schemas.auth import (
    EnrollResponse,
    ForgotRequest,
    LoginRequest,
    MessageResponse,
    MfaChallengeResponse,
    MfaVerifyRequest,
    ResetRequest,
    TokenPair,
    Verify2FARequest,
)
from app.services.auth_service import AuthenticationError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Dependency: resolve tenant from X-Tenant header
# ---------------------------------------------------------------------------

async def get_tenant_id_from_header(
    x_tenant: str = Header(..., alias="X-Tenant"),
) -> uuid.UUID:
    """
    Resolve tenant_id from the X-Tenant request header.

    MVP: the client sends the tenant UUID in `X-Tenant`.
    Production: also support subdomain-based resolution.
    """
    try:
        return uuid.UUID(x_tenant)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant header: must be a valid UUID",
        )


# ---------------------------------------------------------------------------
# Dependency: build AuthService from the request context
# ---------------------------------------------------------------------------

async def get_auth_service(request: Request) -> AuthService:
    """Build an AuthService scoped to this request's DB session."""
    session_factory = request.app.state.session_factory
    session = session_factory()
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    return AuthService(
        auth_identity_repo=AuthIdentityRepository(session),
        refresh_session_repo=RefreshSessionRepository(session),
        recovery_token_repo=RecoveryTokenRepository(session),
        email_port=None,  # TODO: wire real email port when comms module is ready (post C-03)
    )


# ---------------------------------------------------------------------------
# Error mapper
# ---------------------------------------------------------------------------

def _auth_error(detail: str = "Authentication failed") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(
    body: LoginRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id_from_header),
    svc: AuthService = Depends(get_auth_service),
) -> Response:
    """
    Authenticate with email + password.

    Returns access_token in JSON body (no 2FA) or MfaChallengeResponse (2FA gate).
    When no 2FA: the refresh_token is set as an httpOnly cookie (path=/api/v1/auth).
    """
    try:
        result = await svc.login(
            email=body.email, password=body.password, tenant_id=tenant_id
        )
    except AuthenticationError:
        raise _auth_error()

    # MFA challenge — no refresh token yet, return challenge as-is
    if "mfa_required" in result:
        return JSONResponse(content=result)

    # Full session — put refresh_token in httpOnly cookie, access_token in body
    refresh_token = result["refresh_token"]
    response = JSONResponse(content={
        "access_token": result["access_token"],
        "token_type": result.get("token_type", "bearer"),
    })
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return response


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    svc: AuthService = Depends(get_auth_service),
    refresh_token: str | None = Cookie(default=None),
) -> Response:
    """Rotate a refresh token and return a new access token.

    The refresh_token is read from the httpOnly cookie (not the request body).
    The rotated refresh_token is set as a new httpOnly cookie.
    """
    if refresh_token is None:
        raise _auth_error("Missing refresh token cookie")
    try:
        result = await svc.refresh(refresh_token)
    except AuthenticationError:
        raise _auth_error("Invalid or expired refresh token")

    new_refresh_token = result["refresh_token"]
    response = JSONResponse(content={
        "access_token": result["access_token"],
        "token_type": result.get("token_type", "bearer"),
    })
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return response


@router.post("/logout", response_model=MessageResponse)
async def logout(
    svc: AuthService = Depends(get_auth_service),
    refresh_token: str | None = Cookie(default=None),
) -> Response:
    """Revoke the active refresh session.

    The refresh_token is read from the httpOnly cookie (not the request body).
    Idempotent: if no cookie is present, still returns 200 and clears cookie.
    """
    if refresh_token is not None:
        await svc.logout(refresh_token)

    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return response


@router.post("/forgot", response_model=MessageResponse)
async def forgot(
    body: ForgotRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id_from_header),
    svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Initiate password recovery. Uniform response regardless of email existence."""
    result = await svc.forgot(email=body.email, tenant_id=tenant_id)
    return MessageResponse(**result)


@router.post("/reset", response_model=MessageResponse)
async def reset(
    body: ResetRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id_from_header),
    svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Reset password using a recovery token."""
    try:
        await svc.reset(token=body.token, new_password=body.new_password, tenant_id=tenant_id)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return MessageResponse(message="Password reset successfully")


@router.post("/mfa/complete")
async def mfa_complete(
    body: MfaVerifyRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id_from_header),
    svc: AuthService = Depends(get_auth_service),
) -> TokenPair:
    """Complete the MFA challenge and obtain a full session."""
    try:
        result = await svc.complete_mfa(
            mfa_token=body.mfa_token, code=body.code, tenant_id=tenant_id
        )
    except AuthenticationError:
        raise _auth_error("Invalid MFA code or token")
    return TokenPair(**result)


# ---------------------------------------------------------------------------
# Protected endpoints (require valid access token)
# ---------------------------------------------------------------------------

@router.post("/2fa/enroll", response_model=EnrollResponse)
async def enroll_2fa(
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
) -> EnrollResponse:
    """Generate and store a TOTP secret for the authenticated user."""
    identity = await svc._identity_repo.get_by_id(current_user.user_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity not found")
    result = await svc.enroll_2fa(identity)
    return EnrollResponse(**result)


@router.post("/2fa/verify", response_model=MessageResponse)
async def verify_2fa(
    body: Verify2FARequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Activate 2FA for the authenticated user by verifying the TOTP code."""
    identity = await svc._identity_repo.get_by_id(current_user.user_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity not found")
    try:
        await svc.verify_2fa_activation(identity, body.code)
    except AuthenticationError:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    return MessageResponse(message="2FA activated successfully")
