"""
Schemas Pydantic v2 para C-15 avisos-y-acknowledgment.

Design decisions:
    D8  — ConfigDict(extra='forbid') en todos los request schemas.
    D8  — tenant_id, usuario_id, autor_id NUNCA en request schemas.
    D8  — Coherencia de scope-contexto: materia_id/cohorte_id/rol_destino
          requeridos según alcance; null para Global.
    D8  — Coherencia de ventana: fin_en > inicio_en.
    D4  — ack_count en AvisoRead es DERIVADO (never stored).

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.aviso import AvisoAlcance, AvisoSeveridad


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CrearAvisoRequest(BaseModel):
    """
    Payload para publicar un nuevo Aviso.

    tenant_id y autor/identity del actor SIEMPRE desde el JWT — nunca del body.
    Validaciones de coherencia de scope y ventana de validez integradas.
    """
    model_config = ConfigDict(extra="forbid")

    alcance: AvisoAlcance
    materia_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    rol_destino: Optional[str] = None
    severidad: AvisoSeveridad = AvisoSeveridad.Info
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int = 100
    activo: bool = True
    requiere_ack: bool = False

    @model_validator(mode="after")
    def validate_scope_context(self) -> "CrearAvisoRequest":
        """Validate scope-context coherence (D8)."""
        if self.alcance == AvisoAlcance.PorMateria and self.materia_id is None:
            raise ValueError("materia_id is required when alcance=PorMateria")
        if self.alcance == AvisoAlcance.PorCohorte and self.cohorte_id is None:
            raise ValueError("cohorte_id is required when alcance=PorCohorte")
        if self.alcance == AvisoAlcance.PorRol and self.rol_destino is None:
            raise ValueError("rol_destino is required when alcance=PorRol")
        return self

    @model_validator(mode="after")
    def validate_validity_window(self) -> "CrearAvisoRequest":
        """Validate fin_en > inicio_en (D8, RN-18)."""
        if self.fin_en <= self.inicio_en:
            raise ValueError("fin_en must be strictly after inicio_en")
        return self


class ActualizarAvisoRequest(BaseModel):
    """
    Payload para modificar un Aviso existente.

    Todos los campos son opcionales (partial update).
    Aplica las mismas validaciones de coherencia si se envían campos relevantes.
    """
    model_config = ConfigDict(extra="forbid")

    alcance: Optional[AvisoAlcance] = None
    materia_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    rol_destino: Optional[str] = None
    severidad: Optional[AvisoSeveridad] = None
    titulo: Optional[str] = None
    cuerpo: Optional[str] = None
    inicio_en: Optional[datetime] = None
    fin_en: Optional[datetime] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None
    requiere_ack: Optional[bool] = None


class AckAvisoRequest(BaseModel):
    """
    Payload para confirmar la lectura de un Aviso.

    No acepta campos de identidad (usuario_id, tenant_id) — se resuelven del JWT.
    Body vacío es válido; el aviso_id se provee en la URL.
    """
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AvisoRead(BaseModel):
    """Respuesta de lectura de un Aviso con contador de acks derivado."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    alcance: AvisoAlcance
    materia_id: Optional[uuid.UUID]
    cohorte_id: Optional[uuid.UUID]
    rol_destino: Optional[str]
    severidad: AvisoSeveridad
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: datetime
    orden: int
    activo: bool
    requiere_ack: bool
    ack_count: int = 0  # derived field — computed at query time


class AcknowledgmentRead(BaseModel):
    """Respuesta de lectura de un AcknowledgmentAviso."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    aviso_id: uuid.UUID
    usuario_id: uuid.UUID
    confirmado_at: datetime
