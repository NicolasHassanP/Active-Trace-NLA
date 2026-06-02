"""
Tests for auth-related settings fields in config.py.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Task 1.2: REFRESH_TOKEN_EXPIRE_DAYS, MFA_TOKEN_EXPIRE_MINUTES,
          RECOVERY_TOKEN_EXPIRE_MINUTES, LOGIN_RATE_LIMIT must exist with defaults.
"""
import pytest


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://localhost/test",
    "SECRET_KEY": "s" * 32,
    "ENCRYPTION_KEY": "E" * 32,
}


# ==============================================================================
# RED: fields are present with correct defaults
# ==============================================================================

def test_settings_has_refresh_token_expire_days(monkeypatch):
    """REFRESH_TOKEN_EXPIRE_DAYS default is 14."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 14


def test_settings_has_mfa_token_expire_minutes(monkeypatch):
    """MFA_TOKEN_EXPIRE_MINUTES default is 5."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.MFA_TOKEN_EXPIRE_MINUTES == 5


def test_settings_has_recovery_token_expire_minutes(monkeypatch):
    """RECOVERY_TOKEN_EXPIRE_MINUTES default is 30."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.RECOVERY_TOKEN_EXPIRE_MINUTES == 30


def test_settings_has_login_rate_limit(monkeypatch):
    """LOGIN_RATE_LIMIT default is '5/60seconds'."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.LOGIN_RATE_LIMIT == "5/60seconds"


def test_settings_access_token_expire_minutes_default(monkeypatch):
    """ACCESS_TOKEN_EXPIRE_MINUTES default is 15 (existing field)."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15


# ==============================================================================
# TRIANGULATE: env overrides work
# ==============================================================================

def test_settings_refresh_token_expire_days_override(monkeypatch):
    """REFRESH_TOKEN_EXPIRE_DAYS can be overridden via env."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 30


def test_settings_login_rate_limit_override(monkeypatch):
    """LOGIN_RATE_LIMIT can be overridden via env."""
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "10/minute")
    from importlib import reload
    import app.core.config as cfg_mod
    reload(cfg_mod)
    settings = cfg_mod.Settings()
    assert settings.LOGIN_RATE_LIMIT == "10/minute"
