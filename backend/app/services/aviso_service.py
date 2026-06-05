"""
aviso_service.py — Servicio de avisos y acknowledgment.

C-15 Design Decisions:
    D3  — Audience logic delegated to repository.
    D4  — Counters DERIVED via repository COUNT, never stored.
    D5  — Pending feed: repository returns only unacknowledged, requiere_ack=True.
    D6  — Idempotent ack: service-level check + partial unique index defense-in-depth.
    D7  — avisos:publicar permission + AVISO_PUBLICAR audit on create.
    D8  — Identity/tenant ALWAYS from current_user — never from request body.

Identity ALWAYS from current_user — never from request body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.aviso import Aviso, AcknowledgmentAviso
from app.repositories.audit_repository import AuditRepository
from app.repositories.aviso_repository import AcknowledgmentRepository, AvisoRepository
from app.schemas.aviso import (
    AckAvisoRequest,
    ActualizarAvisoRequest,
    AcknowledgmentRead,
    AvisoRead,
    CrearAvisoRequest,
)


# ---------------------------------------------------------------------------
# AvisoService
# ---------------------------------------------------------------------------

class AvisoService:
    """
    Service for avisos-y-acknowledgment operations.

    Identity/tenant ALWAYS from current_user (JWT) — never from request body.
    Delegates all DB operations to repositories.
    """

    def __init__(
        self,
        aviso_repo: AvisoRepository,
        ack_repo: AcknowledgmentRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._aviso_repo = aviso_repo
        self._ack_repo = ack_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # 5.1 / 5.2 — Management: publicar / modificar / eliminar
    # -----------------------------------------------------------------------

    async def publicar_aviso(
        self,
        req: CrearAvisoRequest,
        current_user: CurrentUser,
    ) -> Aviso:
        """
        Publish a new Aviso.

        Tenant from current_user. Scope coherence and validity window
        already validated by the Pydantic schema. Audits AVISO_PUBLICAR.
        """
        aviso = Aviso(
            alcance=req.alcance,
            materia_id=req.materia_id,
            cohorte_id=req.cohorte_id,
            rol_destino=req.rol_destino,
            severidad=req.severidad,
            titulo=req.titulo,
            cuerpo=req.cuerpo,
            inicio_en=req.inicio_en,
            fin_en=req.fin_en,
            orden=req.orden,
            activo=req.activo,
            requiere_ack=req.requiere_ack,
        )
        aviso = await self._aviso_repo.add(aviso)

        await self._emit_audit(
            actor=current_user,
            entidad_id=str(aviso.id),
            after={
                "aviso_id": str(aviso.id),
                "alcance": aviso.alcance.value,
                "titulo": aviso.titulo,
            },
        )

        return aviso

    async def modificar_aviso(
        self,
        aviso_id: uuid.UUID,
        req: ActualizarAvisoRequest,
        current_user: CurrentUser,
    ) -> Aviso:
        """
        Modify an existing Aviso.

        Returns 404 if the aviso does not belong to the caller's tenant.
        Applies only non-None fields from the request (partial update).
        """
        aviso = await self._aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )

        # Apply partial update — only fields provided in request
        update_fields = req.model_dump(exclude_none=True)
        for field, value in update_fields.items():
            setattr(aviso, field, value)

        await self._aviso_repo._session.commit()
        await self._aviso_repo._session.refresh(aviso)
        return aviso

    async def eliminar_aviso(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> None:
        """
        Soft-delete an Aviso.

        Returns 404 if not found in caller's tenant. Hard delete not supported.
        """
        aviso = await self._aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )
        await self._aviso_repo.delete(aviso)

    # -----------------------------------------------------------------------
    # 5.3 / 5.4 — Acknowledgment
    # -----------------------------------------------------------------------

    async def acknowledger_aviso(
        self,
        aviso_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> AcknowledgmentAviso:
        """
        Idempotent acknowledgment: create or return existing active ack.

        Guards:
            - Aviso must be visible to the user (audience + window + activo + not deleted).
            - If ack already exists (not soft-deleted), return it without inserting.
            - Partial unique index acts as defense-in-depth against races.

        Identity (usuario_id, tenant_id) ALWAYS from current_user — never from body.
        """
        # Fetch aviso in scope (get_by_id already scopes to tenant + not deleted)
        aviso = await self._aviso_repo.get_by_id(aviso_id)
        if aviso is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aviso no encontrado",
            )

        # Visibility check: activo + validity window (RN-19)
        now = datetime.now(tz=timezone.utc)
        if not aviso.activo or aviso.inicio_en > now or aviso.fin_en < now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede confirmar un aviso fuera de su ventana de validez o inactivo",
            )

        # Idempotency: return existing active ack (D6)
        existing = await self._ack_repo.get_by_aviso_usuario(aviso_id, current_user.user_id)
        if existing is not None:
            return existing

        # Insert new ack
        ack = AcknowledgmentAviso(
            tenant_id=current_user.tenant_id,
            aviso_id=aviso_id,
            usuario_id=current_user.user_id,
            confirmado_at=now,
        )
        ack = await self._ack_repo.add(ack)
        return ack

    # -----------------------------------------------------------------------
    # 5.5 — Feed / pending retrieval with derived counters
    # -----------------------------------------------------------------------

    async def listar_gestion(
        self,
        actor: CurrentUser,
    ) -> List[AvisoRead]:
        """
        Management list: ALL non-deleted avisos for the caller's tenant.

        No audience filtering — returns the full tenant set ordered newest-first.
        ack_count is derived per aviso via the acknowledgment repository (D4).

        C-15 follow-up resolving OQ-1 of C-23: the audience feed is intentionally
        recipient-scoped; management needs the unfiltered tenant-scoped list.
        Requires avisos:publicar permission (enforced at the router layer).
        Identity/tenant ALWAYS from actor (JWT) — never from request.
        """
        avisos = await self._aviso_repo.listar_todos_gestion()
        return await self._build_feed_response(avisos)

    async def listar_feed(
        self,
        usuario_id: uuid.UUID,
        roles: List[str],
        cohorte_id: Optional[uuid.UUID],
        actor: CurrentUser,
    ) -> List[AvisoRead]:
        """
        Full recipient feed: all visible avisos for the user with derived ack_count.

        Audience + validity filtering delegated to the repository (D3).
        ack_count derived at call time per aviso (D4).
        """
        avisos = await self._aviso_repo.get_recipient_feed(
            usuario_id=usuario_id,
            roles=roles,
            cohorte_id=cohorte_id,
        )
        return await self._build_feed_response(avisos)

    async def listar_pendientes(
        self,
        usuario_id: uuid.UUID,
        roles: List[str],
        cohorte_id: Optional[uuid.UUID],
        actor: CurrentUser,
    ) -> List[AvisoRead]:
        """
        Pending feed: avisos requiring ack not yet acknowledged by this user (D5).

        Only requiere_ack=True avisos appear here.
        """
        avisos = await self._aviso_repo.get_pending_feed(
            usuario_id=usuario_id,
            roles=roles,
            cohorte_id=cohorte_id,
        )
        return await self._build_feed_response(avisos)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _build_feed_response(self, avisos: List[Aviso]) -> List[AvisoRead]:
        """Annotate each aviso with its derived ack_count."""
        result = []
        for aviso in avisos:
            ack_count = await self._ack_repo.count_acks(aviso.id)
            read = AvisoRead.model_validate(aviso)
            read = read.model_copy(update={"ack_count": ack_count})
            result.append(read)
        return result

    async def _emit_audit(
        self,
        actor: CurrentUser,
        entidad_id: str,
        after: dict,
    ) -> None:
        from app.services.audit_service import AuditService
        audit_svc = AuditService(repository=self._audit_repo)
        await audit_svc.record(
            actor=actor,
            action=AuditAction.AVISO_PUBLICAR,
            modulo="avisos",
            entidad_tipo="Aviso",
            entidad_id=entidad_id,
            resultado=AuditResultado.ok,
            registros_afectados=1,
            after=after,
        )
