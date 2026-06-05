"""
Router de perfil propio — /api/v1/perfil

C-20 Design Decisions:
    D1 — Perfil reusa Usuario; endpoints de autoservicio.
    D2 — cuil de solo lectura: PerfilUpdate no lo declara → extra='forbid' da 422.
    D3 — PerfilRead devuelve PII en claro al dueño.
    D7 — Identidad SIEMPRE del JWT; ignora cualquier id de la petición.
    D8 — require_permission("perfil:editar") en PATCH (fail-closed → 403).

Endpoints:
    GET   /perfil  — lee el perfil del titular del JWT.
    PATCH /perfil  — edita el perfil del titular del JWT.

Mapeo de excepciones:
    PerfilNoEncontrado  → 404
    ConflictoEmailPerfil → 409

Flujo: Router → PerfilService → PerfilRepository → Usuario model.
Sin lógica de negocio en el router (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, get_db, require_permission
from app.repositories.audit_repository import AuditRepository
from app.repositories.perfil_repository import PerfilRepository
from app.schemas.perfil import PerfilRead, PerfilUpdate
from app.services.audit_service import AuditService
from app.services.perfil_service import ConflictoEmailPerfil, PerfilNoEncontrado, PerfilService

router = APIRouter(prefix="/perfil", tags=["perfil"])


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _make_service(db: AsyncSession, tenant_id: uuid.UUID) -> PerfilService:
    repo = PerfilRepository(session=db, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db, tenant_id=tenant_id)
    audit_svc = AuditService(repository=audit_repo)
    return PerfilService(repo=repo, audit_svc=audit_svc)


def _build_perfil_read(usuario) -> PerfilRead:
    """
    Construye PerfilRead desde el ORM model.

    Convierte email_encrypted (plaintext via EncryptedString) en 'email'.
    Expone PII en claro al dueño (D3).
    """
    return PerfilRead(
        id=usuario.id,
        email=usuario.email_encrypted,
        nombre=usuario.nombre,
        apellidos=usuario.apellidos,
        dni=usuario.dni,
        cuil=usuario.cuil,
        cbu=usuario.cbu,
        alias_cbu=usuario.alias_cbu,
        genero=getattr(usuario, "genero", None),
        legajo=usuario.legajo,
        legajo_profesional=usuario.legajo_profesional,
        banco=usuario.banco,
        regional=usuario.regional,
        facturador=usuario.facturador,
        created_at=usuario.created_at,
        updated_at=usuario.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=PerfilRead)
async def obtener_perfil(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerfilRead:
    """
    Lee el perfil propio del titular del JWT.

    Identidad SIEMPRE del JWT — ignora ?usuario_id u otros params.
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        usuario = await svc.obtener_perfil(current_user)
    except PerfilNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return _build_perfil_read(usuario)


@router.patch("", response_model=PerfilRead)
async def actualizar_perfil(
    body: PerfilUpdate,
    _grant=Depends(require_permission("perfil:editar")),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PerfilRead:
    """
    Edita el perfil propio del titular del JWT (PATCH parcial).

    Requiere permiso 'perfil:editar' (fail-closed → 403).
    cuil no está en PerfilUpdate → extra='forbid' lo rechaza con 422.
    """
    svc = _make_service(db, current_user.tenant_id)
    try:
        usuario = await svc.actualizar_perfil(
            current_user,
            nombre=body.nombre,
            apellidos=body.apellidos,
            dni=body.dni,
            genero=body.genero,
            banco=body.banco,
            cbu=body.cbu,
            alias_cbu=body.alias_cbu,
            regional=body.regional,
            email=body.email,
            facturador=body.facturador,
            legajo_profesional=body.legajo_profesional,
        )
    except PerfilNoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ConflictoEmailPerfil as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _build_perfil_read(usuario)
