## Context

El módulo de comunicaciones (C-12) cubre el flujo completo de composición, preview, encolado y seguimiento de un lote activo. La tabla `comunicacion` tiene la columna `enviado_por` (FK a `usuario.id`) desde C-12. El repositorio `ComunicacionRepository` tiene `list_by_lote` pero no `list_by_sender`. La sesión del usuario se pierde al navegar, dejando al PROFESOR sin rastro de envíos pasados.

El frontend ya tiene `features/comunicaciones/` con `ComposeComunicacion`, `LoteStatusBandeja` y `AprobacionPanel`. `ComunicacionesPage` muestra composición + bandeja de lote activo. No hay historial.

## Goals / Non-Goals

**Goals:**
- Agregar `GET /api/v1/comunicaciones/mis-envios` con filtro por estado y paginación offset/limit, restringido al remitente autenticado y al tenant.
- Agregar `list_by_sender` a `ComunicacionRepository` con filtering por `enviado_por`, `tenant_id` y opcionalmente `estado`.
- Agregar schema `MisEnviosResponse` con metadata de paginación.
- Agregar componente `ComunicacionesHistorial` (tabla + filtro estado + paginación).
- Agregar tabs "Componer" | "Historial" en `ComunicacionesPage`.

**Non-Goals:**
- No se expone historial de otros usuarios (ni para COORDINADOR en este change).
- No se implementa búsqueda full-text ni filtros por fecha en este change.
- No se expone el campo `cuerpo` completo en la lista (demasiado payload); se puede agregar en un futuro change.
- No se agrega paginación cursor-based (offset/limit es suficiente para el volumen esperado).
- No se migra el schema de BD (el campo `enviado_por` ya existe).

## Decisions

### D1 — Endpoint GET, no POST
El historial es una consulta de lectura pura con filtros opcionales. Se usa `GET /mis-envios` con query params (`estado`, `offset`, `limit`) en lugar de un POST con body, siguiendo el estándar REST y facilitando el caché de TanStack Query. Alternativa descartada: POST con body de filtros (más complejo, no estándar para lectura).

### D2 — `list_by_sender` en el repositorio, no en el service
El filtrado por `enviado_por` es una responsabilidad de acceso a datos. El service simplemente delega al repositorio y construye la respuesta paginada. Esto mantiene el flujo unidireccional Router → Service → Repository y facilita testear la query de forma aislada.

### D3 — Identidad del remitente desde `resolve_domain_user_id()`, no desde query params
El `usuario.id` (dominio) se resuelve llamando a `resolve_domain_user_id(current_user, db)`, igual que en el endpoint `/encolar`. Nunca se acepta un `sender_id` desde query params. Esto es mandatorio por la regla dura #8 del proyecto.

### D4 — `MisEnviosResponse` con metadata de paginación
Se devuelve `{"total": N, "offset": K, "limit": L, "items": [...]}`. La alternativa (devolver directamente la lista) fue descartada porque el frontend necesita saber el total para renderizar la paginación.

### D5 — Tabs en `ComunicacionesPage` con estado local (`activeTab`)
Un estado local `useState<'componer' | 'historial'>` maneja la tab activa. El historial monta `ComunicacionesHistorial` solo cuando la tab está activa. No se usa un router de tabs para no cambiar la URL ni romper el comportamiento actual de pre-carga de destinatarios desde query params.

### D6 — Permiso reutilizado: `comunicacion:enviar`
El historial de envíos propios requiere el mismo permiso que enviar. No se agrega un permiso nuevo `comunicacion:ver-historial`. El PROFESOR ya tiene `comunicacion:enviar`, por lo que no hay cambio en el seed de RBAC. Alternativa descartada: permiso nuevo (overhead de RBAC innecesario para una query de solo lectura sobre datos propios).

### D7 — Cuerpo no se incluye en la lista de historial (truncado implícito)
El campo `cuerpo` puede ser extenso. El endpoint devuelve `ComunicacionRead` completo (que incluye `cuerpo`) porque el schema ya existe y está en uso. El componente frontend optará por mostrar solo asunto + estado + fecha en la lista, con posibilidad de expandir. No se crea un schema "lite" por YAGNI.

## Risks / Trade-offs

- [Sin índice en `(tenant_id, enviado_por, created_at)`] → Riesgo de query lenta a medida que la tabla crece. Mitigación: agregar índice compuesto como parte de este change (sin migración de schema, solo `CREATE INDEX CONCURRENTLY` o en una migración nueva Alembic).
- [El campo `enviado_por` puede ser NULL para comunicaciones antiguas] → Las comunicaciones encoladas antes de C-12 podrían no tener `enviado_por`. El endpoint filtra `enviado_por = domain_user_id` lo que excluye correctamente los registros sin remitente (NULL != UUID). No hay riesgo de exposición cruzada.
- [Paginación offset en tablas grandes] → A largo plazo, offset/limit degrada en tablas con millones de filas. Para el volumen esperado (cientos de envíos por profesor) es aceptable. Migrar a cursor-based es un change futuro.

## Migration Plan

1. Agregar migración Alembic para índice compuesto `ix_comunicacion_tenant_enviado_por_created` en `(tenant_id, enviado_por, created_at DESC)`.
2. Agregar `list_by_sender` en `ComunicacionRepository` y `MisEnviosResponse` en `schemas/comunicacion.py`.
3. Agregar endpoint `GET /comunicaciones/mis-envios` en `routers/comunicaciones.py`.
4. Agregar tests unitarios (repositorio) y de integración (endpoint).
5. Agregar `getMisEnvios` en `comunicacionService.ts`, `useMisEnvios` hook en `comunicacionHooks.ts`.
6. Crear `ComunicacionesHistorial.tsx`.
7. Actualizar `ComunicacionesPage.tsx` con tabs.
8. Agregar tests de componente para `ComunicacionesHistorial` y `ComunicacionesPage`.

Rollback: el endpoint es aditivo; eliminar la ruta y revertir el componente de tabs es suficiente. El índice puede dropearse sin pérdida de datos.

## Open Questions

- ¿El historial debería incluir el `cuerpo` completo en la lista o solo un snippet? (Decisión tomada: devolver completo via `ComunicacionRead`, el componente elige qué mostrar.)
- ¿Queremos filtros por rango de fechas en un cambio futuro? → Dejado para C-28 si se solicita.
