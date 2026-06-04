## Why

C-07 entregó el CRUD de asignaciones individuales (una `Asignacion` por vez), pero el trabajo real de coordinación es **por equipo**: un COORDINADOR piensa en términos de "el equipo de la materia X en la cohorte Y", no asignación por asignación. Hoy no hay forma de ver el equipo agrupado, asignar varios docentes de una vez, clonar el equipo del cuatrimestre anterior, mover la vigencia de todo el equipo en bloque, ni exportarlo. Además, cada docente necesita su vista propia de "mis equipos" para saber dónde está asignado. Sin estas operaciones, configurar el inicio de un período exige decenas de altas manuales (FL-03), lo que es lento y propenso a error.

## What Changes

- **Vista "mis equipos" (F4.2 / HU-17)**: endpoint de solo lectura que devuelve, para el usuario autenticado, sus asignaciones agrupadas con materia, carrera, cohorte, rol, comisiones, vigencia y `estado_vigencia` derivado (RN-10). Protegido por un permiso de lectura nuevo `equipos:ver`.
- **Consulta de equipo agrupado (F4.3)**: endpoint que lista las asignaciones de un equipo identificado por la tripleta `(materia_id, carrera_id, cohorte_id)`, con filtros por rol y relación de reporte, para COORDINADOR/ADMIN.
- **Asignación masiva (F4.4 / HU-18 / RN-30)**: una operación que asigna N docentes a una combinación `materia × carrera × cohorte × rol` con vigencia y comisiones comunes, admitiendo uno o varios `responsable_id` (RN-11). Atómica: o se crean todas o ninguna.
- **Clonar equipo entre cohortes (F4.5 / HU-19 / RN-12)**: duplica todas las asignaciones vigentes de un equipo origen `(materia, carrera, cohorte)` hacia un destino `(materia, carrera, cohorte)`, reescribiendo las fechas con la vigencia del destino. Devuelve un resumen de cuántas se clonaron.
- **Modificar vigencia general del equipo (F4.6 / HU-20)**: actualiza `desde`/`hasta` de todas las asignaciones de un equipo en una sola operación.
- **Exportar equipo (F4.7)**: genera un archivo descargable (CSV) con docente, rol, materia, carrera, cohorte, vigencia y estado de cada asignación del equipo.
- **Endpoints nuevos** bajo `/api/v1/equipos` (las mutaciones masivas se separan del CRUD unitario de `/asignaciones` para no inflar ese router).
- **Permiso nuevo** `equipos:ver` en el catálogo RBAC (lectura de equipos propios y consulta de equipos). Las mutaciones siguen exigiendo `equipos:asignar` (ya existente). Fail-closed.
- **Acciones de auditoría nuevas** para las operaciones en bloque (asignación masiva, clonación, cambio de vigencia general).

No se introduce ninguna tabla nueva: todo opera sobre el modelo `Asignacion` existente (C-07). No hay migración de schema **salvo** que se confirme OQ-1 (ver Open Questions). No hay cambios BREAKING en `/asignaciones`.

## Capabilities

### New Capabilities
- `equipos-docentes`: operaciones de equipo sobre asignaciones — vista "mis equipos", consulta de equipo agrupado por `(materia, carrera, cohorte)`, asignación masiva, clonación entre cohortes, modificación de vigencia general y exportación. Define el permiso de lectura `equipos:ver` y las acciones de auditoría de las operaciones en bloque.

### Modified Capabilities
<!-- No se modifican requisitos de specs existentes. La capability `asignaciones` (C-07)
     queda intacta: C-08 la consume vía repositorio/servicio pero no cambia sus requisitos.
     El permiso `equipos:asignar` ya existe; `equipos:ver` se agrega en la nueva spec. -->
(ninguna)

## Impact

- **Código nuevo**:
  - `backend/app/api/v1/routers/equipos.py` — router `/api/v1/equipos`.
  - `backend/app/services/equipo_service.py` — lógica de equipo (agrupar, masiva, clonar, vigencia general, export).
  - `backend/app/repositories/usuario_repository.py` — métodos de consulta por tripleta de equipo y operaciones bulk en `AsignacionRepository` (extensión, sin tabla nueva).
  - `backend/app/schemas/equipo.py` — DTOs Pydantic v2 (`extra='forbid'`).
- **Catálogo RBAC**: alta del permiso `equipos:ver` (seed/migración del catálogo de permisos).
- **Catálogo de auditoría**: nuevas acciones `EQUIPOS_ASIGNACION_MASIVA`, `EQUIPOS_CLONAR`, `EQUIPOS_VIGENCIA_GENERAL`.
- **Dependencias**: consume `Asignacion`/`Usuario` (C-07), `Materia`/`Carrera`/`Cohorte` (C-06), `require_permission` y `get_current_user` (C-03/C-04), `AuditRepository` (C-05). No agrega dependencias externas.
- **Sin impacto** en `/asignaciones`, padrón, calificaciones ni comunicaciones.

## Open Questions

> Todas las OQs están CERRADAS — resueltas por el usuario antes del apply.

- **OQ-1 — ¿Entidad `EquipoDocente` materializada o vista derivada?** → **RESUELTA: vista derivada (sin tabla nueva).** Negocio no requiere metadatos a nivel de equipo (notas, estados propios). Una única fuente de verdad en `Asignacion`, sin migración de schema de dominio.
- **OQ-2 — Multi-responsable en la asignación masiva?** → **RESUELTA: responsable único por lote.** Multi-responsable por asignación requiere tabla puente; excede el scope de C-08.
- **OQ-3 — Idempotencia de la clonación?** → **RESUELTA: clonación no-destructiva con skip de duplicados.** Re-clonar omite los ya existentes y reporta `(clonadas, omitidas)`. Estrategia idempotente y segura.
- **OQ-4 — ¿A qué roles se asocia `equipos:ver` en el seed?** → **RESUELTA: roles de gestión (ADMIN, COORDINADOR, FINANZAS) para consulta general de equipos; roles docentes (PROFESOR, TUTOR, NEXO) para la vista "mis-equipos".** La asociación se aplica en la migración del catálogo RBAC.
