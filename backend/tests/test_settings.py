import pytest
from pydantic import ValidationError


VALID_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://localhost/testdb",
    "SECRET_KEY": "a" * 32,
    "ENCRYPTION_KEY": "b" * 32,
}


def test_settings_instantiates_with_valid_env(monkeypatch):
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)

    from app.core.config import Settings

    s = Settings()
    assert s.DATABASE_URL == VALID_ENV["DATABASE_URL"]
    assert s.SECRET_KEY == VALID_ENV["SECRET_KEY"]
    assert s.ENCRYPTION_KEY == VALID_ENV["ENCRYPTION_KEY"]


def test_settings_default_token_expiry(monkeypatch):
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

    from app.core.config import Settings

    s = Settings()
    assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 15


def test_settings_fails_when_required_var_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        # Pass _env_file=None so pydantic-settings ignores the .env file on disk
        # and relies only on environment variables (which monkeypatch removed above).
        Settings(_env_file=None)


def test_settings_fails_when_secret_key_too_short(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", VALID_ENV["DATABASE_URL"])
    monkeypatch.setenv("SECRET_KEY", "tooshort")
    monkeypatch.setenv("ENCRYPTION_KEY", VALID_ENV["ENCRYPTION_KEY"])

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_settings_fails_when_encryption_key_wrong_length(monkeypatch):
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENCRYPTION_KEY", "not-exactly-32-chars")

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings()
