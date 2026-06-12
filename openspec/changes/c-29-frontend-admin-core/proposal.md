## Why

Tres ítems de navegación de ADMIN (`/admin/usuarios`, `/admin/estructura`, `/admin/auditoria`) están visibles en el shell pero caen en `NotFound404` adrede, a la espera del change diferido **C-24 `frontend-finanzas-y-admin`**. C-24 está bloqueado por **C-18** (liquidaciones) y por las preguntas abiertas **PA-22/PA-23/PA-25**, pero su parte **admin-core no tiene ninguna de esas dependencias**: los backends de estructura académica (C-06), usuarios (C-07) y auditoría (C-05/C-19) ya están construidos, registrados y testeados. Este change separa (carve-out) la parte NO-finanzas de C-24 para entregar de inmediato el frontend de administración sin esperar a liquidaciones. Desbloquea además un gap conocido: hoy no se pueden crear carreras/materias desde la UI.

## What Changes

- **Página `/admin/estructura`** — ABM de carreras, materias y cohortes consumiendo `GET/POST/PATCH/DELETE /api/v1/admin/{carreras,materias,cohortes}` (C-06). Lectura gateada por `estructura:ver`; escritura por `estructura:gestionar`. Tabla ABM + filtros client-side + formularios RHF/Zod, reutilizando el patrón de `features/asignaciones/`.
- **Página `/admin/usuarios`** — alta, edición y baja lógica (soft delete) de usuarios del tenant, consumiendo `GET/POST/PATCH/DELETE /api/v1/admin/usuarios` (C-07). Gateada por `usuarios:gestionar`. El contrato `UsuarioRead` (OQ-3) nunca expone PII (dni/cuil/cbu/alias_cbu); el frontend solo muestra/edita los campos no-PII expuestos por el backend.
- **Página `/admin/auditoria`** — panel read-only: listado de eventos con filtros + paginación (`GET /auditoria`), métricas (acciones-por-día, interacciones-docente, interacciones-docente-materia, comunicaciones-por-docente) y últimas-acciones (C-05/C-19). Gateada por `auditoria:ver`.
- **Routing** — registrar las 3 rutas reales en `frontend/src/App.tsx` (hoy resuelven a `NotFound404`).
- **Nav** — quitar el carácter de placeholder/404 de los 3 ítems en `buildNav.ts` (las entradas ya existen para rol ADMIN; solo dejan de apuntar a un destino inexistente).
- **RBAC fail-closed en frontend** — cada página gateada por su permiso/rol (patrón `Forbidden403`, como `SetupCuatrimestrePage`).
- **Cero finanzas** — este change NO toca liquidaciones, facturas ni grilla salarial. **No referencia ni depende de C-18.** Esos quedan exclusivamente en C-24, que pasa a contener solo la parte finanzas.

## Capabilities

### New Capabilities
- `estructura-frontend`: Página de administración de estructura académica (ABM de carreras, materias y cohortes) sobre los endpoints `/api/v1/admin/{carreras,materias,cohortes}` (C-06), con RBAC fail-closed (`estructura:ver` lectura, `estructura:gestionar` escritura).
- `usuarios-frontend`: Página de administración de usuarios del tenant (alta/edición/baja lógica) sobre `/api/v1/admin/usuarios` (C-07), gateada por `usuarios:gestionar`, respetando el contrato no-PII de `UsuarioRead`.
- `auditoria-frontend`: Panel de auditoría read-only (listado con filtros + paginación, métricas y últimas acciones) sobre `/api/v1/auditoria` (C-05/C-19), gateado por `auditoria:ver`.

### Modified Capabilities
<!-- Ninguna: no cambian requisitos de specs existentes. El nav (frontend-shell) solo deja de tratar 3 destinos como placeholders, sin cambio de requisito de comportamiento del shell. -->

## Impact

- **Frontend (nuevo)**: `frontend/src/features/admin-estructura/`, `frontend/src/features/admin-usuarios/`, `frontend/src/features/admin-auditoria/` (cada uno con `{components,hooks,services,types,pages}`).
- **Frontend (modificado)**: `frontend/src/App.tsx` (3 rutas protegidas nuevas), `frontend/src/features/shell/components/buildNav.ts` (los 3 ítems dejan de ser placeholders).
- **Backend**: ninguno. Se consumen endpoints existentes ya testeados; no se crean ni modifican routers, services, repositories, modelos ni migraciones.
- **Dependencias**: C-21 (shell + auth, hecho), C-06, C-07, C-05/C-19 (backends hechos). **NO depende de C-18 ni de C-24.**
- **Governance**: usuarios (alta/baja) y RBAC = CRÍTICO; estructura = MEDIO; auditoría = read-only (BAJO). La lógica sensible vive en el backend (`require_permission`, soft delete); el frontend es formulario/tabla.
- **CHANGES.md**: se agrega la entrada C-29 y se anota en C-24 que su parte admin-core migró aquí.
