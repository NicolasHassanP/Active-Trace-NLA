"""
Schemas Pydantic v2 para C-07 usuarios y asignaciones.

D10, OQ-3:
    - UsuarioCreate/Update/Read
    - AsignacionCreate/Update/Read
    - UsuarioAsignableRead: schema read-only para combobox de búsqueda (equipos:asignar).

Todos con model_config = ConfigDict(extra='forbid').
*Read con from_attributes=True.

Contrato de UsuarioRead (OQ-3 RESUELTA):
    Expone EXACTAMENTE: id, email, nombre, apellidos, legajo, estado,
    asignaciones (resumen), created_at, updated_at.
    NUNCA: dni, cuil, cbu, alias_cbu en texto plano; NUNCA tenant_id ni ciphertext crudo.

Contrato de UsuarioAsignableRead:
    Expone SOLO campos no-PII: id, nombre, apellidos, email, legajo.
    NUNCA: dni, cuil, cbu, alias_cbu, tenant_id, ciphertext crudo.

AsignacionRead incluye estado_vigencia computado (D4).

snake_case; ≤500 LOC; extra='forbid' en todos los schemas.
"""
import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.usuario import RolAsignacion, UsuarioEstado
from app.models.vigencia import EstadoVigencia


# ---------------------------------------------------------------------------
# UsuarioAsignableRead — schema read-only para combobox de búsqueda
# Gateado a equipos:asignar (COORDINADOR, ADMIN).
# Solo campos no-PII: NUNCA dni/cuil/cbu/alias_cbu/tenant_id.
# ---------------------------------------------------------------------------

class UsuarioAsignableRead(BaseModel):
    """
    Proyección mínima de Usuario para el combobox de búsqueda de asignaciones.

    Devuelve SOLO campos no-PII: id, nombre, apellidos, email, legajo.
    Nunca expone: dni, cuil, cbu, alias_cbu, tenant_id, email_hash, ciphertext.
    from_attributes=True para serializar desde ORM model directamente.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    nombre: str
    apellidos: str
    email: str
    legajo: Optional[str] = None


# ---------------------------------------------------------------------------
# AsignacionResumen — sub-schema para UsuarioRead (resumen de asignaciones)
# ---------------------------------------------------------------------------

class AsignacionResumen(BaseModel):
    """
    Resumen de una asignación para el read de usuario.
    Solo campos no-PII públicos.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    rol: RolAsignacion
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    desde: date
    hasta: Optional[date] = None
    estado_vigencia: Optional[EstadoVigencia] = None


# ---------------------------------------------------------------------------
# Usuario schemas
# ---------------------------------------------------------------------------

class UsuarioCreate(BaseModel):
    """
    Campos para crear un usuario. tenant_id se deriva del JWT, nunca del body.
    email_hash se computa en el service — el cliente no lo envía.

    PII financiera (cbu, alias_cbu, cuil, dni) es opcional en la creación.
    """
    model_config = ConfigDict(extra="forbid")

    email: str
    nombre: str
    apellidos: str
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    facturador: bool = False
    estado: UsuarioEstado = UsuarioEstado.activo
    # PII financiera — opcional en creación
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    # auth_identity_id — opcional (D9, sin backfill en C-07)
    auth_identity_id: Optional[uuid.UUID] = None

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("email no puede estar vacío")
        return v.strip().lower()


class UsuarioUpdate(BaseModel):
    """PATCH parcial de usuario — todos los campos son opcionales."""
    model_config = ConfigDict(extra="forbid")

    email: Optional[str] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    facturador: Optional[bool] = None
    estado: Optional[UsuarioEstado] = None
    # PII financiera — opcional
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    auth_identity_id: Optional[uuid.UUID] = None


class UsuarioRead(BaseModel):
    """
    Output schema de un usuario. Contrato de exposición OQ-3:
        - Expone: id, email, nombre, apellidos, legajo, estado, asignaciones, timestamps.
        - NUNCA expone: dni, cuil, cbu, alias_cbu en texto plano.
        - NUNCA expone: tenant_id, ciphertext crudo.

    email se serializa desde email_encrypted (el service/endpoint lo pasa como 'email').
    """
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: uuid.UUID
    email: str  # plaintext — el ADMIN lo necesita para gestión/contacto
    nombre: str
    apellidos: str
    legajo: Optional[str] = None
    estado: UsuarioEstado
    asignaciones: List[AsignacionResumen] = []
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Asignacion schemas
# ---------------------------------------------------------------------------

class AsignacionCreate(BaseModel):
    """
    Campos para crear una asignación.
    usuario_id, rol, desde: obligatorios.
    contexto (materia_id/carrera_id/cohorte_id) y hasta: opcionales.
    tenant_id se deriva del JWT, nunca del body.
    """
    model_config = ConfigDict(extra="forbid")

    usuario_id: uuid.UUID
    rol: RolAsignacion
    desde: date
    hasta: Optional[date] = None
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comisiones: List[str] = []
    responsable_id: Optional[uuid.UUID] = None


class AsignacionUpdate(BaseModel):
    """PATCH parcial de asignación — todos los campos son opcionales."""
    model_config = ConfigDict(extra="forbid")

    rol: Optional[RolAsignacion] = None
    desde: Optional[date] = None
    hasta: Optional[date] = None
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comisiones: Optional[List[str]] = None
    responsable_id: Optional[uuid.UUID] = None


class AsignacionRead(BaseModel):
    """
    Output schema de una asignación.
    Incluye estado_vigencia computado (D4).
    Incluye usuario_nombre / usuario_apellidos para visualización UX (no-PII).
    """
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: uuid.UUID
    usuario_id: uuid.UUID
    usuario_nombre: Optional[str] = None
    usuario_apellidos: Optional[str] = None
    rol: RolAsignacion
    desde: date
    hasta: Optional[date] = None
    materia_id: Optional[uuid.UUID] = None
    carrera_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comisiones: List[str] = []
    responsable_id: Optional[uuid.UUID] = None
    estado_vigencia: EstadoVigencia
    created_at: datetime
    updated_at: datetime
