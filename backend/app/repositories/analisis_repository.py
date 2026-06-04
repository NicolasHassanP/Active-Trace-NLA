"""
analisis_repository.py — Repository de lecturas agregadas para C-11 análisis.

C-11 Design Decision D3:
    Repositorio dedicado al análisis (separado de CalificacionRepository)
    para no inflar el de ingesta y mantener ≤500 LOC por archivo.

Métodos:
    calificaciones_por_materia   — lecturas tenant-scoped, con filtro opcional por importador.
    entradas_padron_activas      — entradas del padrón activo para materia×cohorte, con filtros.
    conteo_aprobadas_por_alumno  — GROUP BY para evitar N+1 (tarea 4.5).

Toda query filtra por tenant_id + deleted_at IS NULL (regla dura).
SQL SOLO aquí — nunca en el service.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion
from app.models.padron import EntradaPadron, VersionPadron
from app.repositories.base import TenantScopedRepository


class AnalisisRepository(TenantScopedRepository[Calificacion]):
    """
    Repository tenant-scoped para lecturas agregadas de análisis.

    Hereda de TenantScopedRepository pero agrega métodos especializados
    para el análisis de atrasados, ranking y monitores.

    NO modifica datos (read-only, C-11 es read-only).
    Toda query incluye tenant_id + deleted_at IS NULL (regla dura #11).
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Calificacion, session, tenant_id)

    # -----------------------------------------------------------------------
    # calificaciones_por_materia — scope propio vs global (RN-04, D3)
    # -----------------------------------------------------------------------

    async def calificaciones_por_materia(
        self,
        materia_id: uuid.UUID,
        *,
        importado_por: Optional[uuid.UUID] = None,
        actividades: Optional[List[str]] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> List[Calificacion]:
        """
        Lista calificaciones tenant-scoped para una materia.

        Con importado_por: scope propio (RN-04) — solo calificaciones del docente.
        Sin importado_por: scope global — todas las calificaciones del tenant.

        Filtros opcionales: actividades, rango de fechas por importado_at (OQ-C11-3).
        """
        stmt = (
            select(Calificacion)
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.materia_id == materia_id,
                Calificacion.deleted_at.is_(None),
            )
        )

        if importado_por is not None:
            stmt = stmt.where(Calificacion.importado_por == importado_por)

        if actividades:
            stmt = stmt.where(Calificacion.actividad.in_(actividades))

        if fecha_desde is not None:
            stmt = stmt.where(Calificacion.importado_at >= fecha_desde)

        if fecha_hasta is not None:
            stmt = stmt.where(Calificacion.importado_at <= fecha_hasta)

        stmt = stmt.order_by(Calificacion.entrada_padron_id, Calificacion.actividad)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # entradas_padron_activas — padrón activo con filtros del monitor (D3, 4.4/4.6)
    # -----------------------------------------------------------------------

    async def entradas_padron_activas(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        *,
        comision: Optional[str] = None,
        regional: Optional[str] = None,
        busqueda: Optional[str] = None,
    ) -> List[EntradaPadron]:
        """
        Lista entradas del padrón activo para materia×cohorte con filtros opcionales.

        Delega la resolución de la versión activa reusando el criterio de
        PadronRepository.get_active_version (D3 — la versión activa es única).

        Filtros opcionales: comisión, regional, búsqueda libre por nombre.
        Todos son no-op si no se proveen (OQ-C11-2).
        """
        # Subquery para resolver la versión activa
        active_version_sq = (
            select(VersionPadron.id)
            .where(
                VersionPadron.tenant_id == self._tenant_id,
                VersionPadron.materia_id == materia_id,
                VersionPadron.cohorte_id == cohorte_id,
                VersionPadron.activa.is_(True),
                VersionPadron.deleted_at.is_(None),
            )
            .order_by(VersionPadron.cargado_at.desc())
            .limit(1)
            .scalar_subquery()
        )

        stmt = (
            select(EntradaPadron)
            .where(
                EntradaPadron.tenant_id == self._tenant_id,
                EntradaPadron.version_id == active_version_sq,
                EntradaPadron.deleted_at.is_(None),
            )
        )

        # Filtros opcionales (no-op si None) — OQ-C11-2
        if comision is not None:
            stmt = stmt.where(EntradaPadron.comision == comision)

        if regional is not None:
            stmt = stmt.where(EntradaPadron.regional == regional)

        if busqueda is not None:
            # Búsqueda libre por nombre (ILIKE)
            stmt = stmt.where(
                EntradaPadron.nombre.ilike(f"%{busqueda}%")
            )

        stmt = stmt.order_by(EntradaPadron.apellidos, EntradaPadron.nombre)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # conteo_aprobadas_por_alumno — GROUP BY, evita N+1 (4.5)
    # -----------------------------------------------------------------------

    async def conteo_aprobadas_por_alumno(
        self,
        materia_id: uuid.UUID,
        *,
        importado_por: Optional[uuid.UUID] = None,
        actividades: Optional[List[str]] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> Dict[uuid.UUID, int]:
        """
        Retorna un dict { entrada_padron_id → cantidad_aprobadas } con GROUP BY.

        Evita N+1 al agregar en la DB.
        Filtra por aprobado=True y actividades seleccionadas.
        scope propio si importado_por, global si None.
        """
        stmt = (
            select(
                Calificacion.entrada_padron_id,
                func.count().label("cantidad"),
            )
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.materia_id == materia_id,
                Calificacion.aprobado.is_(True),
                Calificacion.deleted_at.is_(None),
            )
        )

        if importado_por is not None:
            stmt = stmt.where(Calificacion.importado_por == importado_por)

        if actividades:
            stmt = stmt.where(Calificacion.actividad.in_(actividades))

        if fecha_desde is not None:
            stmt = stmt.where(Calificacion.importado_at >= fecha_desde)

        if fecha_hasta is not None:
            stmt = stmt.where(Calificacion.importado_at <= fecha_hasta)

        stmt = stmt.group_by(Calificacion.entrada_padron_id)

        result = await self._session.execute(stmt)
        rows = result.all()
        return {row.entrada_padron_id: row.cantidad for row in rows}
