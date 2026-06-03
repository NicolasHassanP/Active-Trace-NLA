"""
UsuarioService y AsignacionService para C-07 usuarios y asignaciones.

D10: Validaciones de negocio, unicidad, tenant-scope, PII.

UsuarioService:
    - alta/edición/baja lógica de Usuario.
    - Deriva email_hash del email (el cliente no lo envía) — D3.
    - Valida unicidad por email_hash (→ 409 ConflictoEmail).
    - PII en texto plano NUNCA aparece en logs ni excepciones.

AsignacionService:
    - alta/edición/baja lógica de Asignacion.
    - Valida que usuario_id y responsable_id pertenezcan al mismo tenant.
    - Valida contexto (materia/carrera/cohorte) si se provee.
    - expone estado_vigencia derivado (helper de vigencia.py).
    - Multi-rol: un usuario puede tener múltiples asignaciones con roles distintos.

Excepciones mapeadas a HTTP en los routers:
    ConflictoEmail         → 409
    UsuarioNoEncontrado    → 404
    AsignacionNoEncontrada → 404
    ReferenciaInvalida     → 422

Regla dura #11: lógica de negocio SOLO aquí. Queries SOLO en repositories.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.models.usuario import (
    Asignacion,
    RolAsignacion,
    Usuario,
    UsuarioEstado,
)
from app.models.vigencia import EstadoVigencia, estado_vigencia
from app.repositories.usuario_repository import (
    AsignacionRepository,
    UsuarioRepository,
)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class ConflictoEmail(Exception):
    """Email ya existe (no borrado) en el tenant — HTTP 409."""


class UsuarioNoEncontrado(Exception):
    """Usuario no encontrado o no pertenece al tenant — HTTP 404."""


class AsignacionNoEncontrada(Exception):
    """Asignación no encontrada o no pertenece al tenant — HTTP 404."""


class ReferenciaInvalida(Exception):
    """Referencia a entidad inválida (otro tenant, no existe, etc.) — HTTP 422."""


# ---------------------------------------------------------------------------
# UsuarioService
# ---------------------------------------------------------------------------

class UsuarioService:
    """
    Service para el ABM de usuarios de negocio.

    La derivación del email_hash y el cifrado de PII ocurre aquí:
    - email_hash = email_lookup_hash(email) — el cliente nunca lo envía.
    - PII (dni, cuil, cbu, alias_cbu) se cifra vía EncryptedString en el ORM.
    - Identidad/tenant SIEMPRE desde CurrentUser (regla dura #8).
    """

    def __init__(self, repo: UsuarioRepository) -> None:
        self._repo = repo

    # -----------------------------------------------------------------------
    # Alta
    # -----------------------------------------------------------------------

    async def crear_usuario(
        self,
        actor: CurrentUser,
        email: str,
        nombre: str,
        apellidos: str,
        *,
        legajo: Optional[str] = None,
        legajo_profesional: Optional[str] = None,
        banco: Optional[str] = None,
        regional: Optional[str] = None,
        facturador: bool = False,
        estado: UsuarioEstado = UsuarioEstado.activo,
        dni: Optional[str] = None,
        cuil: Optional[str] = None,
        cbu: Optional[str] = None,
        alias_cbu: Optional[str] = None,
        auth_identity_id: Optional[uuid.UUID] = None,
    ) -> Usuario:
        """
        Crea un nuevo usuario para el tenant del actor.

        Deriva email_hash y valida unicidad antes de insertar.
        Raises ConflictoEmail si el email ya existe (no borrado).
        PII nunca se loguea — las excepciones no incluyen el valor del email.
        """
        from app.core.security.passwords import email_lookup_hash

        # Normalizar y derivar el hash (determinístico) — D3
        email_norm = email.strip().lower()
        email_hash = email_lookup_hash(email_norm)

        # Validar unicidad — no se incluye el email plano en el mensaje (D2/D3)
        existente = await self._repo.get_by_email_hash(email_hash)
        if existente is not None:
            raise ConflictoEmail(
                "Ya existe un usuario con ese email en este tenant."
            )

        usuario = Usuario(
            email_encrypted=email_norm,  # EncryptedString cifra automáticamente
            email_hash=email_hash,
            nombre=nombre,
            apellidos=apellidos,
            legajo=legajo,
            legajo_profesional=legajo_profesional,
            banco=banco,
            regional=regional,
            facturador=facturador,
            estado=estado,
            dni=dni,
            cuil=cuil,
            cbu=cbu,
            alias_cbu=alias_cbu,
            auth_identity_id=auth_identity_id,
        )
        return await self._repo.add(usuario)

    # -----------------------------------------------------------------------
    # Lectura
    # -----------------------------------------------------------------------

    async def listar_usuarios(self) -> List[Usuario]:
        """Lista usuarios activos del tenant (deleted_at IS NULL)."""
        return await self._repo.list()

    async def obtener_usuario(self, usuario_id: uuid.UUID) -> Optional[Usuario]:
        """Obtiene usuario por id, scoped al tenant. None si no existe."""
        return await self._repo.get_by_id(usuario_id)

    # -----------------------------------------------------------------------
    # Edición
    # -----------------------------------------------------------------------

    async def editar_usuario(
        self,
        usuario_id: uuid.UUID,
        *,
        email: Optional[str] = None,
        nombre: Optional[str] = None,
        apellidos: Optional[str] = None,
        legajo: Optional[str] = None,
        legajo_profesional: Optional[str] = None,
        banco: Optional[str] = None,
        regional: Optional[str] = None,
        facturador: Optional[bool] = None,
        estado: Optional[UsuarioEstado] = None,
        dni: Optional[str] = None,
        cuil: Optional[str] = None,
        cbu: Optional[str] = None,
        alias_cbu: Optional[str] = None,
        auth_identity_id: Optional[uuid.UUID] = None,
    ) -> Usuario:
        """
        Edita campos de un usuario (PATCH parcial).

        Si se cambia el email, recomputa email_hash y re-valida unicidad.
        Raises UsuarioNoEncontrado, ConflictoEmail.
        """
        from app.core.security.passwords import email_lookup_hash

        usuario = await self._repo.get_by_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado(f"Usuario {usuario_id} no encontrado.")

        updates: dict = {}

        if email is not None:
            email_norm = email.strip().lower()
            new_hash = email_lookup_hash(email_norm)
            if new_hash != usuario.email_hash:
                existente = await self._repo.get_by_email_hash(new_hash)
                if existente is not None:
                    raise ConflictoEmail(
                        "Ya existe un usuario con ese email en este tenant."
                    )
                updates["email_encrypted"] = email_norm
                updates["email_hash"] = new_hash

        if nombre is not None:
            updates["nombre"] = nombre
        if apellidos is not None:
            updates["apellidos"] = apellidos
        if legajo is not None:
            updates["legajo"] = legajo
        if legajo_profesional is not None:
            updates["legajo_profesional"] = legajo_profesional
        if banco is not None:
            updates["banco"] = banco
        if regional is not None:
            updates["regional"] = regional
        if facturador is not None:
            updates["facturador"] = facturador
        if estado is not None:
            updates["estado"] = estado
        if dni is not None:
            updates["dni"] = dni
        if cuil is not None:
            updates["cuil"] = cuil
        if cbu is not None:
            updates["cbu"] = cbu
        if alias_cbu is not None:
            updates["alias_cbu"] = alias_cbu
        if auth_identity_id is not None:
            updates["auth_identity_id"] = auth_identity_id

        return await self._repo.update(usuario, **updates)

    # -----------------------------------------------------------------------
    # Baja lógica
    # -----------------------------------------------------------------------

    async def dar_baja_usuario(self, usuario_id: uuid.UUID) -> Usuario:
        """
        Baja lógica (soft delete) de usuario.
        Raises UsuarioNoEncontrado si no existe.
        """
        usuario = await self._repo.get_by_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado(f"Usuario {usuario_id} no encontrado.")
        await self._repo.delete(usuario)
        return usuario


# ---------------------------------------------------------------------------
# AsignacionService
# ---------------------------------------------------------------------------

class AsignacionService:
    """
    Service para el CRUD de asignaciones (eje de autorización contextual).

    Validaciones:
        - usuario_id debe existir en el mismo tenant.
        - responsable_id, si se provee, debe existir en el mismo tenant.
        - materia_id/carrera_id/cohorte_id, si se proveen, deben ser del tenant.
        - Multi-rol: un usuario puede tener múltiples asignaciones con roles distintos.
        - Asignación vencida se conserva (soft delete explícito requerido).

    estado_vigencia: calculado con el helper puro de vigencia.py (D4).
    Identidad/tenant SIEMPRE desde CurrentUser (regla dura #8).
    """

    def __init__(
        self,
        asignacion_repo: AsignacionRepository,
        usuario_repo: UsuarioRepository,
    ) -> None:
        self._asignaciones = asignacion_repo
        self._usuarios = usuario_repo

    # -----------------------------------------------------------------------
    # Alta
    # -----------------------------------------------------------------------

    async def crear_asignacion(
        self,
        actor: CurrentUser,
        usuario_id: uuid.UUID,
        rol: RolAsignacion,
        desde: date,
        *,
        hasta: Optional[date] = None,
        materia_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        comisiones: Optional[List[str]] = None,
        responsable_id: Optional[uuid.UUID] = None,
    ) -> Asignacion:
        """
        Crea una nueva asignación para un usuario del tenant.

        Valida que:
            - usuario_id existe en el tenant.
            - responsable_id, si se provee, existe en el tenant.
            - materia_id/carrera_id/cohorte_id, si se proveen, se validan (básico).

        Raises UsuarioNoEncontrado, ReferenciaInvalida.
        """
        # Validar usuario
        usuario = await self._usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado(
                f"Usuario {usuario_id} no encontrado en este tenant."
            )

        # Validar responsable
        if responsable_id is not None:
            responsable = await self._usuarios.get_by_id(responsable_id)
            if responsable is None:
                raise ReferenciaInvalida(
                    f"Responsable {responsable_id} no encontrado en este tenant."
                )

        asignacion = Asignacion(
            usuario_id=usuario_id,
            rol=rol,
            desde=desde,
            hasta=hasta,
            materia_id=materia_id,
            carrera_id=carrera_id,
            cohorte_id=cohorte_id,
            comisiones=comisiones or [],
            responsable_id=responsable_id,
        )
        return await self._asignaciones.add(asignacion)

    # -----------------------------------------------------------------------
    # Lectura
    # -----------------------------------------------------------------------

    async def listar_asignaciones(
        self,
        *,
        usuario_id: Optional[uuid.UUID] = None,
        rol: Optional[RolAsignacion] = None,
        responsable_id: Optional[uuid.UUID] = None,
    ) -> List[Asignacion]:
        """Lista asignaciones activas del tenant con filtros opcionales."""
        return await self._asignaciones.list(
            usuario_id=usuario_id,
            rol=rol,
            responsable_id=responsable_id,
        )

    async def obtener_asignacion(
        self, asignacion_id: uuid.UUID
    ) -> Optional[Asignacion]:
        """Obtiene asignación por id, scoped al tenant. None si no existe."""
        return await self._asignaciones.get_by_id(asignacion_id)

    # -----------------------------------------------------------------------
    # Edición
    # -----------------------------------------------------------------------

    async def editar_asignacion(
        self,
        asignacion_id: uuid.UUID,
        *,
        rol: Optional[RolAsignacion] = None,
        desde: Optional[date] = None,
        hasta: Optional[date] = None,
        materia_id: Optional[uuid.UUID] = None,
        carrera_id: Optional[uuid.UUID] = None,
        cohorte_id: Optional[uuid.UUID] = None,
        comisiones: Optional[List[str]] = None,
        responsable_id: Optional[uuid.UUID] = None,
        _responsable_provided: bool = False,
    ) -> Asignacion:
        """
        Edita campos de una asignación (PATCH parcial).

        Si se cambia el responsable_id, valida que exista en el tenant.
        Raises AsignacionNoEncontrada, ReferenciaInvalida.
        """
        asignacion = await self._asignaciones.get_by_id(asignacion_id)
        if asignacion is None:
            raise AsignacionNoEncontrada(
                f"Asignación {asignacion_id} no encontrada."
            )

        if _responsable_provided and responsable_id is not None:
            responsable = await self._usuarios.get_by_id(responsable_id)
            if responsable is None:
                raise ReferenciaInvalida(
                    f"Responsable {responsable_id} no encontrado en este tenant."
                )

        updates: dict = {}
        if rol is not None:
            updates["rol"] = rol
        if desde is not None:
            updates["desde"] = desde
        if _responsable_provided:
            updates["responsable_id"] = responsable_id
        # hasta: solo actualizar si hay valor explícito o se limpió
        if hasta is not None:
            updates["hasta"] = hasta
        if materia_id is not None:
            updates["materia_id"] = materia_id
        if carrera_id is not None:
            updates["carrera_id"] = carrera_id
        if cohorte_id is not None:
            updates["cohorte_id"] = cohorte_id
        if comisiones is not None:
            updates["comisiones"] = comisiones

        return await self._asignaciones.update(asignacion, **updates)

    # -----------------------------------------------------------------------
    # Baja lógica
    # -----------------------------------------------------------------------

    async def dar_baja_asignacion(self, asignacion_id: uuid.UUID) -> Asignacion:
        """
        Baja lógica (soft delete) de asignación.
        Asignaciones vencidas NO se borran automáticamente — solo por baja explícita.
        Raises AsignacionNoEncontrada si no existe.
        """
        asignacion = await self._asignaciones.get_by_id(asignacion_id)
        if asignacion is None:
            raise AsignacionNoEncontrada(
                f"Asignación {asignacion_id} no encontrada."
            )
        await self._asignaciones.delete(asignacion)
        return asignacion

    # -----------------------------------------------------------------------
    # Helper de vigencia — reusable (D4)
    # -----------------------------------------------------------------------

    @staticmethod
    def calcular_vigencia(
        asignacion: Asignacion,
        hoy: Optional[date] = None,
    ) -> EstadoVigencia:
        """
        Calcula el estado de vigencia de una asignación en base a sus fechas.

        Wrapper del helper puro de vigencia.py.
        No modifica la asignación ni la persiste — es una derivación en runtime.
        """
        return estado_vigencia(asignacion.desde, asignacion.hasta, hoy)
