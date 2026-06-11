"""
calificacion_repository.py — Repository tenant-scoped para Calificacion y UmbralMateria.

C-10 Design Decisions:
    D5 — UmbralMateria:
         get_umbral(asignacion_id, materia_id)              → UmbralMateria | None (override por docente).
         get_umbral_default(materia_id, cohorte_id)         → UmbralMateria | None (default scope global).
         upsert_umbral(asignacion_id|None, materia_id, ...) → UmbralMateria.
    D8 — Upsert Calificacion por (tenant, entrada_padron, materia, actividad, importado_por).

Queries SOLO en repositories (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calificacion import Calificacion, CalificacionOrigen, UmbralMateria
from app.repositories.base import TenantScopedRepository


class CalificacionRepository(TenantScopedRepository[Calificacion]):
    """
    Repository tenant-scoped para Calificacion y UmbralMateria.

    Hereda de TenantScopedRepository: add, get_by_id, list, delete.
    Agrega:
        get_umbral: obtiene UmbralMateria para (asignacion, materia).
        upsert_umbral: crea o actualiza UmbralMateria.
        upsert_calificacion: crea o actualiza Calificacion (D8).
        list_by_entrada_padron: lista Calificaciones por entrada_padron_id.
        list_by_materia: lista Calificaciones por materia_id.
        get_by_entrada_actividad_importador: lookup por clave única (D8).
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(Calificacion, session, tenant_id)

    # -----------------------------------------------------------------------
    # UmbralMateria — lectura
    # -----------------------------------------------------------------------

    async def get_umbral(
        self,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> Optional[UmbralMateria]:
        """
        Retorna el UmbralMateria override para (tenant_id, asignacion_id, materia_id).
        asignacion_id NOT NULL — busca el registro de override del docente.
        Returns None si no existe.
        """
        stmt = (
            select(UmbralMateria)
            .where(
                UmbralMateria.tenant_id == self._tenant_id,
                UmbralMateria.asignacion_id == asignacion_id,
                UmbralMateria.materia_id == materia_id,
                UmbralMateria.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_umbral_default(
        self,
        materia_id: uuid.UUID,
        cohorte_id: Optional[uuid.UUID],
    ) -> Optional[UmbralMateria]:
        """
        Retorna el UmbralMateria default para (tenant_id, materia_id, cohorte_id).
        asignacion_id IS NULL — busca el registro de default scope global (ADMIN).
        Returns None si no existe.
        """
        stmt = (
            select(UmbralMateria)
            .where(
                UmbralMateria.tenant_id == self._tenant_id,
                UmbralMateria.materia_id == materia_id,
                UmbralMateria.cohorte_id == cohorte_id,
                UmbralMateria.asignacion_id.is_(None),
                UmbralMateria.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # -----------------------------------------------------------------------
    # UmbralMateria — escritura (upsert D5)
    # -----------------------------------------------------------------------

    async def upsert_umbral(
        self,
        asignacion_id: Optional[uuid.UUID],
        materia_id: uuid.UUID,
        umbral_pct: int,
        valores_aprobatorios: List[str],
        cohorte_id: Optional[uuid.UUID] = None,
    ) -> UmbralMateria:
        """
        Get-or-create UmbralMateria para (tenant, asignacion|None, materia).

        Si asignacion_id is None → opera sobre el default scope global (materia/cohorte).
        Si asignacion_id is not None → opera sobre el override del docente.
        Si existe, actualiza umbral_pct y valores_aprobatorios.
        Si no existe, crea uno nuevo.

        Returns the UmbralMateria (created or updated).
        """
        if asignacion_id is None:
            existing = await self.get_umbral_default(materia_id, cohorte_id)
        else:
            existing = await self.get_umbral(asignacion_id, materia_id)

        if existing is not None:
            existing.umbral_pct = umbral_pct
            existing.valores_aprobatorios = valores_aprobatorios
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        # Create new
        umbral = UmbralMateria(
            tenant_id=self._tenant_id,
            asignacion_id=asignacion_id,
            cohorte_id=cohorte_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )
        self._session.add(umbral)
        await self._session.commit()
        await self._session.refresh(umbral)
        return umbral

    # -----------------------------------------------------------------------
    # Calificacion — upsert (D8)
    # -----------------------------------------------------------------------

    async def get_by_entrada_actividad_importador(
        self,
        entrada_padron_id: uuid.UUID,
        materia_id: uuid.UUID,
        actividad: str,
        importado_por: Optional[uuid.UUID],
    ) -> Optional[Calificacion]:
        """
        Lookup Calificacion por la clave única de upsert (D8):
            (tenant_id, entrada_padron_id, materia_id, actividad, importado_por)
        WHERE deleted_at IS NULL.
        """
        stmt = (
            select(Calificacion)
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.entrada_padron_id == entrada_padron_id,
                Calificacion.materia_id == materia_id,
                Calificacion.actividad == actividad,
                Calificacion.importado_por == importado_por,
                Calificacion.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_calificacion(
        self,
        entrada_padron_id: uuid.UUID,
        materia_id: uuid.UUID,
        actividad: str,
        importado_por: Optional[uuid.UUID],
        nota_numerica: Optional[float],
        nota_textual: Optional[str],
        aprobado: bool,
        origen: CalificacionOrigen,
        importado_at: Optional[datetime] = None,
    ) -> Calificacion:
        """
        Create or update a Calificacion using the upsert key (D8).

        On re-import of the same activity by the same user: updates nota/aprobado/importado_at.
        """
        if importado_at is None:
            importado_at = datetime.now(tz=timezone.utc)

        existing = await self.get_by_entrada_actividad_importador(
            entrada_padron_id=entrada_padron_id,
            materia_id=materia_id,
            actividad=actividad,
            importado_por=importado_por,
        )

        if existing is not None:
            existing.nota_numerica = nota_numerica
            existing.nota_textual = nota_textual
            existing.aprobado = aprobado
            existing.importado_at = importado_at
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        cal = Calificacion(
            tenant_id=self._tenant_id,
            entrada_padron_id=entrada_padron_id,
            materia_id=materia_id,
            importado_por=importado_por,
            actividad=actividad,
            nota_numerica=nota_numerica,
            nota_textual=nota_textual,
            aprobado=aprobado,
            origen=origen,
            importado_at=importado_at,
        )
        self._session.add(cal)
        await self._session.commit()
        await self._session.refresh(cal)
        return cal

    # -----------------------------------------------------------------------
    # Calificacion — lecturas
    # -----------------------------------------------------------------------

    async def list_by_entrada_padron(
        self,
        entrada_padron_id: uuid.UUID,
    ) -> List[Calificacion]:
        """List active Calificaciones for a given entrada_padron_id."""
        stmt = (
            select(Calificacion)
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.entrada_padron_id == entrada_padron_id,
                Calificacion.deleted_at.is_(None),
            )
            .order_by(Calificacion.actividad)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_materia_importador(
        self,
        materia_id: uuid.UUID,
        importado_por: uuid.UUID,
    ) -> List[Calificacion]:
        """List active Calificaciones for a given materia × importador (RN-04)."""
        stmt = (
            select(Calificacion)
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.materia_id == materia_id,
                Calificacion.importado_por == importado_por,
                Calificacion.deleted_at.is_(None),
            )
            .order_by(Calificacion.actividad)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_calificaciones(self) -> int:
        """Count all active Calificaciones for this tenant (used in tests)."""
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(Calificacion)
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def list_by_materia_actividad_textual(
        self,
        materia_id: uuid.UUID,
        actividad: str,
        entrada_padron_ids: List[uuid.UUID],
    ) -> List[Calificacion]:
        """
        List active Calificaciones with nota_textual for given materia, actividad,
        and a set of entrada_padron_ids. Used for reporte de finalización (F1.2).
        """
        if not entrada_padron_ids:
            return []
        stmt = (
            select(Calificacion)
            .where(
                Calificacion.tenant_id == self._tenant_id,
                Calificacion.materia_id == materia_id,
                Calificacion.actividad == actividad,
                Calificacion.entrada_padron_id.in_(entrada_padron_ids),
                Calificacion.nota_textual.is_not(None),
                Calificacion.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
