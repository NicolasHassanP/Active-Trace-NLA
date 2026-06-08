"""
tarea_service.py — Servicio de tareas internas (C-16).

Design decisions:
    D3  — State machine _TRANSICIONES_VALIDAS enforced here; HTTP 409 on illegal/no-op.
    D5  — Delegación: audit TAREA_DELEGAR (before/after) + ComentarioTarea de sistema.
    D6  — Identity (tenant_id, asignado_por, autor_id) ALWAYS from current_user (JWT).
    D7  — Ownership: without tareas:gestionar, only asignado_a or asignado_por can access.
    D8  — AuditAction: TAREA_ASIGNAR, TAREA_DELEGAR, TAREA_CAMBIAR_ESTADO.

Identity ALWAYS from current_user — never from request body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import HTTPException, status

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.tarea import ComentarioTarea, Tarea, TareaEstado
from app.repositories.audit_repository import AuditRepository
from app.repositories.tarea_repository import ComentarioTareaRepository, TareaRepository
from app.schemas.tarea import (
    ComentarioTareaCreate,
    TareaCreate,
)

# ---------------------------------------------------------------------------
# D3 — State transition matrix
# ---------------------------------------------------------------------------

_TRANSICIONES_VALIDAS: dict[TareaEstado, set[TareaEstado]] = {
    TareaEstado.Pendiente: {TareaEstado.EnProgreso, TareaEstado.Resuelta, TareaEstado.Cancelada},
    TareaEstado.EnProgreso: {TareaEstado.Pendiente, TareaEstado.Resuelta, TareaEstado.Cancelada},
    TareaEstado.Resuelta: {TareaEstado.EnProgreso},   # only reopen; FL-05 §7
    TareaEstado.Cancelada: set(),                       # terminal-final, no exits
}


# ---------------------------------------------------------------------------
# TareaService
# ---------------------------------------------------------------------------

class TareaService:
    """
    Service for tareas-internas operations.

    Identity/tenant ALWAYS from current_user (JWT) — never from request body.
    Delegates all DB operations to repositories.
    """

    def __init__(
        self,
        tarea_repo: TareaRepository,
        comentario_repo: ComentarioTareaRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._tarea_repo = tarea_repo
        self._comentario_repo = comentario_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # Publicar / asignar (D6, D8)
    # -----------------------------------------------------------------------

    async def publicar(self, req: TareaCreate, current_user: CurrentUser, domain_user_id: uuid.UUID) -> Tarea:
        """
        Create and assign a new Tarea.

        Estado initial = Pendiente (D2).
        tenant_id and asignado_por from current_user (JWT), never from body (D6).
        domain_user_id: resolved usuario.id (FK target), not auth_identity_id.
        Emits TAREA_ASIGNAR audit (D8).
        """
        tarea = Tarea(
            asignado_a=req.asignado_a,
            asignado_por=domain_user_id,
            descripcion=req.descripcion,
            estado=TareaEstado.Pendiente,
            materia_id=req.materia_id,
            contexto_id=req.contexto_id,
            contexto_tipo=req.contexto_tipo,
        )
        tarea = await self._tarea_repo.add(tarea)

        await self._emit_audit(
            actor=current_user,
            action=AuditAction.TAREA_ASIGNAR,
            entidad_id=str(tarea.id),
            after={
                "tarea_id": str(tarea.id),
                "asignado_a": str(tarea.asignado_a),
                "asignado_por": str(tarea.asignado_por),
                "estado": tarea.estado.value,
            },
        )
        return tarea

    # -----------------------------------------------------------------------
    # Cambiar estado (D3, D7, D8)
    # -----------------------------------------------------------------------

    async def cambiar_estado(
        self,
        tarea_id: uuid.UUID,
        nuevo_estado: TareaEstado,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
        has_gestionar: bool = False,
    ) -> Tarea:
        """
        Change tarea estado with D3 transition matrix enforcement.

        Raises HTTP 409 on illegal or no-op transitions.
        Raises HTTP 403 if caller lacks ownership and tareas:gestionar (D7).
        Raises HTTP 404 if tarea not found in tenant.
        Emits TAREA_CAMBIAR_ESTADO audit on success (D8).
        """
        tarea = await self._get_tarea_or_404(tarea_id)
        self._enforce_ownership(tarea, domain_user_id, has_gestionar=has_gestionar)

        # D3: no-op check
        if tarea.estado == nuevo_estado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"La tarea ya está en estado {nuevo_estado.value}; no-op rechazado",
            )

        # D3: illegal transition check
        transiciones = _TRANSICIONES_VALIDAS.get(tarea.estado, set())
        if nuevo_estado not in transiciones:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Transición ilegal: {tarea.estado.value} → {nuevo_estado.value}. "
                    f"Permitidas: {[e.value for e in transiciones] or 'ninguna (terminal)'}"
                ),
            )

        estado_anterior = tarea.estado
        tarea = await self._tarea_repo.update_estado(tarea, nuevo_estado)

        await self._emit_audit(
            actor=current_user,
            action=AuditAction.TAREA_CAMBIAR_ESTADO,
            entidad_id=str(tarea.id),
            before={"estado": estado_anterior.value},
            after={"estado": nuevo_estado.value},
        )
        return tarea

    # -----------------------------------------------------------------------
    # Delegar (D5, D8)
    # -----------------------------------------------------------------------

    async def delegar(
        self,
        tarea_id: uuid.UUID,
        nuevo_asignado_a: uuid.UUID,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> Tarea:
        """
        Delegate a tarea to another user (D5).

        Updates asignado_a and overwrites asignado_por with the delegating actor.
        Emits TAREA_DELEGAR audit (before/after) and inserts a system ComentarioTarea.
        Requires tareas:gestionar (enforced by router; service trusts it).
        """
        tarea = await self._get_tarea_or_404(tarea_id)

        before_data = {
            "asignado_a": str(tarea.asignado_a),
            "asignado_por": str(tarea.asignado_por),
        }

        tarea = await self._tarea_repo.update_asignacion(
            tarea,
            nuevo_asignado_a=nuevo_asignado_a,
            nuevo_asignado_por=domain_user_id,
        )

        after_data = {
            "asignado_a": str(tarea.asignado_a),
            "asignado_por": str(tarea.asignado_por),
        }

        await self._emit_audit(
            actor=current_user,
            action=AuditAction.TAREA_DELEGAR,
            entidad_id=str(tarea.id),
            before=before_data,
            after=after_data,
        )

        # D5: insert system comment reflecting the delegation
        texto_delegacion = (
            f"Tarea delegada de {before_data['asignado_a']} "
            f"a {after_data['asignado_a']} "
            f"por {str(domain_user_id)}"
        )
        await self._comentario_repo.add_comentario(
            tarea_id=tarea.id,
            autor_id=domain_user_id,
            cuerpo=texto_delegacion,
            es_sistema=True,
        )

        return tarea

    # -----------------------------------------------------------------------
    # Comentar (D6, D7)
    # -----------------------------------------------------------------------

    async def comentar(
        self,
        tarea_id: uuid.UUID,
        req: ComentarioTareaCreate,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
        has_gestionar: bool = False,
    ) -> ComentarioTarea:
        """
        Add a human comment to the thread.

        Raises HTTP 403 if caller lacks ownership and tareas:gestionar (D7).
        autor_id from domain_user_id (usuario.id) — never from body (D6).
        """
        tarea = await self._get_tarea_or_404(tarea_id)
        self._enforce_ownership(tarea, domain_user_id, has_gestionar=has_gestionar)

        return await self._comentario_repo.add_comentario(
            tarea_id=tarea.id,
            autor_id=domain_user_id,
            cuerpo=req.cuerpo,
            es_sistema=False,
        )

    # -----------------------------------------------------------------------
    # listar_mias (D7)
    # -----------------------------------------------------------------------

    async def listar_mias(self, domain_user_id: uuid.UUID) -> List[Tarea]:
        """
        Return tareas assigned to the caller (self-service F8.1).

        No gestionar permission required — any authenticated user can list their own tasks.
        domain_user_id: resolved usuario.id.
        """
        return await self._tarea_repo.listar_mias(domain_user_id)

    # -----------------------------------------------------------------------
    # listar_admin (D7, D10)
    # -----------------------------------------------------------------------

    async def listar_admin(
        self,
        current_user: CurrentUser,
        asignado_a: Optional[uuid.UUID] = None,
        asignado_por: Optional[uuid.UUID] = None,
        materia_id: Optional[uuid.UUID] = None,
        estado: Optional[TareaEstado] = None,
        q: Optional[str] = None,
    ) -> List[Tarea]:
        """
        Admin global listing with optional filters (F8.3).

        Requires tareas:gestionar (enforced by router).
        """
        return await self._tarea_repo.listar_admin(
            asignado_a=asignado_a,
            asignado_por=asignado_por,
            materia_id=materia_id,
            estado=estado,
            q=q,
        )

    # -----------------------------------------------------------------------
    # Soft delete
    # -----------------------------------------------------------------------

    async def eliminar(self, tarea_id: uuid.UUID, current_user: CurrentUser) -> None:
        """Soft-delete a tarea. Requires tareas:gestionar (enforced by router)."""
        tarea = await self._get_tarea_or_404(tarea_id)
        await self._tarea_repo.delete(tarea)

    # -----------------------------------------------------------------------
    # Detail + thread (D7)
    # -----------------------------------------------------------------------

    async def detalle(
        self,
        tarea_id: uuid.UUID,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
        has_gestionar: bool = False,
    ) -> Tarea:
        """
        Get tarea detail.

        Raises HTTP 403 if caller lacks ownership and tareas:gestionar (D7).
        """
        tarea = await self._get_tarea_or_404(tarea_id)
        self._enforce_ownership(tarea, domain_user_id, has_gestionar=has_gestionar)
        return tarea

    async def listar_comentarios(
        self,
        tarea_id: uuid.UUID,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
        has_gestionar: bool = False,
    ) -> List[ComentarioTarea]:
        """
        List the comment thread.

        Same access control as detalle (D7).
        """
        tarea = await self._get_tarea_or_404(tarea_id)
        self._enforce_ownership(tarea, domain_user_id, has_gestionar=has_gestionar)
        return await self._comentario_repo.listar_hilo(tarea_id)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _get_tarea_or_404(self, tarea_id: uuid.UUID) -> Tarea:
        tarea = await self._tarea_repo.get_by_id(tarea_id)
        if tarea is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarea no encontrada",
            )
        return tarea

    def _enforce_ownership(
        self,
        tarea: Tarea,
        domain_user_id: uuid.UUID,
        has_gestionar: bool = False,
    ) -> None:
        """
        D7: without tareas:gestionar, only asignado_a or asignado_por may access.

        domain_user_id: resolved usuario.id (matches FKs stored in tarea table).
        has_gestionar is resolved by the router via require_permission and passed in.
        Raises HTTP 403 if access is not allowed.
        """
        if has_gestionar:
            return  # full access
        if domain_user_id not in (tarea.asignado_a, tarea.asignado_por):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: no es asignado_a ni asignado_por de esta tarea",
            )

    async def _emit_audit(
        self,
        actor: CurrentUser,
        action: AuditAction,
        entidad_id: str,
        after: Optional[dict] = None,
        before: Optional[dict] = None,
    ) -> None:
        from app.services.audit_service import AuditService
        audit_svc = AuditService(repository=self._audit_repo)
        await audit_svc.record(
            actor=actor,
            action=action,
            modulo="tareas",
            entidad_tipo="Tarea",
            entidad_id=entidad_id,
            resultado=AuditResultado.ok,
            registros_afectados=1,
            before=before,
            after=after,
        )
