"""
fecha_academica_service.py — Servicio para gestión de fechas académicas.

C-17 Design Decisions:
    D5  — chequeo de duplicado activo → FechaAcademicaConflictError (409).
    D7  — listar y listar_calendario comparten el mismo repo query.
    D8  — audit: FECHA_ACADEMICA_GESTIONAR en alta, edición y baja.
    D9  — reusar permiso 'estructura:gestionar'.

Identity ALWAYS from current_user — never from body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.models.academico import FechaAcademica, FechaAcademicaTipo
from app.models.audit import AuditAction, AuditResultado
from app.repositories.audit_repository import AuditRepository
from app.repositories.fecha_academica_repository import FechaAcademicaRepository
from app.schemas.academico import (
    FechaAcademicaCreate,
    FechaAcademicaRead,
    FechaAcademicaUpdate,
)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class FechaAcademicaConflictError(Exception):
    """Raised when an active fecha exists for the same combo (D5)."""


class FechaAcademicaNotFoundError(Exception):
    """Raised when a fecha is not found or belongs to another tenant."""


# ---------------------------------------------------------------------------
# FechaAcademicaService
# ---------------------------------------------------------------------------

class FechaAcademicaService:
    """
    Service for FechaAcademica operations.

    Orchestrates FechaAcademicaRepository + AuditRepository.
    No direct DB access — all persistence via repos.
    Identity/tenant ALWAYS from current_user (JWT).
    """

    def __init__(
        self,
        fecha_repo: FechaAcademicaRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._repo = fecha_repo
        self._audit_repo = audit_repo

    async def crear(
        self, payload: FechaAcademicaCreate, current_user: CurrentUser
    ) -> FechaAcademicaRead:
        """
        Crear una fecha académica.

        D5: verifica duplicado activo → FechaAcademicaConflictError (409).
        D8: registra FECHA_ACADEMICA_GESTIONAR en auditoría.
        """
        if await self._repo.existe_activo_para_combo(
            payload.materia_id,
            payload.cohorte_id,
            payload.tipo,
            payload.numero,
            payload.periodo,
        ):
            raise FechaAcademicaConflictError(
                f"Ya existe una fecha activa para "
                f"materia={payload.materia_id} cohorte={payload.cohorte_id} "
                f"tipo={payload.tipo.value} numero={payload.numero} periodo={payload.periodo}"
            )

        fa = FechaAcademica(
            materia_id=payload.materia_id,
            cohorte_id=payload.cohorte_id,
            tipo=payload.tipo,
            numero=payload.numero,
            periodo=payload.periodo,
            fecha=payload.fecha,
            titulo=payload.titulo,
        )
        fa = await self._repo.add(fa)

        await self._emit_audit(
            actor=current_user,
            entidad_id=str(fa.id),
            after={
                "fecha_id": str(fa.id),
                "tipo": fa.tipo.value,
                "numero": fa.numero,
                "periodo": fa.periodo,
                "fecha": str(fa.fecha),
                "titulo": fa.titulo,
                "accion": "alta",
            },
        )

        return FechaAcademicaRead.model_validate(fa)

    async def editar(
        self,
        fecha_id: uuid.UUID,
        patch: FechaAcademicaUpdate,
        current_user: CurrentUser,
    ) -> FechaAcademicaRead:
        """
        Editar campos mutables de una fecha académica.

        Solo modifica los campos presentes en el patch.
        D8: registra FECHA_ACADEMICA_GESTIONAR en auditoría.
        """
        fa = await self._repo.get_by_id(fecha_id)
        if fa is None:
            raise FechaAcademicaNotFoundError(f"FechaAcademica {fecha_id} no encontrada")

        if patch.fecha is not None:
            fa.fecha = patch.fecha
        if patch.titulo is not None:
            fa.titulo = patch.titulo

        await self._repo._session.commit()
        await self._repo._session.refresh(fa)

        await self._emit_audit(
            actor=current_user,
            entidad_id=str(fecha_id),
            after={"fecha_id": str(fecha_id), "accion": "edicion",
                   "titulo": fa.titulo, "fecha": str(fa.fecha)},
        )

        return FechaAcademicaRead.model_validate(fa)

    async def listar(
        self,
        materia_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        tipo: Optional[FechaAcademicaTipo] = None,
        periodo: Optional[str] = None,
    ) -> List[FechaAcademicaRead]:
        """List active fechas académicas with optional filters (tabular view)."""
        fechas = await self._repo.listar(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            tipo=tipo,
            periodo=periodo,
        )
        return [FechaAcademicaRead.model_validate(f) for f in fechas]

    async def listar_calendario(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> List[FechaAcademicaRead]:
        """List fechas ordered by fecha ASC (calendar view, D7)."""
        fechas = await self._repo.listar_calendario(materia_id, cohorte_id)
        return [FechaAcademicaRead.model_validate(f) for f in fechas]

    async def obtener(self, fecha_id: uuid.UUID) -> FechaAcademicaRead:
        """Get a single fecha académica by id (tenant-scoped)."""
        fa = await self._repo.get_by_id(fecha_id)
        if fa is None:
            raise FechaAcademicaNotFoundError(f"FechaAcademica {fecha_id} no encontrada")
        return FechaAcademicaRead.model_validate(fa)

    async def eliminar(self, fecha_id: uuid.UUID, current_user: CurrentUser) -> None:
        """
        Soft-delete a fecha académica.

        D8: registra FECHA_ACADEMICA_GESTIONAR en auditoría.
        """
        fa = await self._repo.get_by_id(fecha_id)
        if fa is None:
            raise FechaAcademicaNotFoundError(f"FechaAcademica {fecha_id} no encontrada")

        await self._repo.delete(fa)

        await self._emit_audit(
            actor=current_user,
            entidad_id=str(fecha_id),
            after={"fecha_id": str(fecha_id), "accion": "baja"},
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _emit_audit(self, actor: CurrentUser, entidad_id: str, after: dict) -> None:
        from app.services.audit_service import AuditService
        audit_svc = AuditService(repository=self._audit_repo)
        await audit_svc.record(
            actor=actor,
            action=AuditAction.FECHA_ACADEMICA_GESTIONAR,
            modulo="fechas-academicas",
            entidad_tipo="FechaAcademica",
            entidad_id=entidad_id,
            resultado=AuditResultado.ok,
            registros_afectados=1,
            after=after,
        )
