"""
ImpersonacionService — lógica de negocio para impersonación de usuarios.

Dominio: CRÍTICO (auth + auditoría).

Responsabilidades:
  1. Validar que el usuario target existe en el mismo tenant que el actor.
  2. Validar que el actor no intenta impersonarse a sí mismo.
  3. Obtener los roles del usuario target (desde su AuthIdentity).
  4. Emitir un access token con claims de impersonación.
  5. Emitir un token limpio al finalizar (roles reales del actor).
  6. Registrar IMPERSONACION_INICIO / IMPERSONACION_FIN en auditoría.

Reglas duras:
  - Identidad del actor SIEMPRE desde el JWT (CurrentUser), nunca de parámetros.
  - Multi-tenancy: target DEBE pertenecer al mismo tenant que el actor.
  - No lógica de negocio en Routers; no acceso a DB desde Services (vía Repos).
  - snake_case en todo.
"""
import uuid
from typing import Any, Dict, Optional

from app.core.dependencies import CurrentUser
from app.core.security import encode_access_token
from app.repositories.auth_identity_repository import AuthIdentityRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.audit_service import AuditService


class UsuarioNoEncontrado(Exception):
    """Raised when the target user does not exist in the actor's tenant."""


class AutoImpersonacionProhibida(Exception):
    """Raised when the actor tries to impersonate themselves."""


class ImpersonacionNoActiva(Exception):
    """Raised when finalizar is called without an active impersonation session."""


class ImpersonacionService:
    """
    Orchestrates impersonation flows.

    Parameters
    ----------
    usuario_repo        : UsuarioRepository  (tenant-scoped to actor's tenant)
    auth_identity_repo  : AuthIdentityRepository
    audit_repo          : AuditRepository    (tenant-scoped to actor's tenant)
    """

    def __init__(
        self,
        usuario_repo: UsuarioRepository,
        auth_identity_repo: AuthIdentityRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._usuario_repo = usuario_repo
        self._auth_identity_repo = auth_identity_repo
        self._audit_svc = AuditService(repository=audit_repo)

    # ------------------------------------------------------------------
    # iniciar — POST /api/v1/usuarios/{usuario_id}/impersonar
    # ------------------------------------------------------------------

    async def iniciar(
        self,
        *,
        actor: CurrentUser,
        target_usuario_id: uuid.UUID,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start an impersonation session.

        1. Load the target Usuario within the actor's tenant (404 if missing).
        2. Reject self-impersonation (400).
        3. Load the target's AuthIdentity to get their roles.
        4. Emit an access token with impersonation claims.
        5. Record IMPERSONACION_INICIO audit event.

        Returns: {"access_token": str, "impersonated_name": str}

        Raises UsuarioNoEncontrado if target does not exist in actor's tenant.
        Raises AutoImpersonacionProhibida if actor == target (by auth_identity_id).
        """
        # 1. Load target usuario — repo already scopes to actor's tenant
        target_usuario = await self._usuario_repo.get_by_id(target_usuario_id)
        if target_usuario is None:
            raise UsuarioNoEncontrado(
                f"Usuario {target_usuario_id} no encontrado en el tenant del actor"
            )

        # 2. Reject self-impersonation: compare auth_identity_id of target vs actor
        # actor.user_id == auth_identities.id (the JWT sub — NOT usuario.id)
        if target_usuario.auth_identity_id == actor.user_id:
            raise AutoImpersonacionProhibida(
                "No es posible impersonarse a uno mismo"
            )

        # 3. Load target's AuthIdentity for their roles
        target_identity = None
        if target_usuario.auth_identity_id is not None:
            target_identity = await self._auth_identity_repo.get_by_id(
                target_usuario.auth_identity_id
            )
        target_roles = target_identity.roles if target_identity is not None else []

        # 4. Emit impersonation token
        # actor.user_id is the real JWT sub (auth_identities.id) — preserved as `sub`
        target_nombre = f"{target_usuario.nombre} {target_usuario.apellidos}"
        token = encode_access_token(
            user_id=actor.user_id,
            tenant_id=actor.tenant_id,
            roles=target_roles,
            impersonated_user_id=target_usuario_id,
            impersonated_name=target_nombre,
        )

        # 5. Audit
        await self._audit_svc.record_impersonation_start(
            actor=actor,
            impersonated_user_id=target_usuario_id,
            ip=ip,
            user_agent=user_agent,
        )

        return {
            "access_token": token,
            "impersonated_name": target_nombre,
        }

    # ------------------------------------------------------------------
    # finalizar — POST /api/v1/auth/impersonacion/finalizar
    # ------------------------------------------------------------------

    async def finalizar(
        self,
        *,
        actor: CurrentUser,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        End an impersonation session.

        1. Verify the current JWT has an active impersonation (via actor.impersonated_user_id).
        2. Reload the actor's real AuthIdentity to get their original roles.
        3. Emit a clean access token (no impersonation claims).
        4. Record IMPERSONACION_FIN audit event.

        Returns: {"access_token": str, "token_type": "bearer"}

        Raises ImpersonacionNoActiva if the token has no impersonation session.
        """
        if actor.impersonated_user_id is None:
            raise ImpersonacionNoActiva("No hay sesión de impersonación activa")

        # 2. Reload actor's real identity for original roles
        # actor.user_id == auth_identities.id (the JWT sub — the REAL actor)
        real_identity = await self._auth_identity_repo.get_by_id(actor.user_id)
        real_roles = real_identity.roles if real_identity is not None else []

        # 3. Emit clean token — no impersonation claims
        clean_token = encode_access_token(
            user_id=actor.user_id,
            tenant_id=actor.tenant_id,
            roles=real_roles,
        )

        # 4. Audit
        await self._audit_svc.record_impersonation_end(
            actor=actor,
            impersonated_user_id=actor.impersonated_user_id,
            ip=ip,
            user_agent=user_agent,
        )

        return {
            "access_token": clean_token,
            "token_type": "bearer",
        }
