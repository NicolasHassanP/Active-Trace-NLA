## Why

Los equipos docentes necesitan planificar, registrar y publicar sus encuentros sincrónicos (clases virtuales) y dejar trazabilidad de las guardias de atención a alumnos. Hoy esa planificación vive fuera del sistema (planillas sueltas), sin auditoría ni visibilidad para coordinación. C-13 incorpora el módulo de **encuentros** (recurrentes y únicos, con registro de grabaciones) y el **registro de guardias**, cerrando el flujo FL-06 y habilitando la supervisión global del tenant.

## What Changes

- Nuevos modelos `SlotEncuentro`, `InstanciaEncuentro` y `Guardia` (tenant-scoped, soft delete, identidad UUID), conforme KB §E9, §E10, §E11.
- **Encuentro recurrente** (F6.1, RN-13): crear un slot con día de semana + horario + fecha de inicio + `cant_semanas` genera automáticamente N instancias semanales.
- **Encuentro único** (F6.2): crear una instancia puntual (`fecha_unica`) sin recurrencia (1 instancia).
- **Editar instancia** (F6.3, RN-14): modificar `estado`, `meet_url`, `video_url` (grabación) y `comentario` de una instancia individual, sin afectar al slot ni a otras instancias.
- **Generar bloque HTML para el aula virtual** (F6.4): salida de texto formateado con el calendario de encuentros y sus grabaciones, lista para copiar al LMS (función pura, sin escritura de DB).
- **Vista admin de encuentros** (F6.5): listado transversal de todos los encuentros del tenant para COORDINADOR/ADMIN.
- **Registro de guardias** (F6.6): un TUTOR registra su guardia (materia, carrera/cohorte, día, horario, estado, comentarios); COORDINADOR/ADMIN consultan el registro global filtrado y lo exportan.
- Endpoints `/api/encuentros/*` y `/api/guardias/*` con guard fino `encuentros:gestionar` (fail-closed); identidad y `asignacion_id` derivados del JWT, nunca del request.
- Migración Alembic **011**: tablas `slot_encuentro`, `instancia_encuentro`, `guardia`; nuevos enums; nuevo permiso `encuentros:gestionar`; nuevo código de auditoría.

## Capabilities

### New Capabilities
- `encuentros`: gestión de slots de encuentro (recurrentes y únicos), generación de instancias, edición individual de instancias, vista admin transversal y generación del bloque HTML para el aula virtual (F6.1–F6.5, RN-13, RN-14).
- `guardias`: registro de guardias por parte de tutores y consulta/exportación global por coordinación (F6.6).

### Modified Capabilities
<!-- Ninguna. C-13 introduce capacidades nuevas; consume RBAC, auth, tenancy, auditoría, Asignacion/Materia/Carrera/Cohorte existentes sin cambiar sus requisitos. -->

## Impact

- **Modelos**: nuevo `backend/app/models/encuentro.py` (`SlotEncuentro`, `InstanciaEncuentro`, `Guardia` + enums `dia_semana`, `instancia_encuentro_estado`, `guardia_estado`).
- **Repositories**: `encuentro_repository.py`, `guardia_repository.py`.
- **Services**: `encuentro_service.py` (slots, instancias, edición), `encuentro_recurrencia.py` (generación de fechas — función pura), `encuentro_html.py` (bloque HTML — función pura), `guardia_service.py`.
- **Schemas**: `backend/app/schemas/encuentro.py`, `backend/app/schemas/guardia.py` (todos `extra='forbid'`).
- **Routers**: `backend/app/api/v1/routers/encuentros.py`, `guardias.py`, registrados en el agregador v1.
- **Migración**: `backend/alembic/versions/011_create_encuentros_guardias.py` (`down_revision="010"`).
- **Auditoría**: nuevo código `ENCUENTRO_GESTIONAR` (o equivalente) en el enum `AuditAction`.
- **RBAC**: nuevo permiso `encuentros:gestionar`, seed idempotente por tenant (PROFESOR, COORDINADOR, ADMIN para encuentros; TUTOR para registro de guardias; COORDINADOR/ADMIN para consulta global).
- **Tests**: `_ensure_schema` en `conftest.py` agrega las tres tablas y sus enums.
- **Dependencias**: requiere C-07 (`Usuario`/`Asignacion`) y la estructura académica (`Materia`/`Carrera`/`Cohorte`) de C-06. No toca auth, tenancy, RBAC ni auditoría existentes — solo los consume.
- **Sin frontend** (C-21+). Sin build ni commit automático.
