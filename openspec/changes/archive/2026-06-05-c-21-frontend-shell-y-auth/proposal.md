## Why

activia-trace tiene su backend de auth (C-03) y RBAC (C-04) operativos, pero no existe ninguna aplicación frontend que permita a un usuario iniciar sesión y operar la plataforma. Sin un shell de SPA con autenticación, guards y cliente HTTP centralizado, ningún módulo de presentación posterior (C-22 docente, C-23 coordinación, C-24 finanzas/admin) puede construirse: todos dependen del flujo de login, del manejo de tokens y de la navegación por rol que este change establece. C-21 es el cimiento sobre el que se monta toda la capa de presentación.

## What Changes

- **Scaffold del proyecto frontend** (`frontend/`): Vite + React 18 + TypeScript, Tailwind CSS, TanStack Query, React Hook Form + Zod y Axios, con la estructura feature-based (`features/{name}/{components,hooks,services,types,pages}` + `shared/`).
- **Cliente HTTP centralizado** (`shared/services/api.ts`): instancia Axios única con interceptor de request que adjunta el access token y interceptor de response que, ante un `401`, dispara el refresh con rotación y reintenta la petición original una sola vez; si el refresh falla, limpia la sesión y redirige a login.
- **Feature `auth`**: página de login (email + password, validación Zod), logout, y todo el ciclo de tokens (access en memoria, refresh vía cookie httpOnly gestionada por el backend).
- **Estado de sesión** (`AuthProvider` + hook `useAuth`): expone `user`, `roles`, `tenantId`, `isAuthenticated`, `login()`, `logout()`. La identidad se deriva EXCLUSIVAMENTE del backend (token verificado / endpoint `me`), nunca de datos manipulables por el cliente.
- **Guards de ruteo** (`ProtectedRoute`): bloquea rutas no autenticadas redirigiendo a `/login`; opcionalmente exige uno o más roles y muestra una pantalla `403` (o redirige) cuando el rol del usuario no califica.
- **Shell / layout principal**: layout raíz (sidebar + topbar + área de contenido) con React Router, lazy loading de features y un slot para que C-22/C-23/C-24 monten sus rutas.
- **Navegación por rol**: el sidebar arma sus items a partir de los roles de la sesión (ALUMNO · TUTOR · PROFESOR · COORDINADOR · NEXO · ADMIN · FINANZAS), ocultando lo que el usuario no puede ver.
- **Contratos TypeScript** del dominio de auth: `AuthUser`, `AuthTokens`, `Role`, `NavItem` — sin `any`.

## Capabilities

### New Capabilities
- `auth-flow`: autenticación del frontend — login con validación, manejo del access token en memoria, refresh automático con rotación vía interceptor Axios, logout que revoca la sesión, estado de sesión expuesto por `useAuth`, y resolución de identidad/roles/tenant exclusivamente desde el backend.
- `shell-navegacion`: shell de la SPA — layout raíz, ruteo con React Router y lazy loading, guards `ProtectedRoute` (autenticación + rol), pantallas `403`/not-found, y navegación lateral construida dinámicamente según el rol del usuario autenticado.

### Modified Capabilities
<!-- Ninguna: C-21 introduce la capa de presentación desde cero; no modifica requerimientos de specs existentes. -->

## Impact

- **Nuevo directorio** `frontend/` (hoy inexistente): scaffold Vite + dependencias (`react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `axios`, `react-hook-form`, `zod`, `tailwindcss`, `vitest`, `@testing-library/react`).
- **Dependencia del backend de auth** (C-03/C-04): consume `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` y un endpoint de identidad (`GET /api/v1/auth/me`) para hidratar la sesión.
- **Prerequisito de C-22, C-23 y C-24**: todo el frontend de dominio monta sus rutas y consume el cliente HTTP y los guards que este change crea.
- **Governance**: MEDIO para auth (manejo de tokens, guards, refresh) — decisiones no obvias se surfacean para revisión; BAJO para shell/layout/navegación.
- **Sin impacto en backend**: no toca modelos, migraciones ni endpoints existentes; asume los contratos de auth ya definidos.
