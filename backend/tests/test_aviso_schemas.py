"""
test_aviso_schemas.py — TDD RED tests for C-15 Pydantic schemas.

Task 3.1–3.3: extra='forbid', scope-context coherence, validity coherence.

Sync tests — no DB needed.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# 3.1 / 3.2: extra='forbid' + no identity fields
# ---------------------------------------------------------------------------

def test_crear_aviso_request_rechaza_campos_extra():
    """3.1 RED: CrearAvisoRequest rejects undeclared fields."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        CrearAvisoRequest(
            alcance=AvisoAlcance.Global,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now + timedelta(days=1),
            campo_extra="no permitido",  # type: ignore
        )


def test_crear_aviso_request_rechaza_tenant_id():
    """3.1 RED: CrearAvisoRequest does NOT accept tenant_id."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises((ValidationError, TypeError)):
        CrearAvisoRequest(
            alcance=AvisoAlcance.Global,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now + timedelta(days=1),
            tenant_id=uuid.uuid4(),  # type: ignore
        )


def test_crear_aviso_request_rechaza_autor_id():
    """3.1 RED: CrearAvisoRequest does NOT accept autor_id."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises((ValidationError, TypeError)):
        CrearAvisoRequest(
            alcance=AvisoAlcance.Global,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now + timedelta(days=1),
            autor_id=uuid.uuid4(),  # type: ignore
        )


# ---------------------------------------------------------------------------
# 3.2: scope-context coherence validation
# ---------------------------------------------------------------------------

def test_por_materia_sin_materia_id_es_rechazado():
    """3.2 RED: PorMateria without materia_id → ValidationError."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        CrearAvisoRequest(
            alcance=AvisoAlcance.PorMateria,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now + timedelta(days=1),
            # materia_id missing
        )


def test_por_cohorte_sin_cohorte_id_es_rechazado():
    """3.2 RED: PorCohorte without cohorte_id → ValidationError."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        CrearAvisoRequest(
            alcance=AvisoAlcance.PorCohorte,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now + timedelta(days=1),
            # cohorte_id missing
        )


def test_por_rol_sin_rol_destino_es_rechazado():
    """3.2 RED: PorRol without rol_destino → ValidationError."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        CrearAvisoRequest(
            alcance=AvisoAlcance.PorRol,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now + timedelta(days=1),
            # rol_destino missing
        )


def test_global_acepta_request_sin_contexto():
    """3.2 GREEN: Global aviso without context fields is valid."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    req = CrearAvisoRequest(
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="Aviso global",
        cuerpo="Contenido",
        inicio_en=now,
        fin_en=now + timedelta(days=1),
    )
    assert req.materia_id is None
    assert req.cohorte_id is None
    assert req.rol_destino is None


def test_por_materia_con_materia_id_es_valido():
    """3.2 TRIANGULATE: PorMateria with materia_id is valid."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    req = CrearAvisoRequest(
        alcance=AvisoAlcance.PorMateria,
        severidad=AvisoSeveridad.Advertencia,
        titulo="Por materia",
        cuerpo="Contenido",
        inicio_en=now,
        fin_en=now + timedelta(days=2),
        materia_id=uuid.uuid4(),
    )
    assert req.materia_id is not None


# ---------------------------------------------------------------------------
# 3.2: validity coherence (fin_en > inicio_en)
# ---------------------------------------------------------------------------

def test_fin_en_antes_de_inicio_en_es_rechazado():
    """3.2 RED: fin_en <= inicio_en → ValidationError."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        CrearAvisoRequest(
            alcance=AvisoAlcance.Global,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now + timedelta(days=1),
            fin_en=now,  # before inicio_en
        )


def test_fin_en_igual_inicio_en_es_rechazado():
    """3.2 TRIANGULATE: fin_en == inicio_en → ValidationError."""
    from app.schemas.aviso import CrearAvisoRequest
    from app.models.aviso import AvisoAlcance, AvisoSeveridad

    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        CrearAvisoRequest(
            alcance=AvisoAlcance.Global,
            severidad=AvisoSeveridad.Info,
            titulo="T",
            cuerpo="C",
            inicio_en=now,
            fin_en=now,  # equal
        )


# ---------------------------------------------------------------------------
# 3.3: AckAvisoRequest — no usuario_id in body
# ---------------------------------------------------------------------------

def test_ack_request_rechaza_usuario_id():
    """3.3 RED: AckAvisoRequest does NOT accept usuario_id."""
    from app.schemas.aviso import AckAvisoRequest

    with pytest.raises((ValidationError, TypeError)):
        AckAvisoRequest(usuario_id=uuid.uuid4())  # type: ignore


def test_ack_request_rechaza_campos_extra():
    """3.3 TRIANGULATE: AckAvisoRequest rejects unknown fields."""
    from app.schemas.aviso import AckAvisoRequest

    with pytest.raises(ValidationError):
        AckAvisoRequest(campo_extra="no")  # type: ignore


def test_ack_request_es_valido_vacio():
    """3.3 GREEN: AckAvisoRequest accepts empty body (no fields needed)."""
    from app.schemas.aviso import AckAvisoRequest
    req = AckAvisoRequest()
    assert req is not None


# ---------------------------------------------------------------------------
# 3.3: AvisoRead — ack_count derived field
# ---------------------------------------------------------------------------

def test_aviso_read_tiene_ack_count():
    """3.3 RED: AvisoRead schema has ack_count field."""
    from app.schemas.aviso import AvisoRead
    # AvisoRead must declare ack_count
    fields = AvisoRead.model_fields
    assert "ack_count" in fields
