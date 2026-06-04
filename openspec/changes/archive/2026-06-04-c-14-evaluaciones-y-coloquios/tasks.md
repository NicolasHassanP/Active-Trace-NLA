## 1. Modelos y migración (cimiento de datos)

- [x] 1.1 Crear `app/models/evaluacion.py` con enums `EvaluacionTipo` (Parcial/TP/Coloquio/Recuperatorio) y `ReservaEstado` (Activa/Cancelada), `create_type=False` + `values_callable` (patrón C-13).
- [x] 1.2 Modelo `Evaluacion(Base, TenantScopedBase)`: `materia_id` FK, `cohorte_id` FK, `tipo`, `instancia` (Text), `dias_disponibles` (Integer), `cerrada` (bool default False). `__repr__` sin PII.
- [x] 1.3 Modelo `TurnoEvaluacion(Base, TenantScopedBase)`: `evaluacion_id` FK RESTRICT, `fecha` (Date, index), `cupo_total` (Integer), `franja` (Text nullable — OQ-2).
- [x] 1.4 Modelo `CandidatoEvaluacion(Base, TenantScopedBase)`: `evaluacion_id` FK, `alumno_id` FK → usuario.
- [x] 1.5 Modelo `ReservaEvaluacion(Base, TenantScopedBase)`: `turno_id` FK, `evaluacion_id` FK, `alumno_id` FK, `estado` (ReservaEstado default Activa).
- [x] 1.6 Modelo `ResultadoEvaluacion(Base, TenantScopedBase)`: `evaluacion_id` FK, `alumno_id` FK, `nota_final` (Text).
- [x] 1.7 Exportar los nuevos modelos en `app/models/__init__.py`.
- [x] 1.8 Crear migración `012_create_evaluaciones_coloquios.py` (`revision="012"`, `down_revision="011"`): extender `audit_action` con `COLOQUIO_GESTIONAR` (idempotente); crear enums `evaluacion_tipo`, `reserva_estado` (idempotente); crear tablas en orden FK; índices nombrados (`tenant_id`, `evaluacion_id`, `turno_id`, `alumno_id`, `fecha`); índice parcial único `(tenant_id, evaluacion_id, alumno_id) WHERE estado='Activa' AND deleted_at IS NULL` (D4); `downgrade` con drop en orden FK inverso.
- [x] 1.9 Seed RBAC en la migración: permisos `coloquios:gestionar` (COORDINADOR, ADMIN, PROFESOR) y `coloquios:reservar` (ALUMNO) por tenant, `ON CONFLICT DO NOTHING` (patrón 011 §2.8).
- [x] 1.10 Test de migración/modelos: aplicar 012 en DB de test (real, sin mocks), verificar tablas, enums, índice parcial único y seed de permisos por tenant.

## 2. Repositorios (capa de datos, tenant-scoped)

- [x] 2.1 `EvaluacionRepository`: CRUD soft-delete tenant-scoped de `Evaluacion`; `listar_con_metricas` derivando convocados / reservas_activas / cupos_libres (D2, sin denormalizar). Test: aislamiento multi-tenant + métricas derivadas.
- [x] 2.2 `TurnoEvaluacionRepository`: alta de turnos, `get_for_update` con `SELECT ... FOR UPDATE` (D3), conteo de reservas activas por turno. Test: lock + conteo correcto.
- [x] 2.3 `CandidatoEvaluacionRepository`: import idempotente por (evaluacion_id, alumno_id), existencia de candidato activo. Test: idempotencia + scope por convocatoria.
- [x] 2.4 `ReservaEvaluacionRepository`: alta, cancelación (estado Cancelada), conteo activas por turno y por (alumno, convocatoria). Test: conteo excluye Cancelada y soft-deleted.
- [x] 2.5 `ResultadoEvaluacionRepository`: upsert por (evaluacion_id, alumno_id), consulta consolidada, consulta del propio alumno. Test: upsert no duplica.

## 3. Servicios (lógica de dominio)

- [x] 3.1 `EvaluacionService.crear_convocatoria`: valida `cupo_total > 0`, crea Evaluacion + turnos, identidad/tenant desde `current_user`, audita. Test RED→GREEN: creación con turnos, cupo<=0 → 422, tenant isolation.
- [x] 3.2 `EvaluacionService.importar_candidatos`: import idempotente, audita. Test: alta, re-import idempotente, scope.
- [x] 3.3 `EvaluacionService.cerrar_convocatoria`: set `cerrada=true`, preserva reservas/resultados, audita. Test: cierre bloquea reservas (integración con 3.4), preserva datos.
- [x] 3.4 `EvaluacionService.crear_reserva`: gating por candidato (D5), lock del turno + recuento (D3), rechazo por cupo lleno (409), unicidad de reserva activa por convocatoria (D4), convocatoria cerrada → 409, identidad del alumno desde JWT. Test (triangulación): éxito, cupo lleno, no-candidato → 403, segunda reserva misma convocatoria → 409, otra convocatoria OK, concurrencia (dos reservas al último cupo → una 409).
- [x] 3.5 `EvaluacionService.cancelar_reserva`: solo el dueño (desde sesión) cancela; libera cupo; permite re-reservar; cancelar de otro → 403/404. Test: cancela y libera, re-reserva OK, cancelar ajeno rechazado.
- [x] 3.6 `EvaluacionService.metricas` (F7.1), `agenda` (F7.5 filtros materia/responsable/fechas/búsqueda) y `registro_academico` + `registrar_resultado` (upsert). Test: métricas derivadas tenant-scoped, agenda excluye Cancelada y filtra por rango, resultado upsert no duplica, alumno lee solo el propio.

## 4. Schemas (Pydantic v2, extra='forbid')

- [x] 4.1 `app/schemas/evaluacion.py`: requests/responses con `model_config = ConfigDict(extra='forbid')` — `CrearConvocatoriaRequest` (con lista de turnos), `ConvocatoriaRead`, `ConvocatoriaMetricasRead`, `ImportarCandidatosRequest`, `ReservaRequest` (SIN alumno_id — viene del JWT), `ReservaRead`, `ResultadoRequest`, `ResultadoRead`, `AgendaItemRead`, `MetricasRead`.
- [x] 4.2 Test de schemas: rechazo de campos no declarados (extra='forbid'); `ReservaRequest` no acepta `alumno_id`.

## 5. Router (capa HTTP, RBAC fail-closed)

- [x] 5.1 `app/api/v1/routers/coloquios.py` (prefix `/coloquios`): service factory que inyecta repos tenant-scoped (patrón encuentros). Sin lógica de negocio en el router.
- [x] 5.2 Endpoints de gestión con `require_permission("coloquios:gestionar")`: POST convocatorias, POST candidatos (import), POST cerrar, GET listado+métricas, GET agenda, GET/POST registro académico (resultado). Mapear errores de dominio a 4xx.
- [x] 5.3 Endpoints de reserva con `require_permission("coloquios:reservar")`: POST reservar turno, POST/DELETE cancelar; identidad del alumno desde `current_user`. Mapear cupo lleno/duplicado → 409, no-candidato → 403.
- [x] 5.4 Registrar el router en el agregador de la API v1.
- [x] 5.5 Tests de integración del router (DB real): 201 creación, 403 fail-closed (ALUMNO no gestiona, gestor no reserva con permiso ajeno), 409 cupo lleno, 404 cross-tenant.

## 6. Verificación final

- [x] 6.1 Correr la suite completa de C-14 (pytest) con DB real; cobertura ≥80% líneas / ≥90% reglas de negocio (cupo, unicidad, gating, cierre).
- [x] 6.2 Verificar que cada archivo backend nuevo respeta ≤500 LOC y snake_case.
- [x] 6.3 Marcar tareas completas y anotar desviaciones (OQ-1..OQ-4) resueltas o pendientes para el archive.
