"""
guardia_service.py — Servicio de guardias de atención.

C-13 Design:
    asignacion_id resuelto desde current_user + materia/carrera/cohorte
    — nunca desde el body (regla dura #8/#14).
    Export como CSV (mismo patrón que equipo_service.py).

Identity ALWAYS from current_user — never from body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import List

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.encuentro import Guardia, GuardiaEstado
from app.repositories.audit_repository import AuditRepository
from app.repositories.guardia_repository import GuardiaRepository
from app.repositories.usuario_repository import AsignacionRepository
from app.schemas.guardia import GuardiaFiltros, GuardiaRead, RegistrarGuardiaRequest


class GuardiaService:
    """
    Service for guardia de atención operations.

    asignacion_id is ALWAYS resolved from current_user — never from request body.
    All DB operations delegated to repositories.
    """

    _ROLES_GLOBALES = {"COORDINADOR", "ADMIN"}

    def __init__(
        self,
        guardia_repo: GuardiaRepository,
        asignacion_repo: AsignacionRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._grd_repo = guardia_repo
        self._asig_repo = asignacion_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # registrar
    # -----------------------------------------------------------------------

    async def registrar(
        self,
        req: RegistrarGuardiaRequest,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> GuardiaRead:
        """
        Registra una guardia de atención.

        asignacion_id resuelto desde domain_user_id + materia (regla dura #8/#14).
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        tenant_id forzado desde el repo scope.
        """
        asig_id = await self._resolver_asignacion(
            domain_user_id, req.materia_id, req.carrera_id, req.cohorte_id
        )

        guardia = Guardia(
            asignacion_id=asig_id,
            materia_id=req.materia_id,
            carrera_id=req.carrera_id,
            cohorte_id=req.cohorte_id,
            dia=req.dia,
            horario=req.horario,
            estado=req.estado,
            comentarios=req.comentarios,
            creada_at=datetime.now(tz=timezone.utc),
        )
        guardia = await self._grd_repo.add(guardia)
        return GuardiaRead.model_validate(guardia)

    # -----------------------------------------------------------------------
    # consultar
    # -----------------------------------------------------------------------

    async def consultar(
        self,
        filtros: GuardiaFiltros,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> List[GuardiaRead]:
        """
        Lista guardias con filtros opcionales.

        COORDINADOR/ADMIN: ven todas las guardias del tenant.
        TUTOR/PROFESOR: ven solo sus propias guardias (filtradas por asignacion_ids).
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        es_global = any(r in self._ROLES_GLOBALES for r in current_user.roles)

        if es_global:
            guardias = await self._grd_repo.list_filtered(
                materia_id=filtros.materia_id,
                carrera_id=filtros.carrera_id,
                cohorte_id=filtros.cohorte_id,
                dia=filtros.dia,
                estado=filtros.estado,
            )
        else:
            mis_asigs = await self._asig_repo.list(usuario_id=domain_user_id)
            asig_ids = [a.id for a in mis_asigs]
            guardias = await self._grd_repo.list_filtered(
                materia_id=filtros.materia_id,
                carrera_id=filtros.carrera_id,
                cohorte_id=filtros.cohorte_id,
                dia=filtros.dia,
                estado=filtros.estado,
                asignacion_ids=asig_ids,
            )

        return [GuardiaRead.model_validate(g) for g in guardias]

    # -----------------------------------------------------------------------
    # exportar (CSV)
    # -----------------------------------------------------------------------

    async def exportar(
        self,
        filtros: GuardiaFiltros,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> str:
        """
        Exporta guardias filtradas como CSV.

        Columnas: guardia_id, asignacion_id, materia_id, carrera_id,
                  cohorte_id, dia, horario, estado, comentarios, creada_at.
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        guardias = await self.consultar(filtros, current_user, domain_user_id)

        output = io.StringIO()
        fieldnames = [
            "guardia_id",
            "asignacion_id",
            "materia_id",
            "carrera_id",
            "cohorte_id",
            "dia",
            "horario",
            "estado",
            "comentarios",
            "creada_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for g in guardias:
            writer.writerow({
                "guardia_id": str(g.id),
                "asignacion_id": str(g.asignacion_id),
                "materia_id": str(g.materia_id),
                "carrera_id": str(g.carrera_id),
                "cohorte_id": str(g.cohorte_id),
                "dia": g.dia.value,
                "horario": g.horario,
                "estado": g.estado.value,
                "comentarios": g.comentarios,
                "creada_at": str(g.creada_at),
            })

        return output.getvalue()

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _resolver_asignacion(
        self,
        domain_user_id: uuid.UUID,
        materia_id: uuid.UUID,
        carrera_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Resolve asignacion_id from domain_user_id + materia/carrera/cohorte.

        domain_user_id: usuario.id (resolved from auth_identity_id in router).
        Looks for an active asignacion matching user + materia/carrera/cohorte.
        Falls back to any asignacion of the user if no exact match.
        Raises ValueError if no asignacion found (never falls back to user_id).
        """
        mis_asigs = await self._asig_repo.list(usuario_id=domain_user_id)
        for asig in mis_asigs:
            if (
                asig.materia_id == materia_id
                and asig.carrera_id == carrera_id
                and asig.cohorte_id == cohorte_id
            ):
                return asig.id
        # Fallback to any asignacion of this user
        if mis_asigs:
            return mis_asigs[0].id
        # No asignacion found: raise, never fall back to domain_user_id
        raise ValueError(
            f"El usuario {domain_user_id} no tiene ninguna asignación activa."
        )
