"""
Schemas Pydantic v2 para C-09 padrón ingesta.

Todos con model_config = ConfigDict(extra='forbid').
tenant_id NUNCA expuesto como editable en schemas de Request/Response.

PadronRowDTO     — fila parseada del archivo (preview + confirm).
ActivarRequest   — payload de confirmación de importación.
VersionPadronRead — respuesta de versión activa (sin tenant_id).
SyncMoodleRequest — cuerpo del endpoint de sync on-demand.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------------------------------------------------------------------------
# PadronRowDTO — fila del padrón parseada del archivo (D5)
# ---------------------------------------------------------------------------

class PadronRowDTO(BaseModel):
    """
    Fila del padrón parseada de un archivo xlsx o csv.

    Devuelta por el endpoint preview y enviada como payload en el endpoint activar.
    email almacenado en texto plano aquí (se cifra en DB al activar).
    """
    model_config = ConfigDict(extra="forbid")

    nombre: str
    apellidos: str
    email: str
    comision: Optional[str] = None
    regional: Optional[str] = None


# ---------------------------------------------------------------------------
# ActivarRequest — payload del endpoint POST /padron/activar (D5)
# ---------------------------------------------------------------------------

class ActivarRequest(BaseModel):
    """
    Payload de confirmación de importación.

    El cliente envía los datos que recibió del endpoint preview + las referencias
    de materia y cohorte. La identidad del actor viene del JWT (nunca del body).
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    rows: List[PadronRowDTO]


# ---------------------------------------------------------------------------
# VersionPadronRead — respuesta del endpoint (sin tenant_id, D5)
# ---------------------------------------------------------------------------

class VersionPadronRead(BaseModel):
    """
    Representación pública de una versión de padrón.

    Omite tenant_id (no se expone en respuestas) y email_encrypted (PII).
    from_attributes=True para mapeo desde ORM.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    cargado_por: Optional[uuid.UUID]
    cargado_at: datetime
    activa: bool
    filas_total: int = 0  # Calculado fuera del ORM (len(entradas))


# ---------------------------------------------------------------------------
# SyncMoodleRequest — payload del endpoint POST /padron/sync-moodle (D7)
# ---------------------------------------------------------------------------

class SyncMoodleRequest(BaseModel):
    """
    Parámetros para sync on-demand desde Moodle WS.

    course_id: ID del curso en Moodle (core_enrol_get_enrolled_users).
    materia_id, cohorte_id: destino en activia-trace.
    """
    model_config = ConfigDict(extra="forbid")

    course_id: int
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
