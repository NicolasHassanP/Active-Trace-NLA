"""
Schemas Pydantic v2 para C-20 mensajería interna.

D4 — Modelo de hilos 1:1 en esta iteración (OQ-3).
D7 — remitente_id NO declarado en schemas de entrada (se atribuye del JWT).
     tenant_id NO declarado (se toma del JWT).

HiloCreate:
    Crear un hilo nuevo: destinatario_id (exactamente 1, OQ-3), asunto, cuerpo.
    remitente_id y tenant_id excluidos (extra='forbid').

RespuestaCreate:
    Responder a un hilo: asunto y cuerpo requeridos y no vacíos.
    remitente_id y tenant_id excluidos.

InboxHiloRead:
    Resumen de hilo en la bandeja: id, asunto, no_leidos, ultimo_mensaje_at.

MensajeRead:
    Mensaje completo: id, hilo_id, remitente_id, asunto, cuerpo, created_at.

Todos con extra='forbid'.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# HiloCreate — iniciar un hilo nuevo 1:1
# ---------------------------------------------------------------------------

class HiloCreate(BaseModel):
    """
    Payload para crear un nuevo hilo.

    destinatario_id: exactamente 1 destinatario (1:1 — OQ-3).
    asunto: opcional (el hilo puede no tener asunto global).
    cuerpo: primer mensaje, obligatorio y no vacío.

    remitente_id y tenant_id excluidos — atribuidos server-side desde el JWT.
    """
    model_config = ConfigDict(extra="forbid")

    destinatario_id: uuid.UUID
    asunto: Optional[str] = None
    cuerpo: str

    @field_validator("cuerpo")
    @classmethod
    def cuerpo_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cuerpo no puede estar vacío")
        return v


# ---------------------------------------------------------------------------
# RespuestaCreate — responder dentro de un hilo
# ---------------------------------------------------------------------------

class RespuestaCreate(BaseModel):
    """
    Payload para agregar un mensaje a un hilo existente.

    asunto y cuerpo son requeridos y no pueden estar vacíos.
    remitente_id y tenant_id excluidos — atribuidos server-side.
    """
    model_config = ConfigDict(extra="forbid")

    asunto: str
    cuerpo: str

    @field_validator("asunto")
    @classmethod
    def asunto_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("asunto no puede estar vacío")
        return v

    @field_validator("cuerpo")
    @classmethod
    def cuerpo_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cuerpo no puede estar vacío")
        return v


# ---------------------------------------------------------------------------
# InboxHiloRead — resumen de hilo en la bandeja
# ---------------------------------------------------------------------------

class InboxHiloRead(BaseModel):
    """
    Resumen de un hilo en la bandeja del usuario.

    no_leidos: mensajes con created_at > last_read_at del participante.
    ultimo_mensaje_at: timestamp del mensaje más reciente.
    otro_participante_nombre: nombre completo del otro usuario en la conversación.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: uuid.UUID
    asunto: Optional[str] = None
    no_leidos: int = 0
    ultimo_mensaje_at: Optional[datetime] = None
    otro_participante_nombre: Optional[str] = None


# ---------------------------------------------------------------------------
# MensajeRead — mensaje completo
# ---------------------------------------------------------------------------

class MensajeRead(BaseModel):
    """
    Output schema de un mensaje completo.

    remitente_id: se expone (usuario del sistema, no PII sensible).
    cuerpo: contenido del mensaje.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=False)

    id: uuid.UUID
    hilo_id: uuid.UUID
    remitente_id: uuid.UUID
    asunto: str
    cuerpo: str
    created_at: datetime
