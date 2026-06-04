"""
padron_service.py — Service para importación y gestión del padrón versionado.

C-09 Design Decisions:
    D5 — import en dos pasos: preview (sin escritura) + activar (escribe y activa).
    D6 — vaciar scope-isolated: PROFESOR solo vacía las propias; COORDINADOR cualquiera.
    D7 — sync_from_moodle mapea user dicts de Moodle a PadronRowDTO y llama activar.

PadronService(repo, db, audit_repo):
    - preview(file_bytes, filename, materia_id, cohorte_id, current_user) → list[PadronRowDTO]
    - activar(rows, materia_id, cohorte_id, current_user) → VersionPadron
    - vaciar(materia_id, cohorte_id, current_user, has_gestionar) → None
    - sync_from_moodle(course_id, materia_id, cohorte_id, current_user, moodle_client) → VersionPadron

Identidad SIEMPRE desde CurrentUser (regla dura #8).
Lógica de negocio SOLO aquí. Queries SOLO en repositories (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.repositories.audit_repository import AuditRepository
from app.repositories.padron_repository import PadronRepository
from app.models.padron import VersionPadron
from app.schemas.padron import PadronRowDTO


# ---------------------------------------------------------------------------
# Excepción de dominio
# ---------------------------------------------------------------------------

class PadronNoEncontrado(Exception):
    """No existe versión activa para materia×cohorte — HTTP 404."""


# ---------------------------------------------------------------------------
# PadronService
# ---------------------------------------------------------------------------

class PadronService:
    """
    Service para importación, activación y gestión del padrón de alumnos.

    Validaciones:
        - preview: parsea el archivo y retorna filas sin escribir en DB.
        - activar: crea VersionPadron + EntradaPadron y desactiva la anterior.
        - vaciar: scope-isolated (D6) — PROFESOR solo propia versión.
        - sync_from_moodle: mapea Moodle users a PadronRowDTO y activa.
    """

    def __init__(
        self,
        repo: PadronRepository,
        db: AsyncSession,
        audit_repo: Optional[AuditRepository] = None,
    ) -> None:
        self._repo = repo
        self._db = db
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # Preview (sin escritura en DB) — D5
    # -----------------------------------------------------------------------

    async def preview(
        self,
        file_bytes: bytes,
        filename: str,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> list[PadronRowDTO]:
        """
        Parsea el archivo y retorna las filas detectadas SIN escribir en DB.

        Raises PadronValidationError (422) si el archivo es inválido.
        Identidad del actor desde current_user (regla dura #8).
        """
        from app.services.padron_parser import parse_padron_file

        rows = parse_padron_file(file_bytes, filename)
        return rows

    # -----------------------------------------------------------------------
    # Activar — D5
    # -----------------------------------------------------------------------

    async def activar(
        self,
        rows: list[PadronRowDTO],
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> VersionPadron:
        """
        Crea VersionPadron + EntradaPadron y activa la nueva versión.

        La versión anterior (si existe) queda inactiva (D2).
        Emite auditoría PADRON_CARGAR (C-05).
        Identidad del actor desde current_user.user_id (regla dura #8).
        """
        version_data = {
            "tenant_id": current_user.tenant_id,
            "materia_id": materia_id,
            "cohorte_id": cohorte_id,
            "activa": True,
            "cargado_por": current_user.user_id,
        }

        entries_data = [
            {
                "nombre": row.nombre,
                "apellidos": row.apellidos,
                "email_encrypted": row.email,  # EncryptedString cifra en ORM
                "comision": row.comision,
                "regional": row.regional,
            }
            for row in rows
        ]

        version = await self._repo.create_and_activate(version_data, entries_data)

        # Auditoría PADRON_CARGAR (C-05)
        if self._audit_repo is not None:
            from app.services.audit_service import AuditService

            audit_svc = AuditService(repository=self._audit_repo)
            await audit_svc.record(
                actor=current_user,
                action=AuditAction.PADRON_CARGAR,
                modulo="padron",
                entidad_tipo="VersionPadron",
                entidad_id=str(version.id),
                resultado=AuditResultado.ok,
                registros_afectados=len(rows),
                after={"materia_id": str(materia_id), "cohorte_id": str(cohorte_id)},
            )

        return version

    # -----------------------------------------------------------------------
    # Vaciar (soft-delete scope-isolated) — D6
    # -----------------------------------------------------------------------

    async def vaciar(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        current_user: CurrentUser,
        has_gestionar: bool,
    ) -> None:
        """
        Soft-delete de la versión activa para materia×cohorte.

        Scope check (D6, RN-04):
            - Si has_gestionar=True (COORDINADOR/ADMIN): puede vaciar cualquier versión.
            - Si has_gestionar=False (PROFESOR): solo puede vaciar si cargado_por == current_user.id.

        Raises HTTPException(404) si no hay versión activa.
        Raises HTTPException(403) si PROFESOR intenta vaciar versión de otro.
        """
        from datetime import datetime, timezone

        version = await self._repo.get_active_version(materia_id, cohorte_id)
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay versión activa del padrón para esta materia y cohorte.",
            )

        # Scope check (D6)
        if not has_gestionar and version.cargado_por != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Solo puedes vaciar versiones del padrón que hayas cargado tú mismo. "
                    "Se requiere permiso 'padron:gestionar' para vaciar versiones de otros."
                ),
            )

        now = datetime.now(tz=timezone.utc)
        await self._repo.soft_delete_version(version.id, now)

    # -----------------------------------------------------------------------
    # Sync desde Moodle — D7
    # -----------------------------------------------------------------------

    async def sync_from_moodle(
        self,
        course_id: int,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        current_user: CurrentUser,
        moodle_client,
    ) -> VersionPadron:
        """
        Sincroniza usuarios matriculados en un curso de Moodle como nueva versión activa.

        Mapea Moodle user dicts → PadronRowDTO y llama activar().
        Si el cliente falla con MoodleWSError(502) → re-raise como HTTPException(502).
        Identidad desde current_user (regla dura #8).
        """
        from app.integrations.moodle_ws import MoodleWSError

        try:
            moodle_users = await moodle_client.get_enrolled_users(course_id)
        except MoodleWSError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.detail,
            )

        # Mapear Moodle user dicts a PadronRowDTO
        rows = [
            PadronRowDTO(
                nombre=user.get("firstname", ""),
                apellidos=user.get("lastname", ""),
                email=user.get("email", ""),
                comision=None,
                regional=None,
            )
            for user in moodle_users
        ]

        return await self.activar(rows, materia_id, cohorte_id, current_user)
