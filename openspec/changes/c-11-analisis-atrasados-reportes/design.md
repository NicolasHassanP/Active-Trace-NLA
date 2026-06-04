## Context

C-10 dejó dos piezas listas que C-11 consume sin modificar:
- `Calificacion` con `aprobado` **persistido** (derivado al importar por `derive_aprobado`, RN-02/RN-03). El umbral ya está horneado en el booleano; C-11 no necesita re-evaluar umbrales para detectar atrasados.
- `UmbralMateria` + `UmbralService.get_efectivo` (umbral efectivo por asignación, con defaults del tenant) — necesario para las notas finales agrupadas y para textos informativos.
- Clave de scope de calificaciones: `(tenant_id, entrada_padron_id, materia_id, actividad, importado_por)`. RN-04 implica que **el análisis se acota al importador** salvo en vistas globales de coordinación.

Estado actual relevante del repo:
- `CalificacionRepository`: ya tiene `list_by_materia_importador`, `list_by_entrada_padron`, `get_umbral`, `count_calificaciones`.
- `CalificacionService.detectar_sin_corregir`: ya implementa RN-07/RN-08 (la detección de TPs sin corregir). C-11 sólo añade la **exportación** y el guard `atrasados:ver`.
- `PadronRepository.get_active_version`: resuelve la versión activa del padrón (materia×cohorte).
- RBAC: `atrasados:ver` y `entregas:ver_sin_corregir` ya seedeados en la migración 003 para TUTOR/PROFESOR/COORDINADOR/ADMIN con scopes `propio`/`global`. **No hay migración nueva en C-11.**
- Patrón de identidad: routers usan `current_user` (JWT) + `require_permission(...)`; servicios reciben `current_user` y nunca leen tenant/usuario del body.

Governance: **MEDIO** (lógica de dominio, read-only). Implementar con checkpoints; sin escritura sobre datos sensibles ni cambios de schema.

## Goals / Non-Goals

**Goals:**
- Implementar el cómputo de atrasados (RN-06), ranking (RN-09), reportes rápidos (F2.4) y notas finales agrupadas (F2.5) como lectura derivada sobre `Calificacion`.
- Exponer monitores de seguimiento general (F2.7), por docente (F2.8) y con rango de fechas (F2.9), con su modelo de scoping por asignación.
- Añadir la exportación de TPs sin corregir (F2.6) sobre la detección ya existente de C-10.
- Mantener Routers → Services → Repositories → Models; SQL sólo en `analisis_repository.py`.
- Toda lectura filtra por `tenant_id` de la sesión; el alcance de docente se deriva de sus asignaciones, no de params.

**Non-Goals:**
- NO re-derivar `aprobado` ni recalcular umbrales por calificación: se usa el booleano persistido por C-10. La excepción es la nota final agrupada (F2.5), que usa `nota_numerica` + umbral efectivo para un agregado.
- NO crear tablas, columnas ni migraciones (C-11 es read-only).
- NO seedear permisos nuevos: se reutilizan los de la migración 003.
- NO implementar el frontend ni el envío de comunicaciones (C-12).
- NO usar ponderación por carga horaria en la nota final: promedio simple confirmado (OQ-C11-1 cerrada).

## Decisions

**D1 — `aprobado` persistido como única fuente de verdad para atrasados.**
El cómputo de atrasados (RN-06) lee `Calificacion.aprobado` directamente; no re-evalúa umbrales. Una actividad "faltante" = no existe `Calificacion` para `(entrada_padron, actividad)` entre las seleccionadas; "reprobada" = existe con `aprobado = False`.
*Alternativa descartada*: re-derivar con `derive_aprobado` en cada lectura — duplicaría lógica y arriesgaría divergencia con lo importado. C-10 ya garantiza consistencia al importar.

**D2 — Función pura `calcular_atrasados(...)` en `atrasados_calculo.py`.**
La regla RN-06 se aísla en una función pura `calcular_atrasados(actividades_seleccionadas, calificaciones_por_alumno) -> list[AlumnoAtrasado]` (sin DB, sin I/O), testeable con triangulación. El servicio arma la entrada (mapa alumno→calificaciones) desde el repositorio y delega el cómputo. Mismo patrón que `calificacion_aprobado.derive_aprobado`.
*Rationale*: cobertura ≥90% de reglas de negocio sobre función pura; el resto del servicio es orquestación.

**D3 — `analisis_repository.py` para las lecturas agregadas.**
Nuevo repositorio tenant-scoped con queries de lectura: calificaciones por materia (×importador para scope `propio`, sin filtro de importador para scope `global`), entradas de padrón activas, conteos por alumno, y filtros (comisión, regional, rango de fechas por `importado_at`). Ningún SQL vive en el servicio (regla dura #11).
*Alternativa descartada*: reutilizar `CalificacionRepository` extendiéndolo — se prefiere un repositorio dedicado al análisis para no inflar el de ingesta y mantener ≤500 LOC por archivo.

**D4 — Scoping por rol resuelto en el servicio desde el scope del permiso + asignaciones.**
El servicio determina si la consulta es `propio` (filtrar por `importado_por = current_user` y materias asignadas) o `global` (todo el tenant) según el rol/scope efectivo del usuario, resuelto desde la sesión. El monitor del docente (F2.8) deriva las materias visibles de `Asignacion` (usuario_id = current_user, vigente). Nunca se acepta un `usuario_id`/`materia_id` de scope desde la petición.
*Rationale*: RN-04 + regla dura #8/#10. Fail-closed: sin asignación ni scope global → resultado vacío, no error 500.

**D5 — `/api/v1/analisis/*` con un único guard `atrasados:ver`.**
Todos los endpoints de análisis y monitores se montan bajo `require_permission("atrasados:ver")`. La distinción `propio` vs `global` se maneja por el **scope** del grant (ya soportado por el sistema RBAC C-04), no por permisos distintos. La exportación de TPs sin corregir también usa `atrasados:ver` (no `calificaciones:importar`), alineado con FL-02 paso 6.
Endpoints previstos:
- `GET  /analisis/atrasados` (materia, cohorte, actividades) → lista de atrasados
- `GET  /analisis/ranking` → ranking de aprobadas
- `GET  /analisis/reporte-materia` → métricas consolidadas
- `GET  /analisis/notas-finales` → notas finales agrupadas
- `GET  /analisis/monitor` → monitor general / seguimiento (scope decide alcance) con filtros y rango de fechas opcional
- `POST /analisis/sin-corregir/export` → exportación de TPs sin corregir (reusa `detectar_sin_corregir`)

**D6 — Schemas Pydantic con `extra='forbid'` y `from_attributes` donde aplique.**
Nuevo `app/schemas/analisis.py`: `AlumnoAtrasado`, `RankingFila`, `ReporteMateria`, `NotaFinalAlumno`, `MonitorFila`, `MonitorFiltros` (filtros de query validados), `ExportSinCorregirRequest`. Todos con `model_config = ConfigDict(extra="forbid")`. Los identificadores de alumno se exponen por `entrada_padron_id` (UUID), nunca por PII directa en el cuerpo a menos que el padrón ya lo exponga descifrado como en C-10.

**D7 — Nota final agrupada = agregado determinista de actividades numéricas seleccionadas.**
F2.5 calcula la nota final como un promedio (o suma normalizada) de `nota_numerica` sobre las actividades seleccionadas, función pura y determinista. La fórmula exacta (promedio simple vs. ponderado) se fija como promedio simple por defecto, dejando ponderación para una iteración futura (ver Open Questions).

**D8 — Exportación: el servicio devuelve filas estructuradas; el formato de archivo (CSV) se serializa en una capa fina del router.**
`detectar_sin_corregir` ya devuelve `EntregaSinCorregir`. La exportación añade auditoría (`AuditService.record`, `modulo='atrasados'`) y serialización CSV. Mismo patrón de auditoría que C-10.

## Risks / Trade-offs

- **[N+1 / performance en monitores]** → Las lecturas agregadas deben hacerse con queries agrupadas en el repositorio (GROUP BY por entrada_padron), no iterando por alumno con una query por cada uno. Mitigación: `analisis_repository` expone métodos que devuelven conteos pre-agregados; cargar padrón + calificaciones en lotes acotados por materia/versión.
- **[Scope `propio` vs `global` mal resuelto]** → expondría datos de otros docentes. Mitigación: resolver el scope SIEMPRE desde el grant del JWT (C-04), con tests que verifican que PROFESOR sólo ve sus importaciones y COORDINADOR ve global; fail-closed ante ausencia de asignación.
- **[Divergencia entre `aprobado` persistido y umbral actual]** → si un docente cambia el umbral después de importar, `aprobado` no se recalcula (es de C-10). Mitigación: documentar que el análisis refleja el estado al momento de importar; re-importar re-deriva (upsert C-10). No es un bug de C-11.
- **[Fórmula de nota final — resuelta]** → F2.5 usa promedio simple de `nota_numerica`. Confirmado por el dueño de producto (2026-06-04). Ponderación por carga horaria queda fuera de scope; si se requiere, se aborda en un change futuro.
- **[Email/PII en monitores]** → los monitores muestran alumnos. Mitigación: exponer `entrada_padron_id` y los campos ya descifrados por el TypeDecorator del padrón (como en C-10), sin re-cifrar ni loguear PII; `__repr__` de modelos no expone PII.

## Migration Plan

- Sin migración de DB (read-only). No hay rollback de schema.
- Registrar el router `analisis` en el agregador de la API v1.
- Despliegue estándar; rollback = revertir el código del router/servicio. Sin estado persistente que limpiar.

## Open Questions

Todas cerradas (2026-06-04):

- **OQ-C11-1 ✅ (F2.5 — nota final)**: Promedio simple de `nota_numerica` de actividades seleccionadas. Solución más directa y determinista para esta etapa. Ponderación por carga horaria fuera de scope; change futuro si se requiere.
- **OQ-C11-2 ✅ (filtros regional/comisión)**: Implementar los filtros sobre los campos de `EntradaPadron` que C-09 dejó poblados. Si los campos están vacíos en la DB, el filtro opera sin efecto (no-op) pero la estructura de la query queda correcta para cuando el padrón los provea.
- **OQ-C11-3 ✅ (rango de fechas F2.9)**: Usar `importado_at` de `Calificacion`. Es el timestamp transaccional más confiable disponible. Fechas académicas (E15, scope de C-06) quedan fuera de este change.
