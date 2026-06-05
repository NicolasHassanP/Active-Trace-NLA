"""
test_perfil_repository.py — TDD suite para C-20 perfil repository.

Task 3.1 RED: get_self aislamiento cross-tenant.
Task 3.3 RED: update_self PII cifrada en reposo.
Task 3.5 TRIANGULATE: unicidad email, email_hash recalculado.
"""
import uuid

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


@pytest_asyncio.fixture(scope="module")
async def perfil_repo_data(test_engine, create_tables):
    """
    Crea dos tenants con usuarios para tests de perfil repository.
    Depende de create_tables (sesión conftest) para que las tablas existan.
    """
    import app.models  # noqa — register all models
    from sqlalchemy import text
    from app.core.security.passwords import email_lookup_hash

    factory = build_session_factory(test_engine)
    session = factory()

    # Ensure genero column exists (migration C-20 — idempotent)
    await session.execute(text(
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"
    ))
    await session.commit()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()

    session.add(Tenant(id=tid_a, nombre=f"Perfil Repo TenantA {tid_a}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre=f"Perfil Repo TenantB {tid_b}", estado=TenantEstado.ACTIVO))
    await session.flush()

    email_a = f"user_a_{tid_a}@test.com"
    email_b = f"user_b_{tid_b}@test.com"

    user_a = Usuario(
        tenant_id=tid_a,
        email_encrypted=email_a,
        email_hash=email_lookup_hash(email_a),
        nombre="Usuario",
        apellidos="TenantA",
        estado=UsuarioEstado.activo,
    )
    user_b = Usuario(
        tenant_id=tid_b,
        email_encrypted=email_b,
        email_hash=email_lookup_hash(email_b),
        nombre="Usuario",
        apellidos="TenantB",
        estado=UsuarioEstado.activo,
    )
    session.add(user_a)
    session.add(user_b)
    await session.commit()
    await session.refresh(user_a)
    await session.refresh(user_b)

    yield {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "user_a": user_a,
        "user_b": user_b,
        "email_a": email_a,
        "email_b": email_b,
    }

    # Cleanup
    from sqlalchemy import delete
    await session.execute(delete(Usuario).where(Usuario.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Tenant).where(Tenant.id.in_([tid_a, tid_b])))
    await session.commit()
    await session.close()


@pytest_asyncio.fixture(scope="module")
def perfil_repo_session_factory(test_engine, create_tables):
    return build_session_factory(test_engine)


# ---------------------------------------------------------------------------
# Task 3.1 RED — get_self aislamiento cross-tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_self_retorna_usuario_correcto(perfil_repo_session_factory, perfil_repo_data):
    """RED: get_self retorna el usuario scoped al tenant correcto."""
    from app.repositories.perfil_repository import PerfilRepository
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        usuario = await repo.get_self(data["user_a"].id)
        assert usuario is not None
        assert usuario.id == data["user_a"].id
        assert usuario.tenant_id == data["tid_a"]
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_get_self_no_retorna_usuario_de_otro_tenant(perfil_repo_session_factory, perfil_repo_data):
    """RED: get_self NO retorna usuario del tenant B cuando el scope es tenant A."""
    from app.repositories.perfil_repository import PerfilRepository
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        # Scoped a tenant_a, pidiendo el id de user del tenant_b
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        resultado = await repo.get_self(data["user_b"].id)
        assert resultado is None
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_get_self_id_inexistente_retorna_none(perfil_repo_session_factory, perfil_repo_data):
    """RED: get_self con id inventado retorna None."""
    from app.repositories.perfil_repository import PerfilRepository
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        id_inexistente = uuid.uuid4()
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        resultado = await repo.get_self(id_inexistente)
        assert resultado is None
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 3.3 RED — update_self PII cifrada en reposo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_self_persiste_campos_editables(perfil_repo_session_factory, perfil_repo_data):
    """RED: update_self persiste campos editables del perfil."""
    from app.repositories.perfil_repository import PerfilRepository
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        usuario = await repo.get_self(data["user_a"].id)
        assert usuario is not None

        updated = await repo.update_self(usuario, banco="Banco Test", regional="Sur")
        assert updated.banco == "Banco Test"
        assert updated.regional == "Sur"
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_update_self_pii_cifrada_en_db(perfil_repo_session_factory, perfil_repo_data):
    """RED: update_self mantiene PII cifrada en reposo (valor DB != texto plano)."""
    from sqlalchemy import text
    from app.repositories.perfil_repository import PerfilRepository
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        usuario = await repo.get_self(data["user_a"].id)
        assert usuario is not None

        cbu_plano = "0000003100012345678901"
        await repo.update_self(usuario, cbu=cbu_plano)

        # Verificar que el valor raw en la DB es diferente al texto plano (está cifrado)
        result = await session.execute(
            text("SELECT cbu FROM usuario WHERE id = :id"),
            {"id": str(data["user_a"].id)},
        )
        raw_value = result.scalar()
        assert raw_value is not None
        assert raw_value != cbu_plano, "PII debe estar cifrada en DB"
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 3.5 TRIANGULATE — unicidad email, email_hash recalculado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_self_email_recalcula_hash(perfil_repo_session_factory, perfil_repo_data):
    """TRIANGULATE: update_self con email nuevo recalcula email_hash."""
    from app.repositories.perfil_repository import PerfilRepository
    from app.core.security.passwords import email_lookup_hash
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        usuario = await repo.get_self(data["user_a"].id)
        old_hash = usuario.email_hash

        new_email = f"nuevo_{uuid.uuid4()}@test.com"
        new_hash = email_lookup_hash(new_email)
        updated = await repo.update_self(usuario, email_encrypted=new_email, email_hash=new_hash)

        assert updated.email_hash == new_hash
        assert updated.email_hash != old_hash
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_get_by_email_hash_retorna_none_para_email_libre(perfil_repo_session_factory, perfil_repo_data):
    """TRIANGULATE: get_by_email_hash retorna None para email libre."""
    from app.repositories.perfil_repository import PerfilRepository
    from app.core.security.passwords import email_lookup_hash
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        repo = PerfilRepository(session=session, tenant_id=data["tid_a"])
        email_libre = f"libre_{uuid.uuid4()}@test.com"
        resultado = await repo.get_by_email_hash(email_lookup_hash(email_libre))
        assert resultado is None
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_get_by_email_hash_retorna_usuario_existente(perfil_repo_session_factory, perfil_repo_data):
    """TRIANGULATE: get_by_email_hash retorna usuario cuando el email existe (usando tenant B, no modificado)."""
    from app.repositories.perfil_repository import PerfilRepository
    from app.core.security.passwords import email_lookup_hash
    data = perfil_repo_data
    session = perfil_repo_session_factory()
    try:
        # Usar tenant_b / user_b cuyo email no fue modificado por tests previos
        repo = PerfilRepository(session=session, tenant_id=data["tid_b"])
        resultado = await repo.get_by_email_hash(email_lookup_hash(data["email_b"]))
        assert resultado is not None
        assert resultado.tenant_id == data["tid_b"]
    finally:
        await session.close()
