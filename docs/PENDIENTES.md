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
