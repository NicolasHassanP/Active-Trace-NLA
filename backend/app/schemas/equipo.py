"""
Schemas Pydantic v2 para C-08 equipos-docentes.

El equipo docente es una proyección derivada de las Asignacion existentes (C-07)
que comparten la tripleta (materia_id, carrera_id, cohorte_id). No hay tabla nueva.

Design decisions:
    D10 — Todos con ConfigDict(extra='forbid').
    D2  — tenant_id NUNCA en schemas de request/response.
    D5  — usuario_ids en masiva forzados al tenant del actor (service layer).
    D8  — CSV export no incluye PII cifrada.

Schemas:
    TripleteEquipo      — mixin de tripleta de contexto (materia, carrera, cohorte).
    AsignacionMasivaRequest  — POST /asignacion-masiva
    ClonarEquipoRequest      — POST /clonar
    VigenciaGeneralRequest   — PATCH /vigencia-general
    EquipoQuery              — GET /equipos (filtros opcionales)
    MisEquiposItem           — ítem de GET /mis-equipos
    ResumenLote              — respuesta de asignacion-masiva
    ResumenClonacion         — respuesta de clonar

snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.usuario import RolAsignacion
from app.models.vigencia import EstadoVigencia


# ---------------------------------------------------------------------------
# TripleteEquipo — mixin de validación compartida de tripleta
# ---------------------------------------------------------------------------

class TripleteEquipo(BaseModel):
    """
    Tripleta de contexto que identifica un equipo docente.
    Los tres campos son obligatorios para identificar el equipo.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID


# ---------------------------------------------------------------------------
# AsignacionMasivaRequest — POST /api/v1/equipos/asignacion-masiva
# ---------------------------------------------------------------------------

class AsignacionMasivaRequest(BaseModel):
    """
    Payload para asignación masiva de usuarios a un equipo docente.

    usuario_ids: lista de UUIDs de usuarios del mismo tenant — no puede estar vacía.
    materia_id, carrera_id, cohorte_id: tripleta de contexto del equipo.
    rol: rol asignado a todos los usuarios del lote.
    desde: fecha de inicio de la asignación.
    hasta: fecha de fin opcional (abierta si None).
    comisiones: lista de comisiones/grupos (opcional).
    responsable_id: UUID del responsable del lote (opcional, mismo tenant).

    tenant_id NUNCA en el body — se fuerza desde el JWT (regla dura #8).
    """
    model_config = ConfigDict(extra="forbid")

    usuario_ids: List[uuid.UUID]
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    rol: RolAsignacion
    desde: date
    hasta: Optional[date] = None
    comisiones: List[str] = []
    responsable_id: Optional[uuid.UUID] = None

    @field_validator("usuario_ids")
    @classmethod
    def usuario_ids_no_vacia(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if not v:
            raise ValueError("usuario_ids no puede estar vacía")
        return v

    @model_validator(mode="after")
    def hasta_no_anterior_a_desde(self) -> "AsignacionMasivaRequest":
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("hasta no puede ser anterior a desde")
        return self


# ---------------------------------------------------------------------------
# ClonarEquipoRequest — POST /api/v1/equipos/clonar
# ---------------------------------------------------------------------------

class ClonarEquipoRequest(BaseModel):
    """
    Payload para clonar un equipo de una tripleta origen a una tripleta destino.

    La clonación es no-destructiva: copia las asignaciones vigentes del origen
    al destino con las fechas del destino. Duplicados se omiten (skip).

    origen_*: tripleta del equipo fuente.
    destino_*: tripleta del equipo de destino.
    desde: fecha de inicio de las asignaciones clonadas.
    hasta: fecha de fin opcional.
    """
    model_config = ConfigDict(extra="forbid")

    origen_materia_id: uuid.UUID
    origen_carrera_id: uuid.UUID
    origen_cohorte_id: uuid.UUID
    destino_materia_id: uuid.UUID
    destino_carrera_id: uuid.UUID
    destino_cohorte_id: uuid.UUID
    desde: date
    hasta: Optional[date] = None

    @model_validator(mode="after")
    def hasta_no_anterior_a_desde(self) -> "ClonarEquipoRequest":
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("hasta no puede ser anterior a desde")
        return self


# ---------------------------------------------------------------------------
# VigenciaGeneralRequest — PATCH /api/v1/equipos/vigencia-general
# ---------------------------------------------------------------------------

class VigenciaGeneralRequest(BaseModel):
    """
    Payload para modificar la vigencia de todas las asignaciones de un equipo.

    Actualiza desde/hasta de todas las asignaciones activas de la tripleta.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    desde: date
    hasta: Optional[date] = None

    @model_validator(mode="after")
    def hasta_no_anterior_a_desde(self) -> "VigenciaGeneralRequest":
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("hasta no puede ser anterior a desde")
        return self


# ---------------------------------------------------------------------------
# EquipoQuery — GET /api/v1/equipos (filtros opcionales sobre tripleta)
# ---------------------------------------------------------------------------

class EquipoQuery(BaseModel):
    """
    Parámetros de consulta de un equipo docente.

    Tripleta obligatoria + filtros opcionales de rol y responsable.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    rol: Optional[RolAsignacion] = None
    responsable_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# MisEquiposItem — ítem de respuesta de GET /api/v1/equipos/mis-equipos
# ---------------------------------------------------------------------------

class MisEquiposItem(BaseModel):
    """
    Resumen de un equipo al que pertenece el usuario autenticado.

    Incluye la tripleta de contexto, el rol asignado y el estado de vigencia.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    asignacion_id: uuid.UUID
    materia_id: Optional[uuid.UUID]
    carrera_id: Optional[uuid.UUID]
    cohorte_id: Optional[uuid.UUID]
    rol: RolAsignacion
    desde: date
    hasta: Optional[date]
    estado_vigencia: EstadoVigencia
    comisiones: List[str] = []
    responsable_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# ResumenLote — respuesta de POST /api/v1/equipos/asignacion-masiva
# ---------------------------------------------------------------------------

class ResumenLote(BaseModel):
    """
    Resumen del resultado de una asignación masiva.

    creadas: número de asignaciones creadas exitosamente.
    """
    model_config = ConfigDict(extra="forbid")

    creadas: int


# ---------------------------------------------------------------------------
# ResumenClonacion — respuesta de POST /api/v1/equipos/clonar
# ---------------------------------------------------------------------------

class ResumenClonacion(BaseModel):
    """
    Resumen del resultado de una clonación de equipo.

    clonadas: número de asignaciones copiadas al equipo destino.
    omitidas: número de asignaciones omitidas por ya existir en destino.
    """
    model_config = ConfigDict(extra="forbid")

    clonadas: int
    omitidas: int
