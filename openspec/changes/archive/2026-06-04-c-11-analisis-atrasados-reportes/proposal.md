## Why

C-10 dejó las calificaciones importadas y el campo `aprobado` derivado y persistido, pero todavía no existe ninguna lectura analítica sobre esos datos. El PROFESOR no puede ver quién está atrasado, coordinación no puede monitorear el estado de actividades del tenant y no hay forma de exportar TPs sin corregir ni de producir notas finales. C-11 cierra el tramo de mayor valor del camino crítico (importar → analizar → comunicar): convierte los datos crudos en información accionable que habilita la comunicación con alumnos en riesgo (C-12).

## What Changes

- **Cómputo de alumnos atrasados** (RN-06): un alumno está atrasado si tiene actividades faltantes (sin calificación sobre las actividades seleccionadas) o al menos una nota por debajo del umbral efectivo de la asignación.
- **Ranking de actividades aprobadas** (RN-09): tabla ordenada por cantidad de actividades aprobadas por alumno, excluyendo a quienes no tienen ninguna aprobada.
- **Reportes rápidos por materia** (F2.4): métricas consolidadas (totales de actividades, aprobaciones, atrasados, tasa de aprobación) con estado informativo cuando no hay datos.
- **Notas finales agrupadas** (F2.5): nota final por alumno agrupando las actividades configuradas, lista para exportar.
- **Exportar TPs sin corregir** (F2.6, RN-07/RN-08): endpoint de exportación del listado de entregas textuales finalizadas sin nota. La detección ya existe en `CalificacionService.detectar_sin_corregir` (C-10); C-11 agrega la lectura/exportación bajo `atrasados:ver`.
- **Monitores de seguimiento** (F2.7/F2.8/F2.9): monitor general transversal del tenant (coordinación/admin), monitor de seguimiento por alumnos asignados (tutor/profesor) y la variante coordinación/admin con rango de fechas. Filtros: materia, comisión, regional, alumno, estado de actividad.
- Nuevos endpoints REST bajo `/api/v1/analisis/*`, todos protegidos por `require_permission("atrasados:ver")`.
- Toda la lógica de cómputo vive en un `AnalisisService` (sin SQL en services); las queries de lectura agregada viven en un `analisis_repository.py`.
- **Sin nueva migración de RBAC**: los permisos `atrasados:ver` y `entregas:ver_sin_corregir` ya están seedeados en la migración 003 para TUTOR/PROFESOR/COORDINADOR/ADMIN con sus scopes (`propio`/`global`). C-11 los reutiliza.

## Capabilities

### New Capabilities
- `analisis-academico`: cómputo de alumnos atrasados (RN-06), ranking de actividades aprobadas (RN-09), reportes rápidos por materia y notas finales agrupadas. Lectura derivada sobre `Calificacion` + umbral efectivo, scopeada por tenant y asignación.
- `monitores-seguimiento`: monitores de estado de actividades — general transversal (coordinación/admin), seguimiento de alumnos asignados (tutor/profesor) y variante con rango de fechas (coordinación/admin), con filtros y exportación de TPs sin corregir.

### Modified Capabilities
<!-- Ninguna. C-11 sólo lee datos producidos por calificaciones-ingesta/umbral-aprobacion; no cambia sus requirements. -->

## Impact

- **Backend nuevo**: `app/services/analisis_service.py`, `app/services/atrasados_calculo.py` (función pura RN-06), `app/repositories/analisis_repository.py`, `app/schemas/analisis.py`, `app/api/v1/routers/analisis.py` (registrado en el router v1).
- **Reutiliza sin modificar**: `Calificacion`/`UmbralMateria` (modelos C-10), `CalificacionRepository`, `UmbralService.get_efectivo`, `PadronRepository.get_active_version`, `CalificacionService.detectar_sin_corregir`, `derive_aprobado`, `Asignacion`.
- **RBAC**: reutiliza `atrasados:ver` (scope `propio` para PROFESOR/`global` para COORDINADOR/ADMIN, `global` para TUTOR) y `entregas:ver_sin_corregir`. No requiere migración Alembic.
- **Sin cambios de schema de DB**: C-11 es read-only sobre tablas existentes. No hay nuevas tablas ni columnas.
- **Auditoría**: las exportaciones (TPs sin corregir, notas finales) emiten eventos de auditoría vía `AuditService` siguiendo el patrón de C-10.
- **Frontend / C-12**: habilita las pantallas de análisis y la selección de alumnos atrasados para comunicación (C-12).
