"""
Schemas Pydantic v2 para C-13 encuentros-y-guardias — guardias.

Design decisions:
    D1  — ConfigDict(extra='forbid') en todos.
    D2  — asignacion_id y tenant_id NUNCA aceptados en request schemas
          (regla dura #8/#14 — identidad desde el JWT).
    D3  — from_attributes=True en Read schemas.

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.encuentro import DiaSemana, GuardiaEstado


# ---------------------------------------------------------------------------
# RegistrarGuardiaRequest — POST /guardias
# ---------------------------------------------------------------------------

class RegistrarGuardiaRequest(BaseModel):
    """
    Payload para registrar una guardia de atención.

    asignacion_id y tenant_id NO aceptados — se resuelven desde el JWT
    (current_user + materia/carrera/cohorte).
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    dia: DiaSemana
    horario: str
    estado: GuardiaEstado = GuardiaEstado.Pendiente
    comentarios: str = ""


# ---------------------------------------------------------------------------
# GuardiaRead — respuesta de lectura de guardia
# ---------------------------------------------------------------------------

class GuardiaRead(BaseModel):
    """Respuesta de lectura de guardia. Sin tenant_id."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    asignacion_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    dia: DiaSemana
    horario: str
    estado: GuardiaEstado
    comentarios: str
    creada_at: datetime


# ---------------------------------------------------------------------------
# GuardiaFiltros — query params para GET /guardias
# ---------------------------------------------------------------------------

class GuardiaFiltros(BaseModel):
    """Filtros de consulta de guardias. Todos opcionales."""
    model_config = ConfigDict(extra="forbid")

    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    dia: Optional[DiaSemana] = None
    estado: Optional[GuardiaEstado] = None
