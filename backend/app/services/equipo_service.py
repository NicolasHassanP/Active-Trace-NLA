"""
equipo_service.py — Servicio de equipos docentes.

C-08 Design Decisions:
    D3/D5 — El equipo es una proyección derivada de Asignacion. Sin tabla nueva.
    D5    — bulk_add fuerza tenant_id desde el repo scope.
    D6    — clonar: no-destructivo, skip de duplicados por (usuario_id, rol, tripleta).
    D7    — Todas las operaciones de escritura emiten auditoría.
    D9    — Acciones: EQUIPOS_ASIGNACION_MASIVA, EQUIPOS_CLONAR, EQUIPOS_VIGENCIA_GENERAL.
    D10   — Schemas Pydantic v2 para request/response.

Identity ALWAYS from current_user (JWT session) — never from request body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import io
import csv
import uuid
from datetime import date
from typing import List, Optional, Tuple

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.usuario import Asignacion, RolAsignacion
from app.models.vigencia import estado_vigencia
from app.repositories.audit_repository import AuditRepository
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.equipo import (
    AsignacionMasivaRequest,
    ClonarEquipoRequest,
    EquipoQuery,
    MisEquiposItem,
    ResumenClonacion,
    ResumenLote,
    VigenciaGeneralRequest,
)
from app.services.usuario_service import ReferenciaInvalida, UsuarioNoEncontrado


# ---------------------------------------------------------------------------
# EquipoService
# ---------------------------------------------------------------------------

class EquipoService:
    """
    Service for equipo docente operations.

    Equipo = projection of Asignacion rows sharing (materia_id, carrera_id, cohorte_id).
    All identity/tenant resolution from current_user (never from request body).
    Delegates DB operations to repositories.
    """

    def __init__(
        self,
        asignacion_repo: AsignacionRepository,
        usuario_repo: UsuarioRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._asig_repo = asignacion_repo
        self._usr_repo = usuario_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # listar_mis_equipos — GET /mis-equipos
    # -----------------------------------------------------------------------

    async def listar_mis_equipos(self, current_user: CurrentUser) -> List[MisEquiposItem]:
        """
        Devuelve las asignaciones del usuario autenticado con estado_vigencia derivado.
        Identidad SIEMPRE desde el JWT — nunca del body.
        """
        asignaciones = await self._asig_repo.list(usuario_id=current_user.user_id)
        return [self._to_mis_equipos_item(a) for a in asignaciones]

    def _to_mis_equipos_item(self, asig: Asignacion) -> MisEquiposItem:
        """Mapea una Asignacion a MisEquiposItem con estado_vigencia derivado."""
        ev = estado_vigencia(asig.desde, asig.hasta)
        return MisEquiposItem(
            asignacion_id=asig.id,
            materia_id=asig.materia_id,
            carrera_id=asig.carrera_id,
            cohorte_id=asig.cohorte_id,
            rol=asig.rol,
            desde=asig.desde,
            hasta=asig.hasta,
            estado_vigencia=ev,
            comisiones=asig.comisiones or [],
            responsable_id=asig.responsable_id,
        )

    # -----------------------------------------------------------------------
    # consultar_equipo — GET /equipos
    # -----------------------------------------------------------------------

    async def consultar_equipo(self, query: EquipoQuery) -> List[MisEquiposItem]:
        """
        Lista asignaciones del equipo identificado por la tripleta + filtros opcionales.
        """
        asignaciones = await self._asig_repo.list_by_equipo(
            materia_id=query.materia_id,
            carrera_id=query.carrera_id,
            cohorte_id=query.cohorte_id,
            rol=query.rol,
            responsable_id=query.responsable_id,
        )
        return [self._to_mis_equipos_item(a) for a in asignaciones]

    # -----------------------------------------------------------------------
    # asignacion_masiva — POST /asignacion-masiva
    # -----------------------------------------------------------------------

    async def asignacion_masiva(
        self,
        current_user: CurrentUser,
        req: AsignacionMasivaRequest,
    ) -> ResumenLote:
        """
        Crea N asignaciones atómicamente y emite auditoría EQUIPOS_ASIGNACION_MASIVA.

        Valida TODOS los usuario_ids y el responsable_id contra el tenant ANTES de persistir.
        Si cualquier validación falla, hace rollback completo (0 filas).
        """
        # Validate all usuario_ids belong to this tenant
        for uid in req.usuario_ids:
            usuario = await self._usr_repo.get_by_id(uid)
            if usuario is None:
                raise UsuarioNoEncontrado(
                    f"Usuario {uid} no encontrado en el tenant"
                )

        # Validate responsable_id if provided
        if req.responsable_id is not None:
            responsable = await self._usr_repo.get_by_id(req.responsable_id)
            if responsable is None:
                raise ReferenciaInvalida(
                    f"Responsable {req.responsable_id} no encontrado en el tenant"
                )

        # Build asignacion objects
        asignaciones = [
            Asignacion(
                usuario_id=uid,
                rol=req.rol,
                materia_id=req.materia_id,
                carrera_id=req.carrera_id,
                cohorte_id=req.cohorte_id,
                desde=req.desde,
                hasta=req.hasta,
                comisiones=req.comisiones,
                responsable_id=req.responsable_id,
            )
            for uid in req.usuario_ids
        ]

        # Persist atomically (bulk_add forces tenant_id from repo scope)
        await self._asig_repo.bulk_add(asignaciones)

        # Audit event
        await self._emit_audit(
            actor=current_user,
            action=AuditAction.EQUIPOS_ASIGNACION_MASIVA,
            registros_afectados=len(asignaciones),
            after={
                "materia_id": str(req.materia_id),
                "carrera_id": str(req.carrera_id),
                "cohorte_id": str(req.cohorte_id),
                "rol": req.rol.value,
                "total_creadas": len(asignaciones),
            },
        )

        return ResumenLote(creadas=len(asignaciones))

    # -----------------------------------------------------------------------
    # clonar_equipo — POST /clonar
    # -----------------------------------------------------------------------

    async def clonar_equipo(
        self,
        current_user: CurrentUser,
        req: ClonarEquipoRequest,
    ) -> ResumenClonacion:
        """
        Clona las asignaciones vigentes del equipo origen al destino.
        No-destructivo: skip de duplicados (mismo usuario_id + rol + tripleta destino).
        Emite auditoría EQUIPOS_CLONAR.
        """
        # Get source team asignaciones (active, not soft-deleted)
        origen = await self._asig_repo.list_by_equipo(
            materia_id=req.origen_materia_id,
            carrera_id=req.origen_carrera_id,
            cohorte_id=req.origen_cohorte_id,
        )

        # Get existing destination asignaciones to detect duplicates
        destino_existing = await self._asig_repo.list_by_equipo(
            materia_id=req.destino_materia_id,
            carrera_id=req.destino_carrera_id,
            cohorte_id=req.destino_cohorte_id,
        )
        existing_keys = {(a.usuario_id, a.rol) for a in destino_existing}

        to_clone = []
        omitidas = 0
        for asig in origen:
            key = (asig.usuario_id, asig.rol)
            if key in existing_keys:
                omitidas += 1
            else:
                to_clone.append(
                    Asignacion(
                        usuario_id=asig.usuario_id,
                        rol=asig.rol,
                        materia_id=req.destino_materia_id,
                        carrera_id=req.destino_carrera_id,
                        cohorte_id=req.destino_cohorte_id,
                        desde=req.desde,
                        hasta=req.hasta,
                        comisiones=asig.comisiones or [],
                        responsable_id=asig.responsable_id,
                    )
                )

        if to_clone:
            await self._asig_repo.bulk_add(to_clone)

        await self._emit_audit(
            actor=current_user,
            action=AuditAction.EQUIPOS_CLONAR,
            registros_afectados=len(to_clone),
            after={
                "origen_materia_id": str(req.origen_materia_id),
                "destino_materia_id": str(req.destino_materia_id),
                "clonadas": len(to_clone),
                "omitidas": omitidas,
            },
        )

        return ResumenClonacion(clonadas=len(to_clone), omitidas=omitidas)

    # -----------------------------------------------------------------------
    # modificar_vigencia_general — PATCH /vigencia-general
    # -----------------------------------------------------------------------

    async def modificar_vigencia_general(
        self,
        current_user: CurrentUser,
        req: VigenciaGeneralRequest,
    ) -> int:
        """
        Actualiza desde/hasta de todas las asignaciones activas del equipo.
        Retorna la cantidad afectada. Emite auditoría EQUIPOS_VIGENCIA_GENERAL.
        """
        afectadas = await self._asig_repo.bulk_update_vigencia(
            materia_id=req.materia_id,
            carrera_id=req.carrera_id,
            cohorte_id=req.cohorte_id,
            desde=req.desde,
            hasta=req.hasta,
        )

        await self._emit_audit(
            actor=current_user,
            action=AuditAction.EQUIPOS_VIGENCIA_GENERAL,
            registros_afectados=afectadas,
            after={
                "materia_id": str(req.materia_id),
                "carrera_id": str(req.carrera_id),
                "cohorte_id": str(req.cohorte_id),
                "desde": str(req.desde),
                "hasta": str(req.hasta) if req.hasta else None,
                "afectadas": afectadas,
            },
        )

        return afectadas

    # -----------------------------------------------------------------------
    # exportar_equipo — GET /exportar (CSV)
    # -----------------------------------------------------------------------

    async def exportar_equipo(self, query: EquipoQuery) -> str:
        """
        Exporta el equipo como CSV. Sin PII cifrada (D8).

        Columnas: asignacion_id, usuario_id, rol, materia_id, carrera_id,
                  cohorte_id, comisiones, desde, hasta, estado_vigencia.

        Retorna el contenido CSV como string (UTF-8).
        Equipo vacío → CSV solo con header.
        """
        asignaciones = await self._asig_repo.list_by_equipo(
            materia_id=query.materia_id,
            carrera_id=query.carrera_id,
            cohorte_id=query.cohorte_id,
            rol=query.rol,
            responsable_id=query.responsable_id,
        )

        output = io.StringIO()
        fieldnames = [
            "asignacion_id",
            "usuario_id",
            "rol",
            "materia_id",
            "carrera_id",
            "cohorte_id",
            "comisiones",
            "desde",
            "hasta",
            "estado_vigencia",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for asig in asignaciones:
            ev = estado_vigencia(asig.desde, asig.hasta)
            writer.writerow(self._to_csv_row(asig, ev.value))

        return output.getvalue()

    def _to_csv_row(self, asig: Asignacion, ev_value: str) -> dict:
        """Build a CSV row dict from an Asignacion. No PII cifrada."""
        return {
            "asignacion_id": str(asig.id),
            "usuario_id": str(asig.usuario_id),
            "rol": asig.rol.value,
            "materia_id": str(asig.materia_id) if asig.materia_id else "",
            "carrera_id": str(asig.carrera_id) if asig.carrera_id else "",
            "cohorte_id": str(asig.cohorte_id) if asig.cohorte_id else "",
            "comisiones": ";".join(asig.comisiones or []),
            "desde": str(asig.desde),
            "hasta": str(asig.hasta) if asig.hasta else "",
            "estado_vigencia": ev_value,
        }

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _emit_audit(
        self,
        actor: CurrentUser,
        action: AuditAction,
        registros_afectados: int,
        after: dict,
    ) -> None:
        """Emite un evento de auditoría para operaciones de equipo."""
        from app.services.audit_service import AuditService
        audit_svc = AuditService(repository=self._audit_repo)
        await audit_svc.record(
            actor=actor,
            action=action,
            modulo="equipos",
            entidad_tipo="Asignacion",
            resultado=AuditResultado.ok,
            registros_afectados=registros_afectados,
            after=after,
        )
