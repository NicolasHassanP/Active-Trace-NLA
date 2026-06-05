"""
Schemas Pydantic v2 para C-20 perfil propio.

D1 — Perfil reusa Usuario; schemas independientes de UsuarioRead/UsuarioUpdate.
D2 — cuil NO existe en PerfilUpdate (extra='forbid' lo rechaza automáticamente).
D3 — PerfilRead devuelve PII en claro al propio dueño.

PerfilUpdate:
    Campos editables: nombre, apellidos, dni, genero (nuevo OQ-2), banco,
    cbu, alias_cbu, regional, email, facturador, legajo_profesional.
    NO incluye: cuil (solo lectura), estado, tenant_id, id, legajo.

PerfilRead:
    Incluye cuil como solo lectura.
    Expone PII en claro (al dueño autenticado): dni, cbu, alias_cbu, cuil.

Todos con extra='forbid'.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# PerfilUpdate — PATCH parcial del perfil propio (campos editables)
# ---------------------------------------------------------------------------

class PerfilUpdate(BaseModel):
    """
    PATCH parcial del perfil propio.

    Solo los campos que el usuario puede editar en su propio perfil.
    cuil no está declarado → extra='forbid' lo rechaza con 422.
    tenant_id, estado, id, legajo tampoco están declarados.
    """
    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    # PII cifrada (AES-256 via EncryptedString en el ORM)
    dni: Optional[str] = None
    # genero: columna nueva agregada en migración C-20 (OQ-2)
    genero: Optional[str] = None
    banco: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    regional: Optional[str] = None
    email: Optional[str] = None
    facturador: Optional[bool] = None
    legajo_profesional: Optional[str] = None

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("email no puede estar vacío")
        return v.strip().lower() if v is not None else None


# ---------------------------------------------------------------------------
# PerfilRead — respuesta del GET /perfil (PII en claro al dueño)
# ---------------------------------------------------------------------------

class PerfilRead(BaseModel):
    """
    Output schema del perfil propio.

    Devuelve PII en claro al propio titular (D3):
        dni, cbu, alias_cbu, cuil.

    email se serializa desde email_encrypted (el service lo pasa como 'email').
    cuil es solo lectura — no aparece en PerfilUpdate.
    tenant_id NUNCA se expone.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: uuid.UUID
    email: str
    nombre: str
    apellidos: str
    # PII cifrada en DB — devuelta en claro al titular
    dni: Optional[str] = None
    cuil: Optional[str] = None
    cbu: Optional[str] = None
    alias_cbu: Optional[str] = None
    # Columna nueva C-20 (OQ-2)
    genero: Optional[str] = None
    # Negocio
    legajo: Optional[str] = None
    legajo_profesional: Optional[str] = None
    banco: Optional[str] = None
    regional: Optional[str] = None
    facturador: bool = False
    # Timestamps
    created_at: datetime
    updated_at: datetime
