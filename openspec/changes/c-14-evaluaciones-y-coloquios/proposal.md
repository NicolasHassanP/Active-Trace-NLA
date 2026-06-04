## Why

La plataforma todavía no permite gestionar las evaluaciones orales (coloquios) ni las reservas de turno de los alumnos. Los docentes necesitan convocar a una instancia de evaluación, definir días y cupos, importar el padrón de candidatos, y que cada alumno habilitado reserve su turno respetando el cupo disponible; coordinación necesita la agenda consolidada de reservas y el registro académico de notas finales. Hoy ese flujo (FL-07) vive fuera del sistema y no audita.

Este change implementa la épica 7 (Coloquios, F7.1–F7.5) sobre la base de usuarios y asignaciones ya entregada por C-07, cerrando el ciclo convocatoria → reserva → resultado con trazabilidad multi-tenant.

## What Changes

- **Nuevo modelo `Evaluacion`** (convocatoria): materia, cohorte, tipo (`Parcial`/`TP`/`Coloquio`/`Recuperatorio`), instancia (denominación libre) y ventana de inscripción en días.
- **Nuevo modelo `TurnoEvaluacion`**: día concreto reservable de una convocatoria, con `cupo_total` y cupos derivados. Se introduce para soportar "días disponibles y cupos por día" (FL-07 paso 2, HU-31), que el modelo plano `Evaluacion.dias_disponibles` de la KB §E14 no cubre. Ver Open Questions del design.
- **Nuevo modelo `ReservaEvaluacion`**: reserva de un alumno sobre un turno; estado `Activa`/`Cancelada`. Reservar resta cupo; sin cupo se rechaza; el alumno solo puede tener una reserva activa por convocatoria.
- **Nuevo modelo `ResultadoEvaluacion`**: nota final (numérica o cualitativa) por alumno y convocatoria, para el registro académico consolidado.
- **Nuevo modelo `CandidatoEvaluacion`** (padrón de convocatoria): alumnos habilitados importados a una convocatoria específica (F7.2), separado del padrón general. Solo un candidato habilitado puede reservar.
- **Endpoints `/api/v1/coloquios/*`**: gestión de convocatorias, turnos, importación de candidatos, métricas y registro académico (COORDINADOR/ADMIN/PROFESOR), y reserva/cancelación de turno (ALUMNO).
- **Migración Alembic 012** (`down_revision="011"`): tablas `evaluacion`, `turno_evaluacion`, `candidato_evaluacion`, `reserva_evaluacion`, `resultado_evaluacion`, enums asociados y seed de permisos RBAC.
- **Permisos RBAC**: `coloquios:gestionar` (COORDINADOR, ADMIN, PROFESOR) y `coloquios:reservar` (ALUMNO), fail-closed.

## Capabilities

### New Capabilities
- `evaluacion-convocatoria`: creación, edición, cierre y listado de convocatorias de evaluación (Evaluacion + TurnoEvaluacion), e importación del padrón de candidatos a una convocatoria. Cubre F7.2, F7.3, F7.4, F7.5 (gestión).
- `evaluacion-reserva`: reserva y cancelación de turno por el ALUMNO sobre un turno con cupo, con las reglas de cupo y unicidad de reserva activa. Cubre F7 / FL-07 (reserva).
- `evaluacion-registro`: panel de métricas de coloquios, agenda consolidada de reservas activas y registro académico de resultados finales. Cubre F7.1 y F7.5 (registro/agenda).

### Modified Capabilities
<!-- Ninguna: no cambian requisitos de specs existentes. Las capabilities nuevas consumen asignaciones/usuarios (C-07) y RBAC (C-04) sin modificar sus requisitos. -->

## Impact

- **Código nuevo**: `app/models/evaluacion.py`, `app/repositories/evaluacion_repository.py`, `app/services/evaluacion_service.py`, `app/schemas/evaluacion.py`, `app/api/v1/routers/coloquios.py`; registro del router en el agregador de la API v1; export de modelos en `app/models/__init__.py`.
- **Migración**: nueva `012_create_evaluaciones_coloquios.py` (down_revision="011"); extiende `audit_action` con la acción de auditoría del módulo.
- **RBAC**: nuevos permisos `coloquios:gestionar` y `coloquios:reservar` sembrados por tenant.
- **Dependencias**: `C-07` (usuarios y asignaciones — `Usuario` ALUMNO, `Materia`, `Cohorte`). Sin nuevas dependencias externas.
- **Sin breaking changes**: solo agrega tablas, endpoints y permisos.
