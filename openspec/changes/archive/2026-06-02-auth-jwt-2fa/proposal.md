## Why

Hoy el sistema tiene la base de persistencia multi-tenant (C-02: `Tenant`, mixins, `TenantScopedRepository`, AES-256, soft delete) pero **ningún mecanismo para emitir una sesión autenticada**. El `TenantScopedRepository` recibe el `tenant_id` por inyección y todo el modelo de seguridad (`docs/ARQUITECTURA.md §5`, regla de oro de `03_actores_y_roles.md §1` y FL-01) depende de que ese `tenant_id` —junto con la identidad y los roles— provenga **exclusivamente de un JWT verificado**. C-03 construye esa fuente: el flujo de autenticación propio (ADR-001) que materializa la regla de oro y desbloquea todo el camino crítico (importar → analizar → comunicar).

## What Changes

- **Login** `POST /api/auth/login`: email + password, verificación con **Argon2id**, emisión de **access token JWT (15 min)** + **refresh token con rotación**. Claims mínimos del access token: `sub` (user_id), `tenant_id`, `roles`, `exp`. Nada de permisos en el token (se resuelven server-side en C-04).
- **Refresh con rotación** `POST /api/auth/refresh`: el refresh recibido se invalida y se emite un par nuevo. **Reuso de un refresh ya consumido → rechazo** (detección de reuse).
- **Logout** `POST /api/auth/logout`: revoca la sesión (refresh) activa.
- **2FA TOTP opcional por usuario**: enrolamiento (`POST /api/auth/2fa/enroll`), verificación de activación (`POST /api/auth/2fa/verify`), y **gate entre la validación de credenciales y la emisión de sesión** en el login (si el usuario tiene 2FA activo, el login devuelve un challenge y exige el código TOTP antes de emitir tokens).
- **Recuperación de contraseña**: `POST /api/auth/forgot` (token de un solo uso enviado por email, expiración corta) + `POST /api/auth/reset` (consume el token y setea el nuevo hash Argon2id). El token se invalida tras uso o por vencimiento.
- **Rate limiting** 5/60s por (IP + email) en login (y forgot), fail-closed.
- **Dependency `get_current_user`**: resuelve identidad + tenant + roles **desde el JWT verificado** y los expone a routers/repositories. Llena el slot reservado en `core/dependencies.py` y conecta el `tenant_id` real al `TenantScopedRepository` de C-02 vía `core/tenancy.py`.
- **Tabla auth-owned de identidad mínima** para autenticación (credenciales, lookup por email, 2FA, sesiones de refresh, tokens de recuperación). **NO** es la entidad `Usuario` completa (eso es C-07); es el subconjunto estrictamente necesario para autenticar, diseñado para ser reconciliado/absorbido por `Usuario` en C-07.
- Dependencias nuevas declaradas en `pyproject.toml`: **pyotp** (TOTP) y un limitador de tasa (**slowapi**/`limits`). `python-jose` y `argon2-cffi` ya están declaradas (C-01).

## Capabilities

### New Capabilities
- `jwt-authentication`: login email+password (Argon2id), emisión de access token JWT de 15 min con claims mínimos, y la regla de oro (identidad/tenant/roles solo desde el token verificado).
- `refresh-token-rotation`: emisión y rotación de refresh tokens, invalidación del token usado, detección de reuse y revocación de sesión (logout).
- `totp-2fa`: enrolamiento y verificación de un segundo factor TOTP opcional por usuario, con gate en el login entre credenciales válidas y emisión de sesión.
- `password-recovery`: solicitud de recuperación (`forgot`) con token de un solo uso y expiración corta, y reseteo (`reset`) que consume el token e invalida los anteriores.
- `login-rate-limiting`: límite de 5 intentos por 60s por (IP + email) en endpoints de autenticación, fail-closed.
- `current-user-dependency`: dependency `get_current_user` que deriva identidad, tenant y roles del JWT verificado y los inyecta en la capa de routers y en el scope del repository.

### Modified Capabilities
<!-- Ninguna: C-02 no publicó specs versionadas en openspec/specs/. Este change solo introduce capacidades nuevas. -->

## Impact

- **Código nuevo**: `app/models/auth.py` (identidad de auth, refresh sessions, 2FA secret, recovery tokens); `app/repositories/auth_*` (repos de auth, parte tenant-scoped, parte por email-hash); `app/services/auth_service.py` (login, refresh, 2fa, recovery); `app/schemas/auth.py` (DTOs Pydantic `extra='forbid'`); `app/api/v1/routers/auth.py`; ampliación de `app/core/security.py` (Argon2id hashing, codificación/decodificación JWT, TOTP helpers, hash determinista de email para lookup); `app/core/dependencies.py` (`get_current_user`); `app/core/tenancy.py` (conectar tenant_id del JWT al repository); `app/core/config.py` (TTLs y parámetros de token/2fa/recovery).
- **DB**: una migración Alembic nueva **`002_create_auth_tables`** con las tablas de auth (OQ-2 resuelta: numeración cronológica real; RBAC C-04 tomará `003`).
- **Dependencias**: `+pyotp`, `+slowapi` (o `limits`) en `pyproject.toml`. AES-256 (`EncryptedString`) reutilizado para email/secretos en reposo; Argon2id para passwords; hash determinista (HMAC-SHA256 con clave de `SECRET_KEY`) para lookup por email.
- **Contrato transversal**: a partir de C-03, `get_current_user` es la única fuente de identidad/tenant/roles. C-04 (RBAC) se monta encima añadiendo `require_permission`. C-05 (audit) consumirá el actor real desde la sesión. C-07 (Usuario) reconciliará la tabla de identidad de auth.
- **Fuera de alcance**: entidad `Usuario` completa, catálogo rol×permiso y `require_permission` (C-04), impersonación (ADR-004), Moodle SSO (Fase 2), audit log (C-05).
