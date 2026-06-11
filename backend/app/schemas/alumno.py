"""
Schemas Pydantic v2 para C-25 alumno-portal.

D1 — Identidad del alumno siempre desde el JWT (CurrentUser.user_id).
D3 — avance_pct se deriva en tiempo real, no se persiste.
D4 — estado_entrega: aprobada / con_nota / sin_entrega (derivado de Calificacion).
D5 — Un solo endpoint agregador: GET /alumno/estado-academico.
D6 — AlumnoRepository dedicado; no reutiliza TenantScopedRepository.

EstadoEntregaAlumno — enum derivado al calcular el estado de cada actividad.
CalificacionAlumnoRead — detalle de una actividad con su estado de entrega.
MateriaCursadaRead — resumen de una materia con lista de calificaciones.
ColoquioReservadoRead — turno de coloquio reservado activo.
EstadoAcademicoRead — respuesta raíz: avance global + materias + coloquios.

Todos con extra='forbid'; from_attributes=True para ORM mapping.
snake_case; ≤500 LOC.
"""
import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# EstadoEntregaAlumno
# ---------------------------------------------------------------------------

class EstadoEntregaAlumno(str, enum.Enum):
    aprobada = "aprobada"
    con_nota = "con_nota"
    sin_entrega = "sin_entrega"


# ---------------------------------------------------------------------------
# CalificacionAlumnoRead
# ---------------------------------------------------------------------------

class CalificacionAlumnoRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    actividad: str
    nota_numerica: Optional[Decimal] = None
    nota_textual: Optional[str] = None
    aprobado: bool
    estado_entrega: EstadoEntregaAlumno


# ---------------------------------------------------------------------------
# MateriaCursadaRead
# ---------------------------------------------------------------------------

class MateriaCursadaRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    materia_id: uuid.UUID
    materia_nombre: str
    avance_pct: int
    total_actividades: int
    aprobadas: int
    calificaciones: List[CalificacionAlumnoRead] = []


# ---------------------------------------------------------------------------
# ColoquioReservadoRead
# ---------------------------------------------------------------------------

class ColoquioReservadoRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    evaluacion_id: uuid.UUID
    materia_nombre: str
    instancia: str
    tipo: str
    fecha: date
    franja: Optional[str] = None


# ---------------------------------------------------------------------------
# EstadoAcademicoRead
# ---------------------------------------------------------------------------

class EstadoAcademicoRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    avance_global_pct: int
    total_actividades: int
    aprobadas: int
    materias: List[MateriaCursadaRead] = []
    coloquios_reservados: List[ColoquioReservadoRead] = []
