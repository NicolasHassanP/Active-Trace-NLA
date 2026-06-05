"""
test_audit_panel_config.py — Tasks 1.1 & 1.2 (C-19)

Tests for AUDIT_PANEL_LOG_MAX setting.

Coverage:
    1.1 RED   — Settings exposes AUDIT_PANEL_LOG_MAX with default 200.
    1.2 GREEN — AUDIT_PANEL_LOG_MAX can be overridden from the environment.
"""

VALID_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://localhost/testdb",
    "SECRET_KEY": "a" * 32,
    "ENCRYPTION_KEY": "b" * 32,
}


# ---------------------------------------------------------------------------
# Task 1.1 RED — default value is 200
# ---------------------------------------------------------------------------

def test_audit_panel_log_max_default_is_200(monkeypatch):
    """Settings.AUDIT_PANEL_LOG_MAX defaults to 200 when not set in env."""
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("AUDIT_PANEL_LOG_MAX", raising=False)

    # Force fresh import after monkeypatching env
    from importlib import reload
    import app.core.config as config_module
    reload(config_module)
    from app.core.config import Settings

    s = Settings(_env_file=None)
    assert s.AUDIT_PANEL_LOG_MAX == 200


# ---------------------------------------------------------------------------
# Task 1.2 Triangulation — value can be overridden from env
# ---------------------------------------------------------------------------

def test_audit_panel_log_max_override_from_env(monkeypatch):
    """AUDIT_PANEL_LOG_MAX can be overridden via environment variable."""
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("AUDIT_PANEL_LOG_MAX", "500")

    from importlib import reload
    import app.core.config as config_module
    reload(config_module)
    from app.core.config import Settings

    s = Settings(_env_file=None)
    assert s.AUDIT_PANEL_LOG_MAX == 500
