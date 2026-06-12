## ADDED Requirements

### Requirement: Panel de auditoría read-only

El sistema SHALL exponer la ruta `/admin/auditoria` que permite a un usuario ADMIN consultar el log de eventos de auditoría y las métricas del panel, consumiendo `/api/v1/auditoria` y `/api/v1/auditoria/metricas/*` (C-05/C-19). El panel SHALL ser read-only: NO SHALL realizar mutaciones. El gate SHALL ser fail-closed (solo ADMIN; otros roles reciben `Forbidden403`). El scope (propio/global) lo resuelve el backend según el grant; el frontend NO SHALL forzarlo.

#### Scenario: ADMIN abre el panel de auditoría
- **WHEN** un usuario ADMIN navega a `/admin/auditoria`
- **THEN** el sistema muestra el listado de eventos vía `GET /api/v1/auditoria` y las métricas del panel

#### Scenario: Usuario sin rol ADMIN intenta entrar
- **WHEN** un usuario sin rol ADMIN navega a `/admin/auditoria`
- **THEN** el sistema renderiza `Forbidden403` y no realiza ninguna petición

### Requirement: Listado de eventos con filtros y paginación

El sistema SHALL listar eventos de auditoría con paginación por `limit`/`offset` y permitir filtros de fecha (`desde`/`hasta`) y `actor_user_id` donde los endpoints lo acepten. Al no haber total count, la paginación SHALL avanzar por offset y deshabilitar "siguiente" cuando la página devuelve menos de `limit` filas.

#### Scenario: Paginar el listado
- **WHEN** el ADMIN avanza a la página siguiente del listado
- **THEN** el sistema solicita `GET /api/v1/auditoria` con el `offset` incrementado y muestra los nuevos eventos

#### Scenario: Última página alcanzada
- **WHEN** una página devuelve menos eventos que el `limit`
- **THEN** el sistema deshabilita el control "siguiente"

### Requirement: Métricas y últimas acciones del panel

El sistema SHALL mostrar las métricas del panel (acciones-por-día, interacciones-docente, interacciones-docente-materia, comunicaciones-por-docente) y las últimas-acciones, consumiendo los endpoints `/metricas/*` y `ultimas-acciones`, renderizadas como tablas o KPIs.

#### Scenario: Cargar métricas del panel
- **WHEN** el ADMIN abre el panel de auditoría
- **THEN** el sistema consume los endpoints de métricas y muestra cada resultado como tabla o KPI

#### Scenario: Aplicar rango de fechas a las métricas
- **WHEN** el ADMIN selecciona un rango `desde`/`hasta` para una métrica que lo soporta
- **THEN** el sistema reconsulta esa métrica con los query params `desde`/`hasta` y actualiza la vista
