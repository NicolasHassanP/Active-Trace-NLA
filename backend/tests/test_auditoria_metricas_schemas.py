"""
test_auditoria_metricas_schemas.py — Tasks 4.1 & 4.2 (C-19)

Tests for Pydantic v2 output schemas for audit metrics.

Coverage:
    4.1 RED+GREEN — DTOs with extra='forbid'; correct serialization.
    4.2 RED+GREEN — UltimaAccionItem reuses AuditEventRead structure.
"""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.audit import AuditAction, AuditResultado
from app.models.comunicacion import ComunicacionEstado


# ---------------------------------------------------------------------------
# Task 4.1 — DTOs with extra='forbid'
# ---------------------------------------------------------------------------

def test_acciones_por_dia_item_valid():
    """AccionesPorDiaItem serializes dia and total correctly."""
    from app.schemas.auditoria_metricas import AccionesPorDiaItem

    item = AccionesPorDiaItem(
        dia=datetime(2026, 6, 1, tzinfo=timezone.utc),
        total=42,
    )
    assert item.total == 42
    assert item.dia.year == 2026


def test_acciones_por_dia_item_rejects_extra():
    """AccionesPorDiaItem rejects unknown fields (extra='forbid')."""
    from app.schemas.auditoria_metricas import AccionesPorDiaItem

    with pytest.raises(ValidationError):
        AccionesPorDiaItem(
            dia=datetime(2026, 6, 1, tzinfo=timezone.utc),
            total=1,
            extra_field="bad",
        )


def test_interacciones_docente_item_valid():
    """InteraccionesDocenteItem serializes actor_user_id, accion, total."""
    from app.schemas.auditoria_metricas import InteraccionesDocenteItem

    actor_id = uuid.uuid4()
    item = InteraccionesDocenteItem(
        actor_user_id=actor_id,
        accion=AuditAction.AUDITORIA_CONSULTA,
        total=5,
    )
    assert item.actor_user_id == actor_id
    assert item.accion == AuditAction.AUDITORIA_CONSULTA


def test_interacciones_docente_materia_item_null_materia():
    """InteraccionesDocenteMateriaItem accepts materia_id=None (D1 null bucket)."""
    from app.schemas.auditoria_metricas import InteraccionesDocenteMateriaItem

    item = InteraccionesDocenteMateriaItem(
        actor_user_id=uuid.uuid4(),
        materia_id=None,
        total=3,
    )
    assert item.materia_id is None


def test_interacciones_docente_materia_item_with_materia():
    """InteraccionesDocenteMateriaItem accepts materia_id as string."""
    from app.schemas.auditoria_metricas import InteraccionesDocenteMateriaItem

    materia_id = str(uuid.uuid4())
    item = InteraccionesDocenteMateriaItem(
        actor_user_id=uuid.uuid4(),
        materia_id=materia_id,
        total=7,
    )
    assert item.materia_id == materia_id


def test_comunicaciones_por_docente_item_valid():
    """ComunicacionesPorDocenteItem serializes enviado_por, estado, total."""
    from app.schemas.auditoria_metricas import ComunicacionesPorDocenteItem

    item = ComunicacionesPorDocenteItem(
        enviado_por=uuid.uuid4(),
        estado=ComunicacionEstado.Error,
        total=2,
    )
    assert item.estado == ComunicacionEstado.Error


def test_comunicaciones_por_docente_item_rejects_extra():
    """ComunicacionesPorDocenteItem rejects unknown fields."""
    from app.schemas.auditoria_metricas import ComunicacionesPorDocenteItem

    with pytest.raises(ValidationError):
        ComunicacionesPorDocenteItem(
            enviado_por=uuid.uuid4(),
            estado=ComunicacionEstado.Enviado,
            total=1,
            unknown="field",
        )


# ---------------------------------------------------------------------------
# Task 4.2 — UltimaAccionItem (reuses AuditEventRead structure)
# ---------------------------------------------------------------------------

def test_ultima_accion_item_valid_with_impersonation():
    """UltimaAccionItem serializes all AuditEventRead fields, including optional ones."""
    from app.schemas.auditoria_metricas import UltimaAccionItem

    item = UltimaAccionItem(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        actor_user_id=uuid.uuid4(),
        impersonated_user_id=uuid.uuid4(),
        accion=AuditAction.IMPERSONACION_INICIO,
        modulo="auth",
        entidad_tipo="Usuario",
        entidad_id=str(uuid.uuid4()),
        resultado=AuditResultado.ok,
        registros_afectados=1,
        ip="127.0.0.1",
        user_agent="test",
        before=None,
        after=None,
        created_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
    )
    assert item.impersonated_user_id is not None


def test_ultima_accion_item_valid_no_materia():
    """UltimaAccionItem works when entidad_id is None (no materia/entity context)."""
    from app.schemas.auditoria_metricas import UltimaAccionItem

    item = UltimaAccionItem(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        actor_user_id=uuid.uuid4(),
        impersonated_user_id=None,
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        entidad_id=None,
        resultado=AuditResultado.ok,
        registros_afectados=None,
        ip=None,
        user_agent=None,
        before=None,
        after=None,
        created_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
    )
    assert item.entidad_id is None
    assert item.impersonated_user_id is None


def test_ultima_accion_item_rejects_extra():
    """UltimaAccionItem rejects extra fields (extra='forbid')."""
    from app.schemas.auditoria_metricas import UltimaAccionItem

    with pytest.raises(ValidationError):
        UltimaAccionItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            actor_user_id=uuid.uuid4(),
            impersonated_user_id=None,
            accion=AuditAction.AUDITORIA_CONSULTA,
            modulo="auditoria",
            entidad_tipo="AuditEvent",
            entidad_id=None,
            resultado=AuditResultado.ok,
            registros_afectados=None,
            ip=None,
            user_agent=None,
            before=None,
            after=None,
            created_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
            extra_field="not allowed",
        )
