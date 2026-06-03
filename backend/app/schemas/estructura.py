"""
Schemas Pydantic v2 para C-06 estructura académica.

D11: *Create, *Update (PATCH parcial), *Read para Carrera, Cohorte, Materia.
Todos con model_config = ConfigDict(extra='forbid').

CohorteCreate: carrera_id obligatorio, anio int NOT NULL, vig_desde date NOT NULL,
               vig_hasta date nullable (None = cohorte abierta).

Los *Read exponen id, estado, timestamps; nunca exponen tenant_id como editable.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.estructura import EstadoEstructura


# ---------------------------------------------------------------------------
# Carrera schemas
# ---------------------------------------------------------------------------

class CarreraCreate(BaseModel):
    """Campos para crear una carrera. tenant_id se deriva del JWT, nunca del body."""
    model_config = ConfigDict(extra="forbid")

    codigo: str
    nombre: str


class CarreraUpdate(BaseModel):
    """PATCH parcial de carrera — todos los campos son opcionales."""
    model_config = ConfigDict(extra="forbid")

    codigo: Optional[str] = None
    nombre: Optional[str] = None
    estado: Optional[EstadoEstructura] = None


class CarreraRead(BaseModel):
    """Output schema de una carrera. from_attributes=True para .model_validate(orm_obj)."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str
    estado: EstadoEstructura
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Materia schemas
# ---------------------------------------------------------------------------

class MateriaCreate(BaseModel):
    """Campos para crear una materia. tenant_id se deriva del JWT, nunca del body."""
    model_config = ConfigDict(extra="forbid")

    codigo: str
    nombre: str


class MateriaUpdate(BaseModel):
    """PATCH parcial de materia — todos los campos son opcionales."""
    model_config = ConfigDict(extra="forbid")

    codigo: Optional[str] = None
    nombre: Optional[str] = None
    estado: Optional[EstadoEstructura] = None


class MateriaRead(BaseModel):
    """Output schema de una materia."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    codigo: str
    nombre: str
    estado: EstadoEstructura
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Cohorte schemas (D11)
# ---------------------------------------------------------------------------

class CohorteCreate(BaseModel):
    """
    Campos para crear una cohorte.

    carrera_id obligatorio (PA-07).
    anio int NOT NULL.
    vig_desde date NOT NULL.
    vig_hasta date nullable — None = cohorte abierta.
    tenant_id se deriva del JWT, nunca del body.
    """
    model_config = ConfigDict(extra="forbid")

    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: Optional[date] = None


class CohorteUpdate(BaseModel):
    """PATCH parcial de cohorte — todos los campos son opcionales."""
    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = None
    anio: Optional[int] = None
    vig_desde: Optional[date] = None
    vig_hasta: Optional[date] = None
    estado: Optional[EstadoEstructura] = None


class CohorteRead(BaseModel):
    """Output schema de una cohorte."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    carrera_id: uuid.UUID
    nombre: str
    anio: int
    vig_desde: date
    vig_hasta: Optional[date]
    estado: EstadoEstructura
    created_at: datetime
    updated_at: datetime
