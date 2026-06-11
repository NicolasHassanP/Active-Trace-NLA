"""
umbral_service.py — Gestión del umbral de aprobación por Asignacion×Materia.

C-10 Design Decision D5 (actualizado):
    UmbralService.get_efectivo(asignacion_id|None, materia_id, cohorte_id|None):
        Precedencia:
            (1) override del docente → buscar por (asignacion_id, materia_id)
            (2) default materia/cohorte → buscar por (materia_id, cohorte_id) WHERE asignacion_id IS NULL
            (3) default sistema (60%)
        Retorna UmbralMateriaRead con is_default=True si usa (2) o (3).
    UmbralService.configurar(materia_id, umbral_pct, valores_aprobatorios, current_user,
                             asignacion_id|None, cohorte_id|None):
        Si asignacion_id is None → escribe default scope global (ADMIN).
        Si asignacion_id is not None → escribe override scope docente.

Identity ALWAYS from current_user (JWT session) — never from request body (regla dura #8/#14).
Queries ONLY via repository (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.repositories.calificacion_repository import CalificacionRepository
from app.schemas.calificacion import UmbralMateriaRead


class UmbralService:
    """
    Service for managing UmbralMateria (approval threshold) records.

    Wraps CalificacionRepository for umbral operations.
    Identity (asignacion_id) always resolved from the JWT session or None for ADMIN global.
    """

    def __init__(self, repo: CalificacionRepository) -> None:
        self._repo = repo

    async def get_efectivo(
        self,
        materia_id: uuid.UUID,
        asignacion_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
    ) -> UmbralMateriaRead:
        """
        Return the effective UmbralMateriaRead following precedence rules:
            (1) override del docente: by (asignacion_id, materia_id) — only if asignacion_id given
            (2) default materia/cohorte: by (materia_id, cohorte_id) WHERE asignacion_id IS NULL
            (3) default sistema (60%)

        is_default=True when using (2) or (3).
        Tenant scope enforced by the repository.
        """
        from app.core.config import Settings
        settings = Settings()

        # (1) override del docente
        if asignacion_id is not None:
            umbral = await self._repo.get_umbral(
                asignacion_id=asignacion_id,
                materia_id=materia_id,
            )
            if umbral is not None:
                return UmbralMateriaRead(
                    id=umbral.id,
                    asignacion_id=umbral.asignacion_id,
                    cohorte_id=umbral.cohorte_id,
                    materia_id=umbral.materia_id,
                    umbral_pct=umbral.umbral_pct,
                    valores_aprobatorios=umbral.valores_aprobatorios or [],
                    is_default=False,
                )

        # (2) default materia/cohorte
        umbral_default = await self._repo.get_umbral_default(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
        )
        if umbral_default is not None:
            return UmbralMateriaRead(
                id=umbral_default.id,
                asignacion_id=None,
                cohorte_id=umbral_default.cohorte_id,
                materia_id=umbral_default.materia_id,
                umbral_pct=umbral_default.umbral_pct,
                valores_aprobatorios=umbral_default.valores_aprobatorios or [],
                is_default=True,
            )

        # (3) default sistema
        return UmbralMateriaRead(
            id=None,
            asignacion_id=None,
            cohorte_id=cohorte_id,
            materia_id=materia_id,
            umbral_pct=settings.UMBRAL_PCT_DEFECTO,
            valores_aprobatorios=settings.VALORES_APROBATORIOS_DEFECTO,
            is_default=True,
        )

    async def configurar(
        self,
        materia_id: uuid.UUID,
        umbral_pct: int,
        valores_aprobatorios: List[str],
        current_user: CurrentUser,
        asignacion_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
    ) -> UmbralMateriaRead:
        """
        Configure the approval threshold.

        If asignacion_id is None → write default scope global (ADMIN via grant.scope=global).
        If asignacion_id is not None → write override scope propio (docente).

        When called from a docente scope (asignacion_id=None from router) the router
        first resolves asignacion_id from current_user + materia_id and passes it here.
        Identity (asignacion_id) must NEVER come from the request body — only from JWT resolution.
        """
        umbral = await self._repo.upsert_umbral(
            asignacion_id=asignacion_id,
            materia_id=materia_id,
            umbral_pct=umbral_pct,
            valores_aprobatorios=valores_aprobatorios,
            cohorte_id=cohorte_id,
        )

        is_default_record = umbral.asignacion_id is None
        return UmbralMateriaRead(
            id=umbral.id,
            asignacion_id=umbral.asignacion_id,
            cohorte_id=umbral.cohorte_id,
            materia_id=umbral.materia_id,
            umbral_pct=umbral.umbral_pct,
            valores_aprobatorios=umbral.valores_aprobatorios or [],
            is_default=is_default_record,
        )

    async def _resolve_asignacion(
        self,
        auth_identity_id: uuid.UUID,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> uuid.UUID:
        """
        Resolve the asignacion_id for current_user in materia_id.

        auth_identity_id = auth_identities.id (JWT sub). Joins through Usuario
        to reach Asignacion.usuario_id (usuario.id).
        Raises ValueError if no matching Asignacion is found.
        """
        from sqlalchemy import select
        from app.models.usuario import Asignacion, Usuario

        stmt = (
            select(Asignacion)
            .join(Usuario, (Usuario.id == Asignacion.usuario_id) & (Usuario.deleted_at.is_(None)))
            .where(
                Asignacion.tenant_id == tenant_id,
                Usuario.auth_identity_id == auth_identity_id,
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
                f"No existe una asignación activa en la materia {materia_id}. "
                "Es necesario tener una asignación para configurar el umbral."
            )

        return asignacion.id
