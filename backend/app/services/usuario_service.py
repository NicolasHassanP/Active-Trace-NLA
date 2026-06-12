"""
UsuarioService y AsignacionService para C-07 usuarios y asignaciones.

UsuarioService: ABM de usuarios (email_hash, PII, unicidad).
AsignacionService: ABM de asignaciones docentes (tenant-scope, RN-11, vigencia,
    notificación vía mensajería al crear asignación).

Excepciones → HTTP: ConflictoEmail→409, UsuarioNoEncontrado→404,
    AsignacionNoEncontrada→404, ReferenciaInvalida→422.
Regla dura #11: lógica SOLO aquí, queries SOLO en repositories. snake_case; ≤500 LOC.
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
from app.repositories.estructura_repository import CohorteRepository, MateriaRepository
from app.repositories.mensajeria_repository import MensajeriaRepository
from app.repositories.usuario_repository import (
    AsignacionRepository,
    UsuarioRepository,
)
from app.services.asignacion_notif import notificar_asignacion


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

    Valida tenant-scope, RN-11 (jerarquía acíclica), multi-rol y vigencia.
    Identidad/tenant SIEMPRE desde CurrentUser (regla dura #8).
    """

    def __init__(
        self,
        asignacion_repo: AsignacionRepository,
        usuario_repo: UsuarioRepository,
        mensajeria_repo: Optional[MensajeriaRepository] = None,
        materia_repo: Optional[MateriaRepository] = None,
        cohorte_repo: Optional[CohorteRepository] = None,
    ) -> None:
        self._asignaciones = asignacion_repo
        self._usuarios = usuario_repo
        self._mensajeria_repo = mensajeria_repo
        self._materia_repo = materia_repo
        self._cohorte_repo = cohorte_repo

    # -----------------------------------------------------------------------
    # RN-11 — Validación de jerarquía acíclica de responsables
    # -----------------------------------------------------------------------

    async def _validar_aciclo_responsable(
        self,
        usuario_id: uuid.UUID,
        responsable_id: uuid.UUID,
    ) -> None:
        """
        RN-11: valida que la asignación no forme un ciclo en la jerarquía.

        Detecta auto-referencia (A→A) y ciclos transitivos (A→B→…→A).
        Traversa la cadena solo sobre asignaciones activas, con scope de tenant.
        Raises ReferenciaInvalida si detecta ciclo.
        Soft limit de 1000 nodos como defensa ante datos corruptos.
        """
        if usuario_id == responsable_id:
            raise ReferenciaInvalida(
                f"Ciclo detectado: el usuario {usuario_id} no puede ser "
                "su propio responsable (auto-referencia)."
            )

        visited: set = set()
        queue = {responsable_id}
        _LIMIT = 1000

        while queue:
            if len(visited) >= _LIMIT:
                break
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            ancestors = await self._asignaciones.get_responsables_de_usuario(current)
            if usuario_id in ancestors:
                raise ReferenciaInvalida(
                    f"Ciclo detectado: asignar {responsable_id} como responsable "
                    f"de {usuario_id} crearía un ciclo en la jerarquía."
                )
            queue.update(ancestors - visited)

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
        domain_user_id: Optional[uuid.UUID] = None,
    ) -> Asignacion:
        """
        Crea una nueva asignación para un usuario del tenant.

        Valida usuario_id, responsable_id (RN-11) y refs opcionales.
        domain_user_id: usuario.id del actor — activa notificación mensajería si ≠ None.
        Raises UsuarioNoEncontrado, ReferenciaInvalida.
        """
        # Validar usuario
        usuario = await self._usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado(
                f"Usuario {usuario_id} no encontrado en este tenant."
            )

        # Validar responsable: existe en el tenant y no forma ciclo (RN-11)
        if responsable_id is not None:
            responsable = await self._usuarios.get_by_id(responsable_id)
            if responsable is None:
                raise ReferenciaInvalida(
                    f"Responsable {responsable_id} no encontrado en este tenant."
                )
            await self._validar_aciclo_responsable(usuario_id, responsable_id)

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
        saved = await self._asignaciones.add(asignacion)

        # Notify the assigned docente (skip self-assignment)
        if domain_user_id is not None and self._mensajeria_repo is not None:
            # Resolver nombres vía repositories (queries solo en repos — regla #11)
            materia_nombre: Optional[str] = None
            cohorte_nombre: Optional[str] = None
            if materia_id is not None and self._materia_repo is not None:
                mat = await self._materia_repo.get_by_id(materia_id)
                if mat is not None:
                    materia_nombre = mat.nombre
            if cohorte_id is not None and self._cohorte_repo is not None:
                coh = await self._cohorte_repo.get_by_id(cohorte_id)
                if coh is not None:
                    cohorte_nombre = coh.nombre
            await notificar_asignacion(
                self._mensajeria_repo,
                remitente_id=domain_user_id,
                destinatario_id=usuario_id,
                materia_id=materia_id,
                cohorte_id=cohorte_id,
                rol=rol,
                desde=desde,
                materia_nombre=materia_nombre,
                cohorte_nombre=cohorte_nombre,
            )

        return saved

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

        Si se cambia el responsable_id, valida que exista en el tenant
        y que no forme un ciclo en la jerarquía (RN-11).
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
            # RN-11: validar jerarquía acíclica usando el usuario dueño de la asignación
            await self._validar_aciclo_responsable(asignacion.usuario_id, responsable_id)

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
