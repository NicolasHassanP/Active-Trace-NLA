"""
auditoria_metricas.py — Output schemas for C-19 audit panel endpoints.

C-19: Design decision D7.
    All schemas use model_config = ConfigDict(extra='forbid', from_attributes=True).
    No PII exposed — only identifiers, action codes, states, dates, and totals.
    UltimaAccionItem reuses the same field shape as AuditEventRead (C-05);
    before/after payloads are already redacted upstream.

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.audit import AuditAction, AuditResultado
from app.models.comunicacion import ComunicacionEstado


# ---------------------------------------------------------------------------
# Metric aggregate items
# ---------------------------------------------------------------------------

class AccionesPorDiaItem(BaseModel):
    """One bucket of the acciones-por-dia time series."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    dia: datetime    # date_trunc('day') result from the DB
    total: int


class InteraccionesDocenteItem(BaseModel):
    """One (actor, accion, total) aggregate row."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    actor_user_id: uuid.UUID
    accion: AuditAction
    total: int
    actor_nombre: Optional[str] = None


class InteraccionesDocenteMateriaItem(BaseModel):
    """
    One (actor, materia_id|None, total) aggregate row.

    materia_id is derived from entidad_id WHERE entidad_tipo='Materia' (D1).
    None means the actor performed actions not linked to any materia.
    actor_nombre: resolved display name for actor_user_id (auth_identity_id join).
    materia_nombre: resolved display name for materia_id.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    actor_user_id: uuid.UUID
    materia_id: Optional[str]   # None = "sin materia" bucket (D1)
    total: int
    actor_nombre: Optional[str] = None
    materia_nombre: Optional[str] = None


class ComunicacionesPorDocenteItem(BaseModel):
    """One (enviado_por, estado, total) row from the comunicacion table."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    enviado_por: Optional[uuid.UUID]   # nullable FK in the model
    estado: ComunicacionEstado
    total: int


# ---------------------------------------------------------------------------
# Response list wrappers
# ---------------------------------------------------------------------------

class AccionesPorDiaResponse(BaseModel):
    """Response payload for GET /auditoria/metricas/acciones-por-dia."""
    model_config = ConfigDict(extra="forbid")

    items: List[AccionesPorDiaItem]


class InteraccionesDocenteResponse(BaseModel):
    """Response payload for GET /auditoria/metricas/interacciones-docente."""
    model_config = ConfigDict(extra="forbid")

    items: List[InteraccionesDocenteItem]


class InteraccionesDocenteMateriaResponse(BaseModel):
    """Response payload for GET /auditoria/metricas/interacciones-docente-materia."""
    model_config = ConfigDict(extra="forbid")

    items: List[InteraccionesDocenteMateriaItem]


class ComunicacionesPorDocenteResponse(BaseModel):
    """Response payload for GET /auditoria/metricas/comunicaciones-por-docente."""
    model_config = ConfigDict(extra="forbid")

    items: List[ComunicacionesPorDocenteItem]


# ---------------------------------------------------------------------------
# Log item — mirrors AuditEventRead (C-05) without modification
# ---------------------------------------------------------------------------

class UltimaAccionItem(BaseModel):
    """
    Single audit event in the panel log.

    Mirrors AuditEventRead (C-05) field-for-field. before/after are already
    redacted of PII upstream (at record time). Reusing this shape means the
    frontend can handle both the paginated list and the panel log uniformly.

    actor_nombre: resolved display name for actor_user_id (auth_identity_id join).
    entidad_nombre: resolved human-readable name for entidad_id (Materia/Carrera/Cohorte).
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID
    impersonated_user_id: Optional[uuid.UUID]
    accion: AuditAction
    modulo: str
    entidad_tipo: str
    entidad_id: Optional[str]
    resultado: AuditResultado
    registros_afectados: Optional[int]
    ip: Optional[str]
    user_agent: Optional[str]
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    created_at: datetime
    actor_nombre: Optional[str] = None
    entidad_nombre: Optional[str] = None
