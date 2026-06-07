"""
AlumnoService — C-25 alumno-portal.

D1 — Identidad siempre desde CurrentUser (JWT). JAMÁS del body/params.
D3 — avance_pct derivado, no persistido.
D4 — estado_entrega: aprobada / con_nota / sin_entrega derivado de Calificacion.
D5 — Endpoint único agregador.

Funciones puras (sin side-effects — fáciles de testear unitariamente):
    clasificar_estado_entrega(calificacion) → EstadoEntregaAlumno
    calcular_avance(aprobadas, total)       → int (porcentaje, 0 si total=0)

Método principal:
    get_estado_academico(current_user) → EstadoAcademicoRead

Flujo: Router → AlumnoService → AlumnoRepository → models.
Sin lógica de negocio en el router.
snake_case; ≤500 LOC.
"""
import uuid
from decimal import Decimal
from typing import List

from app.core.dependencies import CurrentUser
from app.models.calificacion import Calificacion
from app.repositories.alumno_repository import AlumnoRepository
from app.schemas.alumno import (
    CalificacionAlumnoRead,
    ColoquioReservadoRead,
    EstadoAcademicoRead,
    EstadoEntregaAlumno,
    MateriaCursadaRead,
)


# ---------------------------------------------------------------------------
# Task 3.2 — función pura: clasificar_estado_entrega
# ---------------------------------------------------------------------------

def clasificar_estado_entrega(calificacion: Calificacion) -> EstadoEntregaAlumno:
    """
    Deriva el estado de entrega de una Calificacion.

    aprobada    — aprobado=True
    con_nota    — hay nota pero aprobado=False
    sin_entrega — sin nota en absoluto
    """
    if calificacion.aprobado:
        return EstadoEntregaAlumno.aprobada
    has_nota = (
        calificacion.nota_numerica is not None
        or calificacion.nota_textual is not None
    )
    if has_nota:
        return EstadoEntregaAlumno.con_nota
    return EstadoEntregaAlumno.sin_entrega


# ---------------------------------------------------------------------------
# Task 3.3 — función pura: calcular_avance
# ---------------------------------------------------------------------------

def calcular_avance(aprobadas: int, total: int) -> int:
    """Retorna porcentaje de avance redondeado; 0 si total=0."""
    if total == 0:
        return 0
    return round(aprobadas / total * 100)


# ---------------------------------------------------------------------------
# AlumnoService
# ---------------------------------------------------------------------------

class AlumnoService:
    def __init__(self, repo: AlumnoRepository) -> None:
        self._repo = repo

    # -----------------------------------------------------------------------
    # Task 3.1 / 3.4 — get_estado_academico
    # -----------------------------------------------------------------------

    async def get_estado_academico(self, current_user: CurrentUser, domain_user_id: uuid.UUID | None = None) -> EstadoAcademicoRead:
        """
        Agrega el estado académico completo del alumno autenticado.

        domain_user_id: usuario.id resuelto desde auth_identities.id (JWT sub).
        Identidad SIEMPRE desde current_user (nunca body/params).
        """
        usuario_id: uuid.UUID = domain_user_id or current_user.user_id

        # -- Padrón activo --
        entradas_con_materia = await self._repo.get_entradas_padron_activas(usuario_id)

        # -- Calificaciones --
        entrada_ids = [ep.id for ep, _ in entradas_con_materia]
        calificaciones = await self._repo.get_calificaciones_por_entradas(entrada_ids)

        # Agrupar calificaciones por entrada_padron_id
        cal_por_entrada: dict[uuid.UUID, List[Calificacion]] = {}
        for cal in calificaciones:
            cal_por_entrada.setdefault(cal.entrada_padron_id, []).append(cal)

        # -- Construir materias --
        materias: List[MateriaCursadaRead] = []
        total_global = 0
        aprobadas_global = 0

        for entrada, materia in entradas_con_materia:
            cals = cal_por_entrada.get(entrada.id, [])
            total_mat = len(cals)
            aprobadas_mat = sum(1 for c in cals if c.aprobado)

            total_global += total_mat
            aprobadas_global += aprobadas_mat

            cal_reads = [
                CalificacionAlumnoRead(
                    actividad=c.actividad,
                    nota_numerica=c.nota_numerica,
                    nota_textual=c.nota_textual,
                    aprobado=c.aprobado,
                    estado_entrega=clasificar_estado_entrega(c),
                )
                for c in cals
            ]

            materias.append(
                MateriaCursadaRead(
                    materia_id=materia.id,
                    materia_nombre=materia.nombre,
                    avance_pct=calcular_avance(aprobadas_mat, total_mat),
                    total_actividades=total_mat,
                    aprobadas=aprobadas_mat,
                    calificaciones=cal_reads,
                )
            )

        # -- Reservas activas --
        reservas_rows = await self._repo.get_reservas_activas(usuario_id)
        coloquios: List[ColoquioReservadoRead] = [
            ColoquioReservadoRead(
                evaluacion_id=evaluacion.id,
                materia_nombre=mat.nombre,
                instancia=evaluacion.instancia,
                tipo=evaluacion.tipo.value,
                fecha=turno.fecha,
                franja=turno.franja,
            )
            for _, turno, evaluacion, mat in reservas_rows
        ]

        # Task 3.4 — avance global ponderado (suma plana de actividades)
        return EstadoAcademicoRead(
            avance_global_pct=calcular_avance(aprobadas_global, total_global),
            total_actividades=total_global,
            aprobadas=aprobadas_global,
            materias=materias,
            coloquios_reservados=coloquios,
        )
