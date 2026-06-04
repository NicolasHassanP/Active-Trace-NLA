## Context

C-14 implementa la épica 7 (Coloquios) sobre la base entregada por C-07 (usuarios y asignaciones) y C-04 (RBAC). El flujo objetivo es FL-07: el PROFESOR importa el padrón de candidatos, crea una convocatoria con días y cupos, el sistema crea turnos reservables, los alumnos habilitados reservan, y coordinación consulta métricas, agenda y registro académico.

Estado actual relevante:
- Última migración aplicada: **011** (C-13 encuentros). La migración de este change es **012**, `down_revision="011"`.
- Patrón ORM: `TenantScopedBase` (`app/models/mixins.py`) aporta `id` UUID, `tenant_id` FK, `created_at`/`updated_at`, `deleted_at` (soft delete).
- Patrón de enums: `SAEnum(..., create_type=False, values_callable=...)`; los tipos se crean en la migración con `DO $$ ... duplicate_object` (idempotente).
- Patrón de migración: SQL explícito (`op.execute`), índices con nombres explícitos, seed de permisos RBAC por tenant con `ON CONFLICT DO NOTHING` (ver migración 011 §2.8).
- Patrón de router: `require_permission(...)` fail-closed, identidad del actor SIEMPRE desde `current_user` (JWT), service factory que inyecta repos tenant-scoped.
- Clean Architecture estricta: Routers → Services → Repositories → Models. Sin lógica de negocio en routers, sin acceso a DB desde services.

Governance del dominio: **MEDIO** (lógica de dominio). Implementación con checkpoints; decisiones no obvias se surfacean (ver Open Questions).

## Goals / Non-Goals

**Goals:**
- Modelar convocatoria de evaluación con días reservables y cupos por día.
- Permitir al ALUMNO reservar un turno con control de cupo y unicidad de reserva activa por convocatoria.
- Importar el padrón de candidatos a una convocatoria (separado del padrón general).
- Exponer métricas (convocados / reservas activas / cupos libres / notas registradas), agenda consolidada de reservas y registro académico de resultados.
- Cumplir multi-tenancy row-level, RBAC fino fail-closed, soft delete y auditoría en cada operación de gestión.

**Non-Goals:**
- Calendarización de fechas académicas (`FechaAcademica`, §E15) — pertenece a C-17.
- Notas de parciales/TPs (consolidación de calificaciones) — pertenece a C-10/C-11. Aquí `ResultadoEvaluacion` cubre solo la nota final de la instancia de evaluación (coloquio).
- Frontend de coloquios — pertenece a C-22/C-23.
- Notificación/comunicación de reservas a los alumnos — la cola de comunicaciones es C-12; este change no encola mensajes.

## Decisions

### D1 — Introducir `TurnoEvaluacion` (día + cupo) por encima del `dias_disponibles` plano de la KB
La KB §E14 modela `Evaluacion.dias_disponibles` como un entero (ventana de inscripción en días), sin entidad de día reservable ni cupo. Pero FL-07 (paso 2/3) y HU-31 exigen "días disponibles **y cupos**" y "turnos reservables con sus cupos", y F7.4 expone "cupos libres" por convocatoria. Un entero plano no puede expresar cupo-por-día ni soportar reservas.
**Decisión**: agregar `TurnoEvaluacion` { `evaluacion_id`, `fecha`, `cupo_total` }. La reserva apunta a un turno, no a la convocatoria directamente. `Evaluacion.dias_disponibles` se conserva como ventana de inscripción (metadato), pero los días reservables concretos viven en `TurnoEvaluacion`.
**Alternativa descartada**: guardar cupos en un JSONB dentro de `Evaluacion`. Rechazada porque las reservas necesitan FK a un turno para integridad referencial y conteo por turno; un JSONB no soporta FK ni constraint de cupo a nivel fila.
**Estado**: desviación documentada respecto de la KB → OQ-1.

### D2 — Cupos derivados, nunca denormalizados
`cupo_total` se almacena en `TurnoEvaluacion`. Los `cupos_libres` y `reservas_activas` se calculan como `cupo_total - count(reservas Activa del turno)`. No se persiste un contador mutable.
**Rationale**: evita drift entre el contador y la realidad (mismo principio que avisos/acknowledgment, RN sin denormalización). El conteo se hace en el repository con `COUNT` filtrado por `estado = Activa` y `deleted_at IS NULL`.
**Alternativa descartada**: contador `cupos_ocupados` decrementado en cada reserva. Rechazado por riesgo de inconsistencia ante cancelaciones y soft-deletes.

### D3 — Control de cupo bajo bloqueo para evitar sobre-reserva (race condition)
Reservar implica leer cupo y escribir reserva. Dos alumnos concurrentes podrían pasar el chequeo y exceder el cupo.
**Decisión**: el `crear_reserva` del service hace `SELECT ... FOR UPDATE` sobre el turno (lock pesimista a nivel fila) dentro de la transacción, recuenta reservas activas, y solo entonces inserta. Si `reservas_activas >= cupo_total` → 409/422 sin insertar.
**Alternativa considerada**: constraint de unicidad. No alcanza para "N reservas ≤ cupo" (no es unicidad). El lock pesimista es la opción simple y correcta para el volumen esperado (coloquios, decenas por turno).

### D4 — Una reserva activa por (alumno, convocatoria)
HU-31/FL-07: el alumno reserva "su turno" en la convocatoria. Reservar dos turnos de la misma convocatoria no tiene semántica.
**Decisión**: el service rechaza una segunda reserva `Activa` del mismo alumno en la misma `Evaluacion` (a través de cualquiera de sus turnos). Cancelar libera la posición y permite re-reservar.
Se valida en el service (no solo con índice) porque la unicidad cruza turnos de una misma convocatoria; se complementa con un índice parcial único sobre (`tenant_id`, `evaluacion_id`, `alumno_id`) donde `estado='Activa'` para defensa en profundidad.

### D5 — Solo candidatos importados pueden reservar (gating por padrón)
F7.2 separa el padrón de coloquio del padrón general. Solo un alumno en `CandidatoEvaluacion` de esa convocatoria, habilitado, puede reservar.
**Decisión**: `crear_reserva` verifica que exista `CandidatoEvaluacion` activo para (`evaluacion_id`, `alumno_id`); si no, 403/404. La importación es upsert idempotente por (`evaluacion_id`, `alumno_id`).

### D6 — Un permiso de gestión y un permiso de reserva, diferenciación de rol en el service
Siguiendo el patrón de C-13 (un permiso por módulo): `coloquios:gestionar` (COORDINADOR, ADMIN, PROFESOR) cubre crear/editar/cerrar convocatoria, importar candidatos, métricas, agenda, registro y carga de resultados. `coloquios:reservar` (ALUMNO) cubre reservar/cancelar.
**Rationale**: fail-closed; la matriz de roles (03_actores_y_roles §matriz: "Reservar instancia de evaluación" solo ALUMNO) se respeta separando reserva de gestión. La identidad del alumno se toma del JWT, jamás del body (regla dura #8).

### D7 — Estados y enums
- `EvaluacionTipo`: `Parcial | TP | Coloquio | Recuperatorio` (DB enum `evaluacion_tipo`).
- `ReservaEstado`: `Activa | Cancelada` (DB enum `reserva_estado`).
- `Evaluacion` tiene `cerrada: bool` (no enum) para el cierre de convocatoria (F7.5): convocatoria cerrada no acepta nuevas reservas.
- `nota_final` es `TEXT` (numérica o cualitativa, §E14) — no se valida formato.

### D8 — Auditoría
Cada operación de gestión y cada reserva/cancelación registra en `audit_event_log` vía `AuditRepository`, con una acción `COLOQUIO_GESTIONAR` agregada al enum `audit_action` en la migración 012 (patrón idempotente de 011 §2.2). La reserva del alumno también audita (`COLOQUIO_GESTIONAR` con actor ALUMNO) — toda acción del producto *trace* audita.

### D9 — Soft delete
Cerrar/cancelar usa estado o flag; el borrado de convocatorias/turnos es soft (`deleted_at`). Nunca hard delete (regla dura #13).

## Risks / Trade-offs

- [Lock pesimista en alta concurrencia de reservas] → Mitigación: el volumen real de coloquios es bajo (decenas por turno); `FOR UPDATE` por fila de turno no serializa toda la tabla. Si crece, migrar a constraint + retry optimista.
- [Desviación del modelo KB §E14 (TurnoEvaluacion no existe en la KB)] → Mitigación: documentado en OQ-1; el campo `dias_disponibles` de la KB se preserva como metadato. Re-sincronizar la KB §E14 al archivar.
- [Doble fuente de unicidad de reserva (service + índice parcial)] → Mitigación: el índice es defensa en profundidad; el service es la fuente de la regla y del mensaje de error 4xx.
- [`nota_final` sin validación de formato] → Aceptado: la KB lo define como texto libre (numérico o cualitativo). El registro académico no calcula promedios aquí.

## Migration Plan

1. Crear `012_create_evaluaciones_coloquios.py` con `revision="012"`, `down_revision="011"`.
2. `upgrade`: extender `audit_action` (idempotente) → crear enums `evaluacion_tipo`, `reserva_estado` (idempotente) → crear tablas `evaluacion`, `turno_evaluacion`, `candidato_evaluacion`, `reserva_evaluacion`, `resultado_evaluacion` → índices nombrados → índice parcial único de reserva activa → seed de permisos `coloquios:gestionar` y `coloquios:reservar` por tenant (ON CONFLICT DO NOTHING).
3. `downgrade`: revertir seed de permisos → drop de tablas en orden FK (reserva, resultado, candidato, turno, evaluacion) → (enums/audit_action quedan, no totalmente reversibles, igual que 011).
4. Rollback: `alembic downgrade 011`.

## Open Questions

- **OQ-1 (desviación de KB §E14)**: la KB no modela `TurnoEvaluacion` ni cupos por día; usa `dias_disponibles: int`. Este change introduce `TurnoEvaluacion` para cumplir FL-07/HU-31. ¿Se confirma la entidad y se re-sincroniza la KB §E14 al archivar? **Asunción tomada**: sí (sin ella el flujo de reserva con cupo es irrealizable). Se conserva `dias_disponibles` como metadato.
- **OQ-2**: ¿una convocatoria puede tener más de un turno por la misma fecha (p.ej. franjas horarias)? La KB/HU hablan de "días" y "cupos por franja" (HU-31 menciona "franja"). **Asunción**: el turno se identifica por `fecha` (un turno por día); se añade campo opcional `franja: text` para nota descriptiva sin semántica de cupo separada. Si se requieren franjas con cupo independiente, es un cambio menor (turno por franja).
- **OQ-3**: ¿el PROFESOR ve solo convocatorias de sus materias asignadas o todas? La matriz no lo especifica para coloquios. **Asunción**: PROFESOR ve/gestiona convocatorias de materias donde tiene asignación (scope por asignación, igual que C-13 D11); COORDINADOR/ADMIN ven todo. Confirmar con el dueño del dominio.
- **OQ-4**: ¿quién carga `ResultadoEvaluacion` (nota final)? F7.5 lo ubica en "registro académico consolidado". **Asunción**: lo carga `coloquios:gestionar` (PROFESOR de la materia / COORDINADOR / ADMIN). El ALUMNO solo lee su propio resultado.
