## Why

La coordinación académica necesita centralizar dos artefactos que hoy viven dispersos en archivos sueltos y planillas: el **programa oficial** de cada materia (documento por carrera × cohorte) y las **fechas de evaluación** (parciales, TPs, coloquios) por materia × cohorte. Sin un registro único y multi-tenant, el aula virtual del LMS se publica a mano y las fechas quedan desactualizadas. C-06 ya proveyó las entidades raíz (Carrera, Cohorte, Materia), por lo que ahora se puede asociar programas y calendarizar evaluaciones de forma trazable.

## What Changes

- Nuevo modelo `ProgramaMateria`: documento oficial asociado a una combinación materia × carrera × cohorte, con título y `referencia_archivo` (puntero opaco al servicio de almacenamiento, nunca un path de disco).
- Nuevo modelo `FechaAcademica`: instancia evaluativa (Parcial | TP | Coloquio | Recuperatorio) por materia × cohorte × número, con período, fecha y título.
- Nuevos endpoints `/api/v1/programas` (registrar referencia + asociar, listar, baja) bajo `estructura:gestionar`.
- Nuevos endpoints `/api/v1/fechas-academicas` (CRUD completo, listado tabular filtrable y vista calendario) bajo `estructura:gestionar`.
- Generación de un fragmento de contenido (HTML) listo para embeber en el aula virtual del LMS con el calendario de fechas de una materia × cohorte (F5.4).
- Migración `015`: tablas `programa_materia` y `fecha_academica` + enum `fecha_academica_tipo` + acciones de auditoría.

No hay cambios breaking: ambas entidades son aditivas y dependen de tablas ya existentes.

## Capabilities

### New Capabilities
- `programas-materia`: gestión del documento de programa por materia × carrera × cohorte — alta con referencia de archivo opaca, asociación, listado filtrable y baja lógica.
- `fechas-academicas`: gestión y calendarización de fechas de evaluación por materia × cohorte × número — CRUD, listado tabular, vista calendario y generación de fragmento de contenido para el LMS.

### Modified Capabilities
<!-- Ninguna: el permiso estructura:gestionar y las entidades raíz (Carrera/Cohorte/Materia) ya existen desde C-06; este change solo agrega capacidades nuevas. -->

## Impact

- **Modelos**: nuevos `backend/app/models/programa.py` (o `academico.py`) con `ProgramaMateria` y `FechaAcademica`.
- **Migración**: `backend/alembic/versions/015_create_programas_fechas_academicas.py` (la siguiente secuencial tras 014).
- **Capas**: nuevos repositories (tenant-scoped), services y routers siguiendo Routers → Services → Repositories → Models.
- **Schemas**: nuevos Pydantic v2 con `extra='forbid'`.
- **RBAC**: reutiliza el permiso existente `estructura:gestionar` (ADMIN, COORDINADOR) sembrado en migración 005; no crea permisos nuevos.
- **Auditoría**: nuevas acciones `PROGRAMA_GESTIONAR` y `FECHA_ACADEMICA_GESTIONAR` agregadas al enum `audit_action`.
- **Routing**: registro de ambos routers en `backend/app/main.py` con prefijo `/api/v1`.
- **Dependencias**: requiere C-06 (estructura-academica) ya archivado. Consumido más adelante por C-23 (frontend-coordinacion).
