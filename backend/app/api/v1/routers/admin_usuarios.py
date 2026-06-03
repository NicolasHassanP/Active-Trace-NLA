"""
Router ABM usuarios — /api/v1/admin/usuarios

C-07 Design Decision D8:
    Requiere require_permission("usuarios:gestionar") → ADMIN.
    tenant_id SIEMPRE desde el JWT (get_current_user), nunca del body.

Endpoints:
    GET    /admin/usuarios          — lista usuarios activos del tenant
    POST   /admin/usuarios          — crea un nuevo usuario
    PATCH  /admin/usuarios/{id}     — edita un usuario existente
    DELETE /admin/usuarios/{id}     — baja lógica (soft delete)

Mapeo de excepciones del service:
    ConflictoEmail      → 409
    UsuarioNoEncontrado → 404

UsuarioRead (OQ-3): nunca expone dni/cuil/cbu/alias_cbu en texto plano.
snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.models.vigencia import estado_vigencia
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.usuario import (
    AsignacionResumen,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
)
from app.services.usuario_service import (
    ConflictoEmail,
    UsuarioNoEncontrado,
    UsuarioService,
)

router = APIRouter(prefix="/admin", tags=["usuarios"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> UsuarioService:
    return UsuarioService(
        repo=UsuarioRepository(session=db, tenant_id=tenant_id),
    )


def _build_usuario_read(usuario, db: AsyncSession, tenant_id: uuid.UUID) -> UsuarioRead:
    """
    Construye UsuarioRead desde el ORM model.

    Convierte email_encrypted (ORM devuelve plaintext vía EncryptedString)
    en el campo 'email' del schema.
    Computa estado_vigencia para cada asignación.

    Contrato OQ-3: NUNCA serializa dni/cuil/cbu/alias_cbu.
    """
    hoy = date.today()
    asignaciones_resumen = []
    # Las asignaciones se pasan desde el service si se cargan — aquí usamos lista vacía
    # ya que el ORM usa lazy="noload". El endpoint puede cargarlas explícitamente.
    return UsuarioRead(
        id=usuario.id,
        email=usuario.email_encrypted,  # EncryptedString ya descifró en el ORM
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        legajo=usuario.legajo,
        estado=usuario.estado,
        asignaciones=asignaciones_resumen,
        created_at=usuario.created_at,
        updated_at=usuario.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/usuarios", response_model=List[UsuarioRead])
async def listar_usuarios(
    _grant=Depends(require_permission("usuarios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[UsuarioRead]:
    """Lista usuarios activos del tenant (fail-closed: requiere usuarios:gestionar)."""
    svc = _make_service(db, current_user.tenant_id)
    usuarios = await svc.listar_usuarios()
    return [_build_usuario_read(u, db, current_user.tenant_id) for u in usuarios]


@router.post("/usuarios", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    body: UsuarioCreate,
    _grant=Depends(require_permission("usuarios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioRead:
    """Crea un nuevo usuario para el tenant del usuario autenticado."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        usuario = await svc.crear_usuario(
            current_user,
            email=body.email,
            nombre=body.nombre,
            apellidos=body.apellidos,
            legajo=body.legajo,
            legajo_profesional=body.legajo_profesional,
            banco=body.banco,
            regional=body.regional,
            facturador=body.facturador,
            estado=body.estado,
            dni=body.dni,
            cuil=body.cuil,
            cbu=body.cbu,
            alias_cbu=body.alias_cbu,
            auth_identity_id=body.auth_identity_id,
        )
    except ConflictoEmail as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _build_usuario_read(usuario, db, current_user.tenant_id)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioRead)
async def editar_usuario(
    usuario_id: uuid.UUID,
    body: UsuarioUpdate,
    _grant=Depends(require_permission("usuarios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioRead:
    """Edita un usuario existente del tenant (PATCH parcial)."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        usuario = await svc.editar_usuario(
            usuario_id,
            email=body.email,
            nombre=body.nombre,
            apellidos=body.apellidos,
            legajo=body.legajo,
            legajo_profesional=body.legajo_profesional,
            banco=body.banco,
            regional=body.regional,
            facturador=body.facturador,
            estado=body.estado,
            dni=body.dni,
            cuil=body.cuil,
            cbu=body.cbu,
            alias_cbu=body.alias_cbu,
            auth_identity_id=body.auth_identity_id,
        )
    except UsuarioNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictoEmail as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _build_usuario_read(usuario, db, current_user.tenant_id)


@router.delete("/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_baja_usuario(
    usuario_id: uuid.UUID,
    _grant=Depends(require_permission("usuarios:gestionar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Baja lógica de usuario (soft delete)."""
    svc = _make_service(db, current_user.tenant_id)
    try:
        await svc.dar_baja_usuario(usuario_id)
    except UsuarioNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
