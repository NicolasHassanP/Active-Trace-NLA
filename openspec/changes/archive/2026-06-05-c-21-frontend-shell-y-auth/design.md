## Context

activia-trace no tiene aún ningún proyecto frontend: el directorio `frontend/` no existe. El backend de autenticación (C-03) expone login/refresh/logout con JWT (access token de 15 min + refresh con rotación) y el JWT lleva claims mínimos (`sub`, `tenant_id`, `roles`, `exp`); los permisos finos se resuelven server-side por endpoint (C-04). Este change crea el cimiento de la SPA: scaffold, cliente HTTP, flujo de auth, guards y shell de navegación. Es prerequisito de C-22/C-23/C-24, que montarán sus rutas y consumirán el cliente HTTP y los guards definidos aquí.

Restricciones de contrato (reglas duras del proyecto y stack):
- React 18 + TypeScript sin `any` y sin class components; componentes < 200 LOC.
- Estructura feature-based: `features/{name}/{components,hooks,services,types,pages}` + `shared/`.
- Todo fetch pasa por hooks de `services/` con TanStack Query; cliente Axios único en `shared/services/api.ts`.
- Forms con React Hook Form + Zod; estilos con Tailwind (sin CSS modules, sin inline salvo valores dinámicos).
- Identidad / roles / tenant SIEMPRE desde la sesión verificada por el backend, nunca desde datos del cliente.
- Governance: MEDIO para auth (tokens, guards, refresh); BAJO para shell/layout/navegación.

## Goals / Non-Goals

**Goals:**
- Scaffold del proyecto `frontend/` (Vite + React 18 + TS + Tailwind + TanStack Query + RHF/Zod + Axios + Vitest/Testing Library).
- Cliente HTTP centralizado con interceptores de token y refresh automático con rotación, reintento único y serialización de refrescos concurrentes.
- Feature `auth`: login, logout, manejo del access token en memoria, rehidratación de sesión vía refresh, `AuthProvider` + `useAuth`.
- Guards `ProtectedRoute` (autenticación + rol, fail-closed) con pantallas `403` y `404`.
- Shell: layout raíz (sidebar + topbar + área de contenido), ruteo con React Router y lazy loading, navegación construida por rol.
- Tipos TypeScript del dominio de auth (`AuthUser`, `AuthTokens`, `Role`, `NavItem`).

**Non-Goals:**
- Pantallas de dominio (importación, atrasados, equipos, liquidaciones, etc.) — pertenecen a C-22/C-23/C-24.
- 2FA / recuperación de contraseña en la UI — el backend las soporta, pero su frontend se difiere (no son parte del shell mínimo; ver Open Questions).
- Resolución/visualización de permisos finos `modulo:accion` en el cliente: el shell navega por ROL; la autorización fina la enforce el backend por endpoint.
- Impersonación, branding por tenant, theming avanzado.
- Configuración de CI/CD del frontend y Dockerfile (DevOps / otro change).

## Decisions

### D1 — Access token en memoria, refresh en cookie httpOnly (no localStorage) — OQ-2 confirmada
El access token vive solo en memoria (módulo/estado del `AuthProvider`); el refresh token lo gestiona el backend como cookie httpOnly + Secure + SameSite. **Por qué:** mitiga XSS y CSRF. Alinea con la regla dura "tokens JWT nunca en localStorage si hay alternativa más segura".
- **Axios configurado con `withCredentials: true`** en el cliente global y en el endpoint de refresh específicamente, para que el browser envíe automáticamente la cookie httpOnly en los requests cross-origin.
- *Alternativa descartada:* token en `localStorage` — simple pero expuesto a XSS; rechazado.
- *Alternativa descartada:* ambos tokens en memoria sin cookie — pierde la sesión en cada recarga; rechazado.
- *Costo:* al recargar la página el access token se pierde y debe rehidratarse con un refresh inicial; trade-off aceptable.

### D2 — Refresh automático vía interceptor de response de Axios
El interceptor de response intercepta `401`, dispara el refresh, y reintenta la petición original. Un flag por request (`_retry`) evita bucles; una promesa de refresh compartida serializa los refrescos concurrentes (las peticiones que llegan durante un refresh en curso se encolan y se reintentan con el nuevo token). **Por qué:** centraliza el manejo de expiración en un solo lugar; los hooks de feature no se enteran del refresh.
- *Alternativa descartada:* refresh proactivo por timer antes del `exp` — más complejo, sensible a drift de reloj; el reactivo por `401` es más robusto. Se puede agregar después.

### D3 — Rehidratación de identidad desde el payload del JWT (OQ-1 cerrada)
No existe `GET /api/v1/auth/me`. La identidad (`user_id`, `tenant_id`, `roles`, `exp`) viene en los claims del access token generado por C-03. El frontend decodifica el payload Base64 del JWT (sin verificar la firma — eso lo hace el backend) para hidratar `AuthUser`. **Por qué:** es la única fuente disponible, y es válida: el JWT fue emitido y firmado por el backend; leer sus claims públicos es seguro. La regla de oro del proyecto aplica a la *autorización* — identidad NUNCA desde parámetros de la petición, y la firma del token la verifica el servidor en cada request protegido.
- *Importante:* el frontend trata el access token como firmado-por-el-backend; no lo manipula ni confía en tokens que él mismo construya. El decode es solo de lectura para UX (mostrar nombre, filtrar nav).
- *Alternativa descartada:* endpoint `/me` — no existe en C-03; introducirlo requeriría un change de backend fuera de scope.

### D4 — Navegación por ROL en el cliente; autorización fina en el backend
El sidebar y `ProtectedRoute` deciden visibilidad/acceso por **rol** (dato de la sesión). Los permisos finos `modulo:accion` NO se evalúan en el cliente: cada endpoint del backend los enforce y responde `403` si corresponde. **Por qué:** el cliente es una conveniencia de UX, no un control de seguridad; duplicar la matriz de permisos en el front sería frágil y redundante. La seguridad real vive server-side.

### D5 — `AuthProvider` (Context) + `useAuth`, no store global externo
El estado de sesión se modela con un React Context (`AuthProvider`) y se consume con `useAuth`. **Por qué:** la sesión es un estado pequeño, de baja frecuencia de cambio y global; un Context es suficiente y evita sumar una dependencia de store. El estado de servidor (datos de dominio) lo maneja TanStack Query, no el Context.
- *Alternativa descartada:* Zustand/Redux — sobredimensionado para el alcance de la sesión; rechazado para este change.

### D6 — Catálogo de navegación declarativo por rol
La navegación se define como una estructura de datos (`NavItem[]` con los roles que ven cada item) y el sidebar la filtra contra los roles de la sesión, mostrando la unión sin duplicados. **Por qué:** mantiene la navegación testeable como función pura (`buildNav(roles) -> NavItem[]`) y desacoplada del render, encajando con el enfoque TDD del proyecto.

### D7 — Orden de implementación TDD frontend
Por feature: **tipos → service/hook (con su test) → componente (con su test) → test de integración del flujo**. Las piezas con lógica pura (interceptor de refresh, `buildNav`, validación Zod, decisión del guard) se testean primero como funciones puras; los componentes con Vitest + Testing Library. **Por qué:** maximiza la cobertura de la lógica crítica (refresh, guards) con tests rápidos y deterministas, y empuja el diseño hacia funciones puras como pide el proyecto.

## Risks / Trade-offs

- **Pérdida del access token al recargar** → Mitigación: rehidratación vía refresh inicial (D1/D3); `ProtectedRoute` muestra estado de carga hasta resolver la sesión, evitando un flash de redirección a login.
- **Bucle de refresh ante 401 persistente** → Mitigación: flag `_retry` por request (D2); tras un reintento fallido se fuerza logout y redirección a login.
- **Tormenta de refrescos concurrentes** → Mitigación: promesa de refresh compartida que serializa y encola las peticiones afectadas (D2).
- **Contrato del backend de auth no congelado** (forma exacta de la respuesta de login, existencia de `GET /me`, cookie de refresh) → Mitigación: aislar el contrato en `auth/services/` y en tipos; si el endpoint de identidad difiere, el cambio queda contenido en una sola capa. Ver Open Questions.
- **CSRF sobre la cookie de refresh** → Mitigación: cookie SameSite (Strict/Lax) + el backend exige el header `Authorization` para operaciones de estado; el endpoint de refresh debe estar protegido contra uso cross-site. Es responsabilidad compartida con el backend de auth.
- **Divergencia front/back en visibilidad por rol** → Aceptado: el front es UX, el back es la autoridad; un item mostrado de más resulta en un `403` del backend, no en una fuga de datos.

## Migration Plan

No aplica migración de datos ni rollback de schema: es la creación de un proyecto nuevo (`frontend/`). Despliegue: el frontend se sirve como SPA estática apuntando al backend `/api/v1`. Si el change se revierte, basta con eliminar el directorio `frontend/`; no hay impacto en backend ni base de datos.

## Open Questions

- **OQ-1** ✅ **CERRADA (2026-06-05):** No existe `GET /auth/me`. Identidad (`user_id`, `tenant_id`, `roles`, `exp`) viene en los claims del JWT access token de C-03. El frontend decodifica el payload para hidratar `AuthUser` — ver D3.
- **OQ-2** ✅ **CERRADA (2026-06-05):** D1 confirmada. Refresh token como cookie httpOnly. Axios configurado con `withCredentials: true` en el cliente global y en el endpoint de refresh — ver D1.
- **OQ-3:** 2FA y recuperación de contraseña en la UI diferidas fuera de C-21 (Non-Goal).
- **OQ-4:** Catálogo `NavItem[]` definitivo depende de C-22/C-23/C-24; C-21 entrega infra + placeholders por rol.
- **OQ-5:** ALUMNO y NEXO contemplados en el modelo de roles pero sin destinos de navegación hasta que sus módulos existan.
