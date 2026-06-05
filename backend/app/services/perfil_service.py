"""
PerfilService — C-20 autoservicio de perfil propio.

D1 — Perfil reusa el modelo Usuario; el service provee la capa de lógica de
     negocio para el autoservicio.

obtener_perfil(actor):
    Retorna el Usuario cuyo id coincide con actor.user_id (JWT).
    NUNCA acepta un id externo — identidad SIEMPRE del JWT.

actualizar_perfil(actor, **campos):
    PATCH parcial del perfil del actor.
    Valida unicidad de email si se cambia.
    Registra evento de auditoría sin PII en texto plano.

Excepciones mapeadas a HTTP en el router:
    ConflictoEmailPerfil    → 409
    PerfilNoEncontrado      → 404

Regla dura #11: lógica de negocio SOLO aquí. Queries SOLO en repositories.
PII NUNCA en logs ni en mensajes de excepción.
snake_case; ≤500 LOC.
"""
import logging
from typing import Optional

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.usuario import Usuario
from app.repositories.perfil_repository import PerfilRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class ConflictoEmailPerfil(Exception):
    """Email ya existe en el tenant — HTTP 409."""


class PerfilNoEncontrado(Exception):
    """Usuario no encontrado para el actor — HTTP 404."""


# ---------------------------------------------------------------------------
# PerfilService
# ---------------------------------------------------------------------------

class PerfilService:
    """
    Service para el autoservicio de perfil propio.

    Identidad SIEMPRE desde actor (CurrentUser derivado del JWT).
    PII en texto plano NUNCA aparece en logs ni en mensajes de excepción.
    """

    def __init__(self, repo: PerfilRepository, audit_svc: AuditService) -> None:
        self._repo = repo
        self._audit = audit_svc

    async def obtener_perfil(self, actor: CurrentUser) -> Usuario:
        """
        Retorna el perfil del actor (usuario del JWT).

        La identidad viene exclusivamente del JWT — ignora cualquier id
        externo. Raises PerfilNoEncontrado si no existe.
        """
        usuario = await self._repo.get_self(actor.user_id)
        if usuario is None:
            raise PerfilNoEncontrado("Perfil no encontrado.")
        return usuario

    async def actualizar_perfil(
        self,
        actor: CurrentUser,
        *,
        nombre: Optional[str] = None,
        apellidos: Optional[str] = None,
        dni: Optional[str] = None,
        genero: Optional[str] = None,
        banco: Optional[str] = None,
        cbu: Optional[str] = None,
        alias_cbu: Optional[str] = None,
        regional: Optional[str] = None,
        email: Optional[str] = None,
        facturador: Optional[bool] = None,
        legajo_profesional: Optional[str] = None,
    ) -> Usuario:
        """
        Actualiza el perfil del actor (PATCH parcial).

        - Solo aplica los campos explícitamente provistos (no None).
        - Si se cambia el email, recomputa email_hash y valida unicidad.
        - Registra evento de auditoría sin PII en texto plano.
        - Raises: PerfilNoEncontrado, ConflictoEmailPerfil.
        """
        from app.core.security.passwords import email_lookup_hash

        usuario = await self._repo.get_self(actor.user_id)
        if usuario is None:
            raise PerfilNoEncontrado("Perfil no encontrado.")

        updates: dict = {}

        # Manejo especial del email: recalcular hash y validar unicidad
        if email is not None:
            email_norm = email.strip().lower()
            new_hash = email_lookup_hash(email_norm)
            if new_hash != usuario.email_hash:
                existente = await self._repo.get_by_email_hash(new_hash)
                if existente is not None:
                    # No incluir el email en el mensaje (PII)
                    raise ConflictoEmailPerfil(
                        "Ya existe un usuario con ese email en este tenant."
                    )
                updates["email_encrypted"] = email_norm
                updates["email_hash"] = new_hash

        # Campos editables (sin PII en logs)
        if nombre is not None:
            updates["nombre"] = nombre
        if apellidos is not None:
            updates["apellidos"] = apellidos
        if genero is not None:
            updates["genero"] = genero
        if banco is not None:
            updates["banco"] = banco
        if regional is not None:
            updates["regional"] = regional
        if facturador is not None:
            updates["facturador"] = facturador
        if legajo_profesional is not None:
            updates["legajo_profesional"] = legajo_profesional

        # PII: solo en updates, nunca en logs (regla dura #12)
        if dni is not None:
            updates["dni"] = dni
        if cbu is not None:
            updates["cbu"] = cbu
        if alias_cbu is not None:
            updates["alias_cbu"] = alias_cbu

        usuario = await self._repo.update_self(usuario, **updates)

        # Auditoría (sin PII en texto plano — D7)
        _campos_auditados = [k for k in updates if k not in ("dni", "cbu", "alias_cbu", "email_encrypted", "email_hash")]
        try:
            await self._audit.record(
                actor=actor,
                action=AuditAction.PERFIL_EDITAR,
                modulo="perfil",
                entidad_tipo="Usuario",
                entidad_id=str(actor.user_id),
                resultado=AuditResultado.ok,
                registros_afectados=1,
                after={"campos_modificados": _campos_auditados},
            )
        except Exception:
            # La auditoría no debe romper el flujo principal
            logger.warning("No se pudo registrar evento de auditoría de perfil", exc_info=True)

        return usuario
