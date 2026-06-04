from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    MFA_TOKEN_EXPIRE_MINUTES: int = 5
    RECOVERY_TOKEN_EXPIRE_MINUTES: int = 30
    LOGIN_RATE_LIMIT: str = "5/60seconds"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def encryption_key_exact_length(cls, v: str) -> str:
        if len(v) != 32:
            raise ValueError("ENCRYPTION_KEY must be exactly 32 characters")
        return v

    # ---- C-09: Moodle WS integration ----------------------------------------
    # MOODLE_BASE_URL: URL base de la instancia Moodle (ej. https://moodle.example.com)
    # Si no está configurado, el sync Moodle queda deshabilitado sin afectar la importación manual.
    MOODLE_BASE_URL: str | None = None

    # MOODLE_TOKEN: Token de acceso al WS de Moodle (NUNCA aparece en logs ni respuestas).
    MOODLE_TOKEN: str | None = None

    # MOODLE_SYNC_HOUR: Hora UTC en que corre la sincronización nocturna automática (0-23).
    MOODLE_SYNC_HOUR: int = 3

    # PADRON_MAX_ROWS: Límite de filas por archivo de padrón importado.
    PADRON_MAX_ROWS: int = 5000

    # ---- C-10: Umbral de aprobación ----------------------------------------
    # UMBRAL_PCT_DEFECTO: Porcentaje mínimo aprobatorio para notas numéricas
    # cuando el docente no ha configurado un umbral propio (RN-03, OQ-2).
    UMBRAL_PCT_DEFECTO: int = 60

    # VALORES_APROBATORIOS_DEFECTO: Valores textuales que cuentan como aprobado
    # cuando no hay UmbralMateria configurado para la asignación (RN-02).
    VALORES_APROBATORIOS_DEFECTO: list[str] = ["Satisfactorio", "Supera lo esperado"]

    # NOTA_MAXIMA_DEFECTO: Nota máxima asumida para actividades numéricas si el
    # archivo no incluye la nota máxima en el header (OQ-2).
    NOTA_MAXIMA_DEFECTO: float = 10.0
