"""
umbral_service.py — Gestión del umbral de aprobación por Asignacion×Materia.

C-10 Design Decision D5:
    UmbralService.get_efectivo(asignacion_id, materia_id) → UmbralMateriaRead:
        Returns configured umbral or tenant default (60% / standard textual set).
    UmbralService.configurar(materia_id, umbral_pct, valores_aprobatorios, current_user):
        Resolves asignacion_id from current_user.user_id + materia_id.
        Get-or-create upsert via CalificacionRepository.upsert_umbral.

Identity ALWAYS from current_user (JWT session) — never from request body (regla dura #8/#14).
Queries ONLY via repository (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import List

from app.core.dependencies import CurrentUser
from app.repositories.calificacion_repository import CalificacionRepository
from app.schemas.calificacion import UmbralMateriaRead


class UmbralService:
    """
    Service for managing UmbralMateria (approval threshold) records.

    Wraps CalificacionRepository for umbral operations.
    Identity (asignacion_id) always resolved from the JWT session.
    """

    def __init__(self, repo: CalificacionRepository) -> None:
        self._repo = repo

    async def get_efectivo(
        self,
        asignacion_id: uuid.UUID,
        materia_id: uuid.UUID,
    ) -> UmbralMateriaRead:
        """
        Return the effective UmbralMateriaRead for (asignacion_id, materia_id).

        If no UmbralMateria record exists for this asignacion × materia,
        returns the tenant default (umbral_pct=60, valores_aprobatorios from Settings).
        The returned UmbralMateriaRead.is_default=True when using defaults.

        Tenant scope is enforced by the repository (always filters by tenant_id).
        """
        from app.core.config import Settings
        settings = Settings()

        umbral = await self._repo.get_umbral(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
        )

        if umbral is None:
            return UmbralMateriaRead(
                id=None,
                asignacion_id=None,
                materia_id=materia_id,
                umbral_pct=settings.UMBRAL_PCT_DEFECTO,
                valores_aprobatorios=settings.VALORES_APROBATORIOS_DEFECTO,
                is_default=True,
            )

        return UmbralMateriaRead(
            id=umbral.id,
            asignacion_id=umbral.asignacion_id,
            materia_id=umbral.materia_id,
            umbral_pct=umbral.umbral_pct,
            valores_aprobatorios=umbral.valores_aprobatorios or [],
            is_default=False,
        )

    async def configurar(
        self,
        materia_id: uuid.UUID,
        umbral_pct: int,
        valores_aprobatorios: List[str],
        current_user: CurrentUser,
    ) -> UmbralMateriaRead:
        """
        Configure the approval threshold for the current user's asignacion in materia_id.

        Resolves asignacion_id from current_user.user_id + materia_id (D5, regla dura #8/#14).
        Uses get-or-create upsert via repository.

        Raises ValueError if no active Asignacion exists for current_user in materia_id.
        """
        asignacion_id = await self._resolve_asignacion(
            user_id=current_user.user_id,
            materia_id=materia_id,
            tenant_id=current_user.tenant_id,
        )

        umbral = await self._repo.upsert_umbral(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
        )

        return UmbralMateriaRead(
            id=umbral.id,
            asignacion_id=umbral.asignacion_id,
            materia_id=umbral.materia_id,
            umbral_pct=umbral.umbral_pct,
            valores_aprobatorios=umbral.valores_aprobatorios or [],
            is_default=False,
        )

    async def _resolve_asignacion(
        self,
        user_id: uuid.UUID,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Resolve the asignacion_id for current_user in materia_id.

        Queries the DB for an active Asignacion matching:
            (tenant_id, usuario_id=user_id, materia_id, deleted_at IS NULL)

        Returns the asignacion_id.
        Raises ValueError if no matching Asignacion is found.
        """
        from sqlalchemy import select
        from app.models.usuario import Asignacion

        stmt = (
            select(Asignacion)
            .where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == user_id,
                Asignacion.materia_id == materia_id,
                Asignacion.deleted_at.is_(None),
            )
            .order_by(Asignacion.desde.desc())
            .limit(1)
        )
        result = await self._repo._session.execute(stmt)
        asignacion = result.scalar_one_or_none()

        if asignacion is None:
            raise ValueError(
                f"No active Asignacion found for user {user_id} in materia {materia_id}. "
                "Cannot configure umbral without an active assignment."
            )

        return asignacion.id
