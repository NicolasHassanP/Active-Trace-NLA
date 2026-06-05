"""
InboxService — C-20 mensajería interna.

D6 — Independiente de comunicaciones; pull-based, sin despacho externo.
D7 — Remitente SIEMPRE del JWT (anti-spoofing); participación del repositorio.

ver_inbox(actor):
    Lista hilos del actor con conteo de no-leídos.

abrir_hilo(actor, hilo_id):
    Verifica participación, marca leído, retorna mensajes.
    Raises HiloNoEncontrado si el actor no participa o es cross-tenant.

responder(actor, hilo_id, body):
    Agrega mensaje. Remitente = actor.user_id (ignora body).
    Raises HiloNoEncontrado si el actor no participa.

iniciar_hilo(actor, body):
    Valida que destinatario sea del mismo tenant.
    Valida que no exista hilo 1:1 previo entre los dos usuarios (OQ-3).
    Crea el hilo y el primer mensaje.
    Raises DestinatarioInvalido, HiloDuplicado.

Excepciones mapeadas a HTTP en el router:
    HiloNoEncontrado    → 404
    DestinatarioInvalido → 404
    HiloDuplicado       → 409

Regla dura #11: lógica SOLO aquí. Queries SOLO en repository.
snake_case; ≤500 LOC.
"""
from typing import List

from app.core.dependencies import CurrentUser
from app.repositories.mensajeria_repository import MensajeriaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.mensajeria import HiloCreate, InboxHiloRead, MensajeRead, RespuestaCreate


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class HiloNoEncontrado(Exception):
    """Hilo no existe para el actor (no participa o cross-tenant) — HTTP 404."""


class DestinatarioInvalido(Exception):
    """Destinatario no existe en el tenant del actor — HTTP 404."""


class HiloDuplicado(Exception):
    """Ya existe un hilo 1:1 entre los dos usuarios — HTTP 409."""


# ---------------------------------------------------------------------------
# InboxService
# ---------------------------------------------------------------------------

class InboxService:
    """
    Service para la bandeja de mensajería interna.

    Identidad y participación SIEMPRE del server (JWT / hilo_participantes).
    Anti-spoofing: remitente_id del body se ignora; se usa actor.user_id.
    """

    def __init__(self, repo: MensajeriaRepository) -> None:
        self._repo = repo

    async def ver_inbox(self, actor: CurrentUser) -> List[InboxHiloRead]:
        """
        Lista hilos del actor con conteo de no-leídos.

        Usa actor.user_id (JWT) — no acepta id externo.
        """
        hilos_raw = await self._repo.listar_hilos(actor.user_id)
        result = []
        for item in hilos_raw:
            no_leidos = await self._repo.contar_no_leidos(item["hilo_id"], actor.user_id)
            result.append(InboxHiloRead(
                id=item["hilo_id"],
                asunto=item.get("asunto"),
                no_leidos=no_leidos,
                ultimo_mensaje_at=item.get("ultimo_mensaje_at"),
            ))
        return result

    async def abrir_hilo(
        self, actor: CurrentUser, hilo_id
    ) -> List[MensajeRead]:
        """
        Retorna mensajes del hilo y marca leído para el actor.

        Raises HiloNoEncontrado si el actor no participa o es cross-tenant.
        """
        hilo = await self._repo.obtener_hilo(hilo_id, actor.user_id)
        if hilo is None:
            raise HiloNoEncontrado("Hilo no encontrado.")

        await self._repo.marcar_leido(hilo_id, actor.user_id)
        mensajes = await self._repo.obtener_mensajes(hilo_id, actor.user_id)
        return [_mensaje_to_read(m) for m in mensajes]

    async def responder(
        self, actor: CurrentUser, hilo_id, body: RespuestaCreate
    ) -> MensajeRead:
        """
        Agrega un mensaje al hilo.

        Remitente = actor.user_id (anti-spoofing: body no declara remitente_id).
        Raises HiloNoEncontrado si el actor no participa.
        """
        hilo = await self._repo.obtener_hilo(hilo_id, actor.user_id)
        if hilo is None:
            raise HiloNoEncontrado("Hilo no encontrado o no eres participante.")

        msg = await self._repo.agregar_mensaje(
            hilo_id=hilo_id,
            remitente_id=actor.user_id,  # SIEMPRE del JWT
            asunto=body.asunto,
            cuerpo=body.cuerpo,
        )
        return _mensaje_to_read(msg)

    async def iniciar_hilo(
        self, actor: CurrentUser, body: HiloCreate
    ) -> MensajeRead:
        """
        Crea un nuevo hilo 1:1 con el primer mensaje.

        Validaciones:
            - destinatario debe existir en el mismo tenant (DestinatarioInvalido).
            - No debe existir hilo 1:1 activo entre los dos (HiloDuplicado — OQ-3).

        Raises DestinatarioInvalido, HiloDuplicado.
        """
        # Validar que el destinatario sea del mismo tenant
        # Usamos el repo de usuario para verificar existencia en el tenant
        from sqlalchemy import select
        from app.models.usuario import Usuario

        stmt = select(Usuario).where(
            Usuario.id == body.destinatario_id,
            Usuario.tenant_id == actor.tenant_id,
            Usuario.deleted_at.is_(None),
        )
        result = await self._repo._session.execute(stmt)
        destinatario = result.scalar_one_or_none()
        if destinatario is None:
            raise DestinatarioInvalido(
                "Destinatario no encontrado en este tenant."
            )

        # Validar que no exista hilo 1:1 previo (OQ-3)
        hilo_existente = await self._repo.buscar_hilo_existente(
            actor.user_id, body.destinatario_id
        )
        if hilo_existente is not None:
            raise HiloDuplicado(
                "Ya existe un hilo entre estos dos usuarios."
            )

        # Crear hilo + primer mensaje
        _, mensaje = await self._repo.crear_hilo(
            remitente_id=actor.user_id,
            destinatario_id=body.destinatario_id,
            asunto=body.asunto,
            cuerpo=body.cuerpo,
        )
        return _mensaje_to_read(mensaje)


# ---------------------------------------------------------------------------
# Helper de serialización
# ---------------------------------------------------------------------------

def _mensaje_to_read(msg) -> MensajeRead:
    """Convierte un ORM Mensaje en MensajeRead."""
    return MensajeRead(
        id=msg.id,
        hilo_id=msg.hilo_id,
        remitente_id=msg.remitente_id,
        asunto=msg.asunto,
        cuerpo=msg.cuerpo,
        created_at=msg.created_at,
    )
