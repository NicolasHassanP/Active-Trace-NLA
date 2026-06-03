"""
Audit schemas — Pydantic v2 contracts for C-05.

D9: All schemas use model_config = ConfigDict(extra='forbid').
    before/after typed as dict[str, Any] | None.

AuditEventRead — output schema for GET /api/v1/auditoria.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from app.models.audit import AuditAction, AuditResultado


class AuditEventRead(BaseModel):
    """
    Output schema for a single audit event.

    extra='forbid' ensures no undeclared fields leak through (D9, Pydantic v2).
    before/after are nullable JSONB payloads (PII already redacted upstream).
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
