"""
Schemas Pydantic v2 para C-14 evaluaciones-y-coloquios.

Design decisions:
    D1  — ConfigDict(extra='forbid') en todos.
    D2  — tenant_id y alumno_id NUNCA en request schemas (se derivan del JWT).
    D3  — from_attributes=True en Read schemas (mapeo desde ORM).
    D4  — ReservaRequest NO acepta alumno_id (identidad del alumno desde JWT).

snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.evaluacion import EvaluacionTipo, ReservaEstado


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TurnoRequest(BaseModel):
    """Turno para incluir en la creación de una convocatoria."""
    model_config = ConfigDict(extra="forbid")

    fecha: date
    cupo_total: int
    franja: Optional[str] = None

    @field_validator("cupo_total")
    @classmethod
    def cupo_debe_ser_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("cupo_total debe ser mayor a 0")
        return v


class CrearConvocatoriaRequest(BaseModel):
    """
    Payload para crear una Evaluacion + sus TurnoEvaluacion.

    tenant_id y identidad del actor SIEMPRE desde el JWT — nunca del body.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: EvaluacionTipo
    instancia: str
    dias_disponibles: int = 0
    turnos: List[TurnoRequest]


class ImportarCandidatosRequest(BaseModel):
    """Payload para importar el padrón de candidatos a una convocatoria."""
    model_config = ConfigDict(extra="forbid")

    evaluacion_id: uuid.UUID
    alumno_ids: List[uuid.UUID]


class ReservaRequest(BaseModel):
    """
    Payload para que un ALUMNO reserve un turno.

    alumno_id NO se acepta en el body — se resuelve del JWT (regla dura #8).
    """
    model_config = ConfigDict(extra="forbid")

    turno_id: uuid.UUID
    evaluacion_id: uuid.UUID


class ResultadoRequest(BaseModel):
    """Payload para registrar o actualizar una nota final."""
    model_config = ConfigDict(extra="forbid")

    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    nota_final: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TurnoRead(BaseModel):
    """Respuesta de lectura de un TurnoEvaluacion."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    fecha: date
    cupo_total: int
    franja: Optional[str]


class ConvocatoriaRead(BaseModel):
    """Respuesta de lectura de una Evaluacion (convocatoria)."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: EvaluacionTipo
    instancia: str
    dias_disponibles: int
    cerrada: bool


class ConvocatoriaConTurnosRead(BaseModel):
    """Respuesta de creación de convocatoria: evaluacion + turnos."""
    model_config = ConfigDict(extra="forbid")

    evaluacion: ConvocatoriaRead
    turnos: List[TurnoRead]


class ConvocatoriaMetricasRead(BaseModel):
    """Convocatoria con métricas derivadas (F7.4)."""
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: EvaluacionTipo
    instancia: str
    cerrada: bool
    convocados: int
    reservas_activas: int
    cupos_libres: int


class ReservaRead(BaseModel):
    """Respuesta de lectura de una ReservaEvaluacion."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    turno_id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    estado: ReservaEstado


class ResultadoRead(BaseModel):
    """Respuesta de lectura de un ResultadoEvaluacion."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    evaluacion_id: uuid.UUID
    alumno_id: uuid.UUID
    nota_final: Optional[str]


class AgendaItemRead(BaseModel):
    """Item de la agenda consolidada de reservas (F7.5)."""
    model_config = ConfigDict(extra="forbid")

    reserva_id: uuid.UUID
    evaluacion_id: uuid.UUID
    turno_id: uuid.UUID
    fecha_turno: date
    alumno_id: uuid.UUID
    estado: ReservaEstado


class MetricasRead(BaseModel):
    """Panel de métricas globales del módulo coloquios (F7.1)."""
    model_config = ConfigDict(extra="forbid")

    convocatorias_activas: int
    alumnos_cargados: int
    reservas_activas: int
    notas_registradas: int


# ---------------------------------------------------------------------------
# HU-47 — schemas para el ALUMNO (mis convocatorias)
# ---------------------------------------------------------------------------

class TurnoConCupoRead(TurnoRead):
    """TurnoRead extendido con cupos_disponibles derivados (D2 — nunca denormalizados)."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    cupos_disponibles: int


class ConvocatoriasAlumnoRead(BaseModel):
    """
    Convocatoria disponible para el alumno autenticado.

    materia_nombre y tipo vienen del join Evaluacion→Materia.
    turnos incluye cupos_disponibles derivados en query.
    reserva_activa_id: UUID de la ReservaEvaluacion activa del alumno en esta
        convocatoria (None si aún no reservó). Permite al frontend mostrar
        "Cancelar reserva" con el ID correcto (D4 garantiza máximo una activa).
    """
    model_config = ConfigDict(extra="forbid")

    evaluacion_id: uuid.UUID
    materia_nombre: str
    instancia: str
    tipo: EvaluacionTipo
    turnos: List[TurnoConCupoRead]
    reserva_activa_id: Optional[uuid.UUID] = None
