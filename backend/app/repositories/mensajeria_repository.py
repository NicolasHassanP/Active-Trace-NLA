"""
MensajeriaRepository — C-20 mensajería interna.

D4 — Tres entidades: HiloMensaje, Mensaje, HiloParticipante.
D5 — no-leídos = mensajes con created_at > last_read_at del participante.
D6 — Sin cola de despacho; pull-based.
D7 — tenant_id scope siempre activo; aislamiento por usuario y tenant.

Queries SOLO en este repository (regla dura #11).
Sin SQL en services.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mensajeria import HiloMensaje, HiloParticipante, Mensaje


class MensajeriaRepository:
    """
    Repository tenant-scoped para mensajería interna.

    Todas las queries filtran por tenant_id por defecto.
    La participación se verifica via hilo_participantes, nunca de la petición.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Escritura — crear hilo y mensajes
    # ------------------------------------------------------------------

    async def crear_hilo(
        self,
        remitente_id: uuid.UUID,
        destinatario_id: uuid.UUID,
        asunto: Optional[str],
        cuerpo: str,
    ) -> Tuple[HiloMensaje, Mensaje]:
        """
        Crea un HiloMensaje nuevo con su primer Mensaje y dos HiloParticipante.

        Ambos participantes (remitente + destinatario) se registran en
        hilo_participantes. tenant_id viene del scope del repository.
        Retorna (hilo, primer_mensaje).
        """
        hilo = HiloMensaje(tenant_id=self._tenant_id, asunto=asunto)
        self._session.add(hilo)
        await self._session.flush()

        # Participantes (remitente + destinatario)
        for uid in (remitente_id, destinatario_id):
            participante = HiloParticipante(
                hilo_id=hilo.id,
                usuario_id=uid,
                tenant_id=self._tenant_id,
            )
            self._session.add(participante)

        # Primer mensaje
        mensaje = Mensaje(
            tenant_id=self._tenant_id,
            hilo_id=hilo.id,
            remitente_id=remitente_id,
            asunto=asunto or "",
            cuerpo=cuerpo,
        )
        self._session.add(mensaje)
        await self._session.commit()
        await self._session.refresh(hilo)
        await self._session.refresh(mensaje)
        return hilo, mensaje

    async def agregar_mensaje(
        self,
        hilo_id: uuid.UUID,
        remitente_id: uuid.UUID,
        asunto: str,
        cuerpo: str,
    ) -> Mensaje:
        """
        Agrega un Mensaje a un hilo existente.

        tenant_id viene del scope del repository.
        remitente_id es provisto por el service desde el JWT.
        """
        mensaje = Mensaje(
            tenant_id=self._tenant_id,
            hilo_id=hilo_id,
            remitente_id=remitente_id,
            asunto=asunto,
            cuerpo=cuerpo,
        )
        self._session.add(mensaje)
        await self._session.commit()
        await self._session.refresh(mensaje)
        return mensaje

    # ------------------------------------------------------------------
    # Lectura — listar y acceder a hilos
    # ------------------------------------------------------------------

    async def listar_hilos(self, usuario_id: uuid.UUID) -> List[dict]:
        """
        Lista los hilos donde el usuario participa, en orden de actividad.

        Retorna lista de dicts con:
            - hilo_id
            - asunto
            - ultimo_mensaje_at (max created_at de mensajes activos)
        """
        stmt = (
            select(
                HiloMensaje.id.label("hilo_id"),
                HiloMensaje.asunto,
                func.max(Mensaje.created_at).label("ultimo_mensaje_at"),
            )
            .join(HiloParticipante, HiloParticipante.hilo_id == HiloMensaje.id)
            .outerjoin(
                Mensaje,
                and_(
                    Mensaje.hilo_id == HiloMensaje.id,
                    Mensaje.deleted_at.is_(None),
                ),
            )
            .where(
                HiloParticipante.usuario_id == usuario_id,
                HiloParticipante.tenant_id == self._tenant_id,
                HiloMensaje.tenant_id == self._tenant_id,
                HiloMensaje.deleted_at.is_(None),
            )
            .group_by(HiloMensaje.id, HiloMensaje.asunto)
            .order_by(func.max(Mensaje.created_at).desc().nulls_last())
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            {
                "hilo_id": row.hilo_id,
                "asunto": row.asunto,
                "ultimo_mensaje_at": row.ultimo_mensaje_at,
            }
            for row in rows
        ]

    async def obtener_hilo(
        self, hilo_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> Optional[HiloMensaje]:
        """
        Retorna el HiloMensaje solo si el usuario es participante Y el hilo
        pertenece al tenant del scope.

        Retorna None si: no existe, cross-tenant, o usuario no participa.
        404 semántico (D7: hilos ajenos devuelven 404 para evitar enumeración).
        """
        stmt = (
            select(HiloMensaje)
            .join(HiloParticipante, HiloParticipante.hilo_id == HiloMensaje.id)
            .where(
                HiloMensaje.id == hilo_id,
                HiloMensaje.tenant_id == self._tenant_id,
                HiloMensaje.deleted_at.is_(None),
                HiloParticipante.usuario_id == usuario_id,
                HiloParticipante.tenant_id == self._tenant_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def obtener_mensajes(
        self, hilo_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> List[Mensaje]:
        """
        Retorna mensajes del hilo en orden cronológico (excluyendo soft-deleted).

        Solo ejecutar tras verificar participación con obtener_hilo().
        """
        stmt = (
            select(Mensaje)
            .where(
                Mensaje.hilo_id == hilo_id,
                Mensaje.tenant_id == self._tenant_id,
                Mensaje.deleted_at.is_(None),
            )
            .order_by(Mensaje.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Estado de leído
    # ------------------------------------------------------------------

    async def marcar_leido(
        self, hilo_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> None:
        """
        Actualiza last_read_at del participante al momento actual.

        no-leídos posteriores a este momento = 0 hasta nuevo mensaje.
        """
        stmt = (
            select(HiloParticipante)
            .where(
                HiloParticipante.hilo_id == hilo_id,
                HiloParticipante.usuario_id == usuario_id,
            )
        )
        result = await self._session.execute(stmt)
        participante = result.scalar_one_or_none()
        if participante is not None:
            participante.last_read_at = datetime.now(tz=timezone.utc)
            await self._session.commit()

    async def contar_no_leidos(
        self, hilo_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> int:
        """
        Cuenta mensajes con created_at > last_read_at del participante.

        Si last_read_at es None (nunca abrió), cuenta todos los mensajes activos.
        """
        # Obtener last_read_at del participante
        stmt_p = select(HiloParticipante).where(
            HiloParticipante.hilo_id == hilo_id,
            HiloParticipante.usuario_id == usuario_id,
        )
        result_p = await self._session.execute(stmt_p)
        participante = result_p.scalar_one_or_none()

        if participante is None:
            return 0

        stmt = select(func.count()).select_from(Mensaje).where(
            Mensaje.hilo_id == hilo_id,
            Mensaje.tenant_id == self._tenant_id,
            Mensaje.deleted_at.is_(None),
        )
        if participante.last_read_at is not None:
            stmt = stmt.where(Mensaje.created_at > participante.last_read_at)

        result = await self._session.execute(stmt)
        return result.scalar() or 0

    # ------------------------------------------------------------------
    # Anti-duplicación de hilos 1:1
    # ------------------------------------------------------------------

    async def buscar_hilo_existente(
        self, usuario_id_1: uuid.UUID, usuario_id_2: uuid.UUID
    ) -> Optional[uuid.UUID]:
        """
        Busca un hilo activo donde ambos usuarios son los únicos participantes.

        Retorna el hilo_id si existe, None si no hay hilo previo.
        Usado para evitar duplicados 1:1 (OQ-3).
        """
        # Hilos donde participa usuario_1
        sub1 = (
            select(HiloParticipante.hilo_id)
            .where(
                HiloParticipante.usuario_id == usuario_id_1,
                HiloParticipante.tenant_id == self._tenant_id,
            )
        )
        # Hilos donde participa usuario_2
        sub2 = (
            select(HiloParticipante.hilo_id)
            .where(
                HiloParticipante.usuario_id == usuario_id_2,
                HiloParticipante.tenant_id == self._tenant_id,
            )
        )
        # Hilos en común
        hilo_ids_1 = (await self._session.execute(sub1)).scalars().all()
        hilo_ids_2 = (await self._session.execute(sub2)).scalars().all()
        comunes = set(hilo_ids_1) & set(hilo_ids_2)

        if not comunes:
            return None

        # Entre los hilos comunes, encontrar uno que tenga exactamente 2 participantes
        for hilo_id in comunes:
            stmt_count = select(func.count()).select_from(HiloParticipante).where(
                HiloParticipante.hilo_id == hilo_id,
            )
            cnt = (await self._session.execute(stmt_count)).scalar() or 0
            if cnt == 2:
                # Verificar que el hilo no esté borrado
                hilo = await self._session.get(HiloMensaje, hilo_id)
                if hilo and hilo.deleted_at is None and hilo.tenant_id == self._tenant_id:
                    return hilo_id

        return None
