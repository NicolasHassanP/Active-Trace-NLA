"""
Routers ABM estructura académica — Carrera, Cohorte, Materia.

C-06: Design decisions D9.

Endpoints bajo /api/v1/admin/:
    /carreras  — GET, POST, PATCH /{id}, DELETE /{id}
    /cohortes  — GET, POST, PATCH /{id}, DELETE /{id}
    /materias  — GET, POST, PATCH /{id}, DELETE /{id}

GET (lectura de catálogos) requieren require_permission("estructura:ver");
POST/PATCH/DELETE requieren require_permission("estructura:gestionar") → 403 sin permiso (fail-closed).
tenant_id se deriva del JWT (get_current_user), nunca del body.

Mapeo de excepciones del service:
    ConflictoUnicidad          → 409
    CarreraNoEncontrada        → 404
    CarreraInactiva            → 409
    CarreraConCohorteAbiertas  → 409

snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.repositories.estructura_repository import (
    CarreraRepository,
    CohorteRepository,
    MateriaRepository,
)
from app.schemas.estructura import (
    CarreraCreate,
    CarreraRead,
    CarreraUpdate,
    CohorteCreate,
    CohorteRead,
    CohorteUpdate,
    MateriaCreate,
    MateriaRead,
    MateriaUpdate,
)
from app.services.estructura_service import (
    CarreraConCohorteAbiertas,
    CarreraInactiva,
    CarreraNoEncontrada,
    ConflictoUnicidad,
    EstructuraService,
)

router = APIRouter(prefix="/admin", tags=["estructura"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> EstructuraService:
    return EstructuraService(
        carrera_repo=CarreraRepository(session=db, tenant_id=tenant_id),
        cohorte_repo=CohorteRepository(session=db, tenant_id=tenant_id),
        materia_repo=MateriaRepository(session=db, tenant_id=tenant_id),
    )


# ---------------------------------------------------------------------------
# Carreras
# ---------------------------------------------------------------------------

@router.get("/carreras", response_model=List[CarreraRead])
async def listar_carreras(
    _grant=Depends(require_permission("estructura:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CarreraRead]:
    """Lista carreras activas del tenant."""
    svc = _make_service(db, current_user.tenant_id)
    carreras = await svc.listar_carreras()
    return [CarreraRead.model_validate(c) for c in carreras]


@router.post("/carreras", response_model=CarreraRead, status_code=status.HTTP_201_CREATED)
async def crear_carrera(
    body: CarreraCreate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CarreraRead:
    """Crea una nueva carrera para el tenant del usuario autenticado."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        carrera = await svc.crear_carrera(current_user, body.codigo, body.nombre)
    except ConflictoUnicidad as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return CarreraRead.model_validate(carrera)


@router.patch("/carreras/{carrera_id}", response_model=CarreraRead)
async def editar_carrera(
    carrera_id: uuid.UUID,
    body: CarreraUpdate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CarreraRead:
    """Edita una carrera existente. Bloquea desactivación con cohortes abiertas (409)."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        carrera = await svc.editar_carrera(
            carrera_id,
            codigo=body.codigo,
            nombre=body.nombre,
            estado=body.estado,
        )
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictoUnicidad as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CarreraConCohorteAbiertas as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return CarreraRead.model_validate(carrera)


@router.delete("/carreras/{carrera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_carrera(
    carrera_id: uuid.UUID,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Baja lógica de carrera (soft delete)."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        await svc.dar_baja_carrera(carrera_id)
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# Materias
# ---------------------------------------------------------------------------

@router.get("/materias", response_model=List[MateriaRead])
async def listar_materias(
    _grant=Depends(require_permission("estructura:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MateriaRead]:
    """Lista materias activas del tenant."""
    svc = _make_service(db, current_user.tenant_id)
    materias = await svc.listar_materias()
    return [MateriaRead.model_validate(m) for m in materias]


@router.post("/materias", response_model=MateriaRead, status_code=status.HTTP_201_CREATED)
async def crear_materia(
    body: MateriaCreate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MateriaRead:
    """Crea una nueva materia en el catálogo del tenant."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        materia = await svc.crear_materia(current_user, body.codigo, body.nombre)
    except ConflictoUnicidad as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return MateriaRead.model_validate(materia)


@router.patch("/materias/{materia_id}", response_model=MateriaRead)
async def editar_materia(
    materia_id: uuid.UUID,
    body: MateriaUpdate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MateriaRead:
    """Edita una materia existente."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        materia = await svc.editar_materia(
            materia_id,
            codigo=body.codigo,
            nombre=body.nombre,
            estado=body.estado,
        )
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictoUnicidad as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return MateriaRead.model_validate(materia)


@router.delete("/materias/{materia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_materia(
    materia_id: uuid.UUID,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Baja lógica de materia (soft delete)."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        await svc.dar_baja_materia(materia_id)
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# Cohortes
# ---------------------------------------------------------------------------

@router.get("/cohortes", response_model=List[CohorteRead])
async def listar_cohortes(
    carrera_id: Optional[uuid.UUID] = Query(default=None),
    _grant=Depends(require_permission("estructura:ver")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CohorteRead]:
    """Lista cohortes activas del tenant, opcionalmente filtradas por carrera."""
    svc = _make_service(db, current_user.tenant_id)
    cohortes = await svc.listar_cohortes(carrera_id=carrera_id)
    return [CohorteRead.model_validate(c) for c in cohortes]


@router.post("/cohortes", response_model=CohorteRead, status_code=status.HTTP_201_CREATED)
async def crear_cohorte(
    body: CohorteCreate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohorteRead:
    """Crea una nueva cohorte para una carrera del tenant."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        cohorte = await svc.crear_cohorte(
            current_user,
            carrera_id=body.carrera_id,
            nombre=body.nombre,
            anio=body.anio,
            vig_desde=body.vig_desde,
            vig_hasta=body.vig_hasta,
        )
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictoUnicidad as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CarreraInactiva as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return CohorteRead.model_validate(cohorte)


@router.patch("/cohortes/{cohorte_id}", response_model=CohorteRead)
async def editar_cohorte(
    cohorte_id: uuid.UUID,
    body: CohorteUpdate,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CohorteRead:
    """Edita una cohorte existente. Rechaza dejarla abierta bajo carrera inactiva (409)."""
    svc = _make_service(db, current_user.tenant_id)
    # Detectar si vig_hasta fue provisto explícitamente en el body
    vig_hasta_provided = body.model_fields_set is not None and "vig_hasta" in body.model_fields_set
    try:
        cohorte = await svc.editar_cohorte(
            cohorte_id,
            nombre=body.nombre,
            anio=body.anio,
            vig_desde=body.vig_desde,
            vig_hasta=body.vig_hasta,
            estado=body.estado,
            _vig_hasta_provided=vig_hasta_provided,
        )
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictoUnicidad as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CarreraInactiva as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return CohorteRead.model_validate(cohorte)


@router.delete("/cohortes/{cohorte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_cohorte(
    cohorte_id: uuid.UUID,
    _grant=Depends(require_permission("estructura:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Baja lógica de cohorte (soft delete)."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        await svc.dar_baja_cohorte(cohorte_id)
    except CarreraNoEncontrada as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
