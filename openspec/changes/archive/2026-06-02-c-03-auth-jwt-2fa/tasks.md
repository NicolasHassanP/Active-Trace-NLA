# Tasks — auth-jwt-2fa (C-03)

> Strict TDD: cada comportamiento sigue RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos: happy + edge) → REFACTOR. Tests contra **PostgreSQL efímero real** (asyncpg), nunca mockeando la DB. Antes de modificar archivos de C-01/C-02, correr su test suite como safety net. ≤500 LOC/archivo; Pydantic `extra='forbid'`; snake_case; flujo Routers→Services→Repositories→Models.
>
> ⚠️ **Governance CRÍTICO (auth)**: dominio crítico — describir cada modelo/flujo de auth antes de escribirlo y surfacear decisiones no obvias. Las 4 Open Questions están **resueltas** (ver `design.md §Resolved Questions`): OQ-1 tenant por subdominio/header `X-Tenant`; OQ-2 migración `002`; OQ-3 primer ADMIN diferido a C-07 (tests con fixtures de `auth_identity`); OQ-4 rate limiter in-memory (slowapi).

## 1. Dependencias y configuración

- [x] 1.1 Agregar `pyotp` y `slowapi` (o `limits`) a `backend/pyproject.toml`; instalar y verificar import.
- [x] 1.2 Extender `app/core/config.py` con `ACCESS_TOKEN_EXPIRE_MINUTES` (ya existe, default 15), `REFRESH_TOKEN_EXPIRE_DAYS` (default 14), `MFA_TOKEN_EXPIRE_MINUTES` (default 5), `RECOVERY_TOKEN_EXPIRE_MINUTES` (default 30), `LOGIN_RATE_LIMIT` (default "5/60seconds"). RED: test de Settings que falla por campos faltantes → GREEN → TRIANGULATE (defaults + override por env) → REFACTOR.

## 2. Helpers de seguridad en core/security.py (extensión, sin romper C-02)

- [x] 2.1 SAFETY NET: correr `tests/test_security_encryption.py` y capturar baseline (AES-256 intacto).
- [x] 2.2 `hash_password` / `verify_password` (Argon2id, argon2-cffi). RED→GREEN→TRIANGULATE (hash != plano, verify True/False, hashes distintos para misma password por salt)→REFACTOR.
- [x] 2.3 `email_lookup_hash(email)` HMAC-SHA256 con clave de `SECRET_KEY` sobre email normalizado (lowercase+trim). RED→GREEN→TRIANGULATE (determinismo: mismo email→mismo hash; case/space-insensitive; emails distintos→hashes distintos)→REFACTOR.
- [x] 2.4 `encode_access_token` / `decode_access_token` (HS256, claims `sub`/`tenant_id`/`roles`/`iat`/`exp`/`type="access"`). RED→GREEN→TRIANGULATE (round-trip de claims; firma alterada→error; expirado→error; `type` incorrecto→error)→REFACTOR.
- [x] 2.5 `encode_mfa_token` / `decode_mfa_token` (`type="mfa"`, TTL corto). RED→GREEN→TRIANGULATE (round-trip; expirado→error; usar mfa como access falla por type)→REFACTOR.
- [x] 2.6 `generate_opaque_token` / `hash_opaque_token` (token_urlsafe + SHA-256). RED→GREEN→TRIANGULATE (token != hash; mismo token→mismo hash; tokens únicos por llamada)→REFACTOR.
- [x] 2.7 `generate_totp_secret` / `build_totp_uri` / `verify_totp` (pyotp, tolerancia ±1 ventana). RED→GREEN→TRIANGULATE (código actual válido; código de ventana adyacente válido; código fuera de tolerancia inválido)→REFACTOR.
- [x] 2.8 Si `core/security.py` supera 500 LOC, refactor a paquete `core/security/` (`crypto.py`, `passwords.py`, `tokens.py`, `totp.py`) preservando imports; re-correr safety net.

## 3. Modelos y migración (002_create_auth_tables)

- [x] 3.1 `app/models/auth.py` — `AuthIdentity(TenantScopedBase)`: `email_encrypted (EncryptedString)`, `email_hash (str, indexed)`, `password_hash`, `roles (JSONB array str)`, `is_active (bool)`, `totp_secret_encrypted (EncryptedString, nullable)`, `totp_enabled (bool)`. RED (crear y persistir en DB efímera, leer de vuelta)→GREEN→TRIANGULATE (email round-trip cifrado/descifrado; columna cruda en DB != email plano; único `(tenant_id, email_hash)`)→REFACTOR.
- [x] 3.2 `RefreshSession(TenantScopedBase)`: `auth_identity_id (FK)`, `token_hash`, `family_id (UUID)`, `expires_at`, `revoked_at (nullable)`, `rotated_at (nullable)`. RED→GREEN→TRIANGULATE (persistir/leer; estados revocado/rotado)→REFACTOR.
- [x] 3.3 `PasswordRecoveryToken(TenantScopedBase)`: `auth_identity_id (FK)`, `token_hash`, `expires_at`, `used_at (nullable)`. RED→GREEN→TRIANGULATE→REFACTOR.
- [x] 3.4 Crear migración Alembic **`002_create_auth_tables`** con las 3 tablas, índices y el único compuesto `(tenant_id, email_hash)`. Revisar a mano el autogenerate. RED: test que aplica `upgrade head` y verifica que existen las tablas+índices; `downgrade -1` las elimina limpio.

## 4. Repositories (queries; sin lógica de negocio)

- [x] 4.1 `repositories/auth_identity_repository.py`: lookup por `(tenant_id, email_hash)`, get por id, create. (Excepción documentada: el `tenant_id` del lookup de login se resuelve del contexto público — subdominio/header `X-Tenant`, OQ-1.) RED→GREEN→TRIANGULATE (encontrar por email_hash correcto; no encontrar por hash ajeno; aislamiento: identidad de tenant A no aparece scopeada al tenant B)→REFACTOR.
- [x] 4.2 `repositories/refresh_session_repository.py`: create, get por token_hash, mark_rotated, mark_revoked, revoke_family(family_id). RED→GREEN→TRIANGULATE (get por hash; revoke marca soft, no borra; revoke_family afecta solo a esa familia)→REFACTOR.
- [x] 4.3 `repositories/recovery_token_repository.py`: create, get por token_hash, mark_used, invalidate_all_for_identity. RED→GREEN→TRIANGULATE→REFACTOR.

## 5. Schemas Pydantic (extra='forbid')

- [x] 5.1 `schemas/auth.py`: `LoginRequest`, `TokenPair`/`LoginResponse`, `MfaChallengeResponse`, `MfaVerifyRequest`, `RefreshRequest`, `LogoutRequest`, `ForgotRequest`, `ResetRequest`, `EnrollResponse`, `Verify2FARequest`. RED (instanciar con campos válidos)→GREEN→TRIANGULATE (campo extra → ValidationError; tipos inválidos → error; email inválido → error)→REFACTOR.

## 6. AuthService — login + emisión de sesión (jwt-authentication)

- [x] 6.1 `services/auth_service.py` `login(email, password, tenant_ctx)`: normaliza email, busca por email_hash, verifica Argon2id. RED (login OK emite par)→GREEN→TRIANGULATE (password incorrecta→error auth; email inexistente→mismo error + verify dummy anti-timing; usuario inactivo→error)→REFACTOR.
- [x] 6.2 Emisión de access token con claims mínimos y `exp` a 15 min. RED→GREEN→TRIANGULATE (claims presentes; sin permisos en token; exp correcto)→REFACTOR.

## 7. AuthService — refresh rotation (refresh-token-rotation)

- [x] 7.1 Emisión inicial del refresh (opaco, persistido por hash, family_id nueva). RED→GREEN→TRIANGULATE (se guarda hash no plano; expires_at seteado)→REFACTOR.
- [x] 7.2 `refresh(token)`: valida vigente+no revocado, marca rotado, emite par nuevo en misma familia. RED→GREEN→TRIANGULATE (rotación OK; refresh expirado→401; orden de tokens en la familia)→REFACTOR.
- [x] 7.3 Detección de reuse: refresh ya rotado/revocado → revoca toda la familia → 401. RED→GREEN→TRIANGULATE (reuse de token ya usado revoca familia; tras revocar familia, el último refresh legítimo también falla)→REFACTOR.
- [x] 7.4 `logout(token)`: marca `revoked_at`; refresh posterior con ese token → 401. RED→GREEN→TRIANGULATE→REFACTOR.

## 8. AuthService — 2FA TOTP (totp-2fa)

- [x] 8.1 `enroll_2fa(current_user)`: genera secreto, lo cifra, `totp_enabled=False`, devuelve secreto+URI. RED→GREEN→TRIANGULATE (secreto persistido cifrado; columna cruda != secreto; enabled queda False)→REFACTOR.
- [x] 8.2 `verify_2fa_activation(current_user, code)`: valida código → `totp_enabled=True`. RED→GREEN→TRIANGULATE (código válido activa; código inválido no activa)→REFACTOR.
- [x] 8.3 Gate en login: usuario con `totp_enabled` + credenciales válidas → devuelve `mfa_token` (no tokens). RED→GREEN→TRIANGULATE (login 2FA devuelve challenge sin access/refresh; usuario sin 2FA emite par directo)→REFACTOR.
- [x] 8.4 `complete_mfa(mfa_token, code)`: valida mfa_token + TOTP → emite par. RED→GREEN→TRIANGULATE (challenge+código válido emite sesión; código inválido→401; mfa_token expirado→401)→REFACTOR.

## 9. AuthService — recuperación de contraseña (password-recovery)

- [x] 9.1 `forgot(email)`: si existe, crea recovery token (persistido por hash + expires_at) y lo pasa al puerto de envío mockeable; respuesta uniforme. RED→GREEN→TRIANGULATE (email existente genera token y llama al puerto; email inexistente NO genera token pero misma respuesta)→REFACTOR.
- [x] 9.2 `reset(token, new_password)`: valida hash+vigencia+no usado, marca used, invalida los demás tokens, setea nuevo hash, revoca todas las refresh sessions. RED→GREEN→TRIANGULATE (token válido resetea; reuso de token→error; token expirado→error; reset revoca sesiones activas)→REFACTOR.

## 10. Rate limiting (login-rate-limiting)

- [x] 10.1 Integrar slowapi (backend **in-memory**, OQ-4) con clave `(client_ip, email_normalizado)`, límite 5/60s en login y forgot. Interfaz desacoplada para migrar a Redis a futuro. RED→GREEN→TRIANGULATE (≤5 intentos pasan; 6º→429; ventana se reinicia tras 60s)→REFACTOR.
- [x] 10.2 Fail-closed: si el backend del limitador falla, denegar. RED (simular fallo del backend → request denegada)→GREEN→TRIANGULATE→REFACTOR.

## 11. Dependency get_current_user + tenancy (current-user-dependency)

- [x] 11.1 `core/dependencies.py` `get_current_user(request) -> CurrentUser`: extrae Bearer, verifica firma+exp+`type=="access"`, devuelve value object (sin tocar DB). RED→GREEN→TRIANGULATE (token válido→CurrentUser; sin header→401; expirado→401; type incorrecto→401)→REFACTOR.
- [x] 11.2 Identidad inmutable: parámetros de user_id/tenant_id en query/body/header se ignoran frente al token. RED (request con tenant_id falso en body → se usa el del token)→GREEN→TRIANGULATE→REFACTOR.
- [x] 11.3 `core/tenancy.py`: factory que construye `TenantScopedRepository` con el `tenant_id` del `CurrentUser`. RED→GREEN→TRIANGULATE (repo scopeado al tenant del token; usuario A pasando tenant_id de B sigue scopeado a A)→REFACTOR.

## 12. Router de auth (api/v1/routers/auth.py) — sin lógica de negocio

- [x] 12.1 Endpoints `POST /api/auth/login`, `/refresh`, `/logout`, `/2fa/enroll`, `/2fa/verify`, `/forgot`, `/reset` (+ challenge MFA), delegando todo al AuthService; mapear errores a 400/401/429 según `docs/ARQUITECTURA.md §3`. RED (tests de integración por endpoint con DB efímera)→GREEN→TRIANGULATE (caso OK + caso KO por endpoint)→REFACTOR.
- [x] 12.2 Registrar el router en la app (`api/v1`), confirmar que los endpoints de auth son los únicos accesibles sin sesión (KB §6 acceso anónimo).

## 13. Cierre

- [x] 13.1 Correr la suite completa con PostgreSQL efímero; verificar cobertura ≥80% líneas / ≥90% reglas de negocio (login OK/KO, rotación+reuse, 2FA, recovery single-use, rate limit, identidad inmutable).
- [x] 13.2 Verificar reglas duras: ≤500 LOC/archivo, `extra='forbid'`, snake_case, sin lógica en routers, sin SQL en services, soft delete, secretos cifrados, identidad solo desde el token.
- [x] 13.3 Marcar `[x]` C-03 en `CHANGES.md` y dejar nota para C-04 (RBAC monta `require_permission` sobre `get_current_user`) y C-07 (reconciliar `auth_identity` con `Usuario`).
