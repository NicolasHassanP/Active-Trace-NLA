## Context

C-23 es el frente de coordinación/administración del frontend, construido sobre el shell + auth de C-21 y siguiendo el patrón establecido por C-22 (vistas académicas del docente). Todos los backends que consume ya están archivados y validados: C-08 (equipos), C-13 (encuentros/guardias), C-14 (evaluaciones/coloquios), C-15 (avisos+ack), C-16 (tareas internas), C-17 (programas+fechas). C-23 no introduce contratos backend nuevos: solo consume endpoints existentes bajo el prefijo `/api/v1`.

**Estado actual del frontend**:
- `frontend/src/features/` contiene `auth`, `shell`, `padron`, `atrasados`, `comunicaciones` (C-21 + C-22).
- `App.tsx` registra rutas lazy dentro de `ProtectedRoute` + `AppLayout`; ya existe el patrón de `requiredRoles` por ruta.
- `buildNav.ts` ya declara ítems placeholder para `/equipos`, `/encuentros`, `/coloquios` (gateados a COORDINADOR/ADMIN), pendientes de activar.
- Helpers compartidos: `@/shared/services/api` (Axios + interceptor JWT), `@/shared/services/domainError.ts` (`parseDomainError`), `ProtectedRoute`, Sonner (`<Toaster/>` montado en `App.tsx`).

**Constraints (reglas duras del proyecto)**: React 18 + TS sin `any` ni class components; TanStack Query para todo fetch (vía `services/` hooks); RHF + Zod; Tailwind; componentes < 200 LOC; PascalCase en componentes; identidad/tenant SIEMPRE del JWT (nunca en body/URL); RBAC fail-closed en cada ruta; Strict TDD en apply (Vitest + Testing Library).

## Goals / Non-Goals

**Goals:**
- Entregar la superficie de UI de coordinación/admin para equipos, avisos, tareas, monitores, encuentros/guardias, coloquios y el flujo de setup de cuatrimestre.
- Reutilizar al 100% los helpers compartidos (api, domainError, ProtectedRoute, Sonner) y replicar exactamente la estructura feature-based de C-22.
- Dejar cada comportamiento aislado y testeable para el ciclo Strict TDD de apply.
- Alinear types/services con los endpoints reales del backend, sin inventar contratos.

**Non-Goals:**
- NO se modifican contratos ni código del backend.
- NO se cubren features de ALUMNO (reserva de turno de coloquio es lado alumno — fuera de scope; C-23 cubre el lado coordinación).
- NO se cubren liquidaciones (C-18/C-24) ni auditoría/perfil (C-19/C-20).
- NO se rediseña el shell ni el sistema de auth (vienen de C-21).
- NO se agregan dependencias npm nuevas.

## Decisions

### D1 — Decomposición en 7 capabilities = 7 módulos feature
Una capability (delta spec) ⇒ un módulo `frontend/src/features/{name}/`. Módulos elegidos:
`equipos`, `avisos`, `tareas`, `monitores`, `encuentros-coord`, `coloquios`, `setup-cuatrimestre`.
- **Por qué**: cada uno mapea a un backend distinto y a una épica distinta; mantiene los módulos cohesivos y bajo el límite de tamaño. Alternativa descartada: un único mega-módulo "coordinacion" → violaría la separación feature-based y dispararía archivos > 200 LOC.
- `encuentros-coord` se nombra así (no `encuentros`) para no colisionar conceptualmente con un futuro módulo de encuentros del docente (F6.1–F6.4), que NO es parte de C-23.

### D2 — Estructura interna idéntica a C-22
Cada módulo sigue: `types/index.ts`, `services/<name>Service.ts`, `hooks/<name>Hooks.ts`, `components/*`, `pages/*`, más `__tests__` en services/hooks/pages. Los services envuelven cada llamada con `try/catch` → `parseDomainError(err)` (patrón de `atrasadosService.ts`). Los hooks usan `useQuery`/`useMutation` con `queryKey` que incluye TODOS los filtros activos (patrón de `atrasadosHooks.ts`).
- **Por qué**: consistencia con el código existente, predecibilidad para revisión y para el agente de apply.

### D3 — Routing y gating
Cada página se registra como ruta lazy en `App.tsx` dentro del slot protegido, envuelta en `<ProtectedRoute requiredRoles={[...]}>` con la matriz de roles de `03_actores_y_roles.md`:
- `/equipos` → COORDINADOR, ADMIN (gestión); "mis equipos" visible además a PROFESOR, TUTOR, NEXO (la página decide qué render según permiso).
- `/avisos` → cualquier autenticado (bandeja); gestión solo COORDINADOR, ADMIN.
- `/tareas` → TUTOR, PROFESOR, COORDINADOR, ADMIN; panel admin solo COORDINADOR, ADMIN.
- `/monitor`, `/encuentros`, `/coloquios`, `/setup-cuatrimestre` → COORDINADOR, ADMIN.
Los ítems de nav se activan/añaden en `buildNav.ts` con los mismos roles. Gating fail-closed: el rol viene del JWT (sesión), nunca de la URL.
- **Por qué**: `ProtectedRoute` con `requiredRoles` ya es el patrón de C-22 (`App.tsx` lo usa para `/padron`, `/atrasados`). El gating fino dentro de la página (gestión vs lectura) se resuelve con el rol/permiso de la sesión.

### D4 — Setup de cuatrimestre como orquestador, no como nuevo backend
`setup-cuatrimestre` NO tiene endpoints propios: es un wizard que reutiliza los services de `equipos`, `avisos`, `programas`/`fechas-academicas` (estructura académica) en pasos secuenciales. Cada paso reusa el hook/mutation del módulo correspondiente.
- **Por qué**: FL-03 es una secuencia de operaciones ya existentes; duplicar lógica violaría DRY y la regla de "todo fetch por services/". Alternativa descartada: un service propio de setup → no hay backend que lo respalde.

### D5 — Exportaciones (CSV/archivo) vía descarga del blob
`GET /api/v1/equipos/exportar`, `GET /api/v1/guardias/export` y el export del monitor devuelven adjuntos. Se consumen con Axios `responseType: 'blob'` y se dispara la descarga creando un object URL temporal. Patrón encapsulado en un helper de descarga reutilizable dentro del módulo (o compartido si C-22 ya lo tiene — verificar en apply).
- **Por qué**: es la forma estándar sin `any` y sin romper el interceptor JWT.

### D6 — Programas y fechas académicas se consumen desde setup-cuatrimestre (sin módulo propio)
Los endpoints `/api/v1/programas` (F5.3) y `/api/v1/fechas-academicas` (F5.4) se invocan desde el wizard de setup. NO se crea un módulo de "estructura académica" en C-23 — esa pantalla ADMIN (`/admin/estructura`) corresponde a otro change. C-23 solo necesita las acciones de alta puntuales que FL-03 requiere.
- **Por qué**: mantener el scope de C-23 acotado a coordinación; evitar pisar el módulo de estructura académica de ADMIN.

### D7 — Validación tipada con Zod por formulario
Todos los formularios (asignación masiva, clonado, vigencia, alta de aviso, alta de tarea, creación de convocatoria) usan RHF + Zod. Los esquemas Zod codifican las reglas de coherencia (ej. aviso con alcance no global ⇒ contexto obligatorio; cupo de coloquio > 0).
- **Por qué**: regla dura del stack; mueve la validación al borde y la hace testeable.

## Risks / Trade-offs

- **[Contratos de request/response no completamente documentados en las specs backend]** → Las specs backend describen comportamiento (SHALL) pero los shapes exactos de algunos DTOs (ej. `AsignacionMasivaRequest`, `CrearAvisoRequest`, filas del monitor, agenda de coloquios) se leen de los routers/schemas en apply. Mitigación: el agente de apply DEBE leer `backend/app/schemas/{equipo,aviso,tarea,...}.py` antes de escribir `types/index.ts`; no inventar campos. Las OQ abajo capturan los puntos más ambiguos.
- **[`/avisos` no tiene endpoint de "listar avisos gestionados" para coordinación]** → el backend expone POST/PUT/DELETE para gestión y GET feed/pendientes para lectura (filtrados por audiencia del usuario). Un COORDINADOR puede no ver en su feed los avisos que no le aplican por audiencia. Ver OQ-1.
- **[Export del monitor sin endpoint dedicado confirmado]** → `/api/v1/analisis` tiene `/sin-corregir/export` pero el export del monitor general no está confirmado. Ver OQ-3.
- **[Scope grande → riesgo de PRs enormes]** → mitigado por D1 (7 módulos independientes) y por tasks.md agrupado por feature; cada módulo se puede implementar/revisar por separado.
- **[Componentes que superan 200 LOC]** (tablas con muchos filtros: monitor, panel de tareas) → extraer subcomponentes (filtros, fila, toolbar) desde el inicio.

## Migration Plan

No aplica migración de datos (frontend puro). Despliegue: cada módulo es aditivo; las rutas nuevas y los ítems de nav no afectan rutas existentes. Rollback: revertir el registro de rutas en `App.tsx` y los ítems en `buildNav.ts` desactiva el feature sin tocar backend.

## Open Questions

> Resolver ANTES de apply. No adivinar sobre contratos ambiguos.

- ~~**OQ-1 — Lectura de avisos para el panel de gestión**~~ **RESUELTO**: Resolved by adding backend `GET /avisos/gestion` (avisos:publicar) — C-15 follow-up implemented in this change. El endpoint retorna TODOS los avisos no eliminados del tenant sin filtro de audiencia, gateado por `avisos:publicar`, con `ack_count` derivado. Ver delta spec `specs/avisos-publicacion/spec.md`.

- **OQ-2 — Shape exacto de `AsignacionMasivaRequest` y `ClonarEquipoRequest`**: confirmar contra `backend/app/schemas/equipo.py` los campos exactos (ej. lista de `usuario_id` + rol + vigencia; identificación de equipo origen/destino en clonar). Determina los Zod schemas y los `types`. **Resolver leyendo el schema en apply (no inventar).**

- **OQ-3 — Export del monitor general**: ¿existe un endpoint de exportación para `GET /api/v1/analisis/monitor`, o se reutiliza `/api/v1/analisis/sin-corregir/export`, o el export se hace client-side desde las filas ya cargadas? Determina el requisito "Exportación del monitor" en `monitores-frontend`. **Bloqueante para esa acción.**

- **OQ-4 — Filtros disponibles en `GET /api/v1/encuentros/instancias` y `GET /api/v1/guardias`**: confirmar qué query params aceptan (materia, estado, rango de fechas, etc.) para construir los filtros de UI sin asumir. **Resolver leyendo los routers/schemas en apply.**

- **OQ-5 — Helper de descarga de blobs**: ¿C-22 ya dejó un helper compartido para disparar descargas (CSV/archivo), o C-23 debe crearlo? Si no existe, crearlo en `@/shared/services/` y reutilizarlo en equipos/guardias/monitor. **No bloqueante; decisión de ubicación.**
