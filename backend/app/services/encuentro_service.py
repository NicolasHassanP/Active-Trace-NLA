"""
encuentro_service.py — Servicio de slots e instancias de encuentro.

C-13 Design Decisions:
    D9  — Un solo permiso 'encuentros:gestionar' para todo el módulo.
    D11 — listar_instancias: COORDINADOR/ADMIN ven todas; PROFESOR solo las propias.
    RN-13 — Dos modos excluyentes: recurrente OR único.
    RN-14 — Estado de cada instancia es INDEPENDIENTE.

Identity ALWAYS from current_user — never from body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.encuentro import (
    InstanciaEncuentro,
    InstanciaEncuentroEstado,
    SlotEncuentro,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.encuentro_repository import (
    InstanciaEncuentroRepository,
    SlotEncuentroRepository,
)
from app.repositories.usuario_repository import AsignacionRepository
from app.schemas.encuentro import (
    CrearSlotRequest,
    CrearSlotResponse,
    EditarInstanciaRequest,
    InstanciaEncuentroRead,
    SlotEncuentroRead,
)
from app.services.encuentro_recurrencia import generar_fechas


# ---------------------------------------------------------------------------
# EncuentroValidationError — señal de 422 para RN-13
# ---------------------------------------------------------------------------

class EncuentroValidationError(ValueError):
    """
    Raised when a slot creation request violates RN-13 mode exclusivity.
    Maps to HTTP 422 in the router.
    """
    pass


# ---------------------------------------------------------------------------
# EncuentroService
# ---------------------------------------------------------------------------

class EncuentroService:
    """
    Service for slot + instance encuentro operations.

    Identity/tenant ALWAYS from current_user (JWT) — never from request body.
    Delegates all DB operations to repositories.
    """

    _ROLES_GLOBALES = {"COORDINADOR", "ADMIN"}

    def __init__(
        self,
        slot_repo: SlotEncuentroRepository,
        instancia_repo: InstanciaEncuentroRepository,
        asignacion_repo: AsignacionRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._slot_repo = slot_repo
        self._inst_repo = instancia_repo
        self._asig_repo = asignacion_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # crear_slot
    # -----------------------------------------------------------------------

    async def crear_slot(
        self,
        req: CrearSlotRequest,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> CrearSlotResponse:
        """
        Crea un SlotEncuentro y genera sus InstanciaEncuentro.

        RN-13: exige exactamente uno de los modos:
            - Recurrente: cant_semanas > 0 + dia_semana + fecha_inicio
            - Único:      fecha_unica presente, cant_semanas = 0

        Errores:
            EncuentroValidationError(422) si ambos o ningún modo activo.

        Identidad: asignacion_id resuelto desde domain_user_id + materia_id.
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        Auditoría: ENCUENTRO_GESTIONAR con registros_afectados=N instancias.
        """
        modo_recurrente = req.cant_semanas > 0
        modo_unico = req.fecha_unica is not None

        # RN-13 validation
        if modo_recurrente and modo_unico:
            raise EncuentroValidationError(
                "Modos excluyentes: no se puede especificar cant_semanas>0 y fecha_unica simultáneamente."
            )
        if not modo_recurrente and not modo_unico:
            raise EncuentroValidationError(
                "Se requiere exactamente un modo: cant_semanas>0 (recurrente) o fecha_unica (único)."
            )

        # Resolve asignacion_id from domain_user_id + materia
        asig_id = await self._resolver_asignacion(current_user, req.materia_id, domain_user_id)

        # Create slot
        slot = SlotEncuentro(
            asignacion_id=asig_id,
            materia_id=req.materia_id,
            titulo=req.titulo,
            hora=req.hora,
            dia_semana=req.dia_semana,
            fecha_inicio=req.fecha_inicio,
            cant_semanas=req.cant_semanas,
            fecha_unica=req.fecha_unica,
            meet_url=req.meet_url,
            vig_desde=req.vig_desde,
            vig_hasta=req.vig_hasta,
        )
        slot = await self._slot_repo.add(slot)

        # Generate instances
        if modo_recurrente:
            fechas = generar_fechas(req.fecha_inicio, req.dia_semana, req.cant_semanas)
        else:
            fechas = [req.fecha_unica]

        instancias = [
            InstanciaEncuentro(
                slot_id=slot.id,
                materia_id=req.materia_id,
                fecha=f,
                hora=req.hora,
                titulo=req.titulo,
                estado=InstanciaEncuentroEstado.Programado,
                meet_url=req.meet_url,
            )
            for f in fechas
        ]
        instancias = await self._inst_repo.bulk_add(instancias)

        # Audit
        await self._emit_audit(
            actor=current_user,
            registros_afectados=len(instancias),
            after={
                "slot_id": str(slot.id),
                "titulo": req.titulo,
                "instancias_generadas": len(instancias),
                "modo": "recurrente" if modo_recurrente else "unico",
            },
        )

        return CrearSlotResponse(
            slot=SlotEncuentroRead.model_validate(slot),
            instancias=[InstanciaEncuentroRead.model_validate(inst) for inst in instancias],
        )

    # -----------------------------------------------------------------------
    # editar_instancia
    # -----------------------------------------------------------------------

    async def editar_instancia(
        self,
        instancia_id: uuid.UUID,
        patch: EditarInstanciaRequest,
        current_user: CurrentUser,
    ) -> InstanciaEncuentroRead:
        """
        Edita los campos mutables de una sola instancia (RN-14).

        Solo modifica los campos presentes en el patch.
        No afecta al slot ni a otras instancias hermanas.
        """
        inst = await self._inst_repo.get_by_id(instancia_id)
        if inst is None:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"InstanciaEncuentro {instancia_id} no encontrada",
            )

        if patch.estado is not None:
            inst.estado = patch.estado
        if patch.meet_url is not None:
            inst.meet_url = patch.meet_url
        if patch.video_url is not None:
            inst.video_url = patch.video_url
        if patch.comentario is not None:
            inst.comentario = patch.comentario

        await self._inst_repo._session.commit()
        await self._inst_repo._session.refresh(inst)

        return InstanciaEncuentroRead.model_validate(inst)

    # -----------------------------------------------------------------------
    # listar_instancias
    # -----------------------------------------------------------------------

    async def listar_instancias(
        self,
        actor: CurrentUser,
        domain_user_id: uuid.UUID,
        materia_id: Optional[uuid.UUID] = None,
    ) -> List[InstanciaEncuentroRead]:
        """
        Lista instancias de encuentro filtradas por rol del actor (D11).

        COORDINADOR/ADMIN: ven todas las instancias del tenant (asignacion_ids=None).
        PROFESOR/TUTOR:    ven solo las instancias de sus propios slots
                           (asignacion_ids = IDs de sus asignaciones).

        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        Siempre filtra por tenant (base repo scope).
        """
        es_global = any(r in self._ROLES_GLOBALES for r in actor.roles)

        if es_global:
            instancias = await self._inst_repo.list_by_materia(materia_id=materia_id)
        else:
            # Get current user's asignaciones using domain_user_id (FK correcto)
            mis_asigs = await self._asig_repo.list(usuario_id=domain_user_id)
            asig_ids = [a.id for a in mis_asigs]
            instancias = await self._inst_repo.list_by_materia(
                materia_id=materia_id,
                asignacion_ids=asig_ids,
            )

        return [InstanciaEncuentroRead.model_validate(inst) for inst in instancias]

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _resolver_asignacion(
        self,
        current_user: CurrentUser,
        materia_id: uuid.UUID,
        domain_user_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Resolve the asignacion_id for domain_user_id + materia_id.

        domain_user_id: usuario.id (resolved from auth_identity_id in router).
        Prefers an asignacion matching the exact materia_id.
        Falls back to any asignacion of the user (for COORDINADOR/ADMIN who
        manage slots across materias).
        Raises EncuentroValidationError if the user has no asignacion at all.
        """
        mis_asigs = await self._asig_repo.list(usuario_id=domain_user_id)
        for asig in mis_asigs:
            if asig.materia_id == materia_id:
                return asig.id
        # Fallback: any asignacion (COORDINADOR/ADMIN cross-materia management)
        if mis_asigs:
            return mis_asigs[0].id
        raise EncuentroValidationError(
            f"El usuario {domain_user_id} no tiene ninguna asignación activa. "
            "No se puede crear el slot."
        )

    async def _emit_audit(
        self,
        actor: CurrentUser,
        registros_afectados: int,
        after: dict,
    ) -> None:
        from app.services.audit_service import AuditService
        audit_svc = AuditService(repository=self._audit_repo)
        await audit_svc.record(
            actor=actor,
            action=AuditAction.ENCUENTRO_GESTIONAR,
            modulo="encuentros",
            entidad_tipo="SlotEncuentro",
            resultado=AuditResultado.ok,
            registros_afectados=registros_afectados,
            after=after,
        )
