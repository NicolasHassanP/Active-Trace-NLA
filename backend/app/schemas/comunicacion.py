"""
Schemas Pydantic v2 para el módulo de comunicaciones (C-12).

Design decisions:
    - extra='forbid' en todos los schemas (regla dura #5).
    - Identidad/tenant NUNCA en los request schemas — siempre del JWT.
    - ComunicacionRead: incluye estado, lote_id, enviado_at, error_detalle.
    - EncolarRequest: plantillas + variables_por_destinatario.
    - AprobarCancelarLoteRequest: solo lote_id.
    - AprobarCancelarIndividualRequest: solo comunicacion_id.

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# ComunicacionRead — respuesta de consulta
# ---------------------------------------------------------------------------

class ComunicacionRead(BaseModel):
    """Respuesta al listar o consultar una Comunicacion."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    estado: str
    lote_id: uuid.UUID
    asunto: str
    enviado_at: Optional[datetime] = None
    error_detalle: Optional[str] = None
    enviado_por: Optional[uuid.UUID] = None
    aprobado_por: Optional[uuid.UUID] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# PreviewRequest / PreviewResponse — preview de plantilla sin DB
# ---------------------------------------------------------------------------

class PreviewRequest(BaseModel):
    """Request para preview de una comunicación (sin DB)."""

    model_config = ConfigDict(extra="forbid")

    asunto_plantilla: str
    cuerpo_plantilla: str
    variables: Dict[str, Any] = {}


class PreviewResponse(BaseModel):
    """Response del preview renderizado."""

    model_config = ConfigDict(extra="forbid")

    asunto: str
    cuerpo: str


# ---------------------------------------------------------------------------
# EncolarRequest — request para encolar un lote
# ---------------------------------------------------------------------------

class EncolarRequest(BaseModel):
    """
    Request para encolar un lote de comunicaciones.

    La identidad del remitente (enviado_por, tenant_id) viene del JWT.
    NUNCA incluir en este schema.
    """

    model_config = ConfigDict(extra="forbid")

    destinatarios: List[str]
    asunto_plantilla: str
    cuerpo_plantilla: str
    # Variables por destinatario: dict email → {variable: valor}
    variables_por_destinatario: Dict[str, Dict[str, Any]] = {}


class EncolarResponse(BaseModel):
    """Response del encolado de un lote."""

    model_config = ConfigDict(extra="forbid")

    lote_id: uuid.UUID
    total_encolados: int
    mensajes: List[ComunicacionRead]


# ---------------------------------------------------------------------------
# AprobarCancelarLoteRequest — aprobación/cancelación masiva
# ---------------------------------------------------------------------------

class LoteRequest(BaseModel):
    """Request para operaciones sobre un lote completo."""

    model_config = ConfigDict(extra="forbid")

    lote_id: uuid.UUID


# ---------------------------------------------------------------------------
# IndividualRequest — aprobación/cancelación individual
# ---------------------------------------------------------------------------

class IndividualRequest(BaseModel):
    """Request para operaciones sobre un mensaje individual."""

    model_config = ConfigDict(extra="forbid")

    comunicacion_id: uuid.UUID


# ---------------------------------------------------------------------------
# LoteStatusResponse — estado de un lote
# ---------------------------------------------------------------------------

class LoteStatusResponse(BaseModel):
    """Estado de un lote de comunicaciones."""

    model_config = ConfigDict(extra="forbid")

    lote_id: uuid.UUID
    total: int
    pendientes: int
    enviados: int
    errores: int
    cancelados: int
    mensajes: List[ComunicacionRead]
