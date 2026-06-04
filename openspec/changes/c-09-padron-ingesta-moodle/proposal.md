## Why

Sin padrón no hay análisis: el sistema no puede detectar alumnos atrasados ni enviar comunicaciones sin saber quiénes integran cada comisión. C-09 incorpora el padrón versionado de alumnos por materia×cohorte y el primer punto de integración con Moodle, desbloqueando el flujo central de valor del producto (C-10 → C-11 → C-12).

## What Changes

- Nuevos modelos `VersionPadron` y `EntradaPadron` con versionado activo único por `(materia, cohorte)`.
- Importación de padrón desde archivo `.xlsx`/`.csv` con vista previa antes de confirmar (F1.3, F1.4).
- Cliente Moodle Web Services (`integrations/moodle_ws.py`) con sync on-demand + nocturna; errores → `502` con reintento.
- Endpoint para vaciar todos los datos de una materia (F1.5, RN-04).
- Registro de auditoría `PADRON_CARGAR` en cada carga exitosa.
- Migración 007: tablas `version_padron` y `entrada_padron`.
- Seed del permiso `padron:cargar` en la matriz RBAC existente.

## Capabilities

### New Capabilities

- `padron-ingesta`: Gestión versionada del padrón de alumnos por materia×cohorte — carga manual (xlsx/csv), activación (desactiva la anterior), vaciado y consulta. Incluye vista previa de la importación antes de confirmar.
- `moodle-integration`: Cliente de Moodle Web Services — sync de usuarios y actividades on-demand y nocturna; manejo de errores con retry y fallback a carga manual.

### Modified Capabilities

_(ninguna — no hay cambios de requisitos en capabilities existentes)_

## Impact

- **Nuevos archivos**: `backend/app/models/padron.py`, `backend/app/repositories/padron_repository.py`, `backend/app/services/padron_service.py`, `backend/app/api/v1/routers/padron.py`, `backend/app/integrations/moodle_ws.py`, `backend/alembic/versions/007_create_padron.py`.
- **Modificados**: `backend/app/models/__init__.py`, `backend/app/main.py` (registrar router), seed de permisos RBAC (añadir `padron:cargar`).
- **Dependencia externa**: Moodle Web Services API (token por tenant, URL configurable vía `.env`).
- **Tests nuevos**: versionado (activar desactiva anterior), import xlsx/csv, entrada sin `usuario_id`, aislamiento multi-tenant, mock Moodle WS + fallback `502`.
