"""
programa_service.py — Servicio para gestión de programas de materia.

C-17 Design Decisions:
    D3  — referencia_archivo es puntero opaco; el service nunca la interpreta.
    D5  — chequeo de duplicado activo antes de insertar → ProgramaConflictError (409).
    D9  — reusar permiso 'estructura:gestionar'.
    D8  — audit: PROGRAMA_GESTIONAR en alta y baja.

Identity ALWAYS from current_user — never from body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid

from app.core.dependencies import CurrentUser
from app.models.academico import ProgramaMateria
from app.models.audit import AuditAction, AuditResultado
from app.repositories.audit_repository import AuditRepository
from app.repositories.programa_repository import ProgramaMateriaRepository
from app.schemas.academico import ProgramaCreate, ProgramaRead


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class ProgramaConflictError(Exception):
    """Raised when a programa already exists for the same (materia, carrera, cohorte) combo."""


class ProgramaNotFoundError(Exception):
    """Raised when a programa is not found or belongs to another tenant."""


# ---------------------------------------------------------------------------
# ProgramaService
# ---------------------------------------------------------------------------

class ProgramaService:
    """
    Service for ProgramaMateria operations.

    Orchestrates ProgramaMateriaRepository + AuditRepository.
    No direct DB access — all persistence via repos.
    Identity/tenant ALWAYS from current_user (JWT).
    """

    def __init__(
        self,
        programa_repo: ProgramaMateriaRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._repo = programa_repo
        self._audit_repo = audit_repo

    async def crear(self, payload: ProgramaCreate, current_user: CurrentUser) -> ProgramaRead:
        """
        Registrar un nuevo programa de materia.

        D5: verifica duplicado activo → ProgramaConflictError (409).
        D3: referencia_archivo persiste sin transformación.
        D8: registra PROGRAMA_GESTIONAR en auditoría.
        """
        if await self._repo.existe_activo_para_combo(
            payload.materia_id, payload.carrera_id, payload.cohorte_id
        ):
            raise ProgramaConflictError(
                f"Ya existe un programa activo para esta combinación "
                f"materia={payload.materia_id} carrera={payload.carrera_id} "
                f"cohorte={payload.cohorte_id}"
            )

        prog = ProgramaMateria(
            materia_id=payload.materia_id,
            carrera_id=payload.carrera_id,
            cohorte_id=payload.cohorte_id,
            titulo=payload.titulo,
            referencia_archivo=payload.referencia_archivo,
        )
        prog = await self._repo.add(prog)

        await self._emit_audit(
            actor=current_user,
            entidad_id=str(prog.id),
            after={
                "programa_id": str(prog.id),
                "materia_id": str(prog.materia_id),
                "carrera_id": str(prog.carrera_id),
                "cohorte_id": str(prog.cohorte_id),
                "titulo": prog.titulo,
                "accion": "alta",
            },
        )

        return ProgramaRead.model_validate(prog)

    async def listar(
        self,
        materia_id=None,
        carrera_id=None,
        cohorte_id=None,
    ):
        """List active programas, with optional filters."""
        programas = await self._repo.listar(
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
        )
        return [ProgramaRead.model_validate(p) for p in programas]

    async def obtener(self, programa_id: uuid.UUID) -> ProgramaRead:
        """Get a single programa by id (tenant-scoped)."""
        prog = await self._repo.get_by_id(programa_id)
        if prog is None:
            raise ProgramaNotFoundError(f"Programa {programa_id} no encontrado")
        return ProgramaRead.model_validate(prog)

    async def eliminar(self, programa_id: uuid.UUID, current_user: CurrentUser) -> None:
        """
        Soft-delete a programa de materia.

        D8: registra PROGRAMA_GESTIONAR en auditoría.
        """
        prog = await self._repo.get_by_id(programa_id)
        if prog is None:
            raise ProgramaNotFoundError(f"Programa {programa_id} no encontrado")

        await self._repo.delete(prog)

        await self._emit_audit(
            actor=current_user,
            entidad_id=str(programa_id),
            after={"programa_id": str(programa_id), "accion": "baja"},
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _emit_audit(self, actor: CurrentUser, entidad_id: str, after: dict) -> None:
        from app.services.audit_service import AuditService
        audit_svc = AuditService(repository=self._audit_repo)
        await audit_svc.record(
            actor=actor,
            action=AuditAction.PROGRAMA_GESTIONAR,
            modulo="programas",
            entidad_tipo="ProgramaMateria",
            entidad_id=entidad_id,
            resultado=AuditResultado.ok,
            registros_afectados=1,
            after=after,
        )
