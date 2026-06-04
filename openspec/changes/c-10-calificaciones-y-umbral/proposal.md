## Why

Con el padrón ya disponible (C-09), el siguiente eslabón del flujo central del PROFESOR (FL-02) es traer las **calificaciones** del LMS y poder decidir qué cuenta como aprobado. Sin `Calificacion` ni `UmbralMateria` no hay materia prima para el análisis de atrasados, el ranking ni las comunicaciones (C-11 → C-12). C-10 incorpora el modelo de calificaciones (numéricas y textuales con `aprobado` derivado), el umbral de aprobación configurable por docente y la importación desde el archivo del LMS con vista previa y selección de actividades.

## What Changes

- Nuevo modelo `Calificacion`: nota numérica y/o textual por `(EntradaPadron, materia, actividad)`, campo `aprobado` derivado (RN-01/RN-02/RN-03), `origen` (Importado | Manual) y `importado_at`.
- Nuevo modelo `UmbralMateria`: umbral de aprobación por `Asignacion`×`Materia` (`umbral_pct` defecto 60, `valores_aprobatorios` textuales), aislado por docente (RN-03).
- Importación de calificaciones desde archivo del LMS (F1.1): parser que detecta columnas de actividad **numérica** por el sufijo `(Real)` (RN-01) y columnas **textuales** mapeadas a aprobado (RN-02), con **vista previa** (sin escritura) y **selección de actividades** a incluir.
- Importación del **reporte de finalización** del LMS (F1.2): cruza finalización contra calificaciones para detectar TPs entregados sin nota, solo sobre actividades de escala textual (RN-07/RN-08).
- Configuración del umbral por materia (F2.1, RN-03): el PROFESOR fija `umbral_pct` y los valores textuales aprobatorios para su asignación; defecto 60% si no se ajusta.
- Derivación del campo `aprobado` como lógica de negocio pura: numérica vs. umbral (sobre nota máxima), textual vs. conjunto aprobatorio.
- Registro de auditoría `CALIFICACIONES_IMPORTAR` en cada importación exitosa (RN-23).
- Migración **008**: tablas `calificacion` y `umbral_materia`; seed idempotente de permisos `calificaciones:importar` y `calificaciones:configurar-umbral`; extensión del enum `audit_action` con `CALIFICACIONES_IMPORTAR`.

## Capabilities

### New Capabilities

- `calificaciones-ingesta`: Importación de calificaciones del LMS por materia — parser xlsx/csv con detección de actividades numéricas `(Real)` (RN-01) y textuales aprobatorias (RN-02), vista previa sin escritura, selección de actividades a incluir, persistencia de `Calificacion` con `aprobado` derivado, e importación del reporte de finalización para detectar entregas sin corregir (RN-07/RN-08). Auditoría `CALIFICACIONES_IMPORTAR`. Scope-isolated por `(usuario × materia)` (RN-04).
- `umbral-aprobacion`: Configuración del criterio de aprobación por materia y docente — `UmbralMateria` con `umbral_pct` (defecto 60) y `valores_aprobatorios` textuales, aislado por asignación (no afecta a otros docentes, RN-03), y la regla de derivación del campo `aprobado` de una calificación (numérica vs. umbral, textual vs. conjunto).

### Modified Capabilities

_(ninguna — no cambian requisitos de capabilities existentes; C-10 consume padron-ingesta, RBAC, auditoría y moodle-integration sin modificarlos)_

## Impact

- **Nuevos archivos**: `backend/app/models/calificacion.py` (`Calificacion`, `UmbralMateria`), `backend/app/repositories/calificacion_repository.py`, `backend/app/services/calificacion_aprobado.py` (derivación pura), `backend/app/services/calificacion_parser.py` (detección de columnas RN-01/RN-02), `backend/app/services/calificacion_service.py`, `backend/app/services/umbral_service.py`, `backend/app/api/v1/routers/calificaciones.py`, `backend/alembic/versions/008_create_calificaciones.py`.
- **Modificados**: `backend/app/models/__init__.py` (exportar nuevos modelos), `backend/app/models/audit.py` (`AuditAction.CALIFICACIONES_IMPORTAR`), `backend/app/main.py` o el agregador de routers v1 (registrar `calificaciones`), `backend/tests/conftest.py` (`_ensure_schema` de las nuevas tablas), `.env.example` si se agrega configuración.
- **Dependencias reutilizadas sin modificar**: `EntradaPadron` (C-09) como raíz de cada calificación, `TenantScopedRepository`/`TenantScopedBase` (C-02), `require_permission` + `get_current_user` (C-03/C-04), `AuditService.record` (C-05), `Asignacion`/`Materia` (C-06/C-07), parser xlsx/csv (patrón de C-09).
- **Permisos nuevos**: `calificaciones:importar` (PROFESOR, COORDINADOR, ADMIN), `calificaciones:configurar-umbral` (PROFESOR, COORDINADOR, ADMIN).
- **Tests nuevos**: derivación `aprobado` (numérica ≥ umbral, numérica < umbral, textual en conjunto, textual fuera del conjunto, ambas nulas), detección de columnas `(Real)` (RN-01) y textuales (RN-02), preview sin escritura, selección de actividades, import + persistencia, umbral por asignación que no afecta a otros docentes (RN-03), reporte de finalización detecta entregas sin nota solo en escala textual (RN-08), aislamiento multi-tenant, auditoría `CALIFICACIONES_IMPORTAR`, fail-closed 403/401.
