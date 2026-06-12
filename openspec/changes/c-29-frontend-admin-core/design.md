## Context

El shell de la app (C-21, hecho) ya muestra el grupo de nav **ADMINISTRACIÓN** para rol ADMIN con tres ítems: `Usuarios` (`/admin/usuarios`), `Estructura académica` (`/admin/estructura`) y `Auditoría` (`/admin/auditoria`). Ninguna ruta está registrada en `App.tsx`, así que las tres caen en `NotFound404` adrede, esperando al change diferido **C-24 `frontend-finanzas-y-admin`**.

C-24 está bloqueado por **C-18** (liquidaciones) y por **PA-22/PA-23/PA-25**. Pero su parte admin-core no comparte ninguna de esas dependencias: los tres backends ya existen, están registrados y testeados:

- **Estructura (C-06)** — `backend/app/api/v1/routers/admin_estructura.py`, schemas en `backend/app/schemas/estructura.py`. Endpoints bajo `/api/v1/admin/{carreras,materias,cohortes}`: GET (lectura) → `estructura:ver`; POST/PATCH/DELETE → `estructura:gestionar`. Excepciones de dominio mapeadas: 409 `ConflictoUnicidad` / `CarreraInactiva` / `CarreraConCohorteAbiertas`, 404 `*NoEncontrada`.
- **Usuarios (C-07)** — `backend/app/api/v1/routers/admin_usuarios.py`, schema `UsuarioRead`/`UsuarioCreate`/`UsuarioUpdate` en `backend/app/schemas/usuario.py`. GET/POST/PATCH/DELETE `/api/v1/admin/usuarios`, todos `usuarios:gestionar`. 409 `ConflictoEmail`, 404 `UsuarioNoEncontrado`. `UsuarioRead` (OQ-3) expone solo `id,email,nombre,apellidos,legajo,estado,asignaciones,created_at,updated_at` — **nunca** dni/cuil/cbu/alias_cbu.
- **Auditoría (C-05/C-19)** — `backend/app/api/v1/routers/auditoria.py`, schemas `AuditEventRead` y `auditoria_metricas.py`. `GET /api/v1/auditoria` (list con `limit`/`offset`) + 4 endpoints de métricas + `ultimas-acciones`, todos `auditoria:ver`. El scope (propio/global) lo resuelve el `PermissionGrant` en el backend.

El frontend existente ya tiene los patrones a reutilizar:
- `features/asignaciones/` — tabla ABM + filtros client-side + formularios RHF/Zod + service con `parseDomainError` (`frontend/src/features/asignaciones/services/asignacionService.ts`).
- `features/setup-cuatrimestre/components/PasoCohorte.tsx` — crear cohorte vía `POST /admin/cohortes`; `useEstructuraOptions.ts` — cargar catálogos de estructura.
- `UsuarioCombobox` / `UsuarioMultiCombobox` — selección de usuarios.
- `shared/components/ui` — `EmptyState`, `StatusBadge`, `Button`, `PageHeader`; `Forbidden403`; `shared/services/domainError` (`parseDomainError`).
- Cliente HTTP central `@/shared/services/api` (interceptor inyecta JWT; tenant/identidad nunca en el body).

## Goals / Non-Goals

**Goals:**
- Convertir los 3 ítems de nav ADMIN que hoy dan 404 en páginas reales, consumiendo backends existentes.
- ABM completo de carreras/materias/cohortes desde la UI (desbloquea el gap de "crear materias/carreras").
- Alta/edición/baja lógica de usuarios del tenant respetando el contrato no-PII de `UsuarioRead`.
- Panel de auditoría read-only: listado filtrable + paginado, métricas y últimas acciones.
- RBAC fail-closed en cada página (gate por rol/permiso, patrón `Forbidden403`).
- Reutilizar patrones existentes (`features/asignaciones`, `PasoCohorte`, componentes `ui`, `parseDomainError`).

**Non-Goals:**
- **Nada de finanzas**: liquidaciones, facturas, grilla salarial. Quedan exclusivamente en C-24.
- **Cero dependencia y cero referencia a C-18.** Ningún archivo, type, ruta ni nav de este change menciona liquidaciones.
- No tocar el ítem de nav `Liquidaciones` (sigue `disabled` para C-24).
- No crear ni modificar backend (routers/services/repos/modelos/migraciones). Solo se consume.
- No implementar ABM de asignaciones de usuario aquí (ya existe en `features/asignaciones`); la edición de usuario gestiona los campos del propio usuario, no sus asignaciones.
- No implementar gráficos pesados; las métricas se muestran como tablas/KPIs simples (charts opcionales, fuera de alcance del MVP de este change).

## Decisions

### D1 — Tres features independientes, una por página
Crear `features/admin-estructura/`, `features/admin-usuarios/`, `features/admin-auditoria/`, cada una con `{components,hooks,services,types,pages}` (estructura feature-based del proyecto). Alternativa considerada: una sola feature `admin/` con subcarpetas — descartada porque las tres páginas tienen dominios, permisos y governance distintos, y separarlas mantiene cada componente <200 LOC y facilita el testing aislado.

### D2 — Capa de servicios espejo del patrón `asignacionService`
Cada feature tiene un `service` con funciones async que envuelven `apiClient` y traducen errores con `parseDomainError`. Identidad/tenant **nunca** en el body — viajan por el JWT vía interceptor (regla dura #8/#9). Los hooks TanStack Query (`useQuery`/`useMutation`) consumen esos services; ningún componente llama a `apiClient` directo (regla del proyecto: todo fetch pasa por hooks de `services/`). Invalidación de queries tras cada mutación (create/edit/baja) para refrescar la tabla.

### D3 — RBAC fail-closed por página con `Forbidden403`
Cada page hace el patrón de `SetupCuatrimestrePage`: lee `roles` de `useAuth`, y si el usuario no es ADMIN (único rol con estos permisos) renderiza `<Forbidden403/>` antes de montar nada. El backend es la fuente de verdad (fail-closed con `require_permission`); el gate del frontend es UX, no seguridad. Las rutas en `App.tsx` van dentro del wrapper de ruta protegida ya existente.

### D4 — Estructura: tabs por entidad, ABM tabla + form RHF/Zod
`/admin/estructura` con tres secciones (carreras / materias / cohortes), cada una tabla ABM + form de alta/edición. Reutilizar el patrón `AsignacionesTable` + `AsignacionForm`. Cohortes reutiliza la lógica de `PasoCohorte` (carrera_id obligatorio, `vig_hasta` nullable = cohorte abierta). Filtros client-side como en `AsignacionesFilters` (los catálogos son chicos). Manejo de errores de dominio: 409 unicidad/inactiva/cohortes-abiertas y 404 mostrados con el mensaje de `parseDomainError`. Tipos derivados de los schemas `CarreraRead/MateriaRead/CohorteRead` (`estado: EstadoEstructura`).

### D5 — Usuarios: tabla + form con solo campos no-PII; baja = soft delete
La tabla y el form de `/admin/usuarios` operan exactamente sobre el contrato `UsuarioRead` (no-PII). El form de alta envía `UsuarioCreate` (email, nombre, apellidos, legajo, estado y opcionalmente flags como `facturador`); **el frontend no recoge ni muestra dni/cuil/cbu/alias_cbu** — esos campos PII financiera son de C-24/finanzas y quedan fuera. La baja llama `DELETE` (204) = soft delete en backend; la UI confirma antes de ejecutar. 409 `ConflictoEmail` y 404 mapeados con `parseDomainError`.

### D6 — Auditoría: read-only, listado paginado + métricas como tablas/KPIs
`/admin/auditoria` con: (a) tabla de eventos (`GET /auditoria` con `limit`/`offset`, paginación server-side por offset), (b) panel de métricas que consume los 4 endpoints `/metricas/*` y `ultimas-acciones`, renderizados como tablas/KPIs. Filtros de fecha (`desde`/`hasta`) y `actor_user_id` pasados como query params a los endpoints que los aceptan. El scope (propio/global) lo decide el backend según el grant; el frontend no lo fuerza. Sin mutaciones — solo `useQuery`.

### D7 — Routing y nav: registrar rutas, desmarcar placeholders
Agregar en `App.tsx` las 3 rutas protegidas (`/admin/usuarios`, `/admin/estructura`, `/admin/auditoria`) apuntando a las nuevas pages. En `buildNav.ts` los ítems ya existen para ADMIN; solo se elimina su condición de placeholder (el comentario de cabecera que dice "Destinations are placeholders until C-22/C-23/C-24" se actualiza). No se cambia el requisito de comportamiento de `buildNav` (sigue filtrando por roles), por eso no hay capability modificada.

### D8 — Checkpoints de governance en la fase de apply
- **usuarios (CRÍTICO)** y el gateo RBAC de cada página: en apply, describir el form/flujo de alta-baja y el gate `Forbidden403` y **esperar confirmación humana antes de escribir** (governance CRÍTICO del proyecto). La lógica sensible ya está en backend; el checkpoint cubre que el frontend no recoja PII ni evada el gate.
- **estructura (MEDIO)**: implementar con checkpoints, surfaceando decisiones no obvias (p.ej. manejo de cohorte abierta).
- **auditoría (BAJO)**: read-only, autonomía total si pasan los tests.

## Risks / Trade-offs

- **[Filtrado de PII en usuarios]** Si el form de usuarios incluyera campos PII financiera, violaría OQ-3 y la regla dura #12 → Mitigación: el form opera SOLO sobre los campos de `UsuarioRead`/`UsuarioCreate` no-PII; checkpoint CRÍTICO en apply revisa el set de campos antes de codear.
- **[Acoplamiento accidental a C-18]** Reutilizar componentes de C-24 podría arrastrar referencias a finanzas → Mitigación: features nuevas y aisladas; regla dura del change "cero referencia a C-18"; revisión de imports en apply.
- **[Paginación de auditoría]** El endpoint usa `limit`/`offset` sin total count → Mitigación: paginación por offset con botón "siguiente/anterior" y deshabilitar "siguiente" cuando la página devuelve menos de `limit` filas. Charts quedan fuera de alcance (tablas/KPIs).
- **[Permiso lectura vs escritura en estructura]** GET usa `estructura:ver` y escritura `estructura:gestionar`; un ADMIN podría ver pero no gestionar → Mitigación: el gate de página usa rol ADMIN (que tiene ambos); los botones de escritura confían en el 403 del backend y muestran el error de dominio si ocurre.
- **[Resolución de nombres en auditoría]** Las métricas devuelven `actor_user_id`/`materia_id` crudos → Mitigación: para el MVP se muestran los identificadores; resolver a nombres legibles (vía `UsuarioCombobox`/catálogo de estructura) es mejora opcional, no bloqueante.

## Migration Plan

No hay migración de datos ni de backend. Despliegue puramente frontend:
1. Crear las 3 features (services → hooks → components → pages), TDD.
2. Registrar las 3 rutas en `App.tsx` y actualizar `buildNav.ts`.
3. Rollback: revertir el commit del change; las rutas vuelven a `NotFound404` y los ítems de nav siguen visibles (estado previo idéntico). Sin estado persistente que limpiar.

## Open Questions

- ¿Las métricas de auditoría deben resolver `actor_user_id`/`materia_id` a nombres en este change o se difiere a una mejora? (Propuesta: mostrar IDs en el MVP; resolución de nombres como follow-up.)
- ¿La edición de usuario debe permitir cambiar `estado` (activo/baja) además del `DELETE` soft-delete, o `estado` se gestiona solo por la baja? (Propuesta: baja vía `DELETE`; `estado` editable en PATCH solo si la UX lo requiere — decidir en apply con checkpoint CRÍTICO.)
