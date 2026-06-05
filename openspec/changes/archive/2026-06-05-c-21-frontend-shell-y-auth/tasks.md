## 1. Scaffold del proyecto frontend

- [x] 1.1 Inicializar `frontend/` con Vite (template react-ts): `package.json`, `tsconfig.json` (strict, `noImplicitAny`), `vite.config.ts` con alias `@/` → `src/`
- [x] 1.2 Agregar dependencias: `react-router-dom`, `@tanstack/react-query`, `axios`, `react-hook-form`, `zod`, `@hookform/resolvers`
- [x] 1.3 Agregar dev dependencies de test: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`; configurar `vitest.config.ts` (entorno jsdom) y setup de testing-library
- [x] 1.4 Configurar Tailwind CSS (`tailwind.config.js`, `postcss.config.js`, directivas en `index.css`)
- [x] 1.5 Configurar ESLint/TS para prohibir `any` y class components; crear estructura de carpetas `src/features/`, `src/shared/{services,components,hooks}`
- [x] 1.6 Crear `App.tsx` con `QueryClientProvider`, `BrowserRouter` y `AuthProvider`; punto de entrada `main.tsx`

## 2. Tipos del dominio de auth (shell-navegacion + auth-flow)

- [x] 2.1 Definir `Role` (union: ALUMNO · TUTOR · PROFESOR · COORDINADOR · NEXO · ADMIN · FINANZAS) en `features/auth/types/`
- [x] 2.2 Definir `AuthUser` (`id`, `email`, `roles: Role[]`, `tenantId`, nombre) y `AuthTokens`/sesión en `features/auth/types/`
- [x] 2.3 Definir `NavItem` (`label`, `path`, `roles: Role[]`, `icon?`) en `shared/` o `features/shell/types/`

## 3. Cliente HTTP centralizado y refresh (auth-flow)

- [x] 3.1 RED: test del interceptor de request — adjunta `Authorization: Bearer <token>` cuando hay token; no lo adjunta cuando no lo hay (2 casos)
- [x] 3.2 GREEN: crear instancia Axios única en `shared/services/api.ts` con `baseURL` `/api/v1`, `withCredentials: true` (para cookie httpOnly de refresh — OQ-2) e interceptor de request que adjunta `Authorization: Bearer <token>` desde memoria
- [x] 3.3 RED: test del interceptor de response — `401` con refresh válido → refresca, reintenta y resuelve; refresh inválido → limpia sesión y señaliza logout
- [x] 3.4 GREEN: implementar interceptor de response con refresh contra `POST /auth/refresh`, reintento único (flag `_retry`) y promesa de refresh compartida
- [x] 3.5 TRIANGULATE: test de peticiones concurrentes (un solo refresh, todas reintentan) y de no-bucle (petición ya reintentada que vuelve a 401 fuerza logout)
- [x] 3.6 REFACTOR: extraer el manejo del token en memoria a un módulo `tokenStore` (sin `localStorage`/`sessionStorage`) y limpiar duplicación

## 4. Estado de sesión: AuthProvider + useAuth (auth-flow)

- [x] 4.1 RED: test de `useAuth` — sin sesión reporta `isAuthenticated=false`, `user=null`, `roles=[]`; con sesión refleja identidad del backend
- [x] 4.2 GREEN: implementar `AuthProvider` (Context) y `useAuth` exponiendo `user`, `roles`, `tenantId`, `isAuthenticated`, `login()`, `logout()`
- [x] 4.3 RED: test de rehidratación — al montar, intenta refresh inicial; éxito → decodifica payload del JWT para hidratar `AuthUser` (`user_id`, `tenant_id`, `roles`, `exp`); fallo → estado no autenticado
- [x] 4.4 GREEN: implementar rehidratación de sesión al arrancar: `POST /auth/refresh` (cookie httpOnly viaja automáticamente por `withCredentials`) → decodificar payload Base64 del access token devuelto → poblar `AuthUser` — OQ-1 cerrada: no existe `/auth/me`
- [x] 4.5 REFACTOR: consolidar el estado de carga de sesión (`isInitializing`) para que los guards puedan esperar

## 5. Servicios y hooks de auth (auth-flow)

- [x] 5.1 RED: test del schema Zod de login (email válido/ inválido, password requerido)
- [x] 5.2 GREEN: definir el schema Zod y los servicios `login`/`logout`/`refresh` en `features/auth/services/` (sin `me` — OQ-1); todos vía el cliente Axios central; login y refresh decodifican el payload JWT para extraer `AuthUser`
- [x] 5.3 RED: test del hook `useLogin` (TanStack mutation) — éxito guarda token e hidrata sesión; `401` expone error
- [x] 5.4 GREEN: implementar `useLogin` y `useLogout` como hooks de `services/` con TanStack Query; en logout, invalidar/limpiar la caché de Query

## 6. Página de login (auth-flow)

- [x] 6.1 RED: test de `LoginPage` — render del formulario; error de validación Zod no dispara petición; submit válido invoca `useLogin`
- [x] 6.2 GREEN: implementar `LoginPage` con React Hook Form + Zod, estilos Tailwind, ruta pública `/login` (componente < 200 LOC, sin `any`)
- [x] 6.3 RED: test de error de credenciales — `401` muestra mensaje genérico y no navega
- [x] 6.4 GREEN: cablear el manejo de error y la redirección post-login (incluida la ruta de destino preservada por el guard)

## 7. Guards de ruteo (shell-navegacion)

- [x] 7.1 RED: test de `ProtectedRoute` autenticación — sin sesión redirige a `/login` preservando destino; con sesión renderiza; en `isInitializing` muestra carga
- [x] 7.2 GREEN: implementar `ProtectedRoute` (verificación de sesión + estado de carga + redirección con destino preservado)
- [x] 7.3 RED: test de autorización por rol — rol requerido presente renderiza; ausente muestra `403`; múltiples roles aceptados; fail-closed
- [x] 7.4 GREEN: extender `ProtectedRoute` con prop de roles requeridos (fail-closed) y pantalla `403`

## 8. Navegación por rol (shell-navegacion)

- [x] 8.1 RED: test de `buildNav(roles)` (función pura) — filtra items por rol; usuario multi-rol ve la unión sin duplicados; rol sin destinos → lista vacía
- [x] 8.2 GREEN: implementar el catálogo declarativo `NavItem[]` inicial y la función pura `buildNav`
- [x] 8.3 RED: test de `Sidebar` — renderiza solo los items que corresponden a los roles de la sesión
- [x] 8.4 GREEN: implementar `Sidebar` consumiendo `useAuth` + `buildNav`

## 9. Shell / layout principal (shell-navegacion)

- [x] 9.1 RED: test de `AppLayout` — muestra sidebar y topbar; la topbar expone identidad y acción de logout; solo cambia el área de contenido entre rutas
- [x] 9.2 GREEN: implementar `AppLayout` (sidebar + topbar + `<Outlet/>`) con Tailwind
- [x] 9.3 GREEN: cablear el ruteo con React Router: rutas públicas (`/login`) y privadas envueltas por `ProtectedRoute` + `AppLayout`, con lazy loading (`React.lazy` + `Suspense` fallback) y slot para que C-22/C-23/C-24 registren rutas
- [x] 9.4 RED + GREEN: pantallas `403` y `404` (not-found) con su test de render y de navegación a ruta inexistente

## 10. Integración y cierre

- [x] 10.1 Test de integración del flujo de auth: login → acceso a ruta protegida → 401 → refresh transparente → logout → redirección a `/login`
- [x] 10.2 Verificar cobertura (≥80% líneas; ≥90% en interceptor de refresh, guards y `buildNav`) y que la build de tipos pase sin `any`
- [x] 10.3 Documentar en `frontend/README.md` los scripts (`dev`, `test`, `build`), la estructura feature-based y el contrato de auth consumido (endpoints + estrategia de tokens)
