"""
AuditService — orchestrates audit event creation.

C-05: Design decision D7.

Responsibilities:
  1. Validate action ∈ AuditAction catalog (RN-24).
  2. Redact PII/secrets in before/after before persistence (D7).
  3. Construct AuditEvent with correct attribution (D5, RN-41).
  4. Delegate persistence to AuditRepository.

AuditService.record() is the SINGLE entry point for creating audit events.
Changes that generate auditable actions call record() with the exact catalog
code — never raw strings.

record_impersonation_start() / record_impersonation_end() are convenience
wrappers for the impersonation events (task 10.3).

snake_case throughout; ≤500 LOC.
"""
import uuid
from typing import Any, Dict, Optional

from app.core.audit_redaction import redact_pii
from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditEvent, AuditResultado
from app.repositories.audit_repository import AuditRepository


# ---------------------------------------------------------------------------
# Domain exception
# ---------------------------------------------------------------------------

class InvalidAuditAction(Exception):
    """Raised when an action code is not in the AuditAction catalog (RN-24)."""


# ---------------------------------------------------------------------------
# AuditService
# ---------------------------------------------------------------------------

class AuditService:
    """
    Service for creating and retrieving audit events.

    Usage::

        svc = AuditService(repository=repo)
        await svc.record(
            actor=current_user,
            action=AuditAction.AUDITORIA_CONSULTA,
            modulo="auditoria",
            entidad_tipo="AuditEvent",
            resultado=AuditResultado.ok,
        )
    """

    def __init__(self, repository: AuditRepository) -> None:
        self._repo = repository

    async def record(
        self,
        actor: CurrentUser,
        action: AuditAction,
        *,
        modulo: str,
        entidad_tipo: str,
        resultado: AuditResultado,
        entidad_id: Optional[str] = None,
        registros_afectados: Optional[int] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        impersonated_user_id: Optional[uuid.UUID] = None,
    ) -> AuditEvent:
        """
        Record an audit event.

        actor      — the real actor from the JWT (identity from session, rule #8).
        action     — MUST be a member of AuditAction (RN-24); raises
                     InvalidAuditAction otherwise — no event is persisted.
        before/after — JSONB payloads; PII/secrets redacted before persistence.
        impersonated_user_id — present only under impersonation (D5, RN-41).

        Raises InvalidAuditAction if action is not a valid AuditAction member.
        """
        # Validate action belongs to the closed catalog (RN-24)
        if not isinstance(action, AuditAction):
            raise InvalidAuditAction(
                f"Action {action!r} is not a member of the AuditAction catalog. "
                f"Valid actions: {[a.value for a in AuditAction]}"
            )

        # Redact PII/secrets before persistence (D7)
        safe_before = redact_pii(before)
        safe_after = redact_pii(after)

        event = AuditEvent(
            actor_user_id=actor.user_id,
            accion=action,
            modulo=modulo,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            resultado=resultado,
            registros_afectados=registros_afectados,
            before=safe_before,
            after=safe_after,
            ip=ip,
            user_agent=user_agent,
            impersonated_user_id=impersonated_user_id,
        )
        # repository.record() sets tenant_id from scope (D6)
        return await self._repo.record(event)

    async def record_impersonation_start(
        self,
        actor: CurrentUser,
        impersonated_user_id: uuid.UUID,
        *,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record the beginning of an impersonation session.

        Emits IMPERSONACION_INICIO with actor_user_id = actor (real user),
        impersonated_user_id = the user being impersonated.
        """
        return await self.record(
            actor=actor,
            action=AuditAction.IMPERSONACION_INICIO,
            modulo="impersonacion",
            entidad_tipo="User",
            entidad_id=str(impersonated_user_id),
            resultado=AuditResultado.ok,
            ip=ip,
            user_agent=user_agent,
            impersonated_user_id=impersonated_user_id,
        )

    async def record_impersonation_end(
        self,
        actor: CurrentUser,
        impersonated_user_id: uuid.UUID,
        *,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """
        Record the end of an impersonation session.

        Emits IMPERSONACION_FIN with actor_user_id = actor (real user),
        impersonated_user_id = the user who was impersonated.
        """
        return await self.record(
            actor=actor,
            action=AuditAction.IMPERSONACION_FIN,
            modulo="impersonacion",
            entidad_tipo="User",
            entidad_id=str(impersonated_user_id),
            resultado=AuditResultado.ok,
            ip=ip,
            user_agent=user_agent,
            impersonated_user_id=impersonated_user_id,
        )
