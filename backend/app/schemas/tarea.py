"""
Schemas Pydantic v2 para C-16 tareas-internas.

Design decisions:
    D6  — ConfigDict(extra='forbid') en todos los request schemas.
    D6  — tenant_id, asignado_por, autor_id NUNCA en request schemas.
    D4  — Coherencia contexto: contexto_id y contexto_tipo ambos null o ambos presentes.
    D2  — estado inicial Pendiente (seteado en el servicio, no en schema).

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.tarea import TareaEstado


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TareaCreate(BaseModel):
    """
    Payload para crear y asignar una nueva Tarea.

    tenant_id, asignado_por, autor_id SIEMPRE desde el JWT — nunca del body.
    asignado_a SÍ va en el body (el docente que resuelve, no el actor).
    Validación de coherencia de contexto polimórfico (D4): ambos null o ambos presentes.
    """
    model_config = ConfigDict(extra="forbid")

    asignado_a: uuid.UUID
    descripcion: str = Field(min_length=1)
    materia_id: Optional[uuid.UUID] = None
    contexto_id: Optional[uuid.UUID] = None
    contexto_tipo: Optional[str] = None

    @model_validator(mode="after")
    def validate_contexto_coherencia(self) -> "TareaCreate":
        """D4: contexto_id and contexto_tipo must both be null OR both be present."""
        has_id = self.contexto_id is not None
        has_tipo = self.contexto_tipo is not None
        if has_id != has_tipo:
            raise ValueError(
                "contexto_id y contexto_tipo deben ser ambos null o ambos presentes"
            )
        return self


class TareaUpdateEstado(BaseModel):
    """
    Payload para cambiar el estado de una Tarea.

    La transición se valida en el servicio con la matriz D3.
    tenant_id e identidad del actor SIEMPRE desde el JWT.
    """
    model_config = ConfigDict(extra="forbid")

    estado: TareaEstado


class TareaDelegar(BaseModel):
    """
    Payload para delegar una Tarea a otro docente.

    asignado_a es el nuevo receptor (destino de la delegación).
    asignado_por se sobreescribe al actor del JWT en el servicio (D5).
    """
    model_config = ConfigDict(extra="forbid")

    asignado_a: uuid.UUID


class ComentarioTareaCreate(BaseModel):
    """
    Payload para agregar un comentario a una Tarea.

    autor_id y tenant_id SIEMPRE desde el JWT — nunca del body (D6).
    es_sistema NO puede ser seteado externamente (solo el servicio lo setea en True
    para comentarios de delegación; los externos siempre son False).
    """
    model_config = ConfigDict(extra="forbid")

    cuerpo: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TareaRead(BaseModel):
    """Respuesta de lectura de una Tarea.

    materia_nombre y asignado_por_nombre son campos enriquecidos que el
    repositorio resuelve mediante JOIN.  Son opcionales para mantener
    compatibilidad hacia atrás: cuando no se pueden resolver (e.g. el
    registro ya no existe) se devuelve None y el frontend muestra el UUID.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    asignado_a: uuid.UUID
    asignado_por: uuid.UUID
    descripcion: str
    estado: TareaEstado
    materia_id: Optional[uuid.UUID]
    contexto_id: Optional[uuid.UUID]
    contexto_tipo: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    # Campos enriquecidos — resueltos por JOIN en el repositorio
    materia_nombre: Optional[str] = None
    asignado_por_nombre: Optional[str] = None
    asignado_a_nombre: Optional[str] = None


class ComentarioTareaRead(BaseModel):
    """Respuesta de lectura de un ComentarioTarea."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    tarea_id: uuid.UUID
    autor_id: uuid.UUID
    cuerpo: str
    es_sistema: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
