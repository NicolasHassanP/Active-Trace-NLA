## Why

El rol ALUMNO puede autenticarse pero no tiene una vista propia de su estado académico: el sidebar sólo le ofrece "Avisos" y "Coloquios". La matriz de capacidades ([03 — Actores y Roles](../../../knowledge-base/03_actores_y_roles.md)) le otorga explícitamente "Ver estado académico propio" (`academico:ver_propio`), pero esa capacidad nunca se materializó en un endpoint ni en una pantalla. Sin ella, el alumno no puede consultar sus materias, sus notas, su avance ni sus coloquios reservados dentro de la plataforma. Este change cierra ese gap del roadmap (HU-47 y el contexto ALUMNO de las épicas 2 y 7).

## What Changes

- **Backend — nuevo endpoint** `GET /api/v1/alumno/estado-academico` protegido con `require_permission("academico:ver_propio")`.
  - Devuelve, para el alumno autenticado: materias en las que figura inscripto, sus calificaciones propias (con `aprobado` derivado), estado de entregas (aprobadas / con nota / sin entrega) y un porcentaje de avance por materia y global.
  - Incluye sus coloquios reservados (reservas `Activa`) con materia, instancia, fecha y franja.
  - La identidad (`user_id`, `tenant_id`) se deriva SIEMPRE del JWT — nunca de URL, body ni header. El alumno sólo ve datos cuya `entrada_padron.usuario_id` o `reserva.alumno_id` coincide con su `user_id`.
- **Backend — nueva capa Service + Repository** dedicada al portal del alumno (consultas read-only, sin escritura), respetando el flujo Router → Service → Repository → Model.
- **Frontend — nueva feature** `mi-cursada` con la página `/mi-cursada`, visible SÓLO para el rol ALUMNO.
  - Nuevo grupo de navegación `MI CURSADA` exclusivo del alumno en el catálogo de nav.
  - Muestra: tarjetas KPI de avance, tabla de materias cursadas con notas y estado de entregas, y panel de coloquios reservados.
  - Estados vacíos (`EmptyState`) cuando el alumno aún no tiene materias o coloquios.
  - Sigue el design system del handoff (Manrope, tokens Tailwind, sin `max-w-*` ni `mx-auto` en el wrapper raíz de la página).
- **RBAC**: el permiso `academico:ver_propio` ya existe y está asignado a ALUMNO (`global`) en el seed RBAC; este change lo consume, no lo crea.

No hay cambios que rompan compatibilidad (**no BREAKING**). El endpoint y la pantalla son aditivos.

## Capabilities

### New Capabilities
- `alumno-portal`: El portal del alumno — consulta read-only de su propio estado académico (materias inscriptas, calificaciones propias, estado de entregas, porcentaje de avance y coloquios reservados), expuesta vía un endpoint scoped al JWT y una pantalla `/mi-cursada` exclusiva del rol ALUMNO.

### Modified Capabilities
<!-- Ninguna: no cambian los requirements de capacidades existentes. El permiso academico:ver_propio ya está modelado en el RBAC; este change lo consume. -->

## Impact

- **Backend (nuevo)**:
  - `app/api/v1/routers/alumno.py` — router del portal del alumno.
  - `app/services/alumno_service.py` — orquesta el armado del estado académico.
  - `app/repositories/alumno_repository.py` — queries read-only scoped por tenant + alumno.
  - `app/schemas/alumno.py` — DTOs de respuesta (Pydantic v2, `extra='forbid'`).
  - Registro del router en `app/api/v1/routers/__init__.py`.
- **Backend (lectura, sin modificar)**: `EntradaPadron`, `Calificacion`, `Materia`, `ReservaEvaluacion`, `Evaluacion`, `TurnoEvaluacion`, `UmbralMateria`.
- **Frontend (nuevo)**: feature `features/mi-cursada/` (`pages`, `components`, `hooks`, `services`, `types`).
- **Frontend (modificado)**:
  - `features/shell/components/buildNav.ts` — nuevo ítem y grupo `MI CURSADA` para ALUMNO.
  - `App.tsx` — registro de la ruta `/mi-cursada` con `ProtectedRoute requiredRoles={['ALUMNO']}`.
- **Sin migraciones de schema**: el change es read-only sobre tablas existentes.
- **Dependencias satisfechas**: C-07 (usuarios/asignaciones), C-09 (padrón), C-10 (calificaciones), C-14 (evaluaciones/coloquios), C-21 (frontend shell) — todas archivadas.
