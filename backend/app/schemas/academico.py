"""
academico.py — Schemas Pydantic v2 para C-17 programas-y-fechas-academicas.

Schemas:
    ProgramaCreate         — POST /programas
    ProgramaRead           — respuesta con programa completo
    FechaAcademicaCreate   — POST /fechas-academicas
    FechaAcademicaUpdate   — PATCH /fechas-academicas/{id}
    FechaAcademicaRead     — respuesta con fecha completa
    FragmentoLMSResponse   — GET /fechas-academicas/contenido-lms

Design decisions:
    D1  — ConfigDict(extra='forbid') en todos.
    D2  — tenant_id NUNCA aceptado en request schemas (del JWT).
    D3  — referencia_archivo es string no vacío (validación mínima).
    D5  — periodo validado con patrón "AAAA-N" y trim de espacios.
    D5  — numero ≥ 1, titulo no vacío.

snake_case; ≤500 LOC.
"""
import re
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.academico import FechaAcademicaTipo

_PERIODO_PATTERN = re.compile(r"^\d{4}-\d+$")


# ---------------------------------------------------------------------------
# ProgramaCreate — POST /programas
# ---------------------------------------------------------------------------

class ProgramaCreate(BaseModel):
    """
    Payload para registrar un programa de materia.

    tenant_id resuelto desde JWT — no aceptado aquí.
    referencia_archivo: puntero opaco (D3), no puede estar vacío.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: str

    @field_validator("titulo")
    @classmethod
    def titulo_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("titulo no puede estar vacío")
        return v

    @field_validator("referencia_archivo")
    @classmethod
    def referencia_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("referencia_archivo no puede estar vacío (D3)")
        return v


# ---------------------------------------------------------------------------
# ProgramaRead — respuesta GET /programas
# ---------------------------------------------------------------------------

class ProgramaRead(BaseModel):
    """Respuesta de lectura de un programa de materia."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    carrera_id: uuid.UUID
    cohorte_id: uuid.UUID
    titulo: str
    referencia_archivo: str
    cargado_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# FechaAcademicaCreate — POST /fechas-academicas
# ---------------------------------------------------------------------------

class FechaAcademicaCreate(BaseModel):
    """
    Payload para crear una fecha académica.

    tenant_id resuelto desde JWT — no aceptado aquí.
    periodo: patrón "AAAA-N" (trimmed), ejemplo "2026-1".
    numero: ≥ 1.
    titulo: no vacío.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: FechaAcademicaTipo
    numero: int
    periodo: str
    fecha: date
    titulo: str

    @field_validator("numero")
    @classmethod
    def numero_positivo(cls, v: int) -> int:
        if v < 1:
            raise ValueError("numero debe ser ≥ 1")
        return v

    @field_validator("periodo")
    @classmethod
    def periodo_formato(cls, v: str) -> str:
        v = v.strip()
        if not _PERIODO_PATTERN.match(v):
            raise ValueError(
                "periodo debe tener el formato 'AAAA-N' (ej. '2026-1')"
            )
        return v

    @field_validator("titulo")
    @classmethod
    def titulo_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("titulo no puede estar vacío")
        return v


# ---------------------------------------------------------------------------
# FechaAcademicaUpdate — PATCH /fechas-academicas/{id}
# ---------------------------------------------------------------------------

class FechaAcademicaUpdate(BaseModel):
    """
    Payload para editar una fecha académica existente.

    Todos los campos son opcionales — solo se actualiza lo que se envía.
    """
    model_config = ConfigDict(extra="forbid")

    fecha: Optional[date] = None
    titulo: Optional[str] = None

    @field_validator("titulo")
    @classmethod
    def titulo_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("titulo no puede estar vacío")
        return v


# ---------------------------------------------------------------------------
# FechaAcademicaRead — respuesta GET /fechas-academicas
# ---------------------------------------------------------------------------

class FechaAcademicaRead(BaseModel):
    """Respuesta de lectura de una fecha académica."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    tipo: FechaAcademicaTipo
    numero: int
    periodo: str
    fecha: date
    titulo: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# FragmentoLMSResponse — GET .../contenido-lms
# ---------------------------------------------------------------------------

class FragmentoLMSResponse(BaseModel):
    """Respuesta del fragmento HTML para el aula virtual del LMS (F5.4)."""
    model_config = ConfigDict(extra="forbid")

    html: str
