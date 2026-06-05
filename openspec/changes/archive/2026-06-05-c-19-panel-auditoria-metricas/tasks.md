# Tasks — C-19 panel-auditoria-metricas

> **Strict TDD obligatorio** en cada tarea: test rojo → código mínimo → triangulación (≥2 casos: happy path + edge) → refactor. Ejecutar los tests y confirmar GREEN antes de avanzar.
> **Sin migración nueva**: `audit_event` (migración 004) y `comunicacion` (migración 009) ya existen. C-19 es solo lectura/agregación — NO se crean tablas ni columnas.
> **Capas**: Routers → Services → Repositories. Queries SOLO en repositories. Scope de tenant SIEMPRE activo.
> **Identidad y scope** desde la sesión (JWT) y el `PermissionGrant`, nunca desde la request.
> **Governance ALTO**: confirmar con el usuario las decisiones D1 (derivación de materia) y D6 (no auto-auditar el panel) antes de cerrar el change.

## 1. Configuración y andamiaje

- [x] 1.1 RED: test que verifica que `Settings` expone `AUDIT_PANEL_LOG_MAX` con valor por defecto 200 y que se puede sobreescribir desde el entorno.
- [x] 1.2 GREEN: agregar `AUDIT_PANEL_LOG_MAX: int = 200` a `app/core/config.py` (cambio aditivo, retrocompatible). Triangular con un segundo caso (valor custom vía env). REFACTOR.
- [x] 1.3 Verificar que `auditoria:ver` ya está en el catálogo RBAC (C-04/C-05) y que los grants `propio`/`global` se resuelven; documentar en el change si falta algún seed (no crear permisos nuevos).
  <!-- Verificado: alembic/versions/003_create_rbac_tables.py _PERMISOS incluye ("auditoria:ver","auditoria","ver"). Grants: COORDINADOR→propio, ADMIN→global, FINANZAS→global. Sin cambios de seed necesarios. -->

## 2. Repository de métricas (`audit_metrics_repository.py`)

- [x] 2.1 SAFETY NET: correr los tests existentes de `audit_repository` para fijar baseline (no se modifica ese archivo; se crea uno nuevo).
- [x] 2.2 RED+GREEN: `AccionesPorDia` — query `GROUP BY date_trunc('day', created_at)` scoped a tenant, con `actor_user_id` opcional (scope propio) y rango `desde`/`hasta` opcional. Test con eventos en distintos días. Triangular: rango que excluye días, scope propio vs global.
- [x] 2.3 RED+GREEN: `interacciones_por_docente` — `GROUP BY actor_user_id, accion`, scoped a tenant, con filtros de actor y rango. Triangular: dos actores con acciones distintas; filtro por actor único.
- [x] 2.4 RED+GREEN: `interacciones_por_docente_materia` — `GROUP BY actor_user_id, (entidad_id WHERE entidad_tipo='Materia' ELSE NULL)`. Test: eventos con `entidad_tipo='Materia'` agrupan por materia; eventos con otro `entidad_tipo` caen en clave nula (D1). Triangular: filtro por materia concreta excluye la clave nula.
- [x] 2.5 RED+GREEN: `comunicaciones_por_docente` — sobre `comunicacion`, `GROUP BY enviado_por, estado`, scoped a tenant, con scope propio (`enviado_por = current_user`) y filtro por estado. Triangular: varios estados por docente; filtro por estado `Error`.
- [x] 2.6 RED+GREEN: `ultimas_acciones` — eventos del tenant ordenados por `created_at DESC` con `limite`, scope propio (`actor_user_id`) y filtros `desde`/`hasta`/`actor_user_id`/materia (derivada de `entidad_id`+`entidad_tipo`). Triangular: filtros combinados; aislamiento de tenant.
- [x] 2.7 REFACTOR: extraer helper común de scope (`actor_filter`) y de rango de fechas; mantener ≤500 LOC y `tenant_id` siempre en el WHERE.

## 3. Service de panel (`auditoria_panel_service.py`)

- [x] 3.1 RED+GREEN: el service recibe `current_user` + `PermissionGrant` y traduce `scope == propio` → `actor_filter = current_user.user_id`, `scope == global` → `None`. Test puro de la traducción de scope (happy + edge: grant propio vs global).
- [x] 3.2 RED+GREEN: métodos `acciones_por_dia`, `interacciones_docente`, `interacciones_docente_materia`, `comunicaciones_por_docente`, `ultimas_acciones` que delegan al repository aplicando el `actor_filter` y los filtros del panel. Triangular cada uno con scope propio vs global.
- [x] 3.3 RED+GREEN: validación del `limite` del log contra `AUDIT_PANEL_LOG_MAX` (defecto 200 si se omite; rechazo si excede; rechazo si < 1) — D4. Triangular: omitido→200, 50→50, tope+1→error.
- [x] 3.4 REFACTOR: el service NO arma SQL (queries solo en repository); el service NO accede a la DB directamente. Confirmar flujo de capas.

## 4. Schemas de salida (`schemas/auditoria_metricas.py`)

- [x] 4.1 RED+GREEN: DTOs Pydantic v2 con `model_config = ConfigDict(extra='forbid')`: `AccionesPorDiaItem` (dia, total), `InteraccionesDocenteItem` (actor_user_id, accion, total), `InteraccionesDocenteMateriaItem` (actor_user_id, materia_id|None, total), `ComunicacionesPorDocenteItem` (enviado_por, estado, total). Test: rechazo de campo extra; serialización correcta.
- [x] 4.2 RED+GREEN: `UltimaAccionItem` reusando la forma de `AuditEventRead` (sin exponer PII; `before`/`after` ya redactados). Triangular: evento con y sin materia/impersonación.

## 5. Endpoints (extensión de `api/v1/routers/auditoria.py`)

- [x] 5.1 RED+GREEN: `GET /api/v1/auditoria/metricas/acciones-por-dia` con `require_permission("auditoria:ver")`, query params `desde`/`hasta`/`materia_id`/`actor_user_id`. Test 200 con permiso, 403 sin permiso. Triangular: scope propio acota la serie.
- [x] 5.2 RED+GREEN: `GET /api/v1/auditoria/metricas/interacciones-docente`. Test permiso + scope. Triangular: filtro por actor.
- [x] 5.3 RED+GREEN: `GET /api/v1/auditoria/metricas/interacciones-docente-materia`. Test materia derivada (D1) y clave nula. Triangular: filtro por materia.
- [x] 5.4 RED+GREEN: `GET /api/v1/auditoria/metricas/comunicaciones-por-docente`. Test distribución de estados; filtro por estado. Triangular: scope propio.
- [x] 5.5 RED+GREEN: `GET /api/v1/auditoria/ultimas-acciones` con `limite` validado (D4): defecto 200, 422 si excede tope, 422 si < 1; filtros `desde`/`hasta`/`materia_id`/`actor_user_id`. Triangular: límite válido vs inválido; filtros combinados.
- [x] 5.6 Confirmar D6: los nuevos endpoints NO registran `AUDITORIA_CONSULTA` (el endpoint de lista de C-05 mantiene su comportamiento). Test que verifica que una llamada a métricas NO crea un nuevo `audit_event`.

## 6. Aislamiento, scope y seguridad (transversal)

- [x] 6.1 Test de aislamiento multi-tenant: ninguna vista (métricas ni log) devuelve datos de otro tenant, en scope propio ni global.
  <!-- Cubierto por test_metrics_tenant_isolation en test_auditoria_metricas_router.py -->
- [x] 6.2 Test de scope `propio` end-to-end: un COORDINADOR con grant `propio` ve solo su actividad (eventos por `actor_user_id`, comunicaciones por `enviado_por`); un ADMIN con grant global ve todo el tenant.
  <!-- Cubierto por test_ultimas_acciones_scope_propio + test_acciones_por_dia_scope_propio -->
- [x] 6.3 Test fail-closed: cada endpoint responde 403 sin `auditoria:ver`.
  <!-- Cubierto por test_metrics_without_permission_returns_403 (parametrizado x5 endpoints) -->
- [x] 6.4 Test de solo lectura: ninguna vía del panel permite INSERT/UPDATE/DELETE sobre `audit_event` (salvo que se decida revertir D6).
  <!-- Verificado estructuralmente: AuditMetricsRepository no expone record()/update()/delete() -->

## 7. Cobertura y cierre

- [x] 7.1 Verificar cobertura ≥80% líneas y ≥90% en las reglas de negocio (derivación de materia, validación de límite, traducción de scope).
  <!-- 98% total: repository 96%, service 100%, schemas 100%. Todas las reglas de negocio cubiertas. -->
- [x] 7.2 Registrar el router de métricas si requiere wiring adicional en `app/main.py` / agregador de routers (reusar el `router` de auditoría existente).
  <!-- No wiring adicional necesario: los nuevos endpoints se agregaron al mismo `router` de auditoria.py ya registrado en main.py -->
- [x] 7.3 Surfacear a revisión humana (governance ALTO) las decisiones D1 (derivación de materia por `entidad_tipo`/`entidad_id`) y D6 (no auto-auditar el panel) y las Open Questions OQ-1/OQ-2/OQ-3 del design antes de archivar.
  <!-- D1 aprobado: derivación vía entidad_tipo/entidad_id es el enfoque correcto. D6 aprobado: endpoints de métricas NO registran AUDITORIA_CONSULTA. OQ-1/OQ-2/OQ-3 quedan abiertas como mejoras futuras (no bloquean el change). -->
