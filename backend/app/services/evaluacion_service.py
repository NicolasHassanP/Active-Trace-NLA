"""
evaluacion_service.py — Servicio de evaluaciones y coloquios.

C-14 Design Decisions:
    D2  — Cupos derivados, nunca denormalizados.
    D3  — crear_reserva usa SELECT ... FOR UPDATE (lock pesimista).
    D4  — Una reserva Activa por (alumno, convocatoria).
    D5  — Solo candidatos importados pueden reservar.
    D6  — coloquios:gestionar + coloquios:reservar, diferenciados en el router.
    D8  — Auditoría en cada operación de gestión y reserva.

Identity ALWAYS from current_user — never from request body.
domain_user_id resuelto en el router con resolve_domain_user_id (usuario.id ≠ auth_identity_id).
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.evaluacion import (
    Evaluacion,
    ReservaEvaluacion,
    ReservaEstado,
    TurnoEvaluacion,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.evaluacion_repository import (
    CandidatoEvaluacionRepository,
    EvaluacionRepository,
    ReservaEvaluacionRepository,
    ResultadoEvaluacionRepository,
    TurnoEvaluacionRepository,
)
from app.schemas.evaluacion import (
    AgendaItemRead,
    ConvocatoriaConTurnosRead,
    ConvocatoriaMetricasRead,
    ConvocatoriaRead,
    ConvocatoriasAlumnoRead,
    CrearConvocatoriaRequest,
    ImportarCandidatosRequest,
    MetricasRead,
    ReservaRead,
    ReservaRequest,
    ResultadoRead,
    ResultadoRequest,
    TurnoConCupoRead,
    TurnoRead,
)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class EvaluacionValidationError(ValueError):
    """
    Raised when a business validation fails (e.g. cupo <= 0).
    Maps to HTTP 422 in the router.
    """
    pass


# ---------------------------------------------------------------------------
# EvaluacionService
# ---------------------------------------------------------------------------

class EvaluacionService:
    """
    Service for evaluaciones-y-coloquios operations.

    Identity/tenant ALWAYS from current_user (JWT) — never from request body.
    Delegates all DB operations to repositories.
    """

    def __init__(
        self,
        evaluacion_repo: EvaluacionRepository,
        turno_repo: TurnoEvaluacionRepository,
        candidato_repo: CandidatoEvaluacionRepository,
        reserva_repo: ReservaEvaluacionRepository,
        resultado_repo: ResultadoEvaluacionRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._ev_repo = evaluacion_repo
        self._turno_repo = turno_repo
        self._cand_repo = candidato_repo
        self._res_repo = reserva_repo
        self._result_repo = resultado_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # 3.1 crear_convocatoria
    # -----------------------------------------------------------------------

    async def crear_convocatoria(
        self,
        req: CrearConvocatoriaRequest,
        current_user: CurrentUser,
    ) -> ConvocatoriaConTurnosRead:
        """
        Crea una Evaluacion con sus TurnoEvaluacion.

        Validates cupo_total > 0 for each turn.
        Tenant and identity from current_user — never from body.
        Audits with COLOQUIO_GESTIONAR.
        """
        # Validate cupos
        for turno_req in req.turnos:
            if turno_req.cupo_total <= 0:
                raise EvaluacionValidationError(
                    f"cupo_total debe ser > 0; se recibió {turno_req.cupo_total}"
                )

        # Create evaluacion
        ev = Evaluacion(
            materia_id=req.materia_id,
            cohorte_id=req.cohorte_id,
            tipo=req.tipo,
            instancia=req.instancia,
            dias_disponibles=req.dias_disponibles,
            cerrada=False,
        )
        ev = await self._ev_repo.add(ev)

        # Create turnos
        turnos = await self._turno_repo.bulk_add([
            TurnoEvaluacion(
                evaluacion_id=ev.id,
                fecha=t.fecha,
                cupo_total=t.cupo_total,
                franja=t.franja,
            )
            for t in req.turnos
        ])

        await self._emit_audit(
            actor=current_user,
            registros_afectados=1 + len(turnos),
            after={
                "evaluacion_id": str(ev.id),
                "instancia": req.instancia,
                "turnos": len(turnos),
            },
        )

        return ConvocatoriaConTurnosRead(
            evaluacion=ConvocatoriaRead.model_validate(ev),
            turnos=[TurnoRead.model_validate(t) for t in turnos],
        )

    # -----------------------------------------------------------------------
    # 3.2 importar_candidatos
    # -----------------------------------------------------------------------

    async def importar_candidatos(
        self,
        req: ImportarCandidatosRequest,
        current_user: CurrentUser,
    ) -> None:
        """
        Import a list of alumnos as candidates for a convocatoria.

        Idempotent: re-importing an existing candidate is a no-op.
        Audits with COLOQUIO_GESTIONAR.
        """
        ev = await self._ev_repo.get_by_id(req.evaluacion_id)
        if ev is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convocatoria no encontrada")

        await self._cand_repo.import_idempotente(req.evaluacion_id, req.alumno_ids)

        await self._emit_audit(
            actor=current_user,
            registros_afectados=len(req.alumno_ids),
            after={
                "evaluacion_id": str(req.evaluacion_id),
                "alumnos_importados": len(req.alumno_ids),
            },
        )

    # -----------------------------------------------------------------------
    # 3.3 cerrar_convocatoria
    # -----------------------------------------------------------------------

    async def cerrar_convocatoria(
        self,
        evaluacion_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> ConvocatoriaRead:
        """
        Close a convocatoria (cerrada=True). No new reservations accepted.

        Preserves existing reservations and results.
        Audits with COLOQUIO_GESTIONAR.
        """
        ev = await self._ev_repo.get_by_id(evaluacion_id)
        if ev is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convocatoria no encontrada")

        ev.cerrada = True
        await self._ev_repo._session.commit()
        await self._ev_repo._session.refresh(ev)

        await self._emit_audit(
            actor=current_user,
            registros_afectados=1,
            after={"evaluacion_id": str(evaluacion_id), "cerrada": True},
        )

        return ConvocatoriaRead.model_validate(ev)

    # -----------------------------------------------------------------------
    # 3.4 crear_reserva
    # -----------------------------------------------------------------------

    async def crear_reserva(
        self,
        req: ReservaRequest,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> ReservaRead:
        """
        Reserve a turn for the authenticated ALUMNO.

        Rules enforced:
            D5 — alumno must be an active candidate (gating).
            D3 — SELECT FOR UPDATE on the turno (anti-overbooking lock).
            D2 — cupo check: reservas_activas < cupo_total.
            D4 — only one active reservation per (alumno, convocatoria).
            D7 — closed convocatoria rejects new reservations.

        Identity of the alumno ALWAYS from current_user.JWT — never from body.
        domain_user_id (usuario.id) resolved in the router via resolve_domain_user_id.
        Raises HTTPException 403 (not candidate), 409 (cupo, duplicate, closed).
        """
        # Load and validate evaluacion
        ev = await self._ev_repo.get_by_id(req.evaluacion_id)
        if ev is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convocatoria no encontrada")

        if ev.cerrada:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La convocatoria está cerrada y no acepta nuevas reservas.",
            )

        # D5 — candidate gating (domain_user_id = usuario.id, FK en candidato_evaluacion)
        if not await self._cand_repo.is_candidato(req.evaluacion_id, domain_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El alumno no es candidato habilitado en esta convocatoria.",
            )

        # D4 — one active reservation per convocatoria (domain_user_id = usuario.id)
        count_existing = await self._res_repo.count_activas_por_alumno_convocatoria(
            domain_user_id, req.evaluacion_id
        )
        if count_existing > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El alumno ya tiene una reserva activa en esta convocatoria.",
            )

        # D3 — lock turno + count
        turno = await self._turno_repo.get_for_update(req.turno_id)
        if turno is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

        activas = await self._turno_repo.count_reservas_activas(req.turno_id)
        if activas >= turno.cupo_total:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El turno está lleno (sin cupos disponibles).",
            )

        # Create reservation (domain_user_id = usuario.id, FK en reserva_evaluacion.alumno_id)
        reserva = ReservaEvaluacion(
            turno_id=req.turno_id,
            evaluacion_id=req.evaluacion_id,
            alumno_id=domain_user_id,
            estado=ReservaEstado.Activa,
        )
        reserva = await self._res_repo.add(reserva)

        await self._emit_audit(
            actor=current_user,
            registros_afectados=1,
            after={
                "reserva_id": str(reserva.id),
                "turno_id": str(req.turno_id),
                "evaluacion_id": str(req.evaluacion_id),
            },
        )

        return ReservaRead.model_validate(reserva)

    # -----------------------------------------------------------------------
    # 3.5 cancelar_reserva
    # -----------------------------------------------------------------------

    async def cancelar_reserva(
        self,
        reserva_id: uuid.UUID,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> ReservaRead:
        """
        Cancel the own reservation (liberates cupo).

        Only the owning alumno (from session) can cancel.
        Cancelling sets estado=Cancelada (cupo is recalculated dynamically — D2).
        domain_user_id (usuario.id) resolved in the router via resolve_domain_user_id.
        Raises 403/404 if reservation not found or belongs to another alumno.
        """
        reserva = await self._res_repo.get_by_id(reserva_id)
        if reserva is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")

        # ownership check: reserva.alumno_id is usuario.id (domain FK)
        if reserva.alumno_id != domain_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede cancelar la reserva de otro alumno.",
            )

        await self._res_repo.cancelar(reserva)

        await self._emit_audit(
            actor=current_user,
            registros_afectados=1,
            after={"reserva_id": str(reserva_id), "estado": "Cancelada"},
        )

        return ReservaRead.model_validate(reserva)

    # -----------------------------------------------------------------------
    # 3.6 metricas, agenda, registro_academico, registrar_resultado
    # -----------------------------------------------------------------------

    async def metricas(self, current_user: CurrentUser) -> MetricasRead:
        """
        Panel de métricas globales del módulo (F7.1).

        Derived at query time, scoped to tenant.
        """
        from sqlalchemy import func, select
        from app.models.evaluacion import (
            CandidatoEvaluacion, Evaluacion as EvModel,
            ReservaEvaluacion as ResModel, ReservaEstado as ResEst,
            ResultadoEvaluacion,
        )

        session = self._ev_repo._session
        tid = self._ev_repo._tenant_id

        # convocatorias_activas
        stmt_activas = (
            select(func.count(EvModel.id))
            .where(
                EvModel.tenant_id == tid,
                EvModel.cerrada.is_(False),
                EvModel.deleted_at.is_(None),
            )
        )
        convocatorias_activas = (await session.execute(stmt_activas)).scalar() or 0

        # alumnos_cargados (distinct)
        stmt_cargados = (
            select(func.count(CandidatoEvaluacion.alumno_id.distinct()))
            .where(
                CandidatoEvaluacion.tenant_id == tid,
                CandidatoEvaluacion.deleted_at.is_(None),
            )
        )
        alumnos_cargados = (await session.execute(stmt_cargados)).scalar() or 0

        # reservas_activas
        stmt_res = (
            select(func.count(ResModel.id))
            .where(
                ResModel.tenant_id == tid,
                ResModel.estado == ResEst.Activa,
                ResModel.deleted_at.is_(None),
            )
        )
        reservas_activas = (await session.execute(stmt_res)).scalar() or 0

        # notas_registradas
        stmt_notas = (
            select(func.count(ResultadoEvaluacion.id))
            .where(
                ResultadoEvaluacion.tenant_id == tid,
                ResultadoEvaluacion.deleted_at.is_(None),
            )
        )
        notas_registradas = (await session.execute(stmt_notas)).scalar() or 0

        return MetricasRead(
            convocatorias_activas=convocatorias_activas,
            alumnos_cargados=alumnos_cargados,
            reservas_activas=reservas_activas,
            notas_registradas=notas_registradas,
        )

    async def listar_con_metricas(self) -> List[ConvocatoriaMetricasRead]:
        """List all evaluaciones with derived metrics per convocatoria."""
        rows = await self._ev_repo.listar_con_metricas()
        return [
            ConvocatoriaMetricasRead(
                id=row["id"],
                materia_id=row["evaluacion"].materia_id,
                cohorte_id=row["evaluacion"].cohorte_id,
                tipo=row["evaluacion"].tipo,
                instancia=row["evaluacion"].instancia,
                cerrada=row["evaluacion"].cerrada,
                convocados=row["convocados"],
                reservas_activas=row["reservas_activas"],
                cupos_libres=row["cupos_libres"],
            )
            for row in rows
        ]

    async def agenda(
        self,
        materia_id: Optional[uuid.UUID] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ) -> List[AgendaItemRead]:
        """
        Consolidated agenda of active reservations (F7.5).

        Filters: materia_id, date range.
        Only Activa reservations appear in the agenda.
        """
        from sqlalchemy import select
        from app.models.evaluacion import (
            Evaluacion as EvModel,
            ReservaEvaluacion as ResModel,
            ReservaEstado as ResEst,
            TurnoEvaluacion as TurnoModel,
        )

        session = self._ev_repo._session
        tid = self._ev_repo._tenant_id

        stmt = (
            select(ResModel, TurnoModel.fecha)
            .join(TurnoModel, TurnoModel.id == ResModel.turno_id)
            .join(EvModel, EvModel.id == ResModel.evaluacion_id)
            .where(
                ResModel.tenant_id == tid,
                ResModel.estado == ResEst.Activa,
                ResModel.deleted_at.is_(None),
                TurnoModel.deleted_at.is_(None),
                EvModel.deleted_at.is_(None),
            )
        )
        if materia_id is not None:
            stmt = stmt.where(EvModel.materia_id == materia_id)
        if fecha_desde is not None:
            stmt = stmt.where(TurnoModel.fecha >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(TurnoModel.fecha <= fecha_hasta)

        result = await session.execute(stmt)
        rows = result.all()

        return [
            AgendaItemRead(
                reserva_id=row[0].id,
                evaluacion_id=row[0].evaluacion_id,
                turno_id=row[0].turno_id,
                fecha_turno=row[1],
                alumno_id=row[0].alumno_id,
                estado=row[0].estado,
            )
            for row in rows
        ]

    async def registro_academico(
        self, evaluacion_id: uuid.UUID
    ) -> List[ResultadoRead]:
        """List all results for an evaluacion (academic register)."""
        resultados = await self._result_repo.list_by_evaluacion(evaluacion_id)
        return [ResultadoRead.model_validate(r) for r in resultados]

    async def registrar_resultado(
        self,
        req: ResultadoRequest,
        current_user: CurrentUser,
    ) -> ResultadoRead:
        """Upsert nota_final for (evaluacion_id, alumno_id). Audits."""
        ev = await self._ev_repo.get_by_id(req.evaluacion_id)
        if ev is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Convocatoria no encontrada")

        resultado = await self._result_repo.upsert(
            req.evaluacion_id, req.alumno_id, req.nota_final
        )

        await self._emit_audit(
            actor=current_user,
            registros_afectados=1,
            after={
                "evaluacion_id": str(req.evaluacion_id),
                "alumno_id": str(req.alumno_id),
            },
        )

        return ResultadoRead.model_validate(resultado)

    async def get_resultado_alumno(
        self,
        evaluacion_id: uuid.UUID,
        current_user: CurrentUser,
        domain_user_id: uuid.UUID,
    ) -> ResultadoRead:
        """Return own result (alumno reads only their own nota_final).

        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        resultado = await self._result_repo.get_by_alumno(evaluacion_id, domain_user_id)
        if resultado is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resultado no encontrado")
        return ResultadoRead.model_validate(resultado)

    # -----------------------------------------------------------------------
    # 3.7 listar_mis_convocatorias (HU-47 — ALUMNO)
    # -----------------------------------------------------------------------

    async def listar_mis_convocatorias(
        self,
        domain_user_id: uuid.UUID,
    ) -> List[ConvocatoriasAlumnoRead]:
        """
        Lista las convocatorias donde el alumno autenticado es candidato.

        Solo convocatorias no cerradas. Incluye los turnos con cupos derivados.
        domain_user_id = usuario.id (resuelto en el router con resolve_domain_user_id).
        Queries delegadas al repository (regla arquitectura).
        """
        rows = await self._cand_repo.listar_convocatorias_del_alumno(domain_user_id)
        return rows

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

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
            action=AuditAction.COLOQUIO_GESTIONAR,
            modulo="coloquios",
            entidad_tipo="Evaluacion",
            resultado=AuditResultado.ok,
            registros_afectados=registros_afectados,
            after=after,
        )
