# Pendientes y deuda técnica

> Backlog real verificado contra `master` el **2026-06-10**. Todo lo previo (fixes de enums, teardowns de `audit_event`, impersonación RN-41, scope de `listar_instancias`, etc.) ya está mergeado en master y se removió de este doc por ruido. El historial completo vive en Engram.

---

## Vivo (deuda real)

| # | Ítem | Dónde | Prioridad |
|---|------|-------|-----------|
| 1 | **M3 — página frontend de asignaciones (F4.3)**. El backend `backend/app/api/v1/routers/asignaciones.py` está 100% listo (GET/POST/PATCH/DELETE bajo `equipos:asignar`); falta la feature `frontend/src/features/asignaciones/` + ruta/nav para COORDINADOR/ADMIN. Receta igual a M1/M2 (guardias/perfil), TDD con Vitest. | `frontend/src/features/asignaciones/` (no existe) | BAJA — ya operable embebido en Setup Cuatrimestre |
| 2 | **Aprovisionamiento programático de tenants**. El RBAC se siembra solo vía migraciones, que cubren los tenants existentes al migrar. Un tenant creado después no recibe roles/permisos. No hay servicio de onboarding. Bloqueante para multi-tenant real. | `backend/app/` (sin servicio de provisioning) | MEDIA-ALTA cuando se encare multi-tenant productivo; ligado a C-24 |
| 3 | **RN-11 — jerarquía responsable docente sin validación de ciclo**. `usuario_service` valida que el responsable exista en el tenant, pero no detecta cadenas circulares (A→B→C→A posible) ni `responsable ≠ self`. | `backend/app/services/usuario_service.py`, modelo `Asignacion.responsable_id` | MEDIA |
| 4 | **RN-16 — vista previa de comunicaciones no forzada**. `preview_static()` existe pero el flujo de encolar no obliga a previsualizar antes. Gap de UX, no bug. | `backend/.../comunicaciones.py` (`/preview` vs `/encolar`) | BAJA |

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
