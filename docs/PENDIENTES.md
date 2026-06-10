# Pendientes y deuda técnica

> Backlog real verificado contra `master` el **2026-06-10**. Todo lo previo (fixes de enums, teardowns de `audit_event`, impersonación RN-41, scope de `listar_instancias`, etc.) ya está mergeado en master y se removió de este doc por ruido. El historial completo vive en Engram.

> ### ✅ Cerrados 2026-06-10 (commits f3bd49b · ec147b4 · 5a8b94e · 670d988)
> - **M3 — página frontend de asignaciones (F4.3)**: feature `frontend/src/features/asignaciones/` completa + ruta/nav gateadas a COORDINADOR/ADMIN (`equipos:asignar`). 34 tests Vitest.
> - **RN-11 — jerarquía acíclica de responsable docente**: validación BFS en `usuario_service` (vía `usuario_repository`) que prohíbe auto-referencia y ciclos transitivos en `crear/editar_asignacion`. 7 tests pytest.
> - **RN-16 — vista previa obligatoria de comunicaciones**: gate `previewConfirmed` en `ComposeComunicacion.tsx` (Encolar deshabilitado hasta previsualizar). Enforcement en frontend por diseño (un flag backend sería inverificable; RN-17 cubre la autorización).
> - **Fix colateral**: `ComunicacionesPage` volvía a abrir en tab "Historial" por default sin destinatarios, contra C-27/D5 → restaurado "Componer".

---

## Vivo (deuda real)

| # | Ítem | Dónde | Prioridad |
|---|------|-------|-----------|
| 1 | **Aprovisionamiento programático de tenants**. El RBAC se siembra solo vía migraciones, que cubren los tenants existentes al migrar. Un tenant creado después no recibe roles/permisos. No hay servicio de onboarding. Bloqueante para multi-tenant real. | `backend/app/` (sin servicio de provisioning) | MEDIA-ALTA cuando se encare multi-tenant productivo; ligado a C-24 |

> **Nota**: este único ítem vivo es de governance **CRÍTICO** (multi-tenancy + RBAC) y está atado a **C-24** (diferido por PA-22/23/25). No se codea sin desbloquear esas preguntas y aprobación humana explícita.

---

## 🟠 PLANIFICADO (próxima sesión) — ADMIN scope global + umbral por-materia

> Governance **CRÍTICO** (calificaciones + RBAC scope + migración de datos). Diseño aprobado por el usuario el 2026-06-10. NO empezar sin releer esta sección completa. Implementar con **Strict TDD** y **backend primero** (la migración + el contrato son la fuente de verdad), luego frontend.

### Problema (diagnóstico verificado)
El rol **ADMIN** tiene capacidades GLOBALES sobre cátedra (matriz KB §3.3 / PDF `activia-trace-documentacion.pdf`: importar calificaciones, ver atrasados, enviar comunicaciones, configurar umbral — todas **sin** la anotación "(propio)" = scope `global`). Pero las vistas docentes scopean a "la asignación del propio usuario" e ignoran el scope. Síntomas observados con ADMIN logueado:
- **"Mis materias"** vacío ("No tenés asignaciones") — es `GET /equipos/mis-equipos`, vista docente de *mis* asignaciones; ADMIN no es docente → vacío correcto, pero **no debería ofrecerse** esa vista a ADMIN.
- **Calificaciones → tab Umbral** tira error crudo `No active asignacion found for user in materia f2000002-...` (`backend/app/api/v1/routers/calificaciones.py:223-227`) porque exige una asignación del propio ADMIN.

### Decisión tomada
1. **NO sacarle capacidades a ADMIN.** Mantiene acceso a Calificaciones/Padrón/Atrasados (ejerce el scope global vía el selector de materia que esas páginas ya tienen).
2. El **umbral** pasa de "solo por-asignación" a **default por-materia/cohorte (config de ADMIN, scope global) + override por-asignación del docente**.
3. Solo se **oculta "Mis materias" para ADMIN** (es *mis-asignaciones*; no le quita ninguna capacidad).

### Lo que YA está bien (no tocar, solo verificar)
- El patrón de scope-honoring **ya existe**: `backend/app/services/analisis_service.py` (`_es_scope_global(grant)` → `grant.scope == PermisoScope.global_`). `PermissionGrant.scope` viene de `require_permission(...)`.
- **Atrasados** (`analisis.py`) ya respeta el scope global → ADMIN funciona ahí.
- **Importar calificaciones** (`calificacion_service.py:168-189`) ya maneja `asignacion_id = None` gracefully (verificar que con scope global no exija asignación).
- → **El único endpoint realmente roto es el de umbral (GET + PUT).**

### Backend — cambios
1. **Modelo** `backend/app/models/calificacion.py` (`UmbralMateria`, ~líneas 133-183):
   - `asignacion_id` → **nullable** (NULL = default de materia/cohorte; no-NULL = override del docente).
   - Nueva FK `cohorte_id` → `cohorte(id)` `ON DELETE RESTRICT`, nullable.
2. **Migración Alembic** (UNA sola, regla dura; numerar según la última en `backend/alembic/versions/`):
   - `add_column` `cohorte_id` + FK + índice.
   - `alter_column` `asignacion_id` → nullable.
   - **drop** índice único viejo `uq_um_asignacion_materia`.
   - **create** dos índices únicos **parciales**:
     - `uq_um_default_materia_cohorte` ON `(tenant_id, materia_id, cohorte_id)` WHERE `asignacion_id IS NULL AND deleted_at IS NULL`.
     - `uq_um_asignacion_override` ON `(tenant_id, asignacion_id, materia_id)` WHERE `asignacion_id IS NOT NULL AND deleted_at IS NULL`.
   - Data migration: filas existentes mantienen su `asignacion_id` (se vuelven overrides). Downgrade idempotente (`DROP INDEX IF EXISTS`).
3. **`UmbralService.get_efectivo`**: resolución por precedencia → **(1) override del docente** (`asignacion_id` + `materia_id`) → **(2) default de materia/cohorte** (`asignacion_id IS NULL` + `materia_id` + `cohorte_id`) → **(3) default sistema (60%)**. Devolver flag `is_default` para que el front sepa si está heredando.
4. **`UmbralService.configurar`** + **repository** (`calificacion_repository.py`): nuevo `get_umbral_default(materia_id, cohorte_id)`; el setter resuelve si escribe default (asignacion_id NULL) u override según el scope.
5. **Router `calificaciones.py` GET/PUT `/umbral`**: leer `grant.scope`. Si `global` → operar sobre la materia/cohorte seleccionada **sin exigir asignación** (default de materia). Si `propio` → resolver la asignación del docente (override), como hoy. Tenant SIEMPRE desde JWT. Sumar `cohorte_id` al query/body. Eliminar el `raise 404` con string crudo en inglés → estado manejado.

### Frontend — cambios
1. `frontend/src/features/shell/components/buildNav.ts` — sacar `ADMIN` del item **"Mis materias"** (dejar `['PROFESOR','COORDINADOR']`). NO tocar los demás items de MI CÁTEDRA (ADMIN los sigue usando con scope global).
2. `frontend/src/features/calificaciones/` — tab **"Umbral" dual** según rol/scope (`useAuth().roles`):
   - ADMIN → "Umbral por defecto de la materia/cohorte" (setea default; PUT con `asignacion_id: null`).
   - Docente → "Mi umbral" (override de su asignación; muestra el default heredado cuando `is_default`).
   - Refactor: `UmbralConfig.tsx` → `UmbralConfigDocente.tsx` + nuevo `UmbralConfigDefault.tsx`; hooks `useUmbralDocente` / `useUmbralDefault` / `useConfigurarUmbral*`.

### Strict TDD
- **Backend (pytest, DB real, `create_usuario_con_identidad`)**: precedencia de `get_efectivo` (override → default materia/cohorte → 60%); ADMIN (scope global) lee/escribe default SIN asignación; docente (scope propio) escribe override; 403 sin el permiso; aislamiento por tenant. Safety net: `pytest backend/tests/test_calificaciones*.py -q` antes de tocar.
- **Frontend (vitest)**: tab dual renderiza el componente correcto por rol; ADMIN setea default, docente ve override + default heredado; ocultar "Mis materias" para ADMIN.
- NO correr la suite completa (lento, deja shells en Windows). `tsc --noEmit` 0 errores.

### Decisión abierta menor (resolver al implementar)
Granularidad del default: se acordó **por (materia, cohorte)**. Confirmar si el `cohorte_id` siempre está disponible en el flujo (la página de Calificaciones ya selecciona materia + cohorte → sí).

---

## Mejoras de UX — reemplazar IDs crudos por selectores (follow-up, BAJA)

> Varias UIs todavía piden UUIDs a mano. Ya construimos la pieza base: el endpoint `GET /asignaciones/usuarios?q=` (gateado `equipos:asignar`, no-PII) + el componente `UsuarioCombobox` (frontend/src/features/asignaciones/components/). El alta de asignaciones (`AsignacionForm`) y su tabla ya usan nombre. Falta replicar el patrón en el resto:

**Campos de USUARIO** → reusar `UsuarioCombobox` (el componente se reusa; el endpoint de búsqueda se gatea según el permiso del contexto):
- `frontend/src/features/equipos/components/AsignacionMasivaForm.tsx` — "Usuario IDs separados por coma" → combobox **multi-select** (chips). Mismo endpoint `equipos:asignar`.
- `frontend/src/features/mensajeria/components/NuevoHiloForm.tsx` — "UUID del destinatario" → combobox. **Necesita un endpoint de búsqueda nuevo gateado a `inbox:usar`** (más roles que `equipos:asignar`), no se reusa el de asignaciones.
- Filtros de Tareas — "ID Docente asignado" → combobox de usuario.

**Campos de MATERIA / CARRERA / COHORTE** → `<select>` por nombre (lista acotada, no hace falta búsqueda). Endpoints ya existen: `admin_estructura` GET `/materias`·`/carreras`·`/cohortes` (listas), `perfil` GET `/mis-asignaciones` y `equipos` GET `/mis-equipos` (contexto del usuario). **Patrón de referencia ya implementado: `frontend/src/features/tareas/components/TareaForm.tsx`** (select de materia por nombre + docente del equipo).
- `AsignacionForm` y `AsignacionMasivaForm` — campos Materia/Carrera/Cohorte ID a mano.
- Filtros de Tareas — "ID materia".

---

## QA manual pendiente (rol COORDINADOR)

> Checklist de verificación manual todavía sin cubrir, heredado de la sesión de testeo del 2026-06-07. Las secciones ya testeadas y los bugs encontrados (toast `undefined filas`, búsqueda por `apellidos`, filtros Comisión/Regional, columnas en Seguimiento) ya están fixeados en master. Credenciales demo en `DEMO_BOOTSTRAP.md`.

- **Padrón** (`/padron`): importar CSV real y verificar el conteo del toast; vaciar padrón y confirmar que Seguimiento queda vacío.
- **Atrasados** (`/atrasados`): con calificaciones cargadas, confirmar que aparecen atrasados; seleccionar alumnos y usar "Comunicar a seleccionados"; filtros por comisión y regional.
- **Monitor** (`/monitor`): verificar nombre/apellido (misma fix de Seguimiento); filtros de materia, cohorte, estado.
- **Mensajería** (`/mensajes`): iniciar y responder un hilo; nombre del participante (no UUID); deep link `?hilo=<id>`; badge de campanita suma avisos + mensajes no leídos; animación al recibir mensaje.
- **Equipos docentes** (`/equipos`): asignar tutor/profesor a una comisión y verificar persistencia tras recargar.
- **Encuentros** (`/encuentros`): crear, editar y eliminar un encuentro.
- **Coloquios** (`/coloquios`): crear un coloquio y gestionar inscripciones.
- **Tareas** (`/tareas`): crear una tarea de seguimiento y marcarla completada.
- **Setup cuatrimestre** (`/setup-cuatrimestre`): completar el flujo de setup inicial.
- **Seguridad transversal**: logout + acceso directo a `/padron` → redirige al login; COORDINADOR no accede a rutas `/admin/*`.

---

## Fuera de scope (justificado — no tocar sin cerrar preguntas)

- **C-18 (liquidaciones)** y **C-24 (frontend finanzas/admin)**: diferidos a fin de proyecto, bloqueados por **PA-22/PA-23** (claves de Plus, acumulación) y **PA-25** (semántica NEXO).
- **Estructura académica / catálogo de materias**: bloqueado por **PA-01**, **PA-07**.
- **Nav a 404 intencional**: `/liquidaciones`, `/admin/usuarios`, `/admin/estructura`, `/admin/auditoria` son placeholders deliberados hasta C-18/C-24. No gatear ni "arreglar" sin pedido explícito.
- **RN-28 (CSRF)**: probablemente N/A con auth JWT por header `Authorization` (no cookie). Requiere decisión arquitectónica, no es bug.
