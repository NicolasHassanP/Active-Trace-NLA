# Tasks — C-11 análisis, atrasados y reportes

> Strict TDD en cada tarea de lógica: RED (test que falla) → GREEN (mínimo) → TRIANGULATE (≥2 casos) → REFACTOR.
> Tests con DB real (sin mocks de DB). Identidad/tenant SIEMPRE desde JWT. SQL sólo en repositories.
> C-11 es read-only: NO crear migraciones, tablas ni columnas. NO seedear permisos (reusar `atrasados:ver`).

## 1. Schemas Pydantic (app/schemas/analisis.py)

- [x] 1.1 Crear `AlumnoAtrasado` (entrada_padron_id, nombre/email si el padrón ya los expone, actividades_faltantes: list[str], actividades_no_aprobadas: list[str]) con `extra='forbid'`
- [x] 1.2 Crear `RankingFila` (entrada_padron_id, cantidad_aprobadas: int) con `extra='forbid'`
- [x] 1.3 Crear `ReporteMateria` (total_actividades, total_alumnos, total_atrasados, total_aprobadas, tasa_aprobacion, sin_datos: bool) con `extra='forbid'`
- [x] 1.4 Crear `NotaFinalAlumno` (entrada_padron_id, nota_final: Optional[Decimal], actividades_consideradas: int) con `extra='forbid'`
- [x] 1.5 Crear `MonitorFila` (entrada_padron_id, estado: 'atrasado'|'al_dia'|'sin_datos', aprobadas, faltantes) con `extra='forbid'`
- [x] 1.6 Crear `MonitorFiltros` (materia_id, cohorte_id, comision?, regional?, busqueda?, actividad?, min_cumplidas?, fecha_desde?, fecha_hasta?) con `extra='forbid'` y validación `fecha_desde <= fecha_hasta`
- [x] 1.7 Crear `ExportSinCorregirRequest` (materia_id, cohorte_id, filas_finalizacion) con `extra='forbid'`

## 2. Lógica pura — cálculo de atrasados (app/services/atrasados_calculo.py)

- [x] 2.1 RED: test de `calcular_atrasados` — alumno con actividad faltante es atrasado (RN-06 cond. a)
- [x] 2.2 GREEN: implementar `calcular_atrasados(actividades_seleccionadas, calificaciones_por_alumno) -> list[AlumnoAtrasado]` (función pura, sin DB)
- [x] 2.3 TRIANGULATE: alumno con `aprobado=False` es atrasado (cond. b); alumno al día NO aparece; lista de actividades vacía → resultado vacío
- [x] 2.4 REFACTOR: extraer helpers de clasificación (faltante / no_aprobada), nombres claros, ≤500 LOC

## 3. Lógica pura — ranking y nota final (app/services/analisis_calculo.py)

- [x] 3.1 RED: test `calcular_ranking` — alumno sin aprobadas se excluye (RN-09)
- [x] 3.2 GREEN: implementar `calcular_ranking(...)` ordenado desc por cantidad de aprobadas, sólo actividades seleccionadas
- [x] 3.3 TRIANGULATE: orden desc entre dos alumnos; actividad aprobada fuera de las seleccionadas no cuenta
- [x] 3.4 RED: test `calcular_nota_final` — promedio simple determinista de `nota_numerica` (D7)
- [x] 3.5 GREEN + TRIANGULATE: alumno sin calificaciones → nota_final None/0 sin error; misma entrada → mismo resultado (determinismo)
- [x] 3.6 REFACTOR: deduplicar agregaciones, mantener funciones puras

## 4. Repositorio de lecturas agregadas (app/repositories/analisis_repository.py)

- [x] 4.1 RED: test `AnalisisRepository` con DB real — `calificaciones_por_materia(materia_id, importado_por=None)` filtra por tenant; con `importado_por` filtra por importador (RN-04)
- [x] 4.2 GREEN: implementar `AnalisisRepository(TenantScopedRepository)` con `calificaciones_por_materia(...)` (scope propio vs global por parámetro `importado_por`)
- [x] 4.3 TRIANGULATE: aislamiento por tenant (T2 no ve datos de T1); scope propio excluye importaciones de otro docente
- [x] 4.4 Implementar `entradas_padron_activas(materia_id, cohorte_id)` (delegando o reusando `PadronRepository.get_active_version`) — test de versión activa
- [x] 4.5 Implementar `conteo_aprobadas_por_alumno(materia_id, importado_por, actividades)` con GROUP BY (evita N+1) — test de agregación
- [x] 4.6 Implementar filtros del monitor: comisión, regional, búsqueda libre, rango de fechas por `importado_at` — tests por filtro
- [x] 4.7 REFACTOR: SQL sólo aquí; ≤500 LOC; toda query con `tenant_id` + `deleted_at IS NULL`

## 5. Servicio de análisis (app/services/analisis_service.py)

- [x] 5.1 RED: test `AnalisisService.atrasados(req, current_user)` — arma mapa alumno→calificaciones desde repo y delega en `calcular_atrasados`
- [x] 5.2 GREEN: implementar `atrasados(...)` resolviendo scope (`propio`/`global`) desde el scope del grant/asignaciones del `current_user` (D4) — nunca del body
- [x] 5.3 TRIANGULATE: PROFESOR ve sólo sus importaciones; COORDINADOR ve global; sin asignación ni scope global → vacío (fail-closed)
- [x] 5.4 Implementar `ranking(req, current_user)` delegando en `calcular_ranking`
- [x] 5.5 Implementar `reporte_materia(req, current_user)` → `ReporteMateria`, con estado `sin_datos` cuando no hay calificaciones o actividades
- [x] 5.6 Implementar `notas_finales(req, current_user)` delegando en `calcular_nota_final` con umbral efectivo de `UmbralService.get_efectivo`
- [x] 5.7 Implementar `monitor(filtros, current_user)` aplicando scope por rol + filtros (incl. rango de fechas F2.9)
- [x] 5.8 Implementar `export_sin_corregir(req, current_user)` reusando `CalificacionService.detectar_sin_corregir` + auditoría (`modulo='atrasados'`)
- [x] 5.9 REFACTOR: orquestación sin SQL; identidad/tenant desde `current_user`; ≤500 LOC

## 6. Router /api/v1/analisis (app/api/v1/routers/analisis.py)

- [x] 6.1 RED: test de integración — `GET /analisis/atrasados` sin `atrasados:ver` → 403; sin JWT → 401
- [x] 6.2 GREEN: crear router con `GET /analisis/atrasados` bajo `require_permission("atrasados:ver")` + `get_current_user`
- [x] 6.3 TRIANGULATE: PROFESOR (scope propio) recibe sólo sus datos; COORDINADOR (scope global) recibe datos del tenant
- [x] 6.4 Agregar `GET /analisis/ranking`, `GET /analisis/reporte-materia`, `GET /analisis/notas-finales` (todos con guard `atrasados:ver`)
- [x] 6.5 Agregar `GET /analisis/monitor` (general/seguimiento según scope, con filtros y rango de fechas; rango inválido → 422)
- [x] 6.6 Agregar `POST /analisis/sin-corregir/export` (guard `atrasados:ver`, emite auditoría, serializa CSV en capa fina del router)
- [x] 6.7 Registrar el router en el agregador de la API v1 — test de que las rutas existen
- [x] 6.8 REFACTOR: routers sin lógica de negocio (sólo guard + delegación al service); tenant/usuario desde JWT

## 7. Tests de scope, RBAC y aislamiento (transversal)

- [x] 7.1 Test: el scope (`tenant_id`, `usuario_id`) enviado en body/query es ignorado; se usa el del JWT
- [ ] 7.2 Test: TUTOR con `atrasados:ver` (scope global) accede al monitor general; ve alumnos de sus materias
- [x] 7.3 Test: aislamiento por tenant en todos los endpoints (T2 nunca ve datos de T1)
- [ ] 7.4 Test: exportación de TPs sin corregir excluye actividades numéricas (RN-08) y registra `AuditEvent`
- [x] 7.5 Verificar cobertura: ≥80% líneas global, ≥90% en `atrasados_calculo` y `analisis_calculo` (reglas de negocio)

## 8. Cierre

- [x] 8.1 Correr la suite completa de C-11 y confirmar verde + cobertura
- [ ] 8.2 Actualizar Estado de C-11 en CHANGES.md (lo hace /opsx:archive)
