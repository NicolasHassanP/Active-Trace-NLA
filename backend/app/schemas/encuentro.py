"""
Schemas Pydantic v2 para C-13 encuentros-y-guardias — encuentros.

Design decisions:
    D1  — ConfigDict(extra='forbid') en todos.
    D2  — tenant_id y asignacion_id NUNCA aceptados en request schemas.
    D3  — cant_semanas validado 0..52.
    D4  — from_attributes=True en Read schemas (mapeo desde ORM).

snake_case; ≤500 LOC.
"""
import uuid
from datetime import date, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.encuentro import DiaSemana, InstanciaEncuentroEstado


# ---------------------------------------------------------------------------
# CrearSlotRequest — POST /encuentros/slots
# ---------------------------------------------------------------------------

class CrearSlotRequest(BaseModel):
    """
    Payload para crear un slot de encuentro (recurrente o único).

    Modos excluyentes (RN-13):
        Recurrente: cant_semanas > 0 + dia_semana + fecha_inicio
        Único:      fecha_unica (cant_semanas = 0 o ausente)

    La validación de modo exclusivo se hace en el service layer
    (no aquí para dar error 422 con mensaje claro).

    tenant_id y asignacion_id NO aceptados — se resuelven desde el JWT.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    titulo: str
    hora: time
    dia_semana: Optional[DiaSemana] = None
    fecha_inicio: Optional[date] = None
    cant_semanas: int = 0
    fecha_unica: Optional[date] = None
    meet_url: Optional[str] = None
    vig_desde: Optional[date] = None
    vig_hasta: Optional[date] = None

    @field_validator("cant_semanas")
    @classmethod
    def cant_semanas_rango(cls, v: int) -> int:
        if v < 0 or v > 52:
            raise ValueError("cant_semanas debe estar entre 0 y 52")
        return v


# ---------------------------------------------------------------------------
# EditarInstanciaRequest — PATCH /encuentros/instancias/{id}
# ---------------------------------------------------------------------------

class EditarInstanciaRequest(BaseModel):
    """
    Payload para editar los campos mutables de una instancia de encuentro.

    Solo campos modificables; identidad y tenant desde el JWT.
    Todos opcionales: se patchea solo lo que llega.
    """
    model_config = ConfigDict(extra="forbid")

    estado: Optional[InstanciaEncuentroEstado] = None
    meet_url: Optional[str] = None
    video_url: Optional[str] = None
    comentario: Optional[str] = None


# ---------------------------------------------------------------------------
# InstanciaEncuentroRead — respuesta de instancias
# ---------------------------------------------------------------------------

class InstanciaEncuentroRead(BaseModel):
    """Respuesta de lectura de una instancia de encuentro. Sin tenant_id."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    slot_id: Optional[uuid.UUID]
    materia_id: uuid.UUID
    fecha: date
    hora: time
    titulo: str
    estado: InstanciaEncuentroEstado
    meet_url: Optional[str]
    video_url: Optional[str]
    comentario: str


# ---------------------------------------------------------------------------
# SlotEncuentroRead — respuesta de slot
# ---------------------------------------------------------------------------

class SlotEncuentroRead(BaseModel):
    """Respuesta de lectura de un slot de encuentro. Sin tenant_id."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    materia_id: uuid.UUID
    titulo: str
    hora: time
    dia_semana: Optional[DiaSemana]
    fecha_inicio: Optional[date]
    cant_semanas: int
    fecha_unica: Optional[date]
    meet_url: Optional[str]


# ---------------------------------------------------------------------------
# BloqueHtmlResponse — respuesta de GET /bloque-html
# ---------------------------------------------------------------------------

class BloqueHtmlResponse(BaseModel):
    """Respuesta del endpoint de bloque HTML del aula virtual."""
    model_config = ConfigDict(extra="forbid")

    html: str


# ---------------------------------------------------------------------------
# CrearSlotResponse — respuesta del endpoint POST /slots
# ---------------------------------------------------------------------------

class CrearSlotResponse(BaseModel):
    """Respuesta de creación de slot: slot + instancias generadas."""
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    slot: SlotEncuentroRead
    instancias: list[InstanciaEncuentroRead]
