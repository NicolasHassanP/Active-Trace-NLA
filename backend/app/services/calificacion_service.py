"""
calificacion_service.py — Servicio de importación de calificaciones.

C-10 Design Decisions:
    D3 — aprobado derivado y persistido al importar (derive_aprobado).
    D7 — linkeo fila → EntradaPadron por email contra el padrón activo.
    D8 — importado_por en la clave única de upsert; re-import = upsert.
    D10 — auditoría CALIFICACIONES_IMPORTAR en cada importación exitosa.

CalificacionService.preview(file_bytes, filename, current_user) → PreviewCalificaciones
CalificacionService.importar(req, current_user) → list[CalificacionRead]
CalificacionService.importar_with_report(req, current_user) → (list[CalificacionRead], list[str])
CalificacionService.detectar_sin_corregir(req, current_user) → list[EntregaSinCorregir]

Identity ALWAYS from current_user (JWT session) — never from request body.
Queries ONLY via repositories.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.calificacion import CalificacionOrigen
from app.repositories.audit_repository import AuditRepository
from app.repositories.calificacion_repository import CalificacionRepository
from app.repositories.padron_repository import PadronRepository
from app.schemas.calificacion import (
    CalificacionRead,
    EntregaSinCorregir,
    ImportarCalificacionesRequest,
    PreviewCalificaciones,
    ReporteFinalizacionRequest,
)
from app.services.calificacion_aprobado import derive_aprobado
from app.services.calificacion_parser import parse_calificaciones_file
from app.services.umbral_service import UmbralService


class CalificacionService:
    """
    Service for importing, previewing, and reporting on calificaciones.

    All identity/tenant resolution from current_user (never from request body).
    Delegates DB operations to repositories.
    """

    def __init__(
        self,
        repo: CalificacionRepository,
        padron_repo: PadronRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._repo = repo
        self._padron_repo = padron_repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # preview — parse file, detect activities, no DB write
    # -----------------------------------------------------------------------

    async def preview(
        self,
        file_bytes: bytes,
        filename: str,
        current_user: CurrentUser,
    ) -> PreviewCalificaciones:
        """
        Parse a grades file and return detected activities without writing to DB.

        Returns PreviewCalificaciones with:
            - actividades: list of detected activities with scale.
            - filas: parsed rows (key=header_name, value=cell_value).
            - no_en_padron: empty list at preview time (populated at importar).

        Raises CalificacionValidationError(422) if file is invalid.
        """
        from app.core.config import Settings
        settings = Settings()
        escala_textual = settings.VALORES_APROBATORIOS_DEFECTO + [
            "No satisfactorio", "No alcanzado"
        ]

        result = parse_calificaciones_file(
            file_bytes=file_bytes,
            filename=filename,
            escala_textual=escala_textual,
        )
        return result

    # -----------------------------------------------------------------------
    # importar — persist selected activities (two-step confirm)
    # -----------------------------------------------------------------------

    async def importar(
        self,
        req: ImportarCalificacionesRequest,
        current_user: CurrentUser,
        domain_user_id: Optional[uuid.UUID] = None,
    ) -> List[CalificacionRead]:
        """
        Persist Calificacion records for selected activities.

        Returns list of CalificacionRead for all persisted records.
        Records not in the active padron are silently skipped (not reported in this method).
        Use importar_with_report to get the list of unmatched emails.
        """
        cals, _ = await self.importar_with_report(req=req, current_user=current_user, domain_user_id=domain_user_id)
        return cals

    async def importar_with_report(
        self,
        req: ImportarCalificacionesRequest,
        current_user: CurrentUser,
        domain_user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[List[CalificacionRead], List[str]]:
        """
        Persist Calificacion records for selected activities, also returning unmatched emails.

        Returns (calificaciones, no_en_padron) where:
            - calificaciones: list of CalificacionRead for all persisted records.
            - no_en_padron: list of email strings that had no match in the active padron.

        Steps (D7):
            1. Resolve active padron version for (tenant, materia, cohorte).
            2. Build email → entrada_padron_id map (decrypt all entries in memory).
            3. Get effective umbral from UmbralService (for current_user's asignacion).
            4. For each row × selected_activity: link to entrada_padron, derive aprobado, upsert.
            5. Record CALIFICACIONES_IMPORTAR audit event (D10).
        """
        from app.core.config import Settings
        settings = Settings()

        # 1. Resolve active padron
        active_version = await self._padron_repo.get_active_version(
            materia_id=req.materia_id,
            cohorte_id=req.cohorte_id,
        )
        if active_version is None:
            return [], []

        # 2. Build email → entrada_padron mapping from active padron entries
        from sqlalchemy import select
        from app.models.padron import EntradaPadron

        stmt = select(EntradaPadron).where(
            EntradaPadron.version_id == active_version.id,
            EntradaPadron.deleted_at.is_(None),
        )
        result = await self._repo._session.execute(stmt)
        entries = list(result.scalars().all())

        # The ORM TypeDecorator (EncryptedString) already decrypts email_encrypted on load.
        # So entry.email_encrypted is already the plaintext email.
        email_to_entry: Dict[str, Any] = {}
        for entry in entries:
            try:
                plain_email = entry.email_encrypted  # Already decrypted by TypeDecorator
                if plain_email:
                    email_to_entry[plain_email.lower().strip()] = entry
            except Exception:
                pass

        # 3. Get effective umbral for current user's asignacion
        umbral_svc = UmbralService(repo=self._repo)
        asignacion_id = await self._resolve_asignacion(
            domain_user_id=domain_user_id,
            materia_id=req.materia_id,
            tenant_id=current_user.tenant_id,
        )

        if asignacion_id is not None:
            umbral = await umbral_svc.get_efectivo(
                asignacion_id=asignacion_id,
                materia_id=req.materia_id,
            )
        else:
            # No asignacion found — use system defaults
            umbral_pct = settings.UMBRAL_PCT_DEFECTO
            valores_aprobatorios = settings.VALORES_APROBATORIOS_DEFECTO
            from app.schemas.calificacion import UmbralMateriaRead
            umbral = UmbralMateriaRead(
                materia_id=req.materia_id,
                umbral_pct=umbral_pct,
                valores_aprobatorios=valores_aprobatorios,
                is_default=True,
            )

        # 4. Detect identity column in filas
        email_col = self._find_email_col(req.filas)

        calificaciones: List[CalificacionRead] = []
        no_en_padron: List[str] = []
        now = datetime.now(tz=timezone.utc)

        for fila in req.filas:
            row_email = self._extract_email(fila, email_col)
            if row_email is None:
                continue

            entry = email_to_entry.get(row_email.lower().strip())
            if entry is None:
                if row_email not in no_en_padron:
                    no_en_padron.append(row_email)
                continue

            for actividad in req.actividades_seleccionadas:
                # Find the column in filas for this activity
                nota_numerica, nota_textual = self._extract_nota(fila, actividad)

                aprobado = derive_aprobado(
                    nota_numerica=nota_numerica,
                    nota_textual=nota_textual,
                    nota_maxima=settings.NOTA_MAXIMA_DEFECTO,
                    umbral_pct=umbral.umbral_pct,
                    valores_aprobatorios=umbral.valores_aprobatorios,
                )

                cal = await self._repo.upsert_calificacion(
                    entrada_padron_id=entry.id,
                    materia_id=req.materia_id,
                    actividad=actividad,
                    importado_por=domain_user_id or current_user.user_id,
                    nota_numerica=nota_numerica,
                    nota_textual=nota_textual,
                    aprobado=aprobado,
                    origen=CalificacionOrigen.Importado,
                    importado_at=now,
                )
                calificaciones.append(
                    CalificacionRead(
                        id=cal.id,
                        entrada_padron_id=cal.entrada_padron_id,
                        materia_id=cal.materia_id,
                        actividad=cal.actividad,
                        nota_numerica=cal.nota_numerica,
                        nota_textual=cal.nota_textual,
                        aprobado=cal.aprobado,
                        origen=cal.origen.value if cal.origen else "Importado",
                        importado_at=cal.importado_at,
                    )
                )

        # 5. Audit event (D10)
        if calificaciones:
            from app.services.audit_service import AuditService
            audit_svc = AuditService(repository=self._audit_repo)
            await audit_svc.record(
                actor=current_user,
                action=AuditAction.CALIFICACIONES_IMPORTAR,
                modulo="calificaciones",
                entidad_tipo="Calificacion",
                resultado=AuditResultado.ok,
                registros_afectados=len(calificaciones),
                after={
                    "materia_id": str(req.materia_id),
                    "actividades": req.actividades_seleccionadas,
                    "total_records": len(calificaciones),
                },
            )

        return calificaciones, no_en_padron

    # -----------------------------------------------------------------------
    # detectar_sin_corregir — reporte de finalización (F1.2, RN-07/RN-08)
    # -----------------------------------------------------------------------

    async def detectar_sin_corregir(
        self,
        req: ReporteFinalizacionRequest,
        current_user: CurrentUser,
    ) -> List[EntregaSinCorregir]:
        """
        Cross the LMS completion report with stored Calificaciones to find
        textual-scale activities that are completed but have no grade recorded.

        Only textual-scale activities are checked (RN-08).
        Numeric activities are excluded (absence of numeric grade = not-submitted).

        Args:
            req: contains materia_id, cohorte_id, and filas_finalizacion
                (each fila: {'email': str, 'actividad': str, 'completado': bool, 'escala': str}).

        Returns list of EntregaSinCorregir.
        """
        # Get active padron entries (for email → entry_id lookup)
        active_version = await self._padron_repo.get_active_version(
            materia_id=req.materia_id,
            cohorte_id=req.cohorte_id,
        )
        if active_version is None:
            return []

        from sqlalchemy import select
        from app.models.padron import EntradaPadron

        stmt = select(EntradaPadron).where(
            EntradaPadron.version_id == active_version.id,
            EntradaPadron.deleted_at.is_(None),
        )
        result = await self._repo._session.execute(stmt)
        entries = list(result.scalars().all())

        # The ORM TypeDecorator (EncryptedString) already decrypts email_encrypted on load.
        email_to_entry: Dict[str, Any] = {}
        for entry in entries:
            try:
                plain_email = entry.email_encrypted  # Already decrypted by TypeDecorator
                if plain_email:
                    email_to_entry[plain_email.lower().strip()] = entry
            except Exception:
                pass

        sin_corregir: List[EntregaSinCorregir] = []

        for fila in req.filas_finalizacion:
            # Only textual activities (RN-08)
            escala = str(fila.get("escala", "")).lower()
            if escala != "textual":
                continue

            completado = bool(fila.get("completado", False))
            if not completado:
                continue

            row_email = str(fila.get("email", "")).strip()
            actividad = str(fila.get("actividad", "")).strip()

            entry = email_to_entry.get(row_email.lower())
            if entry is None:
                continue

            # Check if a textual grade exists for this entrada_padron + actividad
            from app.models.calificacion import Calificacion
            stmt2 = select(Calificacion).where(
                Calificacion.tenant_id == self._repo._tenant_id,
                Calificacion.entrada_padron_id == entry.id,
                Calificacion.materia_id == req.materia_id,
                Calificacion.actividad == actividad,
                Calificacion.nota_textual.is_not(None),
                Calificacion.deleted_at.is_(None),
            ).limit(1)
            result2 = await self._repo._session.execute(stmt2)
            existing = result2.scalar_one_or_none()

            if existing is None:
                sin_corregir.append(
                    EntregaSinCorregir(
                        entrada_padron_id=entry.id,
                        actividad=actividad,
                    )
                )

        return sin_corregir

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _find_email_col(self, filas: List[Dict[str, Any]]) -> Optional[str]:
        """Find the email column key in the first fila."""
        import re
        email_patterns = [
            re.compile(r"direcci[oó]n de correo", re.IGNORECASE),
            re.compile(r"^email$", re.IGNORECASE),
            re.compile(r"^correo", re.IGNORECASE),
        ]
        if not filas:
            return None
        first_fila = filas[0]
        for key in first_fila:
            for pat in email_patterns:
                if pat.search(key.strip()):
                    return key
        return None

    def _extract_email(self, fila: Dict[str, Any], email_col: Optional[str]) -> Optional[str]:
        """Extract email string from a fila row."""
        if email_col is None:
            return None
        val = fila.get(email_col)
        if val is None:
            return None
        return str(val).strip() if str(val).strip() else None

    def _extract_nota(
        self,
        fila: Dict[str, Any],
        actividad: str,
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract nota_numerica and nota_textual for a given activity from a fila.

        Looks for the original column name (with or without '(Real)' suffix).
        Returns (nota_numerica, nota_textual).
        """
        nota_numerica: Optional[float] = None
        nota_textual: Optional[str] = None

        # Try numeric: look for key '{actividad} (Real)'
        numeric_key = f"{actividad} (Real)"
        for key in fila:
            if key.strip().lower() == numeric_key.lower():
                val = fila[key]
                if val is not None and str(val).strip():
                    try:
                        nota_numerica = float(str(val).strip())
                    except (ValueError, TypeError):
                        pass
                return nota_numerica, None  # Numeric column: ignore textual

        # Try textual: look for key == actividad
        for key in fila:
            if key.strip() == actividad:
                val = fila[key]
                if val is not None and str(val).strip():
                    nota_textual = str(val).strip()
                return None, nota_textual

        return None, None

    async def _resolve_asignacion(
        self,
        domain_user_id: uuid.UUID,
        materia_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[uuid.UUID]:
        """Resolve asignacion_id for usuario.id (domain_user_id) + materia, or None if not found."""
        from sqlalchemy import select
        from app.models.usuario import Asignacion

        stmt = (
            select(Asignacion)
            .where(
                Asignacion.tenant_id == tenant_id,
                Asignacion.usuario_id == domain_user_id,
                Asignacion.materia_id == materia_id,
                Asignacion.deleted_at.is_(None),
            )
            .order_by(Asignacion.desde.desc())
            .limit(1)
        )
        result = await self._repo._session.execute(stmt)
        asignacion = result.scalar_one_or_none()
        return asignacion.id if asignacion else None
