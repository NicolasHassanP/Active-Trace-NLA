"""
test_mensajeria_schemas.py — TDD suite para C-20 schemas de mensajería.

Task 7.1 RED: MensajeCreate/HiloCreate/RespuestaCreate rechazan cuerpo vacío
              y campos no declarados (remitente_id, tenant_id).
Task 7.2 GREEN: schemas con asunto/cuerpo requeridos, extra='forbid'.
Task 7.3 RED→GREEN: InboxHiloRead y MensajeRead.
"""
import uuid
import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Task 7.1 RED — schemas de escritura rechazan campos prohibidos
# ---------------------------------------------------------------------------

def test_hilo_create_rechaza_remitente_id():
    """RED: HiloCreate rechaza remitente_id (campo no declarado)."""
    from app.schemas.mensajeria import HiloCreate
    with pytest.raises(ValidationError):
        HiloCreate(
            destinatario_id=uuid.uuid4(),
            asunto="Test",
            cuerpo="Cuerpo",
            remitente_id=uuid.uuid4(),
        )


def test_hilo_create_rechaza_tenant_id():
    """RED: HiloCreate rechaza tenant_id (campo no declarado)."""
    from app.schemas.mensajeria import HiloCreate
    with pytest.raises(ValidationError):
        HiloCreate(
            destinatario_id=uuid.uuid4(),
            asunto="Test",
            cuerpo="Cuerpo",
            tenant_id=uuid.uuid4(),
        )


def test_respuesta_create_rechaza_cuerpo_vacio():
    """RED: RespuestaCreate rechaza cuerpo vacío."""
    from app.schemas.mensajeria import RespuestaCreate
    with pytest.raises(ValidationError):
        RespuestaCreate(asunto="Test", cuerpo="")


def test_respuesta_create_rechaza_remitente_id():
    """RED: RespuestaCreate rechaza remitente_id (campo no declarado)."""
    from app.schemas.mensajeria import RespuestaCreate
    with pytest.raises(ValidationError):
        RespuestaCreate(asunto="Test", cuerpo="Cuerpo", remitente_id=uuid.uuid4())


def test_respuesta_create_rechaza_tenant_id():
    """RED: RespuestaCreate rechaza tenant_id (campo no declarado)."""
    from app.schemas.mensajeria import RespuestaCreate
    with pytest.raises(ValidationError):
        RespuestaCreate(asunto="Test", cuerpo="Cuerpo", tenant_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Task 7.2 GREEN — schemas con asunto/cuerpo requeridos, HiloCreate 1:1
# ---------------------------------------------------------------------------

def test_hilo_create_valido():
    """GREEN: HiloCreate válido con destinatario_id, asunto y cuerpo."""
    from app.schemas.mensajeria import HiloCreate
    hilo = HiloCreate(
        destinatario_id=uuid.uuid4(),
        asunto="Consulta sobre...",
        cuerpo="Hola, tengo una consulta",
    )
    assert hilo.asunto == "Consulta sobre..."
    assert hilo.cuerpo == "Hola, tengo una consulta"


def test_hilo_create_requiere_destinatario_id():
    """GREEN: HiloCreate requiere destinatario_id."""
    from app.schemas.mensajeria import HiloCreate
    with pytest.raises(ValidationError):
        HiloCreate(asunto="Test", cuerpo="Cuerpo")


def test_hilo_create_requiere_cuerpo():
    """GREEN: HiloCreate requiere cuerpo."""
    from app.schemas.mensajeria import HiloCreate
    with pytest.raises(ValidationError):
        HiloCreate(destinatario_id=uuid.uuid4(), asunto="Test")


def test_hilo_create_rechaza_cuerpo_vacio():
    """GREEN: HiloCreate rechaza cuerpo vacío (OQ-3)."""
    from app.schemas.mensajeria import HiloCreate
    with pytest.raises(ValidationError):
        HiloCreate(destinatario_id=uuid.uuid4(), asunto="Test", cuerpo="")


def test_respuesta_create_valido():
    """GREEN: RespuestaCreate válido con asunto y cuerpo."""
    from app.schemas.mensajeria import RespuestaCreate
    resp = RespuestaCreate(asunto="Re: Consulta", cuerpo="Aquí la respuesta")
    assert resp.cuerpo == "Aquí la respuesta"


# ---------------------------------------------------------------------------
# Task 7.3 RED→GREEN — InboxHiloRead y MensajeRead
# ---------------------------------------------------------------------------

def test_inbox_hilo_read_contiene_no_leidos():
    """RED→GREEN: InboxHiloRead tiene campo no_leidos."""
    from app.schemas.mensajeria import InboxHiloRead
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)
    read = InboxHiloRead(
        id=uuid.uuid4(),
        asunto="Test",
        no_leidos=3,
        ultimo_mensaje_at=now,
    )
    assert read.no_leidos == 3


def test_mensaje_read_contiene_campos_basicos():
    """RED→GREEN: MensajeRead tiene id, hilo_id, remitente_id, asunto, cuerpo."""
    from app.schemas.mensajeria import MensajeRead
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)
    read = MensajeRead(
        id=uuid.uuid4(),
        hilo_id=uuid.uuid4(),
        remitente_id=uuid.uuid4(),
        asunto="Asunto",
        cuerpo="Cuerpo del mensaje",
        created_at=now,
    )
    assert read.cuerpo == "Cuerpo del mensaje"
    assert read.remitente_id is not None


def test_inbox_hilo_read_rechaza_campos_no_declarados():
    """TRIANGULATE: InboxHiloRead rechaza campos no declarados."""
    from app.schemas.mensajeria import InboxHiloRead
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)
    with pytest.raises(ValidationError):
        InboxHiloRead(
            id=uuid.uuid4(),
            asunto="Test",
            no_leidos=0,
            ultimo_mensaje_at=now,
            campo_extra="x",
        )
