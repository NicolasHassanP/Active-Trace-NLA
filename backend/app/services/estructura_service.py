"""
EstructuraService — casos de uso del ABM de estructura académica.

C-06: Design decisions D6, D8.

Responsabilidades:
  - Validar unicidad ANTES de insertar → 409 si existe (D8).
  - Aplicar regla D6 al crear/editar cohorte: carrera referida debe estar Activa
    si la cohorte va a ser abierta (estado=activa y vig_hasta IS NULL).
  - Verificar que carrera_id referido por una cohorte exista, sea del mismo tenant
    y no esté borrado (PA-07 + aislamiento multi-tenant).
  - Bloquear desactivación de carrera con cohortes abiertas → HTTP 409 (D6, OQ-2).
  - Identidad/tenant SIEMPRE desde CurrentUser (regla dura #8).

Lógica de negocio SOLO en services (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.repositories.estructura_repository import (
    CarreraRepository,
    CohorteRepository,
    MateriaRepository,
)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class ConflictoUnicidad(Exception):
    """Código/nombre ya existe (no borrado) en el tenant — HTTP 409."""


class CarreraNoEncontrada(Exception):
    """Carrera no encontrada o no pertenece al tenant — HTTP 404."""


class CarreraInactiva(Exception):
    """La carrera referida está inactiva; no admite cohortes abiertas — HTTP 409."""


class CarreraConCohorteAbiertas(Exception):
    """La carrera tiene cohortes abiertas; no se puede desactivar — HTTP 409."""


# ---------------------------------------------------------------------------
# Helper: cohorte abierta (D9 refactor — reutilizable en ambas reglas D6)
# ---------------------------------------------------------------------------

def _es_cohorte_abierta(estado: EstadoEstructura, vig_hasta: Optional[object]) -> bool:
    """
    Una cohorte es 'abierta' si estado == activa y vig_hasta es None.
    Reutilizado por la regla de creación/edición de cohortes y la regla de desactivación.
    """
    return estado == EstadoEstructura.activa and vig_hasta is None


# ---------------------------------------------------------------------------
# EstructuraService
# ---------------------------------------------------------------------------

class EstructuraService:
    """
    Service para los casos de uso del ABM de estructura académica.

    Uso::

        svc = EstructuraService(carrera_repo, cohorte_repo, materia_repo)
        carrera = await svc.crear_carrera(actor, CarreraCreate(...))
    """

    def __init__(
        self,
        carrera_repo: CarreraRepository,
        cohorte_repo: CohorteRepository,
        materia_repo: MateriaRepository,
    ) -> None:
        self._carreras = carrera_repo
        self._cohortes = cohorte_repo
        self._materias = materia_repo

    # -----------------------------------------------------------------------
    # Carrera — ABM
    # -----------------------------------------------------------------------

    async def crear_carrera(
        self, actor: CurrentUser, codigo: str, nombre: str
    ) -> Carrera:
        """
        Crea una nueva carrera para el tenant del actor.

        Valida unicidad (tenant_id, codigo) antes de insertar.
        Raises ConflictoUnicidad si el código ya existe (no borrado).
        """
        existente = await self._carreras.get_by_codigo(codigo)
        if existente is not None:
            raise ConflictoUnicidad(
                f"Ya existe una carrera con código {codigo!r} en este tenant."
            )
        carrera = Carrera(
            codigo=codigo,
            nombre=nombre,
            estado=EstadoEstructura.activa,
        )
        return await self._carreras.add(carrera)

    async def listar_carreras(self) -> List[Carrera]:
        """Lista carreras activas del tenant (deleted_at IS NULL)."""
        return await self._carreras.list()

    async def obtener_carrera(self, carrera_id: uuid.UUID) -> Optional[Carrera]:
        """Obtiene carrera por id, scoped al tenant. None si no existe."""
        return await self._carreras.get_by_id(carrera_id)

    async def editar_carrera(
        self,
        carrera_id: uuid.UUID,
        *,
        codigo: Optional[str] = None,
        nombre: Optional[str] = None,
        estado: Optional[EstadoEstructura] = None,
    ) -> Carrera:
        """
        Edita campos de una carrera.

        Si se cambia el estado a 'inactiva', verifica que no tenga cohortes abiertas (D6).
        Si se cambia el codigo, verifica unicidad.
        Raises CarreraNoEncontrada, ConflictoUnicidad, CarreraConCohorteAbiertas.
        """
        carrera = await self._carreras.get_by_id(carrera_id)
        if carrera is None:
            raise CarreraNoEncontrada(f"Carrera {carrera_id} no encontrada.")

        # Validar unicidad si cambia el código
        if codigo is not None and codigo != carrera.codigo:
            existente = await self._carreras.get_by_codigo(codigo)
            if existente is not None:
                raise ConflictoUnicidad(
                    f"Ya existe una carrera con código {codigo!r} en este tenant."
                )

        # Bloquear desactivación si tiene cohortes abiertas (D6)
        if estado == EstadoEstructura.inactiva and carrera.estado == EstadoEstructura.activa:
            count = await self._carreras.list_open_cohortes(carrera_id)
            if count > 0:
                raise CarreraConCohorteAbiertas(
                    f"La carrera {carrera.codigo!r} tiene {count} cohorte(s) abierta(s). "
                    "Debe cerrar o inactivar todas las cohortes abiertas antes de "
                    "inactivar la carrera."
                )

        updates = {}
        if codigo is not None:
            updates["codigo"] = codigo
        if nombre is not None:
            updates["nombre"] = nombre
        if estado is not None:
            updates["estado"] = estado

        return await self._carreras.update(carrera, **updates)

    async def dar_baja_carrera(self, carrera_id: uuid.UUID) -> Carrera:
        """
        Baja lógica de carrera (soft delete).
        Raises CarreraNoEncontrada si no existe.
        """
        carrera = await self._carreras.get_by_id(carrera_id)
        if carrera is None:
            raise CarreraNoEncontrada(f"Carrera {carrera_id} no encontrada.")
        await self._carreras.delete(carrera)
        return carrera

    # -----------------------------------------------------------------------
    # Materia — ABM
    # -----------------------------------------------------------------------

    async def crear_materia(
        self, actor: CurrentUser, codigo: str, nombre: str
    ) -> Materia:
        """
        Crea una nueva materia en el catálogo del tenant.

        Valida unicidad (tenant_id, codigo) antes de insertar.
        Raises ConflictoUnicidad si el código ya existe (no borrado).
        """
        existente = await self._materias.get_by_codigo(codigo)
        if existente is not None:
            raise ConflictoUnicidad(
                f"Ya existe una materia con código {codigo!r} en este tenant."
            )
        materia = Materia(
            codigo=codigo,
            nombre=nombre,
            estado=EstadoEstructura.activa,
        )
        return await self._materias.add(materia)

    async def listar_materias(self) -> List[Materia]:
        """Lista materias activas del tenant (deleted_at IS NULL)."""
        return await self._materias.list()

    async def obtener_materia(self, materia_id: uuid.UUID) -> Optional[Materia]:
        """Obtiene materia por id, scoped al tenant. None si no existe."""
        return await self._materias.get_by_id(materia_id)

    async def editar_materia(
        self,
        materia_id: uuid.UUID,
        *,
        codigo: Optional[str] = None,
        nombre: Optional[str] = None,
        estado: Optional[EstadoEstructura] = None,
    ) -> Materia:
        """
        Edita campos de una materia.

        Si se cambia el codigo, verifica unicidad.
        Raises MateriaNoEncontrada, ConflictoUnicidad.
        """
        materia = await self._materias.get_by_id(materia_id)
        if materia is None:
            raise CarreraNoEncontrada(f"Materia {materia_id} no encontrada.")

        if codigo is not None and codigo != materia.codigo:
            existente = await self._materias.get_by_codigo(codigo)
            if existente is not None:
                raise ConflictoUnicidad(
                    f"Ya existe una materia con código {codigo!r} en este tenant."
                )

        updates = {}
        if codigo is not None:
            updates["codigo"] = codigo
        if nombre is not None:
            updates["nombre"] = nombre
        if estado is not None:
            updates["estado"] = estado

        return await self._materias.update(materia, **updates)

    async def dar_baja_materia(self, materia_id: uuid.UUID) -> Materia:
        """
        Baja lógica de materia (soft delete).
        Raises CarreraNoEncontrada si no existe.
        """
        materia = await self._materias.get_by_id(materia_id)
        if materia is None:
            raise CarreraNoEncontrada(f"Materia {materia_id} no encontrada.")
        await self._materias.delete(materia)
        return materia

    # -----------------------------------------------------------------------
    # Cohorte — ABM
    # -----------------------------------------------------------------------

    async def crear_cohorte(
        self,
        actor: CurrentUser,
        carrera_id: uuid.UUID,
        nombre: str,
        anio: int,
        vig_desde,
        vig_hasta=None,
    ) -> Cohorte:
        """
        Crea una nueva cohorte asociada a una carrera del mismo tenant.

        Validaciones:
          1. carrera_id debe existir en el mismo tenant y no estar borrada.
          2. Unicidad (tenant_id, carrera_id, nombre).
          3. Si la cohorte es abierta (vig_hasta IS NULL), la carrera debe estar Activa (D6).

        Raises CarreraNoEncontrada, ConflictoUnicidad, CarreraInactiva.
        """
        # 1. Validar que la carrera exista en este tenant
        carrera = await self._carreras.get_by_id(carrera_id)
        if carrera is None:
            raise CarreraNoEncontrada(
                f"Carrera {carrera_id} no encontrada en este tenant."
            )

        # 2. Unicidad (tenant_id, carrera_id, nombre)
        existente = await self._cohortes.get_by_carrera_nombre(carrera_id, nombre)
        if existente is not None:
            raise ConflictoUnicidad(
                f"Ya existe una cohorte con nombre {nombre!r} en la carrera {carrera_id}."
            )

        # 3. Regla D6: cohorte abierta bajo carrera inactiva → rechazar
        if _es_cohorte_abierta(EstadoEstructura.activa, vig_hasta):
            if carrera.estado == EstadoEstructura.inactiva:
                raise CarreraInactiva(
                    f"La carrera {carrera.codigo!r} está inactiva. "
                    "No se puede crear una cohorte abierta bajo una carrera inactiva."
                )

        cohorte = Cohorte(
            carrera_id=carrera_id,
            nombre=nombre,
            anio=anio,
            vig_desde=vig_desde,
            vig_hasta=vig_hasta,
            estado=EstadoEstructura.activa,
        )
        return await self._cohortes.add(cohorte)

    async def listar_cohortes(
        self, *, carrera_id: Optional[uuid.UUID] = None
    ) -> List[Cohorte]:
        """Lista cohortes activas del tenant, opcionalmente filtradas por carrera."""
        return await self._cohortes.list(carrera_id=carrera_id)

    async def obtener_cohorte(self, cohorte_id: uuid.UUID) -> Optional[Cohorte]:
        """Obtiene cohorte por id, scoped al tenant. None si no existe."""
        return await self._cohortes.get_by_id(cohorte_id)

    async def editar_cohorte(
        self,
        cohorte_id: uuid.UUID,
        *,
        nombre: Optional[str] = None,
        anio: Optional[int] = None,
        vig_desde=None,
        vig_hasta=None,
        estado: Optional[EstadoEstructura] = None,
        _vig_hasta_provided: bool = False,
    ) -> Cohorte:
        """
        Edita campos de una cohorte.

        Si el resultado queda abierto (estado=activa y vig_hasta IS NULL),
        verifica que la carrera esté Activa (D6).
        Si cambia el nombre, verifica unicidad (carrera_id, nombre).
        Raises CarreraNoEncontrada, ConflictoUnicidad, CarreraInactiva.
        """
        cohorte = await self._cohortes.get_by_id(cohorte_id)
        if cohorte is None:
            raise CarreraNoEncontrada(f"Cohorte {cohorte_id} no encontrada.")

        # Validar unicidad si cambia el nombre
        nuevo_nombre = nombre if nombre is not None else cohorte.nombre
        if nombre is not None and nombre != cohorte.nombre:
            existente = await self._cohortes.get_by_carrera_nombre(
                cohorte.carrera_id, nombre
            )
            if existente is not None:
                raise ConflictoUnicidad(
                    f"Ya existe una cohorte con nombre {nombre!r} en la carrera {cohorte.carrera_id}."
                )

        # Determinar el nuevo estado de apertura
        nuevo_estado = estado if estado is not None else cohorte.estado
        # vig_hasta: usar el valor provisto si se provee explícitamente, si no el actual
        nuevo_vig_hasta = vig_hasta if _vig_hasta_provided else cohorte.vig_hasta

        # Regla D6: si el resultado queda abierto, la carrera debe estar Activa
        if _es_cohorte_abierta(nuevo_estado, nuevo_vig_hasta):
            carrera = await self._carreras.get_by_id(cohorte.carrera_id)
            if carrera is not None and carrera.estado == EstadoEstructura.inactiva:
                raise CarreraInactiva(
                    f"La carrera {carrera.codigo!r} está inactiva. "
                    "No se puede dejar una cohorte abierta bajo una carrera inactiva."
                )

        updates = {}
        if nombre is not None:
            updates["nombre"] = nombre
        if anio is not None:
            updates["anio"] = anio
        if vig_desde is not None:
            updates["vig_desde"] = vig_desde
        if _vig_hasta_provided:
            updates["vig_hasta"] = vig_hasta
        if estado is not None:
            updates["estado"] = estado

        return await self._cohortes.update(cohorte, **updates)

    async def dar_baja_cohorte(self, cohorte_id: uuid.UUID) -> Cohorte:
        """
        Baja lógica de cohorte (soft delete).
        Raises CarreraNoEncontrada si no existe.
        """
        cohorte = await self._cohortes.get_by_id(cohorte_id)
        if cohorte is None:
            raise CarreraNoEncontrada(f"Cohorte {cohorte_id} no encontrada.")
        await self._cohortes.delete(cohorte)
        return cohorte
