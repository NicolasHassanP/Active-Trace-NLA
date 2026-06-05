## Context

C-05 (`audit-log`, archivado) creó la tabla `audit_event` (migración 004, append-only, inmutable por trigger) y un endpoint `GET /api/v1/auditoria` que lista eventos paginados, respetando `require_permission("auditoria:ver")` y el scope `propio`/global del `PermissionGrant`. C-12 (`comunicaciones-cola-worker`) creó la tabla `comunicacion` con un enum de estado (`ComunicacionEstado`: Pendiente/Enviando/Enviado/Error/Cancelado) y atribución `enviado_por`.

C-19 construye la **capa de panel de supervisión** (F9.1, F9.2, FL-11) encima de esos datos: agregaciones de uso, distribución de estado de comunicaciones y un log de últimas acciones con límite configurable, todo de **solo lectura**. No hay nueva tabla ni migración.

Governance: **ALTO**. Es una superficie de lectura sobre datos de auditoría sensibles. Las decisiones no obvias (derivación de materia, scope `propio`, tope del log) se documentan aquí para revisión humana antes de implementar.

**Constraint estructural descubierto** (clave para el diseño): el modelo real `AuditEvent` (C-05) **no tiene columna `materia_id`** — la KB (§E-AUD) describía una, pero la implementación usa `modulo`, `entidad_tipo` y `entidad_id`. Tampoco `Comunicacion` (C-12) tiene `materia_id`. Esto invalida el enfoque ingenuo de filtrar/agrupar por `materia_id` directo y obliga a decidir cómo derivar la dimensión "materia".

## Goals / Non-Goals

**Goals:**
- Exponer agregaciones de uso del sistema sobre `audit_event`: acciones por día, interacciones por docente, interacciones por docente×materia.
- Exponer distribución de `ComunicacionEstado` agrupada por docente (`enviado_por`).
- Exponer un log de últimas acciones con N configurable (defecto 200, tope acotado).
- Soportar filtros de panel: rango de fechas, materia, usuario, estado de comunicación.
- Respetar el scope `propio` del COORDINADOR y el global del ADMIN en TODAS las vistas, reusando `PermissionGrant`.
- Mantener el flujo de capas Routers → Services → Repositories; queries solo en repositories; scope de tenant siempre activo.

**Non-Goals:**
- NO modificar el modelo de datos (sin migración, sin nuevas columnas, sin `materia_id` en `audit_event`).
- NO modificar la capacidad `audit-query` de C-05 (el endpoint de lista paginada permanece intacto).
- NO escritura de ningún tipo sobre `audit_event` salvo el registro `AUDITORIA_CONSULTA` ya existente (ver Decisión D6).
- NO frontend (lo consume C-24).
- NO exportación de archivos (fuera de scope de este change).

## Decisions

### D1 — La dimensión "materia" se deriva de `entidad_id` con `entidad_tipo = "Materia"`, NO de una columna `materia_id` ✅ CONFIRMADO
`audit_event` no tiene `materia_id`. Para "interacciones por docente×materia" y el filtro por materia, se interpreta como materia el `entidad_id` de los eventos cuyo `entidad_tipo = "Materia"`. Los eventos cuyo `entidad_tipo` no es `"Materia"` quedan agrupados bajo una clave "sin materia" (materia_id nula) y son incluidos/excluidos según haya o no filtro de materia activo.
- **Alternativa A (rechazada)**: agregar columna `materia_id` a `audit_event` vía migración → viola el Non-Goal de "sin migración" y modificaría una tabla inmutable/append-only ya en producción; alto riesgo sobre un dominio CRÍTICO.
- **Alternativa B (rechazada)**: derivar la materia escarbando el JSONB `before`/`after` → frágil, dependiente de claves no contractuales y con PII ya redactada.
- **Elegida (D1)**: `entidad_tipo`/`entidad_id` es el contrato estable que C-05 ya define. Es determinístico y no toca el schema.
- **OQ-2 cerrada (2026-06-05)**: todos los módulos C-08 a C-17 usarán estrictamente `entidad_tipo="Materia"` y `entidad_id=<materia_id>` al registrar eventos vinculados a una materia. Eventos que no cumplan quedan bajo "sin materia" como comportamiento esperado.

### D2 — "Estado de comunicaciones por docente" agrupa por `Comunicacion.enviado_por`, no por materia
`Comunicacion` tampoco tiene `materia_id`. La sub-vista de F9.1 "estado de comunicaciones agrupado por docente" se implementa como `GROUP BY enviado_por, estado` sobre `comunicacion`, scoped al tenant. La dimensión "por materia" para comunicaciones queda fuera de alcance por ausencia de dato (Non-Goal).

### D3 — Scope `propio`/global se aplica en TODAS las vistas, no solo en el log
El endpoint de C-05 ya aplica scope a la lista. C-19 lo replica en cada agregación: con `PermisoScope.propio`, las queries añaden `WHERE actor_user_id = current_user.user_id` (para `audit_event`) y `WHERE enviado_por = current_user.user_id` (para `comunicacion`). Con global, sin filtro de actor. El service recibe el `PermissionGrant` y traduce a un `actor_filter: UUID | None` que pasa al repository — mismo patrón que el router de C-05. Esto evita que un COORDINADOR con scope `propio` vea métricas agregadas de otros docentes.

### D4 — Límite del log: defecto 200, tope acotado por configuración (no ilimitado)
F9.1 exige "máximo configurable; por defecto 200". Se añade `AUDIT_PANEL_LOG_MAX` (defecto 200) en `core/config.py`. El parámetro `limite` del endpoint de últimas acciones acepta `1 ≤ limite ≤ AUDIT_PANEL_LOG_MAX`; si se omite, usa el defecto (200); si se pide más que el tope, se rechaza con 422 (validación de query param). Esto previene consultas que devuelvan volúmenes ilimitados sobre una tabla append-only que crece sin borrado.
- **Alternativa (rechazada)**: clamp silencioso al tope → oculta al cliente que su pedido excedió el máximo; preferimos 422 explícito y contractual.

### D5 — Las agregaciones se computan con `GROUP BY` en SQL, no en Python
Las series por día (`date_trunc('day', created_at)`), conteos por actor y por (actor, materia), y la distribución de estados se resuelven con agregaciones SQL en el repository. Evita traer N filas a memoria y respeta la regla de "queries solo en repositories". El service solo orquesta y aplica el filtro de scope; no arma SQL.

### D6 — Los endpoints de métricas NO registran `AUDITORIA_CONSULTA` por cada llamada ✅ CONFIRMADO
Para las vistas de panel (que el frontend puede pollear o refrescar con frecuencia para dashboards), registrar un evento por request inflaría la tabla append-only con ruido y distorsionaría las propias métricas de "acciones por día". Decisión: los endpoints de **métricas agregadas** y de **últimas acciones** del panel NO emiten `AUDITORIA_CONSULTA`. El endpoint de lista paginada de C-05 mantiene su comportamiento sin cambios.
- **OQ-1 cerrada (2026-06-05)**: confirmado que NO se registra auto-auditoría en los endpoints del panel. El criterio es evitar ruido en la tabla append-only y no distorsionar las propias métricas.

### D7 — Schemas de salida Pydantic v2 con `extra='forbid'`; sin exponer PII
Los DTOs de métricas (`AccionesPorDiaItem`, `InteraccionesDocenteItem`, `InteraccionesDocenteMateriaItem`, `ComunicacionesPorDocenteItem`, `UltimaAccionItem`) usan `model_config = ConfigDict(extra='forbid')`. El log de últimas acciones reusa la forma de `AuditEventRead` (que ya excluye PII; `before`/`after` vienen redactados de origen). Los conteos no exponen contenido sensible — solo `actor_user_id`, `accion`, fechas y totales.

## Risks / Trade-offs

- **[Materia no atribuida]** Acciones cuyo `entidad_tipo` ≠ `"Materia"` no aparecen bajo ninguna materia en la vista docente×materia. → Mitigación: agruparlas bajo una clave "sin materia" explícita y documentar la convención `entidad_tipo="Materia"` para los módulos productores; surfacear a revisión humana (D1).
- **[Crecimiento de `audit_event`]** Las agregaciones sin rango de fechas escanean toda la tabla. → Mitigación: el filtro `desde`/`hasta` está disponible; `created_at` ya está indexado parcialmente vía orden; documentar recomendación de acotar rango. El log de últimas acciones está acotado por `AUDIT_PANEL_LOG_MAX` (D4).
- **[Asimetría de auto-auditoría]** Las vistas de panel no se auto-auditan (D6). → Mitigación: decisión documentada y reversible; pendiente de confirmación humana por governance ALTO.
- **[Scope `propio` y agregados]** Un COORDINADOR con scope `propio` ve solo su propia actividad, lo que puede parecer "datos vacíos" si no operó. → Mitigación: comportamiento correcto y testeado; el cliente distingue scope por el rol. Documentado en specs.

## Migration Plan

- **Sin migración de base de datos.** No se crean tablas ni columnas; `audit_event` y `comunicacion` ya existen.
- **Config**: agregar `AUDIT_PANEL_LOG_MAX` (defecto 200) a `Settings`. Cambio aditivo y retrocompatible.
- **Despliegue**: solo código backend (repository + service + schemas + extensión de router). No requiere downtime.
- **Rollback**: revertir el código; al no haber cambios de schema, el rollback es inmediato y sin pérdida de datos.

## Open Questions

Todas las OQs cerradas el 2026-06-05:

- **OQ-1** ✅ CERRADA — Los endpoints del panel NO registran `AUDITORIA_CONSULTA`. Hacerlo generaría ruido e inflaría la tabla append-only cada vez que el dashboard se refresque. (→ D6)
- **OQ-2** ✅ CERRADA — Todos los módulos C-08 a C-17 usarán `entidad_tipo="Materia"` y `entidad_id=<materia_id>` al auditar eventos vinculados a una materia. Los eventos que no cumplan quedan bajo "sin materia". (→ D1)
- **OQ-3** ✅ CERRADA — La distribución de comunicaciones se agrupa por docente y estado únicamente. La dimensión lotes (`lote_id`) queda fuera de alcance por ahora. (→ D2)
