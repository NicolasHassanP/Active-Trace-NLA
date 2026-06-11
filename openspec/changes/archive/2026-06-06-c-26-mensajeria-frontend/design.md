## Context

El backend de mensajería interna (C-20) está cerrado y expone cuatro endpoints bajo `/api/v1/inbox` (router en `backend/app/api/v1/routers/inbox.py`):

- `GET /inbox` → `List[InboxHiloRead]` — hilos del titular del JWT, con conteo de no leídos.
- `POST /inbox` → `MensajeRead` (201) — inicia un hilo 1:1 (`HiloCreate`: `destinatario_id`, `asunto?`, `cuerpo`).
- `GET /inbox/{hilo_id}` → `List[MensajeRead]` — mensajes del hilo en orden; marca leído.
- `POST /inbox/{hilo_id}/responder` → `MensajeRead` (201) — agrega mensaje (`RespuestaCreate`: `asunto`, `cuerpo`).

Schemas (de `backend/app/schemas/mensajeria.py`):
- `InboxHiloRead`: `id`, `asunto?`, `no_leidos`, `ultimo_mensaje_at?`.
- `MensajeRead`: `id`, `hilo_id`, `remitente_id`, `asunto`, `cuerpo`, `created_at`.

Todos los endpoints exigen el permiso `inbox:usar` (fail-closed → 403). Errores de dominio mapeados: `HiloNoEncontrado` → 404, `DestinatarioInvalido` → 404, `HiloDuplicado` → 409.

El frontend (React 18 + TS + Tailwind v3 + TanStack Query + RHF/Zod + Axios) ya tiene shell, auth y router (C-21). La feature `features/avisos/` es la referencia canónica de estructura: `services/` envuelve los endpoints con `apiClient` y `parseDomainError`; `hooks/` expone queries/mutations de TanStack con `queryKey` y `invalidateQueries`; `pages/` consume hooks y gatea por rol vía `useAuth`. El catálogo de nav vive en `features/shell/components/buildNav.ts` y las rutas lazy en `App.tsx`. Componentes UI compartidos disponibles: `Button`, `Card`, `PageHeader`, `EmptyState`, `Badge`, `StatusBadge`, `TableWrapper`.

## Goals / Non-Goals

**Goals:**
- Montar `/mensajes` con una `InboxPage` funcional que liste hilos, abra un hilo y permita iniciar/responder.
- Tipar el contrato de `/api/v1/inbox` en TS (sin `any`) espejando los schemas de backend.
- Todo fetch a través de hooks de `services/` con TanStack Query (regla dura).
- Forms con React Hook Form + Zod.
- Agregar el ítem de nav "Mensajes" (ícono `mail`, group `TRABAJO`) para PROFESOR, TUTOR, COORDINADOR, ADMIN.
- Componentes React < 200 LOC; estructura feature-based.

**Non-Goals:**
- Cualquier cambio de backend o de contrato de API (C-20 está cerrado).
- Mensajería grupal (el backend es 1:1 en esta iteración — OQ-3).
- Tiempo real / websockets / polling agresivo (la bandeja es pull-based; refetch on demand / invalidación tras mutación).
- Búsqueda de destinatarios sofisticada / directorio de usuarios completo (el form recibe un `destinatario_id`; un selector rico es trabajo futuro).
- Adjuntos, notificaciones push, badge de no leídos global en el nav (futuro).
- Incluir a NEXO ahora (queda fuera del set de roles inicial; se suma cuando se defina su superficie).

## Decisions

### D1 — Nueva feature `features/mensajeria/` espejando `features/avisos/`
Estructura: `types/index.ts`, `services/mensajeriaService.ts`, `hooks/mensajeriaHooks.ts`, `components/*`, `pages/InboxPage.tsx`. Rationale: consistencia con el patrón ya aplicado en el repo; reduce decisiones nuevas y costo de review. Alternativa descartada: meter mensajería dentro de `comunicaciones` — son dominios distintos (comunicaciones = saliente con aprobación; mensajería = interna pull-based), mezclarlos rompe la cohesión.

### D2 — Service envuelve los 4 endpoints con `apiClient` + `parseDomainError`
Cada función (`listarHilos`, `abrirHilo`, `iniciarHilo`, `responder`) llama a `@/shared/services/api` y normaliza errores con `parseDomainError`, igual que `avisosService`. Identidad y tenant viajan en el JWT vía interceptor — nunca en el body. Rationale: regla dura de cliente HTTP centralizado + manejo uniforme de errores de dominio (404/409).

### D3 — TanStack Query: queries para lectura, mutations para escritura
- `useHilos()` → query key `['mensajeria-hilos']`.
- `useHilo(hiloId)` → query key `['mensajeria-hilo', hiloId]`, `enabled: !!hiloId`.
- `useIniciarHilo()` → mutation; on success invalida `['mensajeria-hilos']`.
- `useResponder()` → mutation; on success invalida `['mensajeria-hilo', hiloId]` y `['mensajeria-hilos']` (responder cambia `ultimo_mensaje_at` y `no_leidos` de la lista).
Abrir un hilo marca leído server-side, así que tras `useHilo` resolver hay que invalidar `['mensajeria-hilos']` para refrescar el contador de no leídos. Rationale: caché coherente sin polling.

### D4 — Estado de hilo seleccionado en la página, no en la URL
`InboxPage` mantiene `selectedHiloId` con `useState`. Layout master-detail: lista de hilos a la izquierda, hilo abierto a la derecha. Rationale: simplicidad; la ruta `/mensajes/:hiloId` es una mejora futura no requerida. Alternativa (ruta anidada) descartada por scope.

### D5 — Forms separados con Zod
`NuevoHiloForm` (campos `destinatario_id` requerido, `asunto?`, `cuerpo` no vacío) y `ResponderForm` (campos `asunto` no vacío, `cuerpo` no vacío), cada uno con su schema Zod espejando las validaciones de backend (`cuerpo`/`asunto` no vacíos). `destinatario_id` es un input de UUID por ahora (sin selector de directorio — ver Non-Goals). Rationale: regla dura RHF + Zod; validación cliente alineada al backend evita 422 evitables.

### D6 — Componentes pequeños y enfocados
- `HilosList` — lista de hilos (asunto/“(sin asunto)”, preview o `ultimo_mensaje_at`, badge de no leídos).
- `HiloView` — mensajes en orden cronológico (remitente, cuerpo, `created_at`); distingue mensajes propios por `remitente_id === currentUserId`.
- `NuevoHiloForm`, `ResponderForm` — forms.
- `InboxPage` — orquesta hooks + estado + layout, gatea por rol con `useAuth`.
Todos < 200 LOC. Rationale: regla dura de tamaño + testabilidad por unidad.

### D7 — Nav y ruta
Agregar a `NAV_CATALOG` un ítem `{ label: 'Mensajes', path: '/mensajes', roles: ['PROFESOR','TUTOR','COORDINADOR','ADMIN'], icon: 'mail', group: 'TRABAJO' }`. Verificar que `mail` esté soportado por `NavIcon` (ya lo usa "Comunicaciones"). En `App.tsx`, agregar página lazy `InboxPage` y ruta protegida `/mensajes` con `requiredRoles` iguales al ítem de nav. Rationale: el backend ya gatea por permiso; el frontend gatea visibilidad/acceso por rol coherentemente. El gate final es el backend (`inbox:usar`).

### D8 — Identidad del usuario actual desde `useAuth`
Para distinguir mensajes propios en `HiloView`, tomar el id del usuario autenticado desde el contexto de auth (`useAuth`), nunca de un parámetro. Rationale: regla dura de identidad desde sesión.

## Risks / Trade-offs

- **[`destinatario_id` como UUID crudo en el form es poco usable]** → Mitigación: se acepta para C-26 (scope frontend de consumo); se documenta como Non-Goal y se deja un punto de extensión (selector de usuarios) para un change futuro. No bloquea el flujo end-to-end.
- **[El nombre del remitente no viene en `InboxHiloRead`/`MensajeRead` — solo `remitente_id`/`destinatario_id` como UUID]** → Mitigación: mostrar lo disponible (asunto del hilo, "Yo" vs "Otro" por comparación de id). Resolver nombres legibles exigiría un endpoint de usuarios o un campo extra de backend — fuera de scope (sin cambios de backend). Se anota como Open Question.
- **[Marcar leído al abrir genera un refetch extra de la lista]** → Mitigación: invalidar `['mensajeria-hilos']` solo tras abrir; costo bajo (lista pequeña, pull-based).
- **[Permiso `inbox:usar` vs roles del nav pueden divergir]** → Mitigación: el backend es la autoridad (403 fail-closed); el nav es solo visibilidad. Si un rol ve el ítem pero no tiene el permiso, recibirá 403 y la UI mostrará el error de dominio. Aceptable; el set de roles inicial se alinea con quienes tienen `inbox:usar`.

## Open Questions

- **OQ-1**: ¿Mostrar nombre legible del remitente/destinatario? Hoy solo hay UUID en el contrato. Resolver requiere endpoint de usuarios o ampliar el schema de backend (otro change). Para C-26 se muestra "Yo"/"Otro" + asunto.
- **OQ-2**: ¿Incluir NEXO en los roles que ven "Mensajes"? Diferido hasta definir la superficie de NEXO; por ahora PROFESOR/TUTOR/COORDINADOR/ADMIN.
- **OQ-3**: ¿`/mensajes/:hiloId` como ruta deep-linkable? Diferido; C-26 usa estado local (D4).
