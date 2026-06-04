"""
ComunicacionRepository — tenant-scoped repository para Comunicacion.

C-12 Design Decisions:
    D1 — Extiende TenantScopedRepository; tenant_id es estado del repo, no param.
    D2 — encolar_lote(): crea N registros Pendiente con un lote_id común.
    D3 — list_by_lote(): lista las comunicaciones de un lote en el tenant.
    D4 — list_pendientes_habilitados(): lista mensajes elegibles para el worker
         (Pendiente + no requieren aprobación, o ya aprobados).
    D5 — actualizar_estado(): transición de estado atómica.
    D6 — Multi-tenancy: todas las queries filtran por tenant_id automáticamente.

snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import Comunicacion, ComunicacionEstado
from app.repositories.base import TenantScopedRepository


class ComunicacionRepository(TenantScopedRepository[Comunicacion]):
    """
    Repository de Comunicacion scoped a un tenant.

    Hereda de TenantScopedRepository:
        - list() → todos los activos del tenant
        - get_by_id() → por UUID, scoped al tenant
        - add() → persiste y asigna tenant_id
        - delete() → soft-delete (marca deleted_at)
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Comunicacion, session, tenant_id)

    # -----------------------------------------------------------------------
    # encolar_lote — crea N registros Pendiente con un lote_id compartido
    # -----------------------------------------------------------------------

    async def encolar_lote(
        self,
        destinatarios: List[str],
        asunto: str,
        cuerpo: str,
        lote_id: uuid.UUID,
        enviado_por: Optional[uuid.UUID] = None,
    ) -> List[Comunicacion]:
        """
        Crea un registro Comunicacion en estado Pendiente por cada destinatario.

        El lote_id es común a todos los registros del lote, permitiendo
        agruparlos y aprobarlos/cancelarlos en conjunto.

        Args:
            destinatarios: lista de emails (PII — serán cifrados por EncryptedString).
            asunto: asunto ya renderizado (plantilla ya aplicada).
            cuerpo: cuerpo ya renderizado por destinatario.
            lote_id: UUID compartido del lote de envío.
            enviado_por: user_id del usuario que encoló (del JWT).

        Returns:
            Lista de Comunicacion creadas, en estado Pendiente, scoped al tenant.
        """
        created: List[Comunicacion] = []
        for destinatario in destinatarios:
            com = Comunicacion(
                tenant_id=self._tenant_id,
                destinatario=destinatario,
                asunto=asunto,
                cuerpo=cuerpo,
                estado=ComunicacionEstado.Pendiente,
                lote_id=lote_id,
                enviado_por=enviado_por,
            )
            created.append(com)
            self._session.add(com)

        await self._session.commit()
        for com in created:
            await self._session.refresh(com)
        return created

    # -----------------------------------------------------------------------
    # list_by_lote — lista comunicaciones de un lote scoped al tenant
    # -----------------------------------------------------------------------

    async def list_by_lote(self, lote_id: uuid.UUID) -> List[Comunicacion]:
        """
        Retorna todas las comunicaciones activas del lote en este tenant.
        Incluye todas las en cualquier estado (no filtra por estado).
        """
        stmt = self._base_query().where(
            Comunicacion.lote_id == lote_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # list_pendientes_habilitados — elegibles para el worker
    # -----------------------------------------------------------------------

    async def list_pendientes_habilitados(self) -> List[Comunicacion]:
        """
        Retorna comunicaciones en estado Pendiente que ya fueron aprobadas
        (aprobado_por IS NOT NULL) o que no requieren aprobación.

        El worker solo procesa comunicaciones elegibles para evitar despachar
        mensajes que aún esperan aprobación.

        Nota: la lógica de "requiere aprobación" se aplica en el service;
        este método solo retorna los Pendiente con aprobado_por IS NOT NULL.
        """
        stmt = self._base_query().where(
            Comunicacion.estado == ComunicacionEstado.Pendiente,
            Comunicacion.aprobado_por.is_not(None),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # list_pendientes_todos — todos los Pendiente (sin aprobación requerida)
    # -----------------------------------------------------------------------

    async def list_pendientes_todos(self) -> List[Comunicacion]:
        """
        Retorna TODOS los comunicaciones en estado Pendiente del tenant.
        Usado cuando aprobacion_comunicacion_requerida=false.
        """
        stmt = self._base_query().where(
            Comunicacion.estado == ComunicacionEstado.Pendiente,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # actualizar_estado — transición atómica de estado
    # -----------------------------------------------------------------------

    async def actualizar_estado(
        self,
        comunicacion: Comunicacion,
        nuevo_estado: ComunicacionEstado,
        aprobado_por: Optional[uuid.UUID] = None,
        enviado_at: Optional[datetime] = None,
        error_detalle: Optional[str] = None,
    ) -> Comunicacion:
        """
        Persiste la transición de estado en la DB.

        No valida si la transición es válida — eso es responsabilidad del service
        (que usa la máquina de estados de comunicacion_estados.py).

        Args:
            comunicacion: instancia a actualizar.
            nuevo_estado: estado destino.
            aprobado_por: user_id del aprobador (solo en aprobación).
            enviado_at: timestamp del envío efectivo (solo al pasar a Enviado).
            error_detalle: detalle de error (solo al pasar a Error).
        """
        comunicacion.estado = nuevo_estado
        if aprobado_por is not None:
            comunicacion.aprobado_por = aprobado_por
        if enviado_at is not None:
            comunicacion.enviado_at = enviado_at
        if error_detalle is not None:
            comunicacion.error_detalle = error_detalle

        await self._session.commit()
        await self._session.refresh(comunicacion)
        return comunicacion

    # -----------------------------------------------------------------------
    # claim_for_worker — toma atómica de un Pendiente habilitado para el worker
    # -----------------------------------------------------------------------

    async def claim_for_worker(
        self, comunicacion_id: uuid.UUID
    ) -> Optional[Comunicacion]:
        """
        Intenta transicionar atómicamente Pendiente → Enviando (WHERE estado='Pendiente').

        Retorna la Comunicacion actualizada si tuvo éxito, None si ya fue tomada
        por otro proceso (protección de concurrencia al tener múltiples workers).
        """
        stmt = (
            update(Comunicacion)
            .where(
                Comunicacion.id == comunicacion_id,
                Comunicacion.tenant_id == self._tenant_id,
                Comunicacion.estado == ComunicacionEstado.Pendiente,
                Comunicacion.deleted_at.is_(None),
            )
            .values(estado=ComunicacionEstado.Enviando)
            .returning(Comunicacion.id)
        )
        result = await self._session.execute(stmt)
        affected = result.scalar_one_or_none()
        if affected is None:
            return None
        await self._session.commit()
        return await self.get_by_id(comunicacion_id)
