"""
test_perfil_schemas.py — TDD RED phase for C-20 perfil schemas.

Task 2.1 RED: PerfilUpdate rechaza cuil y campos no declarados.
Task 2.3 TRIANGULATE: casos de validación adicionales.
Task 2.4 RED→GREEN: PerfilRead incluye cuil solo lectura.
"""
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Task 2.1 RED — PerfilUpdate rechaza cuil y campos no declarados
# ---------------------------------------------------------------------------

def test_perfil_update_rechaza_cuil():
    """RED: PerfilUpdate rechaza cuil con ValidationError (extra='forbid')."""
    from app.schemas.perfil import PerfilUpdate
    with pytest.raises(ValidationError) as exc_info:
        PerfilUpdate(cuil="20-12345678-1")
    assert "cuil" in str(exc_info.value)


def test_perfil_update_rechaza_tenant_id():
    """RED: PerfilUpdate rechaza tenant_id (campo no declarado, extra='forbid')."""
    import uuid
    from app.schemas.perfil import PerfilUpdate
    with pytest.raises(ValidationError) as exc_info:
        PerfilUpdate(tenant_id=str(uuid.uuid4()))
    errors = str(exc_info.value)
    assert "tenant_id" in errors


def test_perfil_update_rechaza_estado():
    """RED: PerfilUpdate rechaza estado (campo no declarado, extra='forbid')."""
    from app.schemas.perfil import PerfilUpdate
    with pytest.raises(ValidationError) as exc_info:
        PerfilUpdate(estado="activo")
    assert "estado" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 2.2 GREEN — PerfilUpdate acepta campos editables
# ---------------------------------------------------------------------------

def test_perfil_update_acepta_campos_editables():
    """GREEN: PerfilUpdate acepta todos los campos editables."""
    from app.schemas.perfil import PerfilUpdate
    update = PerfilUpdate(
        nombre="Juan",
        apellidos="García",
        banco="Banco Nación",
        regional="Córdoba",
        facturador=True,
        legajo_profesional="LP-001",
    )
    assert update.nombre == "Juan"
    assert update.apellidos == "García"
    assert update.banco == "Banco Nación"


def test_perfil_update_vacio_es_valido():
    """GREEN: PerfilUpdate vacío es válido (PATCH parcial — todos opcionales)."""
    from app.schemas.perfil import PerfilUpdate
    update = PerfilUpdate()
    assert update.nombre is None
    assert update.email is None


def test_perfil_update_acepta_genero():
    """GREEN: PerfilUpdate acepta el campo genero (columna nueva OQ-2)."""
    from app.schemas.perfil import PerfilUpdate
    update = PerfilUpdate(genero="Femenino")
    assert update.genero == "Femenino"


# ---------------------------------------------------------------------------
# Task 2.3 TRIANGULATE — validaciones adicionales
# ---------------------------------------------------------------------------

def test_perfil_update_rechaza_id():
    """TRIANGULATE: PerfilUpdate rechaza 'id' (campo no declarado)."""
    import uuid
    from app.schemas.perfil import PerfilUpdate
    with pytest.raises(ValidationError):
        PerfilUpdate(id=str(uuid.uuid4()))


def test_perfil_update_email_none_es_opcional():
    """TRIANGULATE: el campo email es opcional en PerfilUpdate."""
    from app.schemas.perfil import PerfilUpdate
    update = PerfilUpdate(nombre="Solo nombre")
    assert update.email is None


def test_perfil_update_solo_email():
    """TRIANGULATE: PerfilUpdate acepta solo cambio de email."""
    from app.schemas.perfil import PerfilUpdate
    update = PerfilUpdate(email="nuevo@test.com")
    assert update.email == "nuevo@test.com"
    assert update.nombre is None


# ---------------------------------------------------------------------------
# Task 2.4 RED→GREEN — PerfilRead incluye cuil solo lectura y PII en claro
# ---------------------------------------------------------------------------

def test_perfil_read_incluye_cuil():
    """RED→GREEN: PerfilRead tiene campo cuil (solo lectura)."""
    import uuid
    from datetime import datetime, timezone
    from app.schemas.perfil import PerfilRead
    now = datetime.now(tz=timezone.utc)
    pr = PerfilRead(
        id=uuid.uuid4(),
        email="test@example.com",
        nombre="Test",
        apellidos="User",
        cuil="20-12345678-1",
        created_at=now,
        updated_at=now,
    )
    assert pr.cuil == "20-12345678-1"


def test_perfil_read_expone_pii_en_claro():
    """RED→GREEN: PerfilRead expone dni, cbu, alias_cbu en claro al dueño."""
    import uuid
    from datetime import datetime, timezone
    from app.schemas.perfil import PerfilRead
    now = datetime.now(tz=timezone.utc)
    pr = PerfilRead(
        id=uuid.uuid4(),
        email="test@example.com",
        nombre="Test",
        apellidos="User",
        dni="12345678",
        cbu="0000003100012345678901",
        alias_cbu="MI.ALIAS.CBU",
        cuil="20-12345678-1",
        created_at=now,
        updated_at=now,
    )
    assert pr.dni == "12345678"
    assert pr.cbu == "0000003100012345678901"
    assert pr.alias_cbu == "MI.ALIAS.CBU"


def test_perfil_read_rechaza_campos_no_declarados():
    """RED→GREEN: PerfilRead rechaza campos no declarados (extra='forbid')."""
    import uuid
    from datetime import datetime, timezone
    from app.schemas.perfil import PerfilRead
    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        PerfilRead(
            id=uuid.uuid4(),
            email="t@t.com",
            nombre="T",
            apellidos="U",
            created_at=now,
            updated_at=now,
            campo_extra="x",
        )
