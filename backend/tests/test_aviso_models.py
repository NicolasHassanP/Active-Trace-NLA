"""
test_aviso_models.py — TDD RED tests for C-15 avisos/acknowledgment models.

RED phase: these tests reference production code that does NOT yet exist.
They verify:
    - Enums AvisoAlcance and AvisoSeveridad exist and have correct values.
    - Aviso model has expected fields.
    - AcknowledgmentAviso model has expected fields.
    - Both models exported from app.models.

DB real: activia_trace_test. Sin mocks.
"""
import pytest


def test_aviso_alcance_enum_values():
    """RED 2.1: AvisoAlcance has Global, PorMateria, PorCohorte, PorRol."""
    from app.models.aviso import AvisoAlcance
    assert AvisoAlcance.Global.value == "Global"
    assert AvisoAlcance.PorMateria.value == "PorMateria"
    assert AvisoAlcance.PorCohorte.value == "PorCohorte"
    assert AvisoAlcance.PorRol.value == "PorRol"


def test_aviso_severidad_enum_values():
    """RED 2.1: AvisoSeveridad has Info, Advertencia, Critico."""
    from app.models.aviso import AvisoSeveridad
    assert AvisoSeveridad.Info.value == "Info"
    assert AvisoSeveridad.Advertencia.value == "Advertencia"
    assert AvisoSeveridad.Critico.value == "Critico"


def test_aviso_model_tablename():
    """RED 2.2: Aviso model has tablename 'aviso'."""
    from app.models.aviso import Aviso
    assert Aviso.__tablename__ == "aviso"


def test_aviso_model_has_required_columns():
    """RED 2.2: Aviso has tenant_id, alcance, severidad, titulo, cuerpo, activo, etc."""
    from app.models.aviso import Aviso
    cols = {col.key for col in Aviso.__table__.columns}
    # TenantScopedBase
    assert "id" in cols
    assert "tenant_id" in cols
    assert "deleted_at" in cols
    # Business columns
    assert "alcance" in cols
    assert "materia_id" in cols
    assert "cohorte_id" in cols
    assert "rol_destino" in cols
    assert "severidad" in cols
    assert "titulo" in cols
    assert "cuerpo" in cols
    assert "inicio_en" in cols
    assert "fin_en" in cols
    assert "orden" in cols
    assert "activo" in cols
    assert "requiere_ack" in cols


def test_aviso_activo_default_true():
    """RED 2.2: Aviso.activo column has a default of True."""
    from app.models.aviso import Aviso
    col = Aviso.__table__.c["activo"]
    assert col.default is not None and col.default.arg is True


def test_aviso_requiere_ack_default_false():
    """RED 2.2: Aviso.requiere_ack column has a default of False."""
    from app.models.aviso import Aviso
    col = Aviso.__table__.c["requiere_ack"]
    assert col.default is not None and col.default.arg is False


def test_acknowledgment_aviso_tablename():
    """RED 2.2: AcknowledgmentAviso model has tablename 'acknowledgment_aviso'."""
    from app.models.aviso import AcknowledgmentAviso
    assert AcknowledgmentAviso.__tablename__ == "acknowledgment_aviso"


def test_acknowledgment_aviso_has_required_columns():
    """RED 2.2: AcknowledgmentAviso has aviso_id, usuario_id, confirmado_at."""
    from app.models.aviso import AcknowledgmentAviso
    cols = {col.key for col in AcknowledgmentAviso.__table__.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "aviso_id" in cols
    assert "usuario_id" in cols
    assert "confirmado_at" in cols
    assert "deleted_at" in cols


def test_models_exported_from_init():
    """RED 2.3: Aviso and AcknowledgmentAviso exported from app.models."""
    import app.models  # noqa
    from app.models import Aviso, AcknowledgmentAviso, AvisoAlcance, AvisoSeveridad
    assert Aviso is not None
    assert AcknowledgmentAviso is not None
    assert AvisoAlcance is not None
    assert AvisoSeveridad is not None
